# ADR-0014: App structure and visual direction

**Date**: 2026-10-17
**Status**: accepted
**Deciders**: Project owner (feedback on the first sample), facilitated by Claude
**Builds on**: [ADR-0009](0009-streamlit-app-and-stack.md) and [ADR-0010](0010-multi-user-local-accounts.md)

## Context

The first runnable sample was a calculator with four tabs and a persona picker. The project owner judged the
interface poor and the dashboard "measly", and asked for a look similar to IndMoney. Review of that sample
agreed: there was no way to enter a family's own data, no sign-in, and no concrete "what do I do" output. IndMoney's
public site shows the patterns to borrow: Inter type, a white canvas, near-black text, one green accent on pill
buttons, soft grey cards, and net-worth and family tracking as the core idea.

## Decision

Stay on Streamlit (ADR-0009) and build a multi-page app with top navigation: Overview, Recommendation, Risk and
liquidity, Scenarios, and Family profile, behind a sign-in screen. Implement ADR-0010 now: accounts, private profiles
per user, a profile editor, and one-click demo families. The Overview leads with a net-worth hero card, an
allocation donut, a buy and sell plan, key numbers, rule-based insights and planned outflows. Style it with a locked
light theme in `.streamlit/config.toml` (Inter, a green accent, large radii, pill buttons) plus a small amount of CSS
for the hero card, rows and pills. Borrow only layout and style patterns: no logos, names or assets.

## Alternatives Considered

### Alternative 1: Rebuild the front end in React with a Python API
- **Pros**: Full control of every pixel; persistent sessions.
- **Cons**: Needs Node tooling and a build step, and would use much of the remaining hour budget on plumbing.
- **Why not**: The budget is about 100 core hours and the engine is in Python; Streamlit gets most of the look.

### Alternative 2: Keep the plain Streamlit widgets and polish them
- **Pros**: Least work.
- **Cons**: Does not address the feedback; still reads as a calculator.
- **Why not**: The owner explicitly rejected that look.

## Consequences

### Positive
- The app feels like a product and covers the proposal's "profile, allocation, risk, scenarios, dashboard" list.
- Insights, the action plan and the profile editor turn model output into something a family can act on.
- Custom pieces are limited to a few HTML helpers in `fo/ui.py`, all user text escaped.

### Negative
- Refreshing the page signs the user out, because Streamlit sessions are not persistent.
- The CSS depends on Streamlit's `st.html` and key-based class names, so a Streamlit upgrade needs a visual check.
- More code to maintain: roughly five pages, an accounts module and a UI module.

### Risks
- Time spent on presentation competes with data and validation work. Mitigation: the data snapshot and
  validation items in the plan are unchanged, and the cut order in the requirements still applies.
