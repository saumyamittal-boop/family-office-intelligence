# ADR-0015: Guided plan, with strategies built for each comfort level

**Date**: 2026-10-18
**Status**: accepted
**Deciders**: Project owner, following the mentor call of 17 Oct 2026, facilitated by Claude
**Builds on**: [ADR-0014](0014-app-structure-and-visual-direction.md)

## Context

The mentor's central challenge was that the app risked being a glorified Excel: it asked a family for returns,
volatility and an investment horizon, and answered with allocation percentages. He wanted a person who "has no idea
how to manage money" to give their life story and be told what to do, with Strategy A, B and C showing risk and
return and where to buy. He also warned against stock picking and asked what "large cap" means in practice. A first
attempt that held all three strategies to one comfort limit produced three near-identical portfolios.

## Decision

Add a "Plan my money" page: a six-step guided flow (about you, what is coming, comfort with a bad year, safety net,
what you own, strategies). It asks only plain questions and never asks for returns or volatility. Horizon is fixed at
25 years behind the scenes; dated commitments replace it. Comfort maps to a drawdown limit and a modest real-return
goal: Protect 8% and 2%, Balance 15% and 4%, Grow 25% and 6%.

**Each strategy is built for its own comfort level** (A for Protect, B for Balance, C for Grow), so they genuinely
differ; the family's answer only decides which one is marked "Recommended for you" and which are "Beyond your
comfort". Each card shows a typical-year range (the middle 80% of years in the history), the worst year in the history,
a 2020-style crash in rupees, a safety-net multiple, and whether the return goal is met. Asset classes appear as plain
instrument categories (for example "Large-cap index fund"), never named securities. The guided flow uses the stricter
liquidity cover (cash, debt and gold only). Saving stores a profile for the chosen strategy, and a new account lands on
the flow first.

## Alternatives Considered

### Alternative 1: One comfort limit for all three strategies
- **Pros**: Simple; one analysis.
- **Cons**: Observed result: strategies within a point or two of each other, so the choice looked meaningless.
- **Why not**: It defeats the purpose of showing a risk-return trade-off.

### Alternative 2: Keep asking for expected returns and volatility
- **Pros**: Transparent to experts.
- **Cons**: The mentor's "glorified Excel" problem; a non-expert cannot answer.
- **Why not**: The target user in the working assumption is a non-expert family.

### Alternative 3: Recommend named funds or stocks
- **Pros**: A concrete shopping list.
- **Cons**: Stock picking is a long journey, and named recommendations raise the regulatory issue in ADR-0001.
- **Why not**: Instrument categories give a concrete next step without that risk.

## Consequences

### Positive
- The app now leads with a decision, not a calculator, and the strategies show the trade-off clearly.
- Plain language throughout; no technical input is required from the family.
- Reuses the existing engine; the same analysis powers the other pages once a plan is saved.

### Negative
- The comfort thresholds (8%, 15%, 25%) and matching return goals are placeholders to validate with real families.
- Commitment labels (education, wedding) are used only inside the flow; saved profiles store just year and amount.
- Results still depend on synthetic sample data, so details such as a mid-cap preference are artefacts, not findings.

### Risks
- The working assumption (a family with no family office, not a fund manager) may be wrong. Mitigation: confirm with
  the mentor on 24 Oct; the advanced pages remain for a manager.
