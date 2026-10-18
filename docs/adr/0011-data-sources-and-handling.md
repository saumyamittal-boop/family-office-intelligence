# ADR-0011: Data sources, licensing handling and frozen snapshot

**Date**: 2026-10-17
**Status**: accepted
**Deciders**: Project owner, facilitated by Claude (grill-me session, Q8, Q24 to Q28)

## Context

The proposal named NSE, RBI, AMFI and SEBI. A background lookup on 2026-10-17 found: SEBI has no usable
machine-readable data feed; NSE Indices' terms (read directly on the same day) prohibit systematic or
automated data collection without written consent and restrict copying to personal, non-commercial use; the
RBI DBIE portal has no documented API; gold ETF NAV series contain unit-split jumps; the CPI base year changed
in 2024. Some lookup findings were not independently checked (open items in the requirements).

## Decision

Use NSE Indices (Nifty 50 TRI, Nifty Midcap 150 TRI, Nifty 10 yr Benchmark G-Sec, Nifty 1D Rate Index), AMFI
gold ETF NAV (split-adjusted, single-day jumps above 40% rejected, cross-checked against a second ETF),
MoSPI CPI, and a hand-keyed repo-rate table. Drop USD/INR, DBIE and FPI flows. Download NSE files by hand
through the site's own download button, keep them private, show only derived results with attribution, and
send a consent email in week 1. Plan B is AMFI index-fund NAVs. Ingest daily data; use monthly returns for
the optimiser and daily data for drawdown, CVaR and scenario calibration. Target start 2008 with a 2016
floor. Ship a frozen versioned CSV snapshot plus a refresh script so the demo never needs a live website.
This is not legal advice.

## Alternatives Considered

### Alternative 1: Scrape with Python libraries
- **Pros**: Fast, full history.
- **Cons**: Violates the terms; endpoints are unofficial and unstable.
- **Why not**: Legal and reliability risk.

### Alternative 2: AMFI fund NAVs for everything
- **Pros**: One source, fewer terms issues.
- **Cons**: Shorter or impure histories for some classes; fund costs embedded.
- **Why not**: Kept as plan B rather than the first choice.

## Consequences

### Positive
- A reproducible, offline demo; honest handling of licensing.

### Negative
- Manual download effort; RBI is a light source (repo rate only).

### Risks
- Consent refused or history shorter than expected. Mitigation: plan B and the 2016 floor.
