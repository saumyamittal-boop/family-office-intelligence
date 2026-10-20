"""Read a holdings file (CSV or Excel) into validated lines. Pure Python: no web code, so it can be tested on its own.

The file is untrusted. Nothing in it is ever evaluated, executed or echoed back unbounded, and nothing is guessed:
an asset-class label that is not on the fixed list is an error until the person assigns a class to it (see ADR-0020).

`parse_holdings` returns what was read plus a list of problems. `ImportRefused` means the whole file is unusable; its
message is always safe to show.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import re
import zipfile
from dataclasses import dataclass, field

from .data import ASSET_CLASSES
from .personas import ILLIQUID

CLASSES: tuple[str, ...] = tuple(ASSET_CLASSES) + (ILLIQUID,)
UNIT_TO_CRORE = {"cr": 1.0, "lakh": 0.01, "inr": 1e-7}
UNIT_LABEL = {"cr": "rupees crore", "lakh": "rupees lakh", "inr": "rupees"}

MAX_FILE_BYTES = 150 * 1024
MAX_ROWS = 1000
MAX_COLUMNS = 30
MAX_NAME = 80
MAX_ACCOUNT = 60
MAX_VALUE_CR = 1_000_000.0
MAX_PROBLEMS = 200
MAX_HEADER_ECHO = 40
SCAN_LIMIT = 20_000  # physical sheet rows looked at in an Excel file, blank or not
XLSX_MAX_PARTS = 100
XLSX_MAX_UNCOMPRESSED = 8 * 1024 * 1024
XLSX_MAX_RATIO = 200


class ImportRefused(Exception):
    """The whole file cannot be used. The message is written for the person and never contains file content."""


@dataclass(frozen=True)
class Line:
    row: int
    name: str
    asset_class: str
    value_cr: float
    account: str = ""


@dataclass(frozen=True)
class Problem:
    severity: str  # "error" blocks the import; "warning" does not
    message: str
    row: int | None = None
    field: str | None = None


@dataclass
class Parsed:
    file_kind: str
    unit: str
    columns: dict[str, str]
    ignored_columns: list[str]
    lines: list[Line]
    problems: list[Problem]
    mapped: list[tuple[str, str, int]] = field(default_factory=list)  # label as written, class it maps to, rows
    unrecognised: dict[str, int] = field(default_factory=dict)  # label -> rows
    rows_read: int = 0

    @property
    def errors(self) -> list[Problem]:
        return [p for p in self.problems if p.severity == "error"]

    @property
    def ok(self) -> bool:
        return not self.errors and bool(self.lines)

    @property
    def total_cr(self) -> float:
        return math.fsum(line.value_cr for line in self.lines)

    def fingerprint(self) -> str:
        """The same data gives the same fingerprint whatever the file format or row order."""
        rows = sorted(f"{l.name.casefold()}|{l.asset_class}|{l.account.casefold()}|{l.value_cr:.6f}" for l in self.lines)
        return hashlib.sha256(json.dumps(rows).encode("utf-8")).hexdigest()


# ---- What the columns and labels may be called ------------------------------------------------------------------------
def _key(text: object) -> str:
    return re.sub(r"[^a-z0-9]", "", str(text).replace("₹", " inr ").casefold())


NAME_HEADERS = {"name", "holding", "holdings", "instrument", "security", "scheme", "asset", "assetname", "description",
                "particulars", "fund", "fundname", "stock", "scrip", "holdingname"}
CLASS_HEADERS = {"assetclass", "class", "category", "type", "assettype", "classification", "assetcategory"}
ACCOUNT_HEADERS = {"account", "accountname", "custodian", "bank", "broker", "demat", "folio", "portfolio", "holder",
                   "entity", "owner", "platform"}
IGNORED_HEADERS = {"asof", "date", "quantity", "qty", "units", "price", "nav", "isin", "symbol", "ticker", "notes",
                   "remarks", "comment", "comments", "sno", "srno", "no", "sr"}
VALUE_BASES = ("value", "amount", "marketvalue", "currentvalue", "valuation", "balance", "currentamount")

_SYNONYMS: dict[str, tuple[str, ...]] = {
    "Large-cap equity": ("largecap", "largecapequity", "largecapstocks", "equitylargecap", "largecapfund", "bluechip", "nifty50", "largecaps"),
    "Mid-cap equity": ("midcap", "midcapequity", "midcapstocks", "equitymidcap", "midcapfund", "midcaps"),
    "Debt": ("debt", "bonds", "bond", "fixedincome", "fd", "fixeddeposit", "fixeddeposits", "gsec", "governmentsecurities",
             "debtfund", "ncd", "corporatebond", "corporatebonds", "debentures"),
    "Gold": ("gold", "goldetf", "sgb", "sovereigngoldbond", "goldbond", "physicalgold", "goldfund"),
    "Cash & liquid": ("cash", "liquid", "cashliquid", "cashandliquid", "savings", "savingsaccount", "liquidfund",
                      "moneymarket", "bankbalance", "currentaccount", "cashequivalents"),
    "Illiquid": ("illiquid", "realestate", "property", "privateequity", "unlistedequity", "business", "familybusiness",
                 "land", "venturecapital", "art", "unlisted"),
}
CLASS_SYNONYMS: dict[str, str] = {_key(c): c for c in CLASSES}
for _cls, _names in _SYNONYMS.items():
    for _n in _names:
        CLASS_SYNONYMS[_n] = _cls

TEMPLATE_CSV = (
    "Name,Asset class,Account,Value (₹ Cr)\r\n"
    "Sample large-cap fund,Large-cap equity,Demat A,12.5\r\n"
    "Sample mid-cap fund,Mid-cap equity,Demat A,6\r\n"
    "Sample government bonds,Debt,Bank B,18.25\r\n"
    "Sample gold ETF,Gold,Demat A,3\r\n"
    "Sample savings balance,Cash & liquid,Bank B,4.5\r\n"
    "Sample office building,Real estate,,22\r\n"
)


def _value_unit(header: str) -> tuple[bool, str | None]:
    """(is this a value column, the unit its header names or None). 'Value', 'Value (Cr)', 'Amount in lakh' ..."""
    k = _key(header)
    for base in VALUE_BASES:
        if k.startswith(base):
            rest = k[len(base):]
            if rest == "":
                return True, None
            if "lakh" in rest or "lac" in rest:
                return True, "lakh"
            if "cr" in rest:
                return True, "cr"
            if "inr" in rest or "rs" in rest or "rupee" in rest:
                return True, "inr"
            return False, None
    return False, None


# ---- Cell clean-up ----------------------------------------------------------------------------------------------------
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_FORMULA_START = ("=", "+", "-", "@")


def _echo(text: object, limit: int = MAX_HEADER_ECHO) -> str:
    s = _CONTROL.sub("", " ".join(str(text).split()))
    return s if len(s) <= limit else s[: limit - 1] + "…"


def _cell_text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    return " ".join(str(value).replace(" ", " ").split())


class _BadCell(Exception):
    pass


def _text_field(value: object, limit: int) -> str:
    raw = "" if value is None else str(value)
    if _CONTROL.search(raw):
        raise _BadCell("contains a control character")
    s = _cell_text(value)
    if s and s.startswith(_FORMULA_START):
        raise _BadCell("starts with =, +, - or @, which spreadsheets treat as a formula")
    if len(s) > limit:
        raise _BadCell(f"is longer than {limit} characters")
    return s


def _amount(value: object) -> float:
    if isinstance(value, bool):
        raise _BadCell("is not a number")
    if isinstance(value, (int, float)):
        x = float(value)
    else:
        s = _cell_text(value)
        if s.startswith("="):
            raise _BadCell("is a formula; paste the value instead")
        s = re.sub(r"(?i)^(₹|rs\.?|inr)\s*", "", s).replace(",", "").replace(" ", "")
        if not re.fullmatch(r"-?(\d+(\.\d*)?|\.\d+)", s):
            raise _BadCell("is not a plain number (use digits, with an optional decimal point)")
        x = float(s)
    if not math.isfinite(x):
        raise _BadCell("is not a finite number")
    return x


# ---- Reading the two file types ---------------------------------------------------------------------------------------
Rows = list[tuple[int, list[object]]]


def _file_kind(data: bytes, filename: str) -> str:
    ext = ("." + filename.rsplit(".", 1)[-1].casefold()) if "." in filename else ""
    if ext == ".xls":
        raise ImportRefused("Old .xls files are not accepted. Save the sheet as .xlsx or as a CSV file and upload that.")
    if ext not in (".csv", ".txt", ".tsv", ".xlsx"):
        raise ImportRefused("Only .csv and .xlsx files are accepted.")
    is_zip = data[:4] == b"PK\x03\x04"
    if data[:4] == b"\xd0\xcf\x11\xe0":
        raise ImportRefused("That is an old-style Office file. Save it as .xlsx or CSV and upload that.")
    if ext == ".xlsx":
        if not is_zip:
            raise ImportRefused("That file is named .xlsx but is not a real Excel workbook.")
        return "xlsx"
    if is_zip:
        raise ImportRefused("That file is an archive, not a CSV file.")
    return "csv"


UTF8_HELP = "The file is not UTF-8 text. In Excel use Save As > CSV UTF-8, then upload that."


def _read_csv(data: bytes) -> Rows:
    if data[:2] in (b"\xff\xfe", b"\xfe\xff"):  # UTF-16, which Excel's "Unicode Text" export produces
        raise ImportRefused(UTF8_HELP)
    if b"\x00" in data:
        raise ImportRefused("That file is not plain text. Save it as a CSV file and upload that.")
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise ImportRefused(UTF8_HELP) from None
    first = next((line for line in text.splitlines() if line.strip()), "")
    delimiter = max(",;\t|", key=lambda d: first.count(d)) if first else ","
    if first.count(delimiter) == 0:
        delimiter = ","
    rows: Rows = []
    try:
        for number, record in enumerate(csv.reader(io.StringIO(text, newline=""), delimiter=delimiter), start=1):
            if number > SCAN_LIMIT:
                raise ImportRefused("The file has too many rows.")
            rows.append((number, list(record)))
    except csv.Error:
        raise ImportRefused("The file could not be read as CSV. Check for stray quotation marks.") from None
    return rows


def _check_zip(data: bytes) -> None:
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile:
        raise ImportRefused("That is not a valid Excel workbook.") from None
    with archive:
        parts = archive.infolist()
        if len(parts) > XLSX_MAX_PARTS:
            raise ImportRefused("That Excel file has too many internal parts.")
        if sum(p.file_size for p in parts) > XLSX_MAX_UNCOMPRESSED:
            raise ImportRefused("That Excel file expands to far more data than a holdings list needs.")
        names = {p.filename for p in parts}
        for part in parts:
            name = part.filename.casefold()
            if name.startswith("/") or ".." in name.split("/"):
                raise ImportRefused("That Excel file is not safe to read.")
            if part.file_size > 1_000_000 and part.compress_size and part.file_size / part.compress_size > XLSX_MAX_RATIO:
                raise ImportRefused("That Excel file contains data compressed in an unsafe way.")
            if name.endswith("vbaproject.bin") or name.startswith(("xl/macrosheets/", "xl/dialogsheets/")):
                raise ImportRefused("Excel files with macros are not accepted. Save a copy without macros (.xlsx) and upload that.")
            if name.startswith(("xl/activex/", "xl/embeddings/")):
                raise ImportRefused("Excel files with embedded objects are not accepted.")
            if name.startswith("xl/externallinks/"):
                raise ImportRefused("Excel files that link to other workbooks are not accepted. Paste the values and upload again.")
        if "[Content_Types].xml" not in names or "xl/workbook.xml" not in names:
            raise ImportRefused("That is not a valid Excel workbook.")
        content_types = archive.read("[Content_Types].xml")
        if b"macroEnabled" in content_types:
            raise ImportRefused("Excel files with macros are not accepted. Save a copy without macros (.xlsx) and upload that.")


def _read_xlsx(data: bytes) -> Rows:
    _check_zip(data)
    import openpyxl  # imported here so the CSV path works without it

    if not getattr(openpyxl.xml, "DEFUSEDXML", False):
        raise ImportRefused("Excel import is switched off on this server because a safety package is missing. Use a CSV file.")
    rows: Rows = []
    workbook = None
    try:
        workbook = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=False, keep_links=False)
        sheet = next((s for s in workbook.worksheets if getattr(s, "sheet_state", "visible") == "visible"), None)
        if sheet is None:
            raise ImportRefused("That workbook has no visible sheet.")
        for number, record in enumerate(sheet.iter_rows(values_only=True), start=1):
            if number > SCAN_LIMIT:
                raise ImportRefused("The first sheet is too long. Keep only the holdings on it.")
            rows.append((number, list(record)))
    except ImportRefused:
        raise
    except Exception:  # noqa: BLE001 - whatever openpyxl objects to, the person only needs to know it could not be read
        raise ImportRefused("That Excel file could not be read. Save it as a plain .xlsx or CSV file and try again.") from None
    finally:
        if workbook is not None:
            workbook.close()
    return rows


# ---- Putting it together ----------------------------------------------------------------------------------------------
def safe_filename(name: str) -> str:
    base = re.split(r"[\\/]", name or "")[-1]
    return _echo(base, 80) or "holdings"


def _assign_columns(header: list[object], unit_choice: str) -> tuple[dict[str, tuple[int, str]], list[str], str, list[Problem]]:
    roles: dict[str, tuple[int, str]] = {}
    ignored: list[str] = []
    notes: list[Problem] = []
    unit = unit_choice
    for index, cell in enumerate(header):
        text = _cell_text(cell)
        if not text:
            continue
        k = _key(text)
        role = None
        is_value, header_unit = _value_unit(text)
        if is_value:
            role = "value"
        elif k in NAME_HEADERS:
            role = "name"
        elif k in CLASS_HEADERS:
            role = "asset_class"
        elif k in ACCOUNT_HEADERS:
            role = "account"
        if role is None:
            ignored.append(_echo(text))
        elif role in roles:
            ignored.append(_echo(text))
            notes.append(Problem("warning", f"Column “{_echo(text)}” was ignored because “{roles[role][1]}” already supplies the {role.replace('_', ' ')}.", None, role))
        else:
            roles[role] = (index, _echo(text))
            if role == "value" and header_unit:
                unit = header_unit
    return roles, ignored, unit, notes


def parse_holdings(data: bytes, filename: str, unit: str = "cr", class_overrides: dict[str, str] | None = None) -> Parsed:
    """Parse and validate. `unit` is used unless the value column's header names one. Raises ImportRefused for an unusable file."""
    if unit not in UNIT_TO_CRORE:
        raise ImportRefused("The unit must be rupees crore, rupees lakh or rupees.")
    overrides: dict[str, str] = {}
    for label, target in (class_overrides or {}).items():
        if target not in CLASSES:
            raise ImportRefused("An assigned asset class is not one the model uses.")
        overrides[_key(label)] = target
    if not data:
        raise ImportRefused("The file is empty.")
    if len(data) > MAX_FILE_BYTES:
        raise ImportRefused(f"That file is larger than {MAX_FILE_BYTES // 1024} KB. A holdings list should be much smaller.")

    kind = _file_kind(data, safe_filename(filename))
    rows = _read_xlsx(data) if kind == "xlsx" else _read_csv(data)
    rows = [(n, r) for n, r in rows if any(_cell_text(c) for c in r)]
    if not rows:
        raise ImportRefused("The file has no data in it.")
    (_, header), body = rows[0], rows[1:]
    if len([c for c in header if _cell_text(c)]) > MAX_COLUMNS or len(header) > 4 * MAX_COLUMNS:
        raise ImportRefused(f"The file has more than {MAX_COLUMNS} columns.")
    if len(body) > MAX_ROWS:
        raise ImportRefused(f"The file has more than {MAX_ROWS:,} rows.")

    roles, ignored, unit_used, notes = _assign_columns(header, unit)
    missing = [label for role, label in (("name", "name"), ("asset_class", "asset class"), ("value", "value")) if role not in roles]
    if missing:
        found = ", ".join(f"“{_echo(c)}”" for c in header if _cell_text(c)) or "none"
        raise ImportRefused(f"The file needs a column for {', '.join(missing)}. Columns found: {found}.")

    factor = UNIT_TO_CRORE[unit_used]
    problems: list[Problem] = list(notes)
    lines: list[Line] = []
    labels: dict[str, list] = {}  # key -> [label as first written, class or None, rows]
    first_seen: dict[tuple, int] = {}
    capped = 0

    def add(severity: str, message: str, row: int | None, field_name: str | None) -> None:
        nonlocal capped
        if severity == "error" and sum(1 for p in problems if p.severity == "error") >= MAX_PROBLEMS:
            capped += 1
            return
        problems.append(Problem(severity, message, row, field_name))

    def cell(record: list[object], role: str) -> object:
        index = roles[role][0] if role in roles else None
        return record[index] if index is not None and index < len(record) else None

    for number, record in body:
        bad = False
        values: dict[str, object] = {}
        for role, limit in (("name", MAX_NAME), ("account", MAX_ACCOUNT)):
            if role not in roles:
                values[role] = ""
                continue
            try:
                values[role] = _text_field(cell(record, role), limit)
            except _BadCell as why:
                add("error", f"Row {number}: the {role} {why}.", number, role)
                bad = True
        if not bad and not values["name"]:
            add("error", f"Row {number}: the name is empty.", number, "name")
            bad = True

        label = _cell_text(cell(record, "asset_class"))
        resolved = None
        if not label:
            add("error", f"Row {number}: the asset class is empty.", number, "asset_class")
            bad = True
        else:
            key = _key(label)
            resolved = overrides.get(key) or CLASS_SYNONYMS.get(key)
            entry = labels.setdefault(key, [_echo(label), resolved, 0, number])
            entry[2] += 1

        amount = None
        try:
            raw_value = cell(record, "value")
            if _cell_text(raw_value) == "":
                raise _BadCell("is empty")
            amount = _amount(raw_value) * factor
            if amount <= 0:
                raise _BadCell("must be above zero")
            if amount > MAX_VALUE_CR:
                raise _BadCell(f"is more than {MAX_VALUE_CR:,.0f} crore")
        except _BadCell as why:
            add("error", f"Row {number}: the value {why}.", number, "value")
            bad = True

        if not bad and resolved is not None and amount is not None:
            account = str(values["account"])
            identity = (str(values["name"]).casefold(), resolved, account.casefold(), round(amount, 6))
            if identity in first_seen:
                add("warning", f"Row {number} repeats row {first_seen[identity]} (same name, class, account and value). Both are counted.", number, None)
            else:
                first_seen[identity] = number
            lines.append(Line(number, str(values["name"]), resolved, amount, account))

    unrecognised = {entry[0]: entry[2] for entry in labels.values() if entry[1] is None}
    for entry in labels.values():
        if entry[1] is None:
            add("error", f"“{entry[0]}” ({entry[2]} row{'s' if entry[2] != 1 else ''}, first at row {entry[3]}) is not an asset class the model knows. Assign one below.", entry[3], "asset_class")
    if capped:
        problems.append(Problem("error", f"…and {capped} more problems. Fix these first and upload again.", None, None))
    if not body:
        problems.append(Problem("error", "The file has a header but no holdings under it.", None, None))
    mapped = [(entry[0], entry[1], entry[2]) for entry in labels.values() if entry[1] is not None]
    if ignored:
        problems.append(Problem("warning", "Columns not used: " + ", ".join(f"“{c}”" for c in ignored[:8]) + ("…" if len(ignored) > 8 else "") + ".", None, None))

    return Parsed(
        file_kind=kind, unit=unit_used, columns={role: label for role, (_, label) in roles.items()}, ignored_columns=ignored,
        lines=lines, problems=problems, mapped=mapped, unrecognised=unrecognised, rows_read=len(body),
    )
