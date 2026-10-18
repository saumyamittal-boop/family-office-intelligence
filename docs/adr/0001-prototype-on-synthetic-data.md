# ADR-0001: Prototype on synthetic data, outside regulated advice

**Date**: 2026-10-17
**Status**: accepted
**Deciders**: Project owner, facilitated by Claude (grill-me session, Q2 and Q24)

## Context

The tool produces personalised allocations. Under SEBI's Investment Advisers Regulations, acting as or
holding oneself out as an investment adviser without registration is not allowed. A background lookup on
2026-10-17 read the 2013 regulation text and SEBI guidance secondarily; the current consolidated text could
not be fetched, so this is not legal advice. Real family-office data is also confidential and unavailable
to a student project. The project is a 12-week prototype assessed by a mentor.

## Decision

Build a demo prototype that uses synthetic family profiles only. Label every output "illustrative
simulation, not investment advice". Stay at asset-class level, name no securities, promise no returns, and
never present the tool as an adviser. SEBI is the regulatory framing only; it is not a data source.

## Alternatives Considered

### Alternative 1: Pilot with real family data
- **Pros**: Realistic validation.
- **Cons**: Confidentiality, ethics approval, and likely adviser registration.
- **Why not**: Not feasible in 12 weeks and outside the project's purpose.

### Alternative 2: Retail "robo-adviser" framing
- **Pros**: Larger audience.
- **Cons**: Clearly regulated activity.
- **Why not**: Out of scope and legally riskier.

## Consequences

### Positive
- No confidential data, no registration question, simpler testing.

### Negative
- Cannot claim real-world validation.

### Risks
- Anything shown to real families later would likely need registration. Mitigation: keep the disclaimer on every screen and re-check the law before any such step.
