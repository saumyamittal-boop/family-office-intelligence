# Phase 2 report: Design system, navigation and overview

**Date**: 2026-10-19 · **Branch**: `react-migration` (Phase 1 is committed as `88fae33`; Phase 2 is **not committed**; nothing is pushed; `main` is untouched) ·
**State**: built and verified by tests, DOM checks and, at the end, a first visual look (the Browser pane had been hidden until then). **The approval gate for this phase is "Review UI": it is yours** (see "Not verified").

## What was built

| Area | Delivered |
|---|---|
| Design tokens | `styles/tokens.css`: colour, type, space and shape for light and dark; Inter is self-hosted (no external requests) |
| Themes | Light, dark, or match my device; no flash on load; the choice is saved in this browser; blocked storage is handled |
| App shell | Collapsible sidebar (icons only when collapsed, a drawer on small screens), top bar, skip link, landmarks; the chosen family and cover basis live in the address |
| Components | Button, Card, StatTile, Badge, Banner, SegmentedControl, Select, TextField, DataTable, loading/empty/error states, SidePanel, Menu, IconButton |
| Charts (Recharts) | Allocation donut, projection, upcoming outflows, scenario comparison. Each has a one-sentence text alternative and a Chart/Table switch |
| Overview page | Always-visible warnings, four headline numbers with "About" panels, allocation, action plan, projection, outflows, scenario comparison, reasons, insights |
| Resilience | Error boundaries around the app, each page and each chart |
| Placeholders | Seven navigation pages are honest "Not built yet" pages with their phase and no invented numbers |

No Python, API or database file changed in this phase (the engine, API and Streamlit app are exactly as committed in Phase 1).

## Evidence

| Check | Result |
|---|---|
| Web tests | **167 passed in 12 files** (24 at the end of Phase 1); type check clean; production build succeeds |
| Colour contrast (tokens) | 64 checks pass in both themes: text at least 4.5:1; borders, focus ring, brand and every chart colour at least 3:1 |
| Colour contrast (real browser) | 157 to 184 rendered text and SVG-label elements scanned in the running app: **0 failures in light and 0 in dark** |
| Automated accessibility (axe-core, WCAG 2.2 AA) | 14 audits pass with zero violations: sign-in, sign-in with an error, overview as charts, overview as tables, open explanation panel, navigation drawer, error and placeholder pages, each in both themes. A further test feeds it broken markup and confirms it reports all four planted problems |
| Wording vs the model | The assumptions and haircuts quoted in the "About" panels are compared with the frozen Python golden master |
| Keyboard, real browser | First Tab lands on the skip link with a 3 px focus ring; the explanation panel opens as a named dialog, Escape closes it, and focus returns to the exact button that opened it |
| Sidebar, real browser | Collapses to exactly 72 px with icon-only links and names kept for screen readers; the choice survives a reload |
| Theme, real browser | The menu switches the page, the saved value, the colour scheme and the button label; body colours equal the tokens exactly |
| Mobile (375 px) | No horizontal scroll; the sidebar becomes a hamburger; theme and sidebar choices survive a reload; the drawer opens as a dialog with all 8 links |
| Reload | Signed in again after a reload (the Streamlit app cannot do this) |

### Tests migrated, not dropped
The Foundation page was replaced, so its nine tests were moved to the new UI with the same intent: sign-in screen, demo family opens on the stricter cover,
log-in button disabled until filled and server errors shown, server unreachable, optimiser warning names the portfolio, no warning when clean, switching
portfolios, shortfall flagged in the comparison with the basis named, illiquid shown as fixed. Fifteen more were added around them.

## Findings during the phase

1. **A render error blanked the whole app.** My own browser run hit it (a chart crashed during hot-reloading) and the page went white. Fixed with error
   boundaries at three levels and tested; the console later showed a boundary catching a real render error and the app carrying on.
2. **Focus was lost after closing a panel** (WCAG 2.4.3): the panels are opened by ordinary buttons, so Radix did not know where to return focus. A test caught it; fixed.
3. The scenario chart told "held" from "short" by green versus rust only. Colour-blind users could not rely on that, so the bar's value label now says "short" in words.
4. Vitest's `css: false` setting silently blanked a `?raw` CSS import, so my first contrast test parsed an empty file. Fixed by letting only the tokens file through.
5. Two of my test expectations were wrong, not the app: one a rounding sum (162.7 correctly shows as 163) and several over-broad queries.
6. **Bundle size**: 830 KB of JavaScript, 250 KB gzipped, mostly Recharts. Fine for local use and a pilot; route-level code splitting is a later optimisation.
7. The Browser pane was hidden, so animations and transitions do not run in it. That produced one false contrast failure (a button frozen mid-fade) and a "drawer off-screen" reading. Both were proven to be artefacts by switching transitions off.

8. **A first visual look, at the end, found five layout problems that no test could** (fixed, with tests where a test makes sense): the fourth headline tile
   wrapped alone onto a second row (the grid is now 2 columns, 4 when wide, 1 when narrow); the greeting showed a long machine-made demo username (now "Welcome to
   the demo" and "Demo family"); buy and sell rows used chevron icons (now plus and minus); amounts broke across lines at "−" / "₹" and "₹1,500" / "Cr" (a helper now
   keeps them together); and the scenario chart's value labels were misplaced for negative bars (they are now placed from the bar's geometry).

## Not done and not verified

- **Only part of the UI has been seen by me.** I saw the light theme at desktop and tablet width (overview top, charts, scenario chart, expanded sidebar). Dark mode,
  the phone layout and the open panels were checked by measurement (colours, overflow, focus, behaviour) but my screenshots of them came out as partial frames, so
  they are visually unreviewed. Spacing and balance are my judgement, not yours. That is the point of the "Review UI" gate: please run it and look (README:
  "React + FastAPI version"; light and dark; a phone-width window).
- The drawer's slide-in animation and the sidebar's width animation were not seen running.
- Colour-blindness was handled by design (words, icons, patterns) but not simulated.
- Chart exploration by keyboard is limited to the table view; the charts themselves are described, not navigable point by point.
- No Playwright browser tests yet (Phase 7). Theme and sidebar are remembered per browser; per-account preferences come with the dashboard (Phase 4).
- The personalised dashboard, guided plan, analyst workspace, holdings import and assistant are not built.

## Decisions needed before Phase 3

1. **Review the UI** (both themes, desktop and phone) and say what to change.
2. Approve committing Phase 2 to `react-migration` (nothing is committed yet).
3. Two modelling decisions that the guided plan will expose to families, so they should be settled before Strategy A, B and C are rebuilt:
   - **"In a crash like 2020"** is really the stylised Market-crash preset. Recommendation: relabel it "In a severe market crash" and show its assumptions in an "About" panel.
   - **The liquidity-cover requirement never binds** for the demo families. Recommendation for now: keep the model unchanged, keep reporting the cover as a check, and have the screens say it does not shape the mix (the panel already does).
4. Phase 3 will need new API endpoints for the guided plan and profile creation. Confirm that is in scope for Phase 3, as in the plan.

## Run it

See the README section "React + FastAPI version". Short form: `uvicorn api.main:app --port 8100`, then `npm run dev` in `web/`, then open http://localhost:5173 and pick a demo family.
