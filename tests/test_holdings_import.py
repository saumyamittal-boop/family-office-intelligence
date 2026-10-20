"""The holdings-file parser: what it accepts, what it explains, and what it refuses. Synthetic data only."""
import io
import zipfile

import openpyxl
import pytest
from openpyxl import Workbook

from fo import holdings_import as hi
from fo.holdings_import import ImportRefused, parse_holdings


def csv_bytes(text: str) -> bytes:
    return text.encode("utf-8")


def xlsx_bytes(rows, hidden_first=False, extra_sheet=None) -> bytes:
    wb = Workbook()
    ws = wb.active
    for r in rows:
        ws.append(r)
    if extra_sheet is not None:
        other = wb.create_sheet("Second")
        for r in extra_sheet:
            other.append(r)
    if hidden_first:
        ws.sheet_state = "hidden"
    out = io.BytesIO()
    wb.save(out)
    return out.getvalue()


def rezip(data: bytes, edit) -> bytes:
    """Copy an xlsx, letting `edit(zipfile_out)` add or replace parts. Used to build hostile workbooks."""
    src = zipfile.ZipFile(io.BytesIO(data))
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as dst:
        for item in src.infolist():
            dst.writestr(item, src.read(item.filename))
        edit(dst)
    return out.getvalue()


GOOD = [["Name", "Asset class", "Account", "Value (Cr)"], ["Fund A", "Large-cap equity", "Demat 1", 10], ["Bonds B", "Debt", "Bank 1", 5.5]]


def messages(parsed, severity="error"):
    return [p.message for p in parsed.problems if p.severity == severity]


# ---- The happy path ---------------------------------------------------------------------------------------------------
def test_the_template_is_a_clean_file_that_covers_every_class():
    p = parse_holdings(hi.TEMPLATE_CSV.encode("utf-8"), "holdings.csv")
    assert p.ok and p.file_kind == "csv" and p.unit == "cr" and len(p.lines) == 6
    assert p.total_cr == pytest.approx(66.25)
    assert {line.asset_class for line in p.lines} == set(hi.CLASSES)
    assert p.columns == {"name": "Name", "asset_class": "Asset class", "account": "Account", "value": "Value (\u20b9 Cr)"}
    assert ("Real estate", "Illiquid", 1) in p.mapped


def test_row_numbers_count_the_header_as_row_one():
    p = parse_holdings(csv_bytes("Name,Class,Value\nA,Debt,1\nB,Debt,-2\n"), "x.csv")
    assert p.errors[0].row == 3 and "Row 3" in p.errors[0].message


@pytest.mark.parametrize("sep", [",", ";", "\t", "|"])
def test_the_delimiter_is_detected(sep):
    text = sep.join(["Name", "Asset class", "Value"]) + "\n" + sep.join(["A", "Gold", "2"]) + "\n"
    assert parse_holdings(csv_bytes(text), "x.csv").ok


def test_a_byte_order_mark_quoted_commas_blank_rows_and_extra_columns_are_fine():
    text = '\ufeffName,Asset class,Value,ISIN,Quantity\n"Fund, Series A",Gold,"1,250.5",INE000,10\n\n,,,,\nB,Debt,3,INE111,5\n'
    p = parse_holdings(text.encode("utf-8"), "x.csv")
    assert p.ok and [l.name for l in p.lines] == ["Fund, Series A", "B"] and p.lines[0].value_cr == 1250.5
    assert any("not used" in m for m in messages(p, "warning")) and p.ignored_columns == ["ISIN", "Quantity"]


@pytest.mark.parametrize("raw,expected", [("\u20b9 1,200.50", 1200.5), ("Rs. 5", 5.0), ("INR 7.25", 7.25), ("1,23,456.5", 123456.5), (".5", 0.5), ("12", 12.0)])
def test_amounts_written_the_indian_way_are_read(raw, expected):
    assert parse_holdings(csv_bytes(f'Name,Class,Value\nA,Debt,"{raw}"\n'), "x.csv").lines[0].value_cr == pytest.approx(expected)


@pytest.mark.parametrize("header,chosen,factor", [("Value (Lakh)", "cr", 0.01), ("Value in INR", "cr", 1e-7), ("Amount \u20b9 Cr", "lakh", 1.0), ("Value", "lakh", 0.01), ("Value", "inr", 1e-7), ("Market Value", "cr", 1.0)])
def test_the_unit_comes_from_the_header_if_it_names_one_otherwise_from_the_choice(header, chosen, factor):
    p = parse_holdings(csv_bytes(f"Name,Class,{header}\nA,Debt,100\n"), "x.csv", unit=chosen)
    assert p.lines[0].value_cr == pytest.approx(100 * factor)


def test_a_bad_unit_is_refused():
    with pytest.raises(ImportRefused):
        parse_holdings(csv_bytes("Name,Class,Value\nA,Debt,1\n"), "x.csv", unit="dollars")


# ---- Classes: fixed list, nothing guessed -----------------------------------------------------------------------------
@pytest.mark.parametrize(
    "label,expected",
    [("Large cap", "Large-cap equity"), ("LARGE-CAP EQUITY", "Large-cap equity"), ("Mid Cap", "Mid-cap equity"), ("Bonds", "Debt"), ("Fixed deposit", "Debt"),
     ("SGB", "Gold"), ("Gold ETF", "Gold"), ("Savings account", "Cash & liquid"), ("cash", "Cash & liquid"), ("Real estate", "Illiquid"), ("Private equity", "Illiquid"),
     ("Cash & liquid", "Cash & liquid"), ("illiquid", "Illiquid")],
)
def test_known_labels_map_to_the_models_classes(label, expected):
    assert parse_holdings(csv_bytes(f"Name,Class,Value\nA,{label},1\n"), "x.csv").lines[0].asset_class == expected


@pytest.mark.parametrize("label", ["Equity", "Small cap", "Crypto", "Misc", "Mutual fund"])
def test_ambiguous_or_unknown_labels_are_errors_not_guesses(label):
    p = parse_holdings(csv_bytes(f"Name,Class,Value\nA,{label},1\nB,{label},2\nC,Debt,3\n"), "x.csv")
    assert not p.ok and p.unrecognised == {label: 2} and [l.name for l in p.lines] == ["C"]
    assert f"\u201c{label}\u201d (2 rows" in messages(p)[0] and "Assign one" in messages(p)[0]


def test_assigning_a_class_resolves_the_label_whatever_its_case_or_spacing():
    data = csv_bytes("Name,Class,Value\nA,Small cap,1\nB,SMALL-CAP,2\n")
    p = parse_holdings(data, "x.csv", class_overrides={"small  cap": "Mid-cap equity"})
    assert p.ok and p.unrecognised == {} and {l.asset_class for l in p.lines} == {"Mid-cap equity"}


def test_an_assignment_to_a_class_the_model_does_not_have_is_refused():
    with pytest.raises(ImportRefused):
        parse_holdings(csv_bytes("Name,Class,Value\nA,Small cap,1\n"), "x.csv", class_overrides={"small cap": "Crypto"})


# ---- Row-level problems -----------------------------------------------------------------------------------------------
@pytest.mark.parametrize("name", ["=HYPERLINK(\"http://x\")", "+1+1", "-cmd", "@SUM(A1)", "=cmd|' /C calc'!A0"])
def test_text_that_spreadsheets_treat_as_a_formula_is_refused_in_names_and_accounts(name):
    safe = name.replace('"', '""')
    for text in (f'Name,Class,Value\n"{safe}",Debt,1\n', f'Name,Class,Account,Value\nA,Debt,"{safe}",1\n'):
        p = parse_holdings(csv_bytes(text), "x.csv")
        assert not p.ok and "formula" in messages(p)[0]


@pytest.mark.parametrize("value,fragment", [("0", "above zero"), ("-5", "above zero"), ("abc", "plain number"), ("1e5", "plain number"), ("inf", "plain number"), ("nan", "plain number"),
                                            ("", "empty"), ("2,000,000", "more than"), ("=SUM(A1:A2)", "formula")])
def test_bad_amounts_say_what_is_wrong(value, fragment):
    p = parse_holdings(csv_bytes(f'Name,Class,Value\nA,Debt,"{value}"\n'), "x.csv")
    assert not p.ok and fragment in messages(p)[0]


def test_empty_names_empty_classes_control_characters_and_long_text_are_errors():
    long = "x" * (hi.MAX_NAME + 1)
    p = parse_holdings(csv_bytes(f'Name,Class,Value\n,Debt,1\nB,,2\n"C\x07",Debt,3\n{long},Debt,4\n'), "x.csv")
    assert len(p.errors) == 4 and not p.lines
    assert any("name is empty" in m for m in messages(p)) and any("asset class is empty" in m for m in messages(p))
    assert any("control character" in m for m in messages(p)) and any("longer than" in m for m in messages(p))


def test_a_repeated_line_is_a_warning_and_still_counts():
    p = parse_holdings(csv_bytes("Name,Class,Account,Value\nA,Debt,X,1\nA,debt,x,1\n"), "x.csv")
    assert p.ok and len(p.lines) == 2 and "repeats row 2" in messages(p, "warning")[0]


def test_a_second_value_column_is_ignored_with_a_note():
    p = parse_holdings(csv_bytes("Name,Class,Value (Cr),Value (Lakh)\nA,Debt,1,100\n"), "x.csv")
    assert p.ok and p.lines[0].value_cr == 1 and any("already supplies" in m for m in messages(p, "warning"))


def test_a_missing_column_is_refused_and_names_the_columns_found():
    with pytest.raises(ImportRefused, match="needs a column for asset class") as why:
        parse_holdings(csv_bytes("Name,Value\nA,1\n"), "x.csv")
    assert "\u201cName\u201d" in str(why.value)


def test_a_header_with_no_rows_is_an_error_and_so_is_an_empty_file():
    assert not parse_holdings(csv_bytes("Name,Class,Value\n"), "x.csv").ok
    with pytest.raises(ImportRefused):
        parse_holdings(b"", "x.csv")
    with pytest.raises(ImportRefused):
        parse_holdings(csv_bytes("\n,,\n"), "x.csv")


def test_problems_are_capped_and_say_so():
    rows = "".join("A,Debt,-1\n" for _ in range(hi.MAX_PROBLEMS + 25))
    p = parse_holdings(csv_bytes("Name,Class,Value\n" + rows), "x.csv")
    assert len(p.errors) == hi.MAX_PROBLEMS + 1 and "25 more problems" in p.errors[-1].message


# ---- Whole-file refusals ----------------------------------------------------------------------------------------------
def test_size_row_and_column_limits():
    with pytest.raises(ImportRefused, match="larger than"):
        parse_holdings(b"Name,Class,Value\n" + b"A,Debt,1\n" * 20000, "x.csv")
    with pytest.raises(ImportRefused, match="more than 1,000 rows"):
        parse_holdings(csv_bytes("Name,Class,Value\n" + "A,Debt,1\n" * (hi.MAX_ROWS + 1)), "x.csv")
    assert parse_holdings(csv_bytes("Name,Class,Value\n" + "A,Debt,1\n" * hi.MAX_ROWS), "x.csv").ok
    with pytest.raises(ImportRefused, match="columns"):
        parse_holdings(csv_bytes(",".join(f"c{i}" for i in range(hi.MAX_COLUMNS + 1)) + "\n1\n"), "x.csv")


@pytest.mark.parametrize(
    "data,name,fragment",
    [(b"MZ\x90\x00binary", "x.csv", "not plain text"), (bytes(range(256)) * 3, "x.csv", "not plain text"), (b"\xff\xfeN\x00a\x00", "x.csv", "UTF-8"),
     (b"a,b", "x.pdf", "Only .csv"), (b"a,b", "noextension", "Only .csv"), (b"a,b", "x.exe", "Only .csv"), (b"PK\x03\x04junk", "x.csv", "archive"),
     (b"not a zip", "x.xlsx", "not a real Excel"), (b"\xd0\xcf\x11\xe0junk", "x.xlsx", "old-style"), (b"\xd0\xcf\x11\xe0junk", "x.csv", "old-style"), (b"x", "x.xls", ".xls")],
)
def test_wrong_kinds_of_file_are_refused_in_plain_words(data, name, fragment):
    with pytest.raises(ImportRefused, match=fragment):
        parse_holdings(data, name)


def test_a_refusal_never_echoes_the_files_contents():
    secret = b"SECRET-MARKER-9f3a"
    for data, name in ((secret + b"\x00\x01", "x.csv"), (b"PK\x03\x04" + secret, "x.xlsx"), (secret, "x.exe"), (secret + b"\xff\xfe", "x.csv")):
        try:
            parse_holdings(data, name)
        except ImportRefused as why:
            assert secret.decode() not in str(why)


def test_the_columns_found_message_shows_only_a_short_clean_version_of_the_header_names():
    long_header = "h" * 200
    bell = chr(7)
    with pytest.raises(ImportRefused) as why:
        parse_holdings(csv_bytes(long_header + ",Stray" + bell + "Name" + chr(10) + "1,2" + chr(10)), "x.csv")
    message = str(why.value)
    assert "h" * 41 not in message and chr(0x2026) in message and bell not in message and len(message) < 300


@pytest.mark.parametrize("raw,expected", [("C:\\Users\\me\\holdings.csv", "holdings.csv"), ("../../etc/passwd.csv", "passwd.csv"), ("a\x07b.csv", "ab.csv"), ("", "holdings")])
def test_filenames_are_reduced_to_a_safe_display_name(raw, expected):
    assert hi.safe_filename(raw) == expected
    assert len(hi.safe_filename("x" * 500)) <= 80


# ---- Excel ------------------------------------------------------------------------------------------------------------
def test_an_excel_file_is_read_like_a_csv_file():
    p = parse_holdings(xlsx_bytes(GOOD), "h.xlsx")
    assert p.ok and p.file_kind == "xlsx" and [l.value_cr for l in p.lines] == [10.0, 5.5] and p.lines[0].account == "Demat 1"


def test_only_the_first_visible_sheet_is_read():
    data = xlsx_bytes([["junk"]], hidden_first=True, extra_sheet=GOOD)
    assert [l.name for l in parse_holdings(data, "h.xlsx").lines] == ["Fund A", "Bonds B"]


def test_a_formula_in_a_cell_is_an_error_and_is_never_evaluated():
    rows = [GOOD[0], ["Fund A", "Debt", "X", "=1+1"], ["Fund B", "Debt", "=HYPERLINK(\"http://x\")", 3]]
    p = parse_holdings(xlsx_bytes(rows), "h.xlsx")
    assert not p.ok and any("formula" in m for m in messages(p)) and len(p.errors) == 2


def test_numbers_dates_and_booleans_in_cells_are_handled():
    import datetime as dt
    rows = [GOOD[0], [dt.date(2026, 1, 1), "Debt", "X", 4], ["B", "Debt", "X", True], ["C", "Gold", None, 7.0]]
    p = parse_holdings(xlsx_bytes(rows), "h.xlsx")
    assert [l.name[:10] for l in p.lines] == ["2026-01-01", "C"] and any("not a number" in m for m in messages(p))


def test_excel_files_with_macros_links_objects_or_unsafe_paths_are_refused():
    base = xlsx_bytes(GOOD)
    cases = {
        "macros": lambda z: z.writestr("xl/vbaProject.bin", b"vba"),
        "macro sheets": lambda z: z.writestr("xl/macrosheets/sheet1.xml", b"<x/>"),
        "links": lambda z: z.writestr("xl/externalLinks/externalLink1.xml", b"<x/>"),
        "activex": lambda z: z.writestr("xl/activeX/activeX1.xml", b"<x/>"),
        "embedded": lambda z: z.writestr("xl/embeddings/oleObject1.bin", b"ole"),
        "path": lambda z: z.writestr("../evil.xml", b"x"),
    }
    for label, edit in cases.items():
        with pytest.raises(ImportRefused):
            parse_holdings(rezip(base, edit), "h.xlsx")


def test_a_macro_enabled_content_type_is_refused():
    def edit(z):
        z.writestr("[Content_Types].xml", zipfile.ZipFile(io.BytesIO(xlsx_bytes(GOOD))).read("[Content_Types].xml").replace(b"spreadsheetml.sheet.main", b"ms-excel.sheet.macroEnabled.main"))
    # replacing a part twice makes a duplicate name; build the workbook directly instead
    src = zipfile.ZipFile(io.BytesIO(xlsx_bytes(GOOD)))
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as dst:
        for item in src.infolist():
            body = src.read(item.filename)
            if item.filename == "[Content_Types].xml":
                body = body.replace(b"</Types>", b'<Override PartName="/xl/x.xml" ContentType="application/vnd.ms-excel.sheet.macroEnabled.main+xml"/></Types>')
            dst.writestr(item, body)
    with pytest.raises(ImportRefused, match="macros"):
        parse_holdings(out.getvalue(), "h.xlsx")


def test_a_zip_bomb_is_refused_before_anything_is_expanded():
    with pytest.raises(ImportRefused, match="unsafe"):
        parse_holdings(rezip(xlsx_bytes(GOOD), lambda z: z.writestr("xl/bomb.bin", b"0" * 5_000_000)), "h.xlsx")
    with pytest.raises(ImportRefused, match="far more data"):
        parse_holdings(rezip(xlsx_bytes(GOOD), lambda z: [z.writestr(f"xl/pad{i}.bin", bytes(range(256)) * 3000) for i in range(12)]), "h.xlsx")
    with pytest.raises(ImportRefused, match="too many"):
        parse_holdings(rezip(xlsx_bytes(GOOD), lambda z: [z.writestr(f"xl/p{i}.xml", b"<x/>") for i in range(hi.XLSX_MAX_PARTS + 1)]), "h.xlsx")


def test_an_xml_entity_bomb_inside_the_sheet_is_refused():
    bomb = (b'<?xml version="1.0"?><!DOCTYPE d [<!ENTITY a "aaaaaaaaaa"><!ENTITY b "&a;&a;&a;&a;&a;&a;&a;&a;&a;&a;">'
            b'<!ENTITY c "&b;&b;&b;&b;&b;&b;&b;&b;&b;&b;">]><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>&c;</sheetData></worksheet>')
    src = zipfile.ZipFile(io.BytesIO(xlsx_bytes(GOOD)))
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as dst:
        for item in src.infolist():
            dst.writestr(item, bomb if item.filename == "xl/worksheets/sheet1.xml" else src.read(item.filename))
    with pytest.raises(ImportRefused, match="could not be read"):
        parse_holdings(out.getvalue(), "h.xlsx")


def test_excel_import_switches_itself_off_if_the_xml_safety_package_is_missing(monkeypatch):
    monkeypatch.setattr(openpyxl.xml, "DEFUSEDXML", False)
    with pytest.raises(ImportRefused, match="safety package"):
        parse_holdings(xlsx_bytes(GOOD), "h.xlsx")
    assert parse_holdings(csv_bytes("Name,Class,Value\nA,Debt,1\n"), "x.csv").ok  # CSV never needed it


def test_a_corrupt_workbook_gets_a_plain_message():
    broken = rezip(xlsx_bytes(GOOD), lambda z: None).replace(b"worksheets/sheet1.xml", b"worksheets/sheetX.xml")
    with pytest.raises(ImportRefused):
        parse_holdings(broken, "h.xlsx")


# ---- Identity of the data ---------------------------------------------------------------------------------------------
def test_the_fingerprint_ignores_file_format_row_order_and_letter_case_but_not_values():
    a = parse_holdings(xlsx_bytes(GOOD), "h.xlsx")
    b = parse_holdings(csv_bytes("Value (Cr),Name,Asset class,Account\n5.5,bonds b,debt,bank 1\n10,fund a,Large-cap equity,demat 1\n"), "h.csv")
    c = parse_holdings(csv_bytes("Name,Asset class,Account,Value (Cr)\nFund A,Large-cap equity,Demat 1,10\nBonds B,Debt,Bank 1,5.6\n"), "h.csv")
    assert a.fingerprint() == b.fingerprint() != c.fingerprint()
