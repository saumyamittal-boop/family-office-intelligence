# ADR-0007: Risk metrics and calibrated scenarios

**Date**: 2026-10-17
**Status**: accepted
**Deciders**: Project owner, facilitated by Claude (grill-me session, Q10 and Q26)

## Context

The proposal asks for risk analysis and scenario testing of crashes, inflation and unexpected expenses.
Invented shock sizes are hard to defend. Monthly data of about 120 points leaves roughly six observations in the
worst 5% tail and understates drawdowns.

## Decision

Report volatility, maximum drawdown and 95% historical CVaR from the frozen daily snapshot. Provide four
preset scenarios: market crash, inflation and rate spike, sudden large expense (liquidity squeeze), and a
low-return "lost decade". Each is a one-time shock to asset values and cash flows, calibrated from the worst
real episodes in the data where the window allows. Each scenario shows portfolio value change, drawdown-cap
breach, liquidity-cover breach and whether the goals are still met. Custom sliders and a Monte Carlo fan chart
are stretch goals.

## Alternatives Considered

### Alternative 1: Invented shock sizes
- **Pros**: Simple to build.
- **Cons**: Hard to defend.
- **Why not**: Weak against questions from a mentor.

### Alternative 2: Monthly data only
- **Pros**: Less data handling.
- **Cons**: Thin tail and understated drawdown.
- **Why not**: Daily history is available.

## Consequences

### Positive
- Scenarios are tied to real episodes and the same snapshot as everything else.

### Negative
- If the history window starts in 2016, the 2008 crisis is not available for calibration.

### Risks
- Short history. Mitigation: state the achieved window in the documentation.
