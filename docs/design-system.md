# Design system

An original, institutional-fintech look for the React app: calm surfaces, one green accent, dense but readable numbers.
It borrows no logos, names or assets from any product. Everything lives in `web/src`; colours come only from
`styles/tokens.css`, so a theme switch changes variables and nothing else.

## Principles

1. **Numbers first, and honest.** Every headline number has an "About" panel: what it means, how it is worked out, and what it does
   not tell you. Limits are never softened (`content/glossary.ts`; its figures are tested against the frozen model).
2. **Never colour alone.** Status uses an icon and a word as well as colour. Charts have a text summary and a table view; the
   illiquid holding is hatched, and "short" safety nets say "short" in words.
3. **Keyboard and screen reader first.** Native controls where possible (select, radio groups), Radix primitives for dialogs and menus,
   one visible focus ring, a skip link, and landmarks.
4. **Warnings that cannot be hidden.** Critical warnings (solver failure, liquidity shortfall, drawdown above the limit) are computed
   from the analysis alone (`workspace/AttentionBar.tsx`), never from which modules are shown.
5. **A failure stays small.** Error boundaries wrap the app, each page and each chart.

## Tokens (`styles/tokens.css`)

| Group | Tokens |
|---|---|
| Surfaces and text | `--bg`, `--surface`, `--surface-2`, `--ink`, `--ink-2`, `--line`, `--line-strong` |
| Brand and status | `--brand`, `--brand-hover`, `--brand-ink`, `--brand-soft`, `--brand-text`, `--good-*`, `--warn-*`, `--bad-*`, `--info-*`, `--focus` |
| Charts | `--chart-large`, `-mid`, `-debt`, `-gold`, `-cash`, `-illiquid`, `--chart-a`, `--chart-b`, `--chart-grid` |
| Type, space, shape | `--font-sans` (Inter, self-hosted), `--text-xs` to `--text-3xl`, `--space-1` to `--space-7`, `--radius-*`, `--control-h` (40 px) |

`styles/contrast.test.ts` reads this file and checks 64 pairs against WCAG: text at least 4.5:1, borders, focus ring, brand and every chart colour
at least 3:1, in both themes. The two themes must define identical token names.

## Themes

Light, dark, or match the device. `theme/ThemeProvider.tsx` sets `data-theme` on `<html>`; a small script in `index.html` sets it before first
paint so there is no flash. The choice is stored in this browser only (`foi.theme`); blocked storage is handled. Per-account preferences arrive with
the personalised dashboard in phase 4.

## Components

| Area | Components (`web/src/ui`, `charts`, `layout`) |
|---|---|
| Actions | `Button`, `ButtonLink`, `IconButton` (name and tooltip), `Menu` |
| Display | `Card`, `StatTile`, `Badge`, `Banner` (critical, live or plain), `DataTable` |
| Input | `SegmentedControl` (radio group), `Select`, `TextField` (hint and error wired to the input) |
| States | `LoadingBlock`, `EmptyState`, `ErrorState`, `ErrorBoundary` |
| Overlays | `SidePanel` (focus trapped and returned to the opener) |
| Charts | `ChartFrame` (text summary, chart or table), `AllocationChart`, `ProjectionChart`, `OutflowsChart`, `ScenarioChart` (Recharts) |
| Layout | `AppShell`, collapsible `Sidebar` (a drawer on small screens), `Topbar`, `WorkspaceBar` |

## Live behaviour (Phase 3)

| Pattern | Where | Rule |
|---|---|---|
| Stale-while-revalidate | live read-out, strategies | Keep the previous result on screen, dim it, and say "Updating…"; never blank it |
| Debounced input | answers | 350 ms for the read-out, 600 ms for strategies |
| Own-the-typing number box | `ui/NumberField` | Accepts empty, half-typed and comma-grouped numbers; reports a number or null; shows its own range message |
| Step focus | `plan/StepFrame` | Moving to a step focuses its heading; the page's first open does not steal focus |
| Instant switches | comfort level | Anything derivable from data already on the page must not call the server |
| Draft | `plan/draft` | Session storage only, read defensively, never sent anywhere |

## Dashboard and modules (Phase 4)

- **A module is one card with two sizes.** On the dashboard (`ModuleCard`) it is a glance with a "Full view" link; on the analyst pages (`ModuleSection`) it is drawn in full. The cards a module draws
  inside its dashboard card lose their own frame, and their titles become level-3 headings (`HeadingLevel` in `ui/Card.tsx`), so the page reads: page title, module, its parts.
- **Failure stays local.** Each module sits in its own error boundary and loads its own extra data (`QueryBlock`: loading, error with retry, loaded), so one failing module never blanks the dashboard.
- **Customising is a form, not a drag.** Four labelled slots, a swap when a module is picked twice, move buttons, a text preview and a list of where every module lives. It works with a keyboard and a screen reader, and on a phone.
- **A status is words as well as colour.** Scenario results say "Within drawdown limit", "Safety net 9.2x" and "Real corpus 0.85x" in text; the measures table writes Yes and No.
- **Dials** (`ui/Slider.tsx`) read their value in words (`aria-valuetext`) and wait 0.3 s before asking the server, keeping the last result visible and dimmed.
- **Names run together for screen readers when a hidden span carries the space.** Put the space in the visible text, outside the span.

## Layout

The sidebar is 15.5 rem, or 4.5 rem collapsed to icons; its state is remembered. Below 900 px it becomes a drawer. The selected family and
cover basis live in the address (`?profile=5&basis=strict`), so reloads and shared links keep their place.

## What is not built yet

Pages marked "Soon" in the navigation (Holdings, Assistant) are honest placeholders with no invented numbers. The holdings import and the assistant belong to phases 5 and 6;
the dashboard module "Holdings consolidation" waits for the former.
