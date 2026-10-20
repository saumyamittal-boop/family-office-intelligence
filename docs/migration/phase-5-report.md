# Phase 5 report: Holdings import and consolidation

**Date**: 2026-10-20 · **Branch**: `react-migration` (Phases 1 to 4 are committed; Phase 5 is **not committed yet**, as agreed: commit only when asked) ·
**State**: built and verified by tests, deliberate breakages and a real-browser pass with a real server. Nothing is pushed. **The approval gate for this phase is "Verify importing a
statement, the consolidated view and the explicit step that changes a profile"**: the numbers are checked against hand calculations and the engine; the wording, the look and what the
import accepts are yours to review. **Synthetic files only**: no real family statement has been used, and none should be until the privacy gate is passed.

## What was built

| Area | Delivered |
|---|---|
| Holdings page | Choose a CSV or Excel (`.xlsx`) file, pick the unit (crore, lakh, rupees; a unit named in the value column's heading wins), download a template. Before anything is stored the page shows the columns it used, every line, totals by asset class, how each label was read, and every problem |
| Unknown labels | A label the model does not know (plain "Equity", "Small cap") is never guessed: the person assigns one of the six classes from a list, and the file is read again with that choice |
| Import | Named import (defaults to the file name); the same data cannot be imported twice into one profile; up to 20 imports and 5,000 lines per profile; imports can be listed and deleted (two clicks) |
| Consolidated view | Totals by asset class (donut, or table), by account, the five largest holdings with the same name added across accounts, and a comparison with the profile's own holdings and corpus |
| Using the holdings | **"Use these holdings in my profile"** is a separate step with a before-and-after table and an optional tick to set the corpus too. Looking changes nothing; the same rules as the profile editor apply; analysis results are recalculated afterwards |
| Dashboard | Module 8, **Holdings consolidation**, can now be chosen like the other seven (glance size on the dashboard, full size on the Holdings page) |
| New API | `GET /api/holdings/template` and, under `/api/profiles/{id}/`: `holdings/preview`, `holdings/imports` (create, list, delete), `holdings/consolidation`, `holdings/apply/preview`, `holdings/apply`. Migration `003` adds `holding_imports` and `holdings` (cascade from the profile and the user). The file itself is **not** stored: only the parsed lines and a hash of them |

## Evidence

| Check | Result |
|---|---|
| Python suite | **521 passed** (390 before this phase). New: the parser (89), the API (41), plus updated database, contract and dashboard tests. No stall |
| Web suite | **518 tests in 23 files** passed, twice in a row (486 in 22 before); type check clean; production build succeeds at 951 KB of JavaScript (283 KB gzipped; 933 KB / 278 KB after Phase 4) |
| Hostile files | Tests build real `.xlsx` files and refuse each: macros, external links, ActiveX, embedded objects, path traversal in the zip, a macro-enabled content type, a zip bomb, too many parts, an XML entity bomb, and a run with the safe XML parser switched off (the importer then refuses to start). CSV: formula injection (`= + - @`), over the row, column and size limits, a UTF-16 file (with advice to save as UTF-8), bad numbers |
| Isolation | Another account's profile answers 404 for every holdings route; a second profile of the same account does not see the first's imports; a request cannot name a user; CSRF and JSON-only are enforced; the 61st request in a minute gets 429 |
| Numbers | Consolidation totals equal hand calculations; the unit conversions (crore, lakh, rupees) are exact; **after "use these holdings", the engine's own `current.weights_total` equals the imported shares** (end to end through the real analysis endpoint) |
| Mutation checks | Seven deliberate breakages were each caught by a test, then reverted: formula check removed, lakh worth ten times too much, row limit effectively off, ownership check using the wrong user, duplicate import no longer refused, the apply preview saving the profile, the corpus tick doing nothing. An eighth ("apply skips the profile rules") was *equivalent* (the builder already returns no profile when a rule fails), so it proved nothing and is not counted |
| Accessibility (axe, WCAG 2.2 AA) | The Holdings page empty, with a file chosen and problems shown, with the lines open, with imported data and the apply card, with the delete confirmation open, and the dashboard with module 8: zero violations in light and dark (six new audits in each theme) |
| Real-browser pass | Against a real server and a throwaway database: opened the demo family, chose a CSV with an unknown label ("Equity"), saw the problem and the class picker, assigned a class, imported (7 holdings, ₹1,000 Cr), read the consolidated tables, used the holdings in the profile (the dashboard then recalculated: liquidity cover went from a gap to 3.9x, as the imported mix is more liquid), put module 8 on the dashboard, uploaded a real `.xlsx` whose heading said "(Lakh)" (450,000 lakh became ₹4,500 Cr), uploaded a CSV with a formula and bad numbers (three plain-language problems, import disabled). No console errors; no sideways overflow at 375 px |

## Design in one paragraph

The browser sends the file as JSON (base64) and the server parses it **twice**: once for the preview (stores nothing) and again on import, so the preview is a convenience and never the thing trusted.
Excel is inspected as a zip before it is opened, then read with the safe XML parser, values only (a formula cell is a problem, never evaluated). Labels map through a short fixed synonym list; anything else is the person's decision.
Holdings belong to a family profile. Consolidation is calculated when asked, not stored. Changing a profile is the separate "use these holdings" step, validated by the same code as the editor and shown as before and after first.
Full reasoning and the alternatives not taken: [ADR-0020](../adr/0020-holdings-import-and-consolidation.md).

## Changes to existing code

| File | Change | Effect on numbers |
|---|---|---|
| `fo/holdings_import.py` (new), `api/holdings_*.py`, `api/routers/holdings.py`, migration `003` | The parser, the schemas, the store, the service and the routes (ADR-0020) | none: new, and they only read or write holdings |
| `api/deps.py`, `api/main.py`, `api/dashboard.py` | A shared `throttle` helper, the new router and rate limit, module 8 now available | none |
| `requirements-api.txt` | `openpyxl 3.1.5`, `defusedxml 0.7.1`, `et-xmlfile 2.0.0` (pinned; API only, the Streamlit app does not use them) | none |
| `web/` | Holdings page, import flow, consolidation view, apply card, module 8, API hooks; the donut can label its centre and share column differently | none |
| `web/vite.config.ts`, `web/src/test/setup.ts` | Test waits lengthened (below) | none |
| `fo/engine.py` and the other engine files | **untouched** | none |

## Findings

1. **The browser pass found four wording and flow faults the tests had not.** (a) The donut for imported holdings said "total corpus" in its centre and "Share of corpus" in its table, but the whole is the imported total: now it says "imported total" and "Share of imported". (b) A matching total read "(+₹0.0 Cr)": now "(the same)".
   (c) A problem message said "Assign one below" while the class picker sat above it: the problems now come first. (d) A file with nothing usable offered "Import 0 holdings (₹0.0 Cr)" (disabled): now "Nothing to import yet". Each has a test.
2. **Whole-app tests were failing at random under load, never the same ones.** Different tests timed out on each full run (axe audits and whole-page renders against the 5-second default, and lookups against the 1-second default) and passed when re-run; the machine also runs other work. I did not treat that as acceptable noise:
   the test timeout is now 20 seconds and the async-lookup wait 4 seconds. This only lengthens how long a test may wait; no assertion changed, and a passing test is not slower. The full suite then passed twice in a row.
3. **Applying holdings can change the safety picture a lot.** The demo "liquidity gap" family stops having a gap once its holdings are replaced by a more liquid statement. That is correct (the engine did what it was told), and it is why the apply step shows before and after and is never automatic.
4. **A profile's holdings and an imported total can disagree.** The default is to apply the imported *shares* to the profile's own corpus, with a note when the totals differ by more than 0.5%; setting the corpus to the imported total is a tick the person chooses.
5. **Still true and still open.** The liquidity-cover requirement never limits the mix (the model is unchanged and the screens say so). Zero spending with no commitment in the safety-net window still divides by zero in the protected engine; the API refuses it with a clear message.

## Not done and not verified

- **Visual review is yours.** The browser pane was hidden, so I could not take screenshots. I checked the structure, the numbers, the sizes and the overflow through the page, and ran scripted input; I did not see the page by eye.
- **No real statement has been used** and none should be before the privacy gate. Real broker and bank files differ (merged cells, several sheets, totals rows, notes above the header); only the first visible sheet is read, the header must be the first non-empty row, and a totals row would be counted as a holding. The importer refuses what it cannot read rather than guessing, and says why; adapting it to real layouts is the work of a later phase, with permission.
- **Only `.xlsx` and `.csv`.** Not `.xls`, PDF or a pasted table. No price feed, no cost basis, no gains: this phase is "what do we hold and where", not performance.
- **No fuzzy matching of names.** "HDFC Bank" and "HDFC Bank Ltd" are two holdings. The largest-holdings table adds only identical names.
- **Hosting.** The new libraries must be installed wherever the API runs; the deployment notes (Phase 7) should list them. The upload limit is per request (256 KB body) and the rate limit is per process.
- **No Playwright end-to-end run yet** (Phase 7); a keyboard-only run by a person is still to do.

## Decisions needed before Phase 6

1. Review the Holdings page and the new dashboard module in both themes, at desktop and phone width, and say what to change (especially the wording of the problems and the "use these holdings" step).
2. Approve the commit of Phase 5 to `react-migration` (not pushed).
3. Approve Phase 6 (the assistant). It is the first phase that sends text to an outside language model, so the privacy gate applies again: what may be sent, and nothing from imported holdings unless you say so.
4. Open from before: push the branch?; the liquidity-cover fix; the "In a severe market crash" wording; the target-customer decision with the mentor on Saturday 24 October.

## Run it

See the README section "React + FastAPI version". Start the API and `npm run dev`, open http://localhost:5173, choose a demo family and open **Holdings** from the menu. Use **Download a template** to get a file in the right shape,
or make your own with columns Name, Asset class, Account and Value. Use synthetic data only.
