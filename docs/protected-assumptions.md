# Protected financial assumptions

Everything below is frozen by `tests/golden/engine_golden.json` and checked by `tests/test_golden.py` (live engine) and
`tests/test_api_parity.py` (HTTP API). **Changing any of it needs the project owner's explicit approval**, then
`python tools/make_golden.py` and a changelog line saying who approved what. Every number is a **draft placeholder**,
not an externally validated estimate (see [personas-and-assumptions.md](personas-and-assumptions.md)).

## In the engine (`fo/engine.py`)

| Assumption | Value |
|---|---|
| Inflation | 4.5% a year |
| Long-run return priors | Large-cap 11%, mid-cap 12.5%, debt 7%, gold 6.5%, cash 6% |
| Expected return | 50% sample history + 50% prior, per class |
| Covariance | Monthly returns, correlations shrunk towards zero (Schaefer-Strimmer), variances kept |
| Liquidity haircuts | Cash 0%, debt 8%, gold 15%, large-cap 30%, mid-cap 40%; illiquid 100% (never counted) |
| Cover bases | `all` (every class after haircut) and `strict` (cash, debt and gold only) |
| Optimiser | Constrained mean-variance, SLSQP, illiquid bucket held fixed and not optimised |
| Risk levels | Growth / Balanced / Defensive at 75% / 50% / 25% of the volatility range the limits allow |
| Drawdown | Enforced by daily historical replay; risk aversion x1.35 per step, up to 30 steps |
| CVaR | 95%, rolling 21-trading-day windows |
| Target real return | A reported goal, not a constraint |
| Spending | Indexed to inflation; one-off amounts are nominal |
| Stress presets | Equities fall 25%; Market crash (large -35%, mid -45%, debt -2%, gold +5%, illiquid -20%); Inflation and rate spike; Large unexpected expense (8% of corpus); Lost decade (-4% a year) |

## In the guided plan (`fo/plan.py`)

| Assumption | Value |
|---|---|
| Comfort levels | Protect: worst fall 8%, real goal 2%. Balance: 15%, 4%. Grow: 25%, 6% |
| Class limits (share of the liquid part) | Large-cap 0 to 60%, mid-cap 0 to 25%, debt 0 to 80%, gold 0 to 15%, cash 3 to 40% |
| Planning horizon | 25 years (not asked) |
| Safety-net default | 12 months |
| **Illiquid holdings** (not previously listed) | 8% return, 15% volatility, 5-year lock-in, 0.3 correlation with equities |
| Cover basis used | `strict` |

## In the synthetic data (`fo/data.py`)

Seed 42, 2,609 business days from 2016 to 2025, annual means calibrated to 12%, 14%, 7%, 8% and 6%, with a 2020-style
crash and a 2022 rate shock injected. **These are properties of the sample, not evidence about real markets.**

## Known modelling issues (kept visible on purpose)

1. **The liquidity-cover constraint never binds** for the four demo families on either basis (0 of 24 portfolios).
   The class limits already hold far more cover than needed, so the constraint is decorative. How to fix it is an open decision.
2. **Illiquid holdings accrue smoothly** in the drawdown replay, so real drawdowns would look worse.
3. **The guided plan and the analyst pages use different cover bases by default** (strict and all). Results agree today only
   because of issue 1. The API takes the basis explicitly and the screen names the one in force.
4. **"A crash like 2020"** in the guided plan was really the stylised Market crash preset, not a replay of 2020. In the React app (Phase 3) it is
   now "In a severe market crash", with the preset's shocks and "not a replay of any real year" written from the scenario itself. The Streamlit
   wording is unchanged. The change is copy only; the owner was not asked separately, and reverting it is one line (`CRASH_LABEL` in `api/plan_service.py`).
5. **Priors, thresholds and haircuts are provisional.** Passing tests shows the code does what was specified, not that the assumptions are right.
6. **Historical outcomes do not predict future ones**, and nothing here is independently validated or objectively optimal.
7. A **solver failure** used to be silent; it is now flagged (`optimiser_converged`), and in the four demo families every solve converges.
8. **Zero safety-net requirement crashes the scenario step.** `engine.scenario_row` divides by the required cover, which is zero when spending is zero
   and no commitment falls inside the safety-net window, so it raises `ZeroDivisionError` (the Streamlit app would hit it too). The engine is
   unchanged; the API refuses such answers with a clear message (guided plan) or a 422 (stored profile).
