# ADR-0005: Enforce the drawdown limit by historical replay

**Date**: 2026-10-17
**Status**: accepted (amended in part by [ADR-0013](0013-illiquid-fixed-and-modelling-conventions.md): the illiquid bucket accrues smoothly in the replay)
**Deciders**: Project owner, facilitated by Claude (grill-me session, Q19)

## Context

The family's risk tolerance is entered as a maximum tolerable drawdown. Drawdown depends on the path of
returns over time, so it cannot be written as a simple limit on portfolio weights the way class bounds can.
A convex stand-in (such as a CVaR constraint) would change what the user actually specified.

## Decision

Optimise at a given risk aversion, replay the resulting portfolio through the daily historical snapshot to
measure its worst drawdown, and automatically tighten the risk aversion in a simple search loop until the
drawdown fits the tolerance. If even the safest permitted mix breaches the limit, state that openly and show
the closest feasible portfolio rather than failing silently. Each of the three portfolios is shown with its
historical worst drawdown.

## Alternatives Considered

### Alternative 1: CVaR or volatility cap as a stand-in
- **Pros**: Convex and easy to constrain.
- **Cons**: Not the quantity the user entered.
- **Why not**: Misleading to present as a drawdown limit.

### Alternative 2: Report drawdown after the fact, no enforcement
- **Pros**: Simplest.
- **Cons**: The limit would not constrain anything.
- **Why not**: Defeats the input's purpose.

## Consequences

### Positive
- The limit means what it says, in terms of the historical data in the snapshot.

### Negative
- Results depend on the chosen history window; daily data is required for accuracy.

### Risks
- The search loop is the hardest algorithm in the project. Mitigation: build it in the week-4 thin slice and unit-test it early.
