# ADR-0002: One family-office archetype, three personas, one demo path

**Date**: 2026-10-17
**Status**: accepted
**Deciders**: Project owner, facilitated by Claude (grill-me session, Q1, Q3, Q4, Q21)

## Context

One person has about 100 core hours across 12 weeks. The original proposal listed five feature areas, which
is more than that budget supports if each is built fully. A common failure for projects like this is a polished
model with no working application until the last weeks.

## Decision

Design for one Indian single-family-office archetype (corpus about INR 100 to 500 crore, one CIO-type user per
profile). "Done" means one end-to-end path works on three synthetic personas: enter a profile, get an
allocation, see why, then stress it. Each persona is built so a different constraint decides the answer:
Legacy-conservative (liquidity), Business-heavy (illiquid holdings and concentration), Next-gen growth
(drawdown tolerance). Everything else is stretch.

## Alternatives Considered

### Alternative 1: Broad feature set, shallow
- **Pros**: Matches the proposal's wording.
- **Cons**: Several half-working features.
- **Why not**: Weak demo and high risk of missing the deadline.

### Alternative 2: Multi-family and institutional users
- **Pros**: Wider market.
- **Cons**: Different goals, entities and reporting.
- **Why not**: Doubles the modelling for no demo benefit.

## Consequences

### Positive
- A focused demo where the three personas show visibly different behaviour.

### Negative
- Less breadth than the original proposal.

### Risks
- Personas that look artificial. Mitigation: mentor reviews the numbers.
