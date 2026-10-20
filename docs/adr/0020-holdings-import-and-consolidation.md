# ADR-0020: Holdings import and consolidation

**Date**: 2026-10-20
**Status**: accepted (Phase 5, design written before the build)
**Deciders**: Project owner (asked to continue with Phase 5 in the same session; synthetic files only), facilitated by Claude
**Builds on**: [ADR-0017](0017-react-fastapi-migration.md) and [ADR-0019](0019-personalised-dashboard-and-analyst-workspace.md)

## Context

Holdings are typed in today as one percentage per asset class. A family with several accounts has statements, not percentages. The owner wants to import them from
CSV or Excel, see them consolidated by asset class, and (only if they choose) use that as the profile's holdings. This is the first feature that accepts a file, and the
files may one day hold real family data, so the privacy gate applies: this phase is built and tested on synthetic files only. The engine does not change.

## Decision

1. **A file is never trusted until the server has parsed it.** The browser sends the file as JSON (`filename`, base64 `content`), so the API's JSON-only guard and request-size limit stay in force.
   Limits: 150 KB per file, 1,000 rows, 30 columns, 20 imports and 5,000 lines per profile. The preview and the final import both parse the file again on the server.
2. **Preview, then confirm.** `POST .../holdings/preview` stores nothing and returns the rows read, the labels it mapped, blocking errors and warnings. `POST .../holdings/imports`
   re-parses and stores only if there are no errors. Importing the same data twice into one profile is refused (hash of the parsed rows, so a CSV and an Excel file with the same content match).
3. **Excel is read defensively.** The zip is inspected before openpyxl opens it: too many parts, too much uncompressed data, a very high compression ratio, macros, ActiveX, embedded objects or external links are all refused.
   The sheet is opened read-only without evaluating anything; a formula cell is an error ("paste values"). Excel import refuses to run at all if `defusedxml` is missing.
4. **Spreadsheet-formula injection.** Text that starts with `=`, `+`, `-` or `@` is an error in name and account columns. React escapes text on screen, and nothing is exported.
5. **Plain, visible mapping.** Headers are matched against a fixed synonym list; the preview shows which columns were found. Asset-class labels map to the model's six classes through a fixed list (for example Bonds -> Debt, SGB -> Gold,
   Real estate -> Illiquid). A label that is not on the list, or is ambiguous (plain "Equity", "Small cap"), is an error until the person assigns a class to it in the preview. Nothing is guessed.
6. **Amounts.** One value column, read as rupees crore unless the header names a unit (`value_lakh`, `value_inr`) or the person picks one. Values must be finite, above zero and at most 1,000,000 crore.
7. **Storage.** Migration `003`: `holding_imports` and `holdings`, both cascading from the profile and the account, and every query carries the account id taken from the session. Holdings belong to a family profile, not to an account.
8. **Consolidation** is computed on demand from the stored lines: totals and shares by class and by account, the largest positions with the same name added up across accounts, and a comparison with the profile.
9. **Using the holdings in the profile is a separate, explicit action** with a before-and-after view. It replaces only the profile's holding shares (and the corpus, only if the person ticks that box), runs the same validation as the profile editor,
   and is refused with a reason if it fails (for example illiquid holdings above 95%). Nothing changes a profile silently.
10. **The dashboard's eighth module, Holdings consolidation, becomes selectable**; with no import yet it shows an empty state that links to the Holdings page.

## Alternatives Considered

### Alternative 1: Multipart file upload
- **Pros**: Normal for files, no base64 growth.
- **Cons**: Needs a second body path around the API's JSON-only and size guard.
- **Why not**: At 150 KB the base64 cost is trivial and the guard stays whole.

### Alternative 2: Let the person map columns and classes freely, guessing the rest
- **Pros**: Accepts messy files.
- **Cons**: A guessed class silently changes the allocation the model sees.
- **Why not**: A fixed list plus explicit assignment for anything else keeps every mapping visible.

### Alternative 3: Parse in the browser
- **Pros**: No upload.
- **Cons**: Duplicates validation in TypeScript, and the server must re-check anyway.
- **Why not**: One parser, on the server.

## Consequences

### Positive
- Statements can be brought in without retyping, and the result is auditable line by line.
- The riskiest input path in the app is small, bounded and tested against hostile files.

### Negative
- Only one amount column and one sheet are read. Quantity and price columns are ignored.
- Two new packages (openpyxl, defusedxml), pinned in `requirements-api.txt` only; the Streamlit app's requirements are untouched.

### Risks
- Real statements will use labels the list does not know. The preview makes that a quick assignment, but the list will grow with use.
- Real data is out of scope until the owner clears the privacy gate: encryption at rest and retention rules come first.
