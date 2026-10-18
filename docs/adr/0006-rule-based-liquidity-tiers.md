# ADR-0006: Rule-based liquidity tiers

**Date**: 2026-10-17
**Status**: accepted (amended in part by [ADR-0013](0013-illiquid-fixed-and-modelling-conventions.md): haircuts are stored per asset class, grouped by tier)
**Deciders**: Project owner, facilitated by Claude (grill-me session, Q9)

## Context

Family offices face lumpy, dated cash needs. Modelling market impact and transaction costs properly needs
data the project does not have and hours it cannot spare.

## Decision

Assign every asset class to a liquidity tier: tier 1 liquid funds and cash at full value; tier 2 large-cap
equity, gold and debt at a haircut; tier 3 mid-cap equity at a larger haircut; tier 4 illiquid, never counted
until its lock-in ends. Haircuts are editable defaults. The constraint is that haircut-adjusted tiers 1 to 3 must
cover the chosen months of outflows, including the dated one-off outflows. The output is a year-by-year
liquidity ladder, and the cost of the constraint in expected return is reported.

## Alternatives Considered

### Alternative 1: Market-impact and time-to-liquidate model
- **Pros**: More realistic for large positions.
- **Cons**: Needs trading-volume data and calibration.
- **Why not**: No free data and too many hours.

### Alternative 2: A single cash buffer percentage
- **Pros**: Trivial.
- **Cons**: Ignores the timing of outflows.
- **Why not**: Cannot show when cover gets thin.

## Consequences

### Positive
- Transparent, editable and easy to explain and test.

### Negative
- Haircut defaults are judgement calls.

### Risks
- Defaults look arbitrary. Mitigation: document a rationale for each default (open item in the requirements).
