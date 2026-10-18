# Family Office Intelligence: Requirements (v1)

**Date**: 2026-10-17
**Status**: confirmed by the project owner at the end of a 28-question scoping session (decisions Q1 to Q28)
**Companion**: decision records in [adr/](adr/README.md) explain why each choice was made.

## 1. What this is

A 12-week, solo-built **prototype** of a capital-allocation decision-support tool for an Indian
single-family office. A user enters a family profile, receives recommended allocations across six
asset classes with an explanation, and stress-tests them. It runs on **synthetic** family profiles
and public market data. It is labelled "illustrative simulation, not investment advice".

It is not a platform, not a product for real client money, and not a regulated advisory service.

## 2. Constraints

| Item | Value |
|---|---|
| Builder | One person, basic Python with some pandas |
| Time | 12 weeks at about 10 hours a week: roughly 120 hours, planned as about 100 core plus about 20 slack |
| Hard deadline | Fixed 12-week end date |
| Runs on | One laptop (Windows), locally, for the demo |
| Budget | Free data and open-source tools only |

## 3. Users and personas

One target user type: the CIO or head of a single Indian family office with a corpus of roughly
INR 100 to 500 crore. The app supports multiple accounts, each with private profiles (section 7).

Three synthetic personas, each designed so that a different constraint decides the answer:

| Persona | Deciding constraint |
|---|---|
| Legacy-conservative | High annual spending, so the liquidity cover binds |
| Business-heavy | About half the corpus in a family business or real estate, so the illiquid bucket and concentration limits matter |
| Next-gen growth | Long horizon and high return target, so the drawdown tolerance binds |

The numbers for each persona are **to be drafted and reviewed** (section 14).

## 4. Functional requirements

Priority: **Core** must ship. **Stretch** only if the core is done. The cut order is in section 10.

| ID | Requirement | Priority |
|---|---|---|
| FR-1 | Accounts: login, a few pre-made demo accounts, self-registration; each user sees only their own profiles | Core (self-registration is cut order #3) |
| FR-2 | Family profile with the eight inputs in section 5.2; save and load several profiles per user; three seeded personas | Core |
| FR-3 | Recommendation: three alternative portfolios at three risk levels, each respecting all constraints, each shown with expected return, volatility, historical worst drawdown, and a plain-language explanation | Core |
| FR-4 | Liquidity analysis: a year-by-year ladder showing when cover gets thin | Core |
| FR-5 | Risk metrics: volatility, maximum drawdown, 95% historical CVaR | Core |
| FR-6 | Five preset scenarios (equities fall 25%, market crash, inflation and rate spike, large unexpected expense, lost decade) with before-and-after results | Core |
| FR-7 | Custom scenario sliders | Stretch (cut order #2) |
| FR-8 | Editable assumptions table (expected returns, liquidity haircuts), each default with a documented rationale | Core |
| FR-9 | Cost-of-constraint: what the liquidity requirement costs in expected return | Core. Other constraints are cut order #4 |
| FR-10 | Dashboard as five pages with top navigation behind a sign-in screen: Overview, Recommendation, Risk and liquidity, Scenarios, Family profile (ADR-0014) | Core |
| FR-11 | Monte Carlo fan chart of long-run outcomes | Stretch |
| FR-12 | Historical walk-forward backtest against equal-weight and 60/40 benchmarks, labelled illustrative | Stretch |
| FR-13 | Online hosting; roles and sharing between accounts | Stretch |
| FR-15 | Compare options under one scenario: the current mix and the three recommended options side by side (chart and table) for any preset or custom scenario, with a plain-language reading of the trade-off | Core |
| FR-14 | Guided "Plan my money" flow: plain-language questions (no returns or volatility), then Strategy A, B and C each built for its own comfort level, with typical-year range, worst year, a crash in rupees, and what to buy by instrument category; save a strategy as a profile (ADR-0015) | Core |

## 5. Financial model

### 5.1 Asset classes

Five modelled from market data plus one manual bucket:

1. Large-cap equity: Nifty 50 TRI
2. Mid-cap equity: Nifty Midcap 150 TRI (stands in for the "mid and small cap" class)
3. Debt: Nifty 10 yr Benchmark G-Sec (confirm it is a total-return series, section 14)
4. Gold: one gold ETF NAV from AMFI, split-adjusted
5. Cash and liquid: Nifty 1D Rate Index
6. Illiquid and manual: real estate, private equity or AIFs, family business. The user enters a value,
   an assumed return, an assumed volatility and a lock-in period. No market data. It is held fixed until
   its lock-in ends: the optimiser allocates only the other five classes, the "liquid sleeve" (section 5.8).

Out of scope as asset classes: international equity, crypto, REITs and InvITs, derivatives, individual stocks.

### 5.2 Profile inputs (eight)

1. Total corpus (INR)
2. Current holdings by asset class
3. Annual spending plus up to three dated one-off outflows
4. Investment horizon (years)
5. Maximum tolerable drawdown (%), used as the risk-tolerance measure
6. Required liquidity cover (months of outflows held in liquid assets)
7. Minimum and maximum limit per asset class
8. Target real return (above inflation), used as a reported goal and not as a constraint (section 5.8)

Out of scope: tax, succession and estate planning, multiple trusts or entities, multi-currency.

### 5.3 Allocation method

Constrained mean-variance optimisation (scipy, SLSQP):

- Maximise expected return minus a risk penalty.
- Constraints: class limits, maximum weight per class, liquidity cover, drawdown limit.
- Covariance: shrinkage estimator.
- Expected returns: 50% historical, 50% documented long-run assumption, editable per user.
- Run at three risk-aversion levels to give three portfolios.
- Report the cost of the liquidity constraint.

Not in v1: Black-Litterman, risk parity, machine-learning forecasts, tactical views.

### 5.4 Drawdown limit

Maximum drawdown is path-dependent, so it is enforced by replay: optimise, replay the portfolio through
the daily history to measure its worst drawdown, and tighten the risk aversion automatically until it fits.
If even the safest permitted mix breaches the limit, say so and show the closest feasible portfolio.
In the replay the illiquid bucket is valued at smooth accrual of its assumed return; a user-set mark-down
applies to it only in the crash scenario (section 5.8).

### 5.5 Liquidity

Four tiers: (1) liquid funds and cash at full value; (2) large-cap equity, gold and debt at a haircut;
(3) mid-cap equity at a larger haircut; (4) illiquid, never counted until the lock-in ends. Haircuts are
stored per asset class and grouped by tier for display; they are editable defaults. Constraint: haircut-adjusted tiers 1 to 3 must cover the chosen months of
outflows, including the dated one-off outflows.

### 5.6 Risk metrics and scenarios

- Metrics: volatility, maximum drawdown, 95% historical CVaR, all from the frozen snapshot.
- Presets: equities fall 25%, market crash, inflation and rate spike, sudden large expense (liquidity squeeze), low-return
  "lost decade". Each is a one-time shock to asset values and cash flows, calibrated from the worst real
  episodes in the data where the window allows.
- Outputs per scenario: portfolio value change, drawdown-cap breach, liquidity-cover breach, goals still met or not.

### 5.7 Explanations

Rule-based text generated from the optimiser's own output (which constraints bind and what they cost).
No LLM calls.

### 5.8 Modelling conventions (ADR-0013)

- **Illiquid bucket fixed**: held fixed until its lock-in ends. The optimiser allocates only the liquid sleeve
  (the other five classes). Class limits apply to the sleeve. Weights are reported as a share of total corpus.
- **Drawdown replay**: the illiquid bucket accrues smoothly at its assumed return. A user-set mark-down applies
  to it only in the crash scenario. Its volatility is labelled an appraisal-based floor.
- **Target real return**: a reported goal. Each portfolio shows whether it meets or misses the target and by how
  much; scenarios show whether the goal is still met.
- **Haircuts**: per asset class, grouped by tier for display.
- **Inflation**: assumption of 4.5%, editable. Annual spending grows with inflation. One-off outflows are
  nominal amounts in the year they occur.
- **Default numbers** for return priors, haircuts, illiquid holdings and the personas are in
  [personas-and-assumptions.md](personas-and-assumptions.md) and remain a draft for review.

## 6. Data

| Need | Source | Handling |
|---|---|---|
| Equity, debt and cash indices | NSE Indices (niftyindices.com) | Manual download through the site's own download button; private files; consent email in week 1 |
| Gold ETF NAV | AMFI (via portal or the community API mfapi.in) | Split-adjust; reject any single-day move above 40%; cross-check against a second gold ETF |
| Inflation | MoSPI CPI (free sign-up) | Join across the 2024 base-year change |
| Repo rate | RBI policy announcements | Hand-keyed, about 20 changes in ten years |

- **SEBI** is not a data source. It is the regulatory framing only.
- **Dropped**: USD/INR, RBI DBIE, FPI flows.
- **Granularity**: daily ingestion; monthly returns feed the optimiser; daily data feeds drawdown, CVaR and scenario calibration.
- **Window**: target start 1 January 2008 where every series exists; floor 1 January 2016. State the achieved window in the documentation.
- **Storage**: a frozen, versioned CSV snapshot plus a separate refresh script. The app never fetches live data.
- **Licensing**: NSE Indices' terms (read and confirmed on 2026-10-17) prohibit systematic or automated collection without written consent and restrict copying to personal, non-commercial use. Keep raw files private and out of any public repository; publish only derived results with attribution. If consent is refused, plan B is AMFI index-fund NAVs. The same private, no-redistribution handling applies to AMFI data. This is not legal advice.

## 7. Non-functional requirements

- **Accounts and security**: passwords hashed with the standard library's scrypt; SQLite for storage; per-user data isolation. The app states that it accepts synthetic data only and that users must not reuse a real password.
- **Reproducibility**: one `requirements.txt` with pinned versions in a virtual environment; Streamlit 1.57 or newer.
- **Offline demo**: runs entirely from the frozen snapshot.
- **Tooling**: Streamlit, pandas, numpy, scipy, plotly, pytest. PyPortfolioOpt in tests only. No cvxpy.
- **Look and feel**: inspired by IndMoney's public site (white canvas, Inter, one green accent, soft cards,
  pill buttons). Style patterns only; no logos, names or assets (ADR-0014).
- **Known limitation**: refreshing the browser page signs the user out (Streamlit sessions are not persistent).
- **Hosting**: first shareable link on Streamlit Community Cloud, with an optional access code, sign-up cap and login
  throttling; a Docker setup is ready for a persistent host. See [deployment.md](deployment.md) and ADR-0016.

## 8. Validation and testing

1. **Correctness tests**: hand-worked unit cases; cross-check against PyPortfolioOpt on identical inputs; every constraint respected.
2. **Behavioural sanity tests**: more risk aversion gives lower volatility; stricter liquidity cover gives lower expected return; no corner weights without a reason.
3. **Walk-forward backtest** (stretch): against equal-weight and 60/40, labelled illustrative.

The tool claims to be internally consistent and defensible, not optimal. The mentor reviews the three personas' outputs.

## 9. Plan

About 10 hours a week. A thin end-to-end slice comes first.

| When | Milestone | Hours |
|---|---|---|
| End of week 2 | Frozen snapshot; returns and shrinkage covariance in a notebook | 20 |
| End of week 4 | Thin slice: one persona through the optimiser to weights on a bare Streamlit page. **Go/no-go checkpoint** | 20 |
| End of week 6 | Constraints, three risk levels, liquidity ladder, cost-of-constraint, explanations | 20 |
| End of week 8 | Risk metrics, four scenarios, the four-tab UI | 20 |
| End of week 10 | Multi-user accounts, per-user profiles, validation layers 1 and 2 | 20 |
| Weeks 11 to 12 | Documentation, test report, demo rehearsal, slack | 20 |

If the thin slice is not working at the end of week 4, scope is cut then, following section 10.

## 10. Cut order if behind

First to drop:

1. Already stretch: Monte Carlo fan chart, walk-forward backtest, online hosting, roles and sharing.
2. Custom scenario sliders (keep the four presets).
3. Self-registration (keep pre-made demo accounts with login).
4. Cost-of-constraint reporting beyond the liquidity constraint.
5. Per-asset lock-in schedules for the illiquid bucket (use one lock-in year).

**Protected, never cut**: the end-to-end path on three personas, the six asset classes, the constrained
optimiser, the four presets, the liquidity ladder, per-user login and profiles, validation layers 1 and 2,
and the documentation.

## 11. Deliverables and demo

- Working prototype (the Streamlit app) and the allocation and recommendation engine.
- Risk, liquidity and scenario analysis.
- The interactive dashboard.
- Documentation: this document, the decision records, a methodology write-up that grows with the code, and a test report generated from the pytest run.
- **Demo**: a scripted walkthrough of about 10 minutes. Log in as one user and take the Legacy-conservative persona through to a recommendation and a stress test; log in as a second user to show profiles are private. Keep a backup screen recording and exported screenshots.

## 12. Out of scope

Real client data; tax, succession and estate planning; multiple entities; multi-currency; international
assets; named securities; live data feeds; any claim of optimality or return promise.

## 13. Risks

| Risk | Mitigation |
|---|---|
| NSE Indices terms forbid automated collection and restrict copying | Manual downloads, private files, consent email in week 1, AMFI fund NAVs as plan B |
| Multi-user work consumes hours | Basic accounts only; cut order #3; week-4 checkpoint |
| Gold ETF unit splits silently corrupt returns | Split adjustment, jump rejection, cross-check against a second ETF |
| Drawdown replay loop is the hardest algorithm | Build it in the thin slice; unit-test it early |
| Basic Python, steep learning curve | Thin slice first; use the installed skills; keep the stack small |
| Single community-run dependency (mfapi) | Mirror raw AMFI history in the private snapshot |
| NSE history may not reach 2008 | Check in week 1; 2016 floor is acceptable |

## 14. Open items to draft or verify

- [x] Modelling gaps G1 to G5 accepted by the project owner on 2026-10-17 (ADR-0013, section 5.8).
- [ ] Review the drafted persona profiles, liquidity haircuts, long-run return assumptions and illiquid defaults in [personas-and-assumptions.md](personas-and-assumptions.md). The numbers are still a draft awaiting approval.
- [ ] Week 1: send the NSE Indices consent email; check how far back each series goes.
- [ ] Week 1: confirm the G-Sec index is a total-return series by comparing its growth with bond yields.
- [ ] Week 1: re-verify the data-lookup findings that were not independently checked (gold ETF unit splits, MoSPI token behaviour, CPI base-year change, repo-rate history).
- [ ] Show NSE Indices' terms of use to the mentor before relying on manual downloads.

## 15. Changes from the original proposal

For feedback from the mentor:

- "Platform" becomes "prototype"; synthetic profiles only.
- Data sources: SEBI removed as a data source; MoSPI added for CPI; RBI limited to the repo rate.
- Multi-user accounts added (not in the original).
- The app is built as a thin slice by week 4 rather than in weeks 9 to 10.
- The walk-forward backtest and Monte Carlo are stretch goals.
- Mid- and small-cap are merged into one class represented by Nifty Midcap 150.

## 16. Decision traceability

| Questions | Topic | Record |
|---|---|---|
| Q2, Q24 | Prototype framing, SEBI posture | [ADR-0001](adr/0001-prototype-on-synthetic-data.md) |
| Q3, Q4, Q21 | Scope, personas, demo path | [ADR-0002](adr/0002-scope-one-archetype-three-personas.md) |
| Q5, Q6 | Asset classes, profile inputs | [ADR-0003](adr/0003-asset-classes-and-profile-inputs.md) |
| Q7, Q22 | Allocation method | [ADR-0004](adr/0004-constrained-mean-variance.md) |
| Q19 | Drawdown limit | [ADR-0005](adr/0005-drawdown-by-historical-replay.md) |
| Q9 | Liquidity model | [ADR-0006](adr/0006-rule-based-liquidity-tiers.md) |
| Q10 | Risk metrics, scenarios | [ADR-0007](adr/0007-risk-metrics-and-scenarios.md) |
| Q11 | Validation | [ADR-0008](adr/0008-validation-strategy.md) |
| Q12, Q20 | App and tooling | [ADR-0009](adr/0009-streamlit-app-and-stack.md) |
| Q13 to Q15 | Multi-user accounts | [ADR-0010](adr/0010-multi-user-local-accounts.md) |
| Q8, Q25 to Q28 | Data sources and handling | [ADR-0011](adr/0011-data-sources-and-handling.md) |
| Q1, Q16 to Q18, Q23 | Plan, cut order, docs, demo | [ADR-0012](adr/0012-delivery-plan-and-cut-order.md) |
| G1 to G5 | Illiquid held fixed, replay valuation, target return, haircuts, inflation indexing | [ADR-0013](adr/0013-illiquid-fixed-and-modelling-conventions.md) |
| Sample feedback | Five-page app, sign-in, profile editor, visual direction | [ADR-0014](adr/0014-app-structure-and-visual-direction.md) |
| Mentor call, 17 Oct | Guided plan and strategies by comfort level (see also [the backlog](backlog-from-mentor-feedback.md)) | [ADR-0015](adr/0015-guided-plan-and-strategies-by-comfort-level.md) |
| Mentor call, 17 Oct | Shareable link, hosting and public-link protections | [ADR-0016](adr/0016-hosting-and-public-link-protections.md) |
