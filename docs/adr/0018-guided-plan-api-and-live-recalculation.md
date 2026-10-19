# ADR-0018: Guided plan API and live recalculation

**Date**: 2026-10-19
**Status**: accepted (Phase 3)
**Deciders**: Project owner (asked for the guided plan and for the app to be "super dynamic"), facilitated by Claude
**Builds on**: [ADR-0015](0015-guided-plan-and-strategies-by-comfort-level.md) and [ADR-0017](0017-react-fastapi-migration.md)

## Context

The Streamlit "Plan my money" flow re-runs the whole page on every click and shows nothing until the end. The owner wants a
live, responsive app: results that follow each answer, instant feedback, and any answer editable at any time. The full
three-strategy calculation takes about three seconds (three optimiser runs), which is too slow to run on every keystroke.
The financial engine must not change.

## Decision

1. **Split the work by cost.** `POST /api/plan/preview` does cheap arithmetic only (the safety-net requirement, outflows,
   how the wealth divides, plain-language "how your answers shape the plan" lines) and answers in milliseconds, so the screen
   can follow typing. `POST /api/plan/strategies` runs the optimiser through the existing cached analysis service.
2. **The strategies do not depend on the comfort level**, because each strategy is built for its own level (ADR-0015). The
   endpoint therefore returns, for each strategy, whether it fits each comfort level (`within_comfort_of`, `meets_goal_of`).
   The client always sends the same comfort level, so switching comfort is a lookup: no request, and the cards update at once.
3. **Stale-while-revalidate on screen.** The client debounces (350 ms for the preview, 600 ms for strategies), keeps showing the
   previous answer, and marks it "Updating…" until the new one arrives, so nothing blanks or jumps.
4. **Answers are stateless.** Every call carries the full answers; the server stores nothing until the person saves. Saving is
   idempotent: the same plan saved twice returns the first copy.
5. **The server decides, the client formats.** All numbers and sentences about the model come from Python (`fo.plan`, `fo.engine`,
   a new pure `fo.formatting` shared with the Streamlit app). The client holds no financial logic.
6. **The draft lives in `sessionStorage`**: it survives a reload of that tab, is gone when the tab closes, and is never sent
   anywhere. The step number lives in the address, so the browser's Back button moves between steps.
7. **Guards.** Each person may request at most 40 strategy calculations a minute (cached repeats are cheap, new ones take
   seconds); the engine's existing single thread and 90 s timeout apply; zero spending with no commitment in the safety-net window
   is refused with a clear message, because the engine would otherwise divide by zero.
8. **Wording.** "In a crash like 2020" becomes "In a severe market crash", with the preset's actual shocks and the words "not a
   replay of any real year", generated from the scenario itself so they cannot drift. (Applied on the strength of the Phase 2
   recommendation; reverting is a one-line change.)

## Alternatives Considered

### Alternative 1: Stream results over WebSockets or server-sent events
- **Pros**: Could show strategy A before B and C finish.
- **Cons**: A second transport, more state and failure modes, for a three-second wait.
- **Why not**: Debounce, caching and "Updating…" give the same feel with plain requests; revisit if analyses get slower.

### Alternative 2: Compute the preview in the browser
- **Pros**: Zero latency, works offline.
- **Cons**: Duplicates financial rules in TypeScript, where they can drift from the engine.
- **Why not**: The server round trip is milliseconds, and one source of truth matters more.

### Alternative 3: Save drafts on the server
- **Pros**: Resume on another device.
- **Cons**: Stores half-finished financial answers; needs the privacy gate.
- **Why not**: Not needed for the prototype; may return with the hosted pilot.

## Consequences

### Positive
- Typing is answered in milliseconds; comfort changes are instant; slower changes keep the old result visible.
- The engine is untouched and the guided numbers are checked against the golden master through the real HTTP API.

### Negative
- Each answer change can cost three optimiser runs on the single engine thread; a burst of changes queues.
- Two UIs now compute guided plans; the Streamlit version stays as the reference until cut-over.

### Risks
- The rate limit and queue are per process. Mitigation: a shared limiter in Phase 7.
- An analysis in flight cannot be cancelled when newer answers arrive. Mitigation: debouncing, caching, and the timeout.
