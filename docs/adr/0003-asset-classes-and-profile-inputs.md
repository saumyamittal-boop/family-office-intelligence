# ADR-0003: Six asset classes and eight profile inputs

**Date**: 2026-10-17
**Status**: accepted (amended in part by [ADR-0013](0013-illiquid-fixed-and-modelling-conventions.md): the illiquid bucket is held fixed, and the target real return is a reported goal)
**Deciders**: Project owner, facilitated by Claude (grill-me session, Q5, Q6, Q28)

## Context

Family offices hold assets that have no free daily price series (real estate, private equity, operating
businesses). A generic optimiser ignores them. The data budget is limited to free public sources.

## Decision

Model five classes from market data (large-cap equity, mid-cap equity, debt, gold, cash and liquid) plus one
manual "illiquid" bucket where the user enters value, assumed return, assumed volatility and lock-in. The
profile has eight inputs: corpus, current holdings, annual spending plus up to three dated one-off outflows,
horizon, maximum tolerable drawdown, required liquidity cover in months, per-class limits, and target real
return. Excluded: international equity, crypto, REITs and InvITs, derivatives, individual stocks, tax,
estate planning, multiple entities, multi-currency.

## Alternatives Considered

### Alternative 1: Liquid asset classes only
- **Pros**: Everything is data-driven.
- **Cons**: Looks like any robo-optimiser.
- **Why not**: The illiquid bucket is what makes it a family-office tool.

### Alternative 2: Psychometric risk questionnaire
- **Pros**: Familiar to advisers.
- **Cons**: Scoring design and validation work.
- **Why not**: A maximum tolerable drawdown is a direct, testable measure.

## Consequences

### Positive
- Small, testable input surface; illiquidity is modelled explicitly.

### Negative
- Mid- and small-cap are merged and represented by Nifty Midcap 150 only.

### Risks
- Illiquid assumptions are user-entered and unverifiable. Mitigation: show them clearly as assumptions.
