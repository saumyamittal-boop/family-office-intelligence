# ADR-0004: Constrained mean-variance allocation

**Date**: 2026-10-17
**Status**: accepted
**Deciders**: Project owner, facilitated by Claude (grill-me session, Q7 and Q22)

## Context

The proposal asks for a multi-objective allocation covering return, risk, liquidity and diversification. Raw
historical average returns, especially over a strong Indian equity period, make mean-variance results
unstable and extreme. The builder has basic Python, so the method must be simple and testable.

## Decision

Use constrained mean-variance optimisation with scipy (SLSQP): maximise expected return minus a risk
penalty, subject to class limits, a maximum weight per class, the liquidity cover and the drawdown limit
(ADR-0005). Estimate covariance with shrinkage. Expected returns are a 50/50 blend of historical return and a
documented long-run assumption, editable per user. Run at three risk-aversion levels to produce three
portfolios. Liquidity and diversification act as constraints, and the cost of the liquidity constraint is
reported. Black-Litterman, risk parity, machine-learning forecasts and tactical views are future work.

## Alternatives Considered

### Alternative 1: Black-Litterman or risk parity
- **Pros**: More stable in theory.
- **Cons**: More concepts to build, test and explain.
- **Why not**: Exceeds the hours; listed as future work.

### Alternative 2: Raw historical means
- **Pros**: No assumptions to document.
- **Cons**: Overweights whatever did best.
- **Why not**: Poor and unstable recommendations.

## Consequences

### Positive
- Small, explainable engine; the cost-of-constraint output makes the trade-off visible.

### Negative
- Long-run assumptions need defensible sources, and they are a judgement call.

### Risks
- Results look more precise than they are. Mitigation: label the output illustrative and show the assumptions table.
