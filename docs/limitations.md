# Status, known limitations and incomplete work

> Illustrative simulation, not investment advice. Results depend on the data, assumptions, and methodology used. Historical outcomes do not
> guarantee future performance.

This page separates what is **built and tested** from what is **partly done** and what is **only planned**. If a capability is not in the first
table, do not assume it exists. The gate for real data is in [production-readiness.md](production-readiness.md).

## 1. Implemented and tested (React + FastAPI, branch `react-migration`)

| Area | What exists | Evidence |
|---|---|---|
| Engine | Estimation, constrained allocation, drawdown replay, CVaR, liquidity cover and ladder, five stress presets plus a custom scenario, action plan, projection, insights | Golden master, parity and invariant tests |
| Accounts | Sign-up, sign-in, sign-out, three demo families plus the liquidity-gap family as private throwaway copies, server-side sessions | `tests/test_api_auth.py`, `tests/test_security_review.py`, browser tests |
| Profiles | Several profiles per account, full editing with the same validation as Streamlit, delete (never the last) | `tests/test_api_profiles.py` |
| Guided plan | Six-step flow ("Plan my money") with live recalculation and three strategies | `tests/test_api_plan.py`, web tests |
| Analyst pages | Recommendation, Risk and liquidity, Scenarios (preset, custom, side-by-side) | `tests/test_api_analyst.py`, web tests |
| Dashboard | Choose and order four of eight modules per account | `tests/test_api_dashboard.py` |
| Holdings import | CSV and Excel (`.xlsx`) preview, confirmed import, consolidation, explicit apply to a profile | `tests/test_holdings_import.py`, `tests/test_api_holdings.py`, [holdings-import.md](holdings-import.md) |
| Assistant | Twenty question types answered from the model's own figures with the evidence for each; fixed refusals for advice, predictions, instructions to act and rule-breaking; no language model; question not stored | `tests/test_explain_*.py`, `tests/test_question_*.py` |
| Web app | Themes (light and dark), responsive layout, keyboard navigation, charts with text alternatives | Web unit tests, `web/e2e` |
| Security controls | See [architecture.md](architecture.md) and the [Phase 7 report](migration/phase-7-report.md) | `tests/test_security_review.py`, `web/e2e/security.spec.ts`, `csp.spec.ts` |
| Documentation | This folder; API reference generated from the code | `tests/test_api_docs.py`, `tests/test_docs.py` |

## 2. Partly done

| Area | What is missing |
|---|---|
| Assistant routing | Matches 79% of fresh questions (bar 85%). The router's local model is optional; with word matching alone it is 71%. It never invents a figure. |
| Accessibility | Automated and keyboard checks only; no manual screen-reader test; no conformance claim. |
| Browser coverage | Edge (Chromium) only. |
| Operating systems | Windows only. Linux and macOS never run. |
| Deployment | Documented ([deployment-react.md](deployment-react.md)); never executed on a host; no container build. |
| Security | Self-reviewed and tested; no outside review. Limitations in [production-readiness.md](production-readiness.md). |
| Streamlit app | Works and is the live mentor demo on `main`; not part of the security review. |

## 3. Not built, or not claimed

- **Real market data ingestion.** Synthetic returns only. A snapshot loader reads a CSV if one is placed on disk; no feed, no licence, no checks.
- **External account integrations.** No bank, broker, depository, aggregator or custodian connection. Statements are uploaded by hand as files.
- **Production authentication.** No password reset, no email verification, no second factor, no single sign-on, no account lock beyond throttling,
  no idle timeout. Password hashing is below today's guidance.
- **Regulatory compliance of any kind.** Nothing is claimed about SEBI, RBI, data-protection law or any other rule. No review has been made.
- **Independent financial validation.** No outside review of the method or assumptions; no out-of-sample backtest; no cross-check against a second
  optimiser (both were planned).
- **Account deletion, data export, audit trail.**
- **Language-model features.** Deliberately deferred.
- **Tax, trading costs, execution or order placement.** The action plan is a pre-tax, pre-cost difference between two mixes.
- **PostgreSQL, multiple server processes, shared rate-limit store, CI, container image for the API, monitoring.**
- **Multi-currency, multi-entity or multi-generation structures.** One family profile = one corpus in rupees crore.

## 4. Known defects and modelling issues

None of these is hidden by the product; each is either shown on screen or refused with a message.

| # | Issue | Effect | Status |
|---|---|---|---|
| 1 | The liquidity-cover constraint never binds for the four demo families (0 of 24 portfolios) | The cover is reported but does not shape the mix for them | Open decision |
| 2 | Guided plan defaults to the `strict` cover basis, analyst pages to `all` | Agree today only because of issue 1; the screen names the basis | Open decision |
| 3 | Zero spending with no commitment in the safety-net window makes the protected engine divide by zero | The API refuses such input with a message; the Streamlit app would crash | Engine unchanged on purpose |
| 4 | SciPy's HiGHS solver can hang when a thread that used it exits (Windows) | The API keeps its engine thread alive; Streamlit runs the solver on short-lived threads and can freeze | Mitigated in the API only |
| 5 | The drawdown replay uses constant weights, no costs, smooth illiquid accrual | Real drawdowns would look worse | By design, documented |
| 6 | Stress shock sizes are fixed placeholders; the crash preset is not a replay of any year | Scenario results are illustrations | By design, documented |
| 7 | `HEAD /api/health` answers 405 | Probes must use GET | Documented |
| 8 | A username can be locked for ten minutes by anyone who guesses wrongly five times | Accepted trade-off | Open |
| 9 | Rate limits reset on restart and are per process | Fine for one process | Documented |
| 10 | Jsdom prints "Not implemented: HTMLCanvasElement's getContext()" lines during `npm test` | Harmless noise from the test environment | Cosmetic |
| 11 | Pillow 12.3.0 has 28 advisories (fixed in 13.0.0) but is capped by Streamlit and fastembed | No code path reaches it | Re-audit before deploying |

No other defect is known at the time of writing. That is a statement about what the tests and the author's manual use found, not a guarantee.

## 5. Decisions waiting for the project owner

1. Which security limitations must close before any real family is invited (recommended: A1, A2, A5, A6, A7 and the proxy items in
   [production-readiness.md](production-readiness.md); A4 after deciding about the shared database).
2. Password-hashing cost and whether the database stays shared with the Streamlit app.
3. How to improve the Assistant's routing (larger embedding model, or collect real questions and re-measure) or accept it as is.
4. Whether to push the branch (needed for a Linux CI run) and how to retire or review the Streamlit app.
5. The liquidity-cover fix, the default cover basis, the "In a severe market crash" wording.
6. The target customer, and a hosting choice.
