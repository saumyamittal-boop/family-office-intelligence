# ADR-0019: Personalised dashboard and analyst workspace

**Date**: 2026-10-19
**Status**: accepted (Phase 4)
**Deciders**: Project owner (approved decision D8: dashboard preferences per account, default four modules), facilitated by Claude
**Builds on**: [ADR-0017](0017-react-fastapi-migration.md) and [ADR-0018](0018-guided-plan-api-and-live-recalculation.md)

## Context

The overview was one fixed page. The master prompt asks for a dashboard of eight modules from which each person picks exactly four,
puts them in the order they want, and finds them again after signing out, alongside deeper analyst pages for risk, liquidity,
scenarios and the family profile. Two rules came with it: a critical warning must never be hidden by someone's choice of modules,
and the financial engine must not change.

## Decision

1. **Eight modules, seven built.** Allocation and actions, Liquidity and commitments, Risk exposure, Stress scenarios, Net worth and
   projection, Historical performance, Why this recommendation, and Holdings consolidation. The last needs the holdings import (Phase 5),
   so the server lists it but marks it unavailable, refuses it in a save, and the picker shows it as "arrives in phase 5".
2. **The server knows ids, not words.** `api/dashboard.py` holds the module ids, which are ready, and the default four (allocation,
   liquidity, risk, stress). Titles, summaries and layouts live in the web app (`web/src/modules/catalog.ts`). The ids travel as a
   typed list in the API contract, so a module added on one side and not the other fails the type check.
3. **One choice per account** (D8): table `dashboard_preferences(user_id, modules, updated)` from numbered migration `002`, deleted with
   the account (so a demo copy's choice goes when the copy expires). `GET`, `PUT` and `DELETE /api/dashboard`. A save must name exactly four
   different available modules; anything else is refused and nothing is stored. A stored value that is no longer valid reads as the
   default instead of breaking the page. The user id always comes from the session.
4. **Pick by slot, not by drag.** The customise panel has four slots, each a labelled list of modules. Choosing a module already in
   another slot swaps the two, so there are always four different ones. Move up and Move down reorder. A preview shows the layout,
   and a list says where every module lives. This works with a keyboard and a screen reader and needs no drag library.
5. **Every module has two sizes.** On the dashboard a module is a glance in one card with a link to its full page. On the analyst pages
   (Recommendation, Risk and liquidity, Scenarios) the same module is drawn in full. A module that is not on the dashboard is therefore
   one click away, and the dashboard lists where.
6. **Warnings do not depend on the choice.** The attention bar and the four headline tiles are drawn from the analysis, above the modules,
   whatever is chosen. A test runs seven different choices and requires the liquidity warning in each. A module that fails to draw, or
   whose data cannot be fetched, shows its own error and leaves the rest of the page alone.
7. **New read-only endpoints, no new maths.** `GET /api/profiles/{id}/history` returns value and drawdown curves for the current mix and
   the three options. `POST /api/profiles/{id}/scenarios` applies one built-in or custom scenario to all four. Both reuse the cached
   engine results (the analysis cache now keeps the portfolios as well as the response), so neither runs the optimiser again. The analysis
   also gained `current_ladder` and `current_scenarios`, which the current mix lacked.
8. **History is thinned without hiding the worst day.** Daily returns become one point per five trading days, each drawdown point is the
   deepest day inside its step, and the curve starts from a base day at 100, so the deepest point on screen equals the engine's own
   worst drawdown (a test requires this to within a millionth).
9. **Custom scenarios keep the Streamlit rules.** Six dials with the same ranges, mid-cap moving 25% more than large-cap (never below
   -95%). The ranges are read from the request model and served in `/api/meta`, so the sliders and the validation share one definition.
10. **The editor mirrors the server's rules, and a test proves it.** The family profile editor checks as the person types, using the same
    rules as `fo/profile_form.py`. `tools/make_profile_vectors.py` records the server's verdict on 115 cases, edges included, and a web
    test requires the editor to agree on every one. This found two real differences: Python 3.12's `sum()` is compensated, so a
    holdings total of exactly 99.5% or 100.5% is refused by the server but looked fine to a plain JavaScript sum; and the name limit was
    not enforced. Both are fixed on the editor side.
11. **The golden master grew, additively.** The two new analysis fields were added to `tests/golden/engine_golden.json` by a script that
    first checked every existing value still reproduced, then added keys only (1,040 lines added, none removed).

## Alternatives Considered

### Alternative 1: Drag-and-drop reordering
- **Pros**: Direct, familiar.
- **Cons**: Needs a library, is hard to make accessible, and is awkward on a phone.
- **Why not**: Slots plus move buttons do the same job for everyone. Dragging can be added later on top.

### Alternative 2: Store the choice per family profile
- **Pros**: Different layouts for different families.
- **Cons**: Decision D8 chose per account; one person looking after several families usually wants one layout.
- **Why not**: Per account, as approved. The table could gain a profile column later without losing data.

### Alternative 3: Compute history and scenarios in the browser
- **Pros**: No requests while dragging a dial.
- **Cons**: Copies financial rules into TypeScript, where they can drift from the engine.
- **Why not**: A request takes a few milliseconds once the analysis is cached; the dials wait 0.3 s and keep the last answer on screen.

### Alternative 4: Let people hide warnings with their module choice
- **Pros**: A cleaner screen for someone who dislikes the warning.
- **Cons**: Defeats the purpose of a warning.
- **Why not**: Explicitly ruled out by the master prompt.

## Consequences

### Positive
- A person's layout follows their account across devices and sign-ins; the default is sensible and restorable.
- Every module is reachable whatever is chosen, and the dashboard says where.
- The new numbers are checked against the engine and the golden master; the editor is checked against the server.

### Negative
- Eight module views, three pages and their charts are a lot of screen code; each is covered by tests but the visual review is the owner's.
- The history response carries about 500 points per portfolio (about 60 KB); fine locally, worth compressing before a hosted pilot.

### Risks
- A module added later must be added to both the server list and the web catalog; the type check catches a mismatch, but a retired module
  needs a migration decision (stored choices that name it fall back to the default).
- The compensated-sum behaviour the editor copies belongs to Python 3.12; the vector test will fail loudly if a newer Python changes it.

## References
- Master prompt phases 4 (dashboard and analyst workspace) and the strict change-control rules
- [docs/migration/phase-4-report.md](../migration/phase-4-report.md), [docs/protected-assumptions.md](../protected-assumptions.md)
