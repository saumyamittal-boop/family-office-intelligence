# ADR-0012: Delivery plan, cut order and documentation

**Date**: 2026-10-17
**Status**: accepted
**Deciders**: Project owner, facilitated by Claude (grill-me session, Q1, Q16, Q17, Q18, Q23)

## Context

One builder, about 10 hours a week, a fixed 12-week deadline: roughly 120 hours, planned as about 100 core
plus about 20 slack. The original plan built the app in weeks 9 and 10 and tested in week 11. Documentation
and the demo are the items most often squeezed at the end.

## Decision

Build a thin end-to-end slice first, with a go/no-go checkpoint at the end of week 4. Milestones are at
weeks 2, 4, 6, 8 and 10, with weeks 11 and 12 for documentation, the test report, demo rehearsal and slack.
Agree the cut order up front: stretch items first, then custom sliders, then self-registration, then
cost-of-constraint beyond liquidity, then per-asset lock-in schedules. The protected core is never cut.
Write documentation as the work proceeds, starting with this requirements document and these records. The
demo is a scripted walkthrough of about 10 minutes with a backup screen recording.

## Alternatives Considered

### Alternative 1: Finish each layer before the next
- **Pros**: Tidy.
- **Cons**: No working application until late.
- **Why not**: Highest risk of missing the deadline.

### Alternative 2: Write documentation at the end
- **Pros**: Less context switching.
- **Cons**: Squeezed or skipped.
- **Why not**: Documentation is a stated deliverable.

## Consequences

### Positive
- Early evidence of feasibility and no panic decisions about scope.

### Negative
- Early code is rough and will be revised.

### Risks
- Slack gets consumed early. Mitigation: review hours at each milestone.
