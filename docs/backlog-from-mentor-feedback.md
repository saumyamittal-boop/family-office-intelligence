# Backlog from the mentor call (17 Oct 2026)

Source: capstone guidance call with the project mentor. The prototype demo drew praise for the sign-in feature and
the UI, and a clear challenge: make it decision-driving, not a "glorified Excel".

## What the mentor asked for

| # | Feedback | Status |
|---|---|---|
| 1 | Be a guided, decision-driving tool: ask life-story questions (goals, risk appetite, commitments), then output Strategy A, B and C with risk and return and what to buy | **Phase 1, built** (ADR-0015); needs the mentor's reaction on 24 Oct |
| 2 | Do not ask for technical inputs (expected return, volatility) from a non-expert | Phase 1: the guided flow asks none; the profile editor stays as an advanced view |
| 3 | Horizon is not a meaningful question for perpetual family wealth; ask about commitments instead | Phase 1: guided flow asks for dated commitments; horizon is fixed at 25 years behind the scenes |
| 4 | Stay away from stock picking; say what "large cap" means in practice (index funds) | Phase 1: each asset class maps to a plain instrument category, not a named security |
| 5 | Show effectiveness on past data and the range-bound risk | Phase 1: typical-year range, worst year in history, and a 2020-style crash per strategy |
| 6 | Ask about the goal: preserve, grow, or participate in the market | Phase 1: three plain-language risk and goal choices |
| 7 | Define who the product is for | **Open decision** (below) |
| 8 | Wow-factor demo; the deck is a two-minute intro | Ongoing; demo flow is the Plan my money wizard |
| 9 | Customisable fields for different needs | Phase 2: custom commitment types and notes |
| 10 | Deploy and share a link; web before native app unless cheap | Phase 3: deployment (owner: the team's engineer, by end of October) |
| 11 | Work with one friendly family-office contact | Phase 3: depends on the mentor's introduction |

## Open decision: who is the product for?

The mentor sees a white space in wealthy families with no family office or fund manager, served by extremely cheap,
simple software. A fund manager already knows volatility and Sharpe ratio and would want a consolidated dashboard
instead. **Working assumption for now:** the guided flow targets the first group, and the existing Overview, Risk and
Scenarios pages serve as the advanced view for a manager. This is the project owner's call and should be confirmed
with the mentor next Saturday (24 Oct).

## Phases

1. **Guided plan (this change):** plain-language questionnaire to three strategies with instruments, ranges and
   amounts; saved into the account's profiles.
2. **Depth:** commitment labels and custom types, a clearer "what changed since last time" view, ~~side-by-side option
   comparison under a chosen scenario, a one-click demo for the liquidity-gap example~~ (both built 18 Oct).
3. **Reach:** deployment, a shareable link, a friendly pilot family, and real data once licensing is settled.
   Deployment preparation was done on 18 Oct ([guide](deployment.md)); it now waits on a GitHub account and the
   hosting choice.

## Not changing

Stock picking stays out of scope. Output remains an illustrative simulation on synthetic data until real data and
validation are in place.
