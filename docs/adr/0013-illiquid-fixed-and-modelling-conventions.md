# ADR-0013: Illiquid holdings held fixed, and four modelling conventions

**Date**: 2026-10-17
**Status**: accepted
**Deciders**: Project owner (accepted the recommended answers to G1 to G5), facilitated by Claude
**Amends**: parts of [ADR-0003](0003-asset-classes-and-profile-inputs.md),
[ADR-0005](0005-drawdown-by-historical-replay.md) and [ADR-0006](0006-rule-based-liquidity-tiers.md)

## Context

While drafting the three personas, five modelling points surfaced that the scoping session had not settled:
whether the illiquid bucket is optimised, how it appears in the drawdown replay, how the target real return is
used, whether liquidity haircuts are per tier or per class, and whether outflows are indexed to inflation.
Leaving them open would have let the code decide them by accident.

## Decision

1. **Illiquid bucket fixed (G1).** It is an input held fixed until its lock-in ends. The optimiser allocates
   only the other five classes (the liquid sleeve). Per-class minimum and maximum limits apply to the liquid
   sleeve. Weights are reported as a share of total corpus.
2. **Illiquid in the drawdown replay (G2).** In the replay it is valued at smooth accrual of its assumed
   return. A user-set mark-down applies to it only in the crash scenario.
3. **Target real return (G3).** It is a reported goal, not a constraint. Each portfolio is shown as meeting or
   missing the target, with the gap, and scenarios show whether the goal is still met.
4. **Haircuts per class (G4).** Liquidity haircuts are stored per asset class and grouped by tier for display.
   This refines the per-tier wording in ADR-0006.
5. **Inflation indexing (G5).** The inflation assumption is 4.5% and editable. Annual spending grows with it.
   The three one-off outflows are nominal amounts in the year they occur.

## Alternatives Considered

### Alternative 1: Optimise the illiquid bucket too
- **Pros**: One uniform optimiser.
- **Cons**: Recommends selling a business stake or a locked fund.
- **Why not**: Unrealistic output that a mentor would challenge immediately.

### Alternative 2: Hard return-target constraint
- **Pros**: Guarantees the goal is addressed.
- **Cons**: Often infeasible next to the drawdown limit.
- **Why not**: Reporting the gap is more informative than reporting infeasibility.

### Alternative 3: One haircut per tier
- **Pros**: Simpler to explain.
- **Cons**: Tier 2 mixes debt, gold and equity, which lose value very differently.
- **Why not**: Too blunt to be defensible.

## Consequences

### Positive
- The code has no unstated modelling choices; each is traceable to this record.
- Illiquidity is handled honestly: shown as a constraint on the family, not a lever for the optimiser.

### Negative
- Smooth accrual understates the illiquid bucket's true risk in the replay. The mark-down in the crash scenario
  is the only place that risk appears.
- Reported weights over total corpus differ from the optimiser's sleeve weights, which needs clear labelling.

### Risks
- Users may read the smoothed risk figures as real. Mitigation: label the illiquid bucket's volatility as an
  appraisal-based floor in the interface and the documentation.
