# Holdings import: file format and rules

The Holdings page reads a statement the person already has (a CSV or Excel file), shows exactly what was read, and only then stores it. Using
the imported holdings in a family profile is a separate, explicit step. **Use synthetic files only until the readiness checks in
[production-readiness.md](production-readiness.md) are met.** Decision record: [ADR-0020](adr/0020-holdings-import-and-consolidation.md).

This feature reads a file the person uploads. It does not connect to any bank, broker, depository or aggregator, and it does not fetch prices.
A sample file is served by `GET /api/holdings/template` (also a button on the page).

## The file

| Rule | Value |
|---|---|
| Types | `.csv` (UTF-8) or `.xlsx`. Old `.xls`, macro-enabled workbooks, archives and anything else are refused. |
| Size | 150 KB at most; 1,000 data rows; 30 columns. The upload also has to fit the API's body limit (`FO_API_MAX_BODY_KB`, default 256 KB). |
| Header | The first non-empty row, matched by name, ignoring case, spaces and punctuation. |
| Sheet | For Excel, the first visible sheet only. At most 20,000 physical rows are scanned. |

Three columns are required:

| Column | Accepted headings (examples) | Notes |
|---|---|---|
| Name | Name, Holding, Instrument, Security, Scheme, Fund, Stock, Particulars … | Up to 80 characters. |
| Asset class | Asset class, Class, Category, Type … | Matched to one of the model's six classes (below). |
| Value | Value, Amount, Market value, Current value, Valuation, Balance … | A plain number: digits with an optional decimal point. A leading `₹`, `Rs`, `INR` and thousands commas are removed. Must be above zero and at most 1,000,000 crore. |

Optional: **Account** (Account, Custodian, Bank, Broker, Demat, Folio, Portfolio, Holder, Entity, Owner, Platform), up to 60 characters. Columns for
date, quantity, units, price, NAV, ISIN, symbol, notes, serial numbers and similar are accepted and ignored, and the page says which were not used.
If two columns could supply the same thing, the first is used and the other is reported as ignored.

### Units

The page asks for the unit (rupees crore, lakh or rupees). **A unit named in the value column's heading wins** over the page's choice: `Value (₹ Cr)`
reads as crore, `Amount in lakh` as lakh, `Value (INR)` as rupees. Everything is stored in crore (1 crore = 100 lakh = 10,000,000 rupees).

### Asset classes

Labels are matched after lower-casing and dropping spaces and punctuation:

| Model class | Labels recognised (besides its own name) |
|---|---|
| Large-cap equity | large cap, blue chip, Nifty 50, large-cap fund / stocks |
| Mid-cap equity | mid cap, mid-cap fund / stocks |
| Debt | bonds, fixed income, FD, fixed deposit, G-Sec, government securities, debt fund, NCD, corporate bonds, debentures |
| Gold | gold ETF, SGB, sovereign gold bond, physical gold, gold fund |
| Cash & liquid | cash, liquid, savings, savings account, liquid fund, money market, bank balance, current account, cash equivalents |
| Illiquid | real estate, property, private equity, unlisted equity, business, family business, land, venture capital, art, unlisted |

**A label that is not on the list is never guessed.** A bare "Equity" is ambiguous between large and mid cap, so it is reported as an
error and the person assigns a class for that label in the preview. Assigned classes apply to that import only.

## What is refused or flagged

- **Refused outright** (nothing is read): wrong or disguised file type, empty file, too big, too many rows or columns, a missing required column,
  and for Excel: macros, ActiveX or embedded objects, links to other workbooks, path tricks in the archive, too many internal parts, data that
  expands more than 200 times or beyond 8 MB when unpacked, and an unsafe-XML condition (`defusedxml` rejects XML bombs and external entities;
  if that package is missing the server refuses to read Excel files at all).
- **Row errors** (the import is blocked until fixed): empty name or class, value missing, not a number, zero or negative, too large, text
  containing control characters, a cell that starts with `=`, `+`, `-` or `@` where text is expected (a possible spreadsheet formula), an
  unknown class label. At most 200 errors are listed.
- **Warnings** (do not block): ignored columns; an identical row repeated (same name, class, account and value), where both are counted.

## What is stored, and what the server does

1. **Preview** (`POST …/holdings/preview`): the server parses the file and returns what it found. Nothing is stored.
2. **Import** (`POST …/holdings/imports`): the server **parses the file again** (it never trusts the preview) and stores the lines only if nothing
   blocks it. The same data cannot be imported twice into one profile; the fingerprint is a hash of the sorted lines, so it matches whatever the
   file format or row order. The file itself is not kept: only its name, kind, unit, SHA-256 and the confirmed lines.
3. **Consolidation** (`GET …/holdings/consolidation`): totals by asset class and by account, the five largest positions (the same name held in
   several accounts is added together), and a comparison with the profile's current shares.
4. **Apply** (`POST …/holdings/apply`, previewed first by `…/apply/preview`): sets the profile's holding **shares** to the imported shares, and
   with the box ticked also sets the corpus to the imported total. The profile must still pass the usual profile rules afterwards (for example
   illiquid holdings at most 95%); otherwise the change is refused and nothing is saved. Nothing else ever changes a profile from an import.

Imports are listed and deleted from the page (two clicks); deleting an import never changes a profile that already used it.

Every route is limited to the signed-in account (`holdings_user`, 60 per minute) and another account's profile answers 404.

## Limits to keep in mind

- Values are taken as given. There is no price lookup, no currency conversion, no corporate-action handling and no reconciliation against a
  custodian; "value" is whatever the person's file says.
- The file is held in memory while parsed; the size, row and unpacked-size limits are what keep that bounded.
- The checks are tested with generated hostile files (`tests/test_holdings_import.py`, `tests/test_security_review.py`); they have not been
  reviewed by an outside security specialist.
