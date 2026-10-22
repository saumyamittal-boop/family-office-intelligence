# Family Office Intelligence (prototype)

A capital-allocation decision-support app for a family office: see the whole picture, get a buy and sell plan towards a mix that fits the
family's own limits, check risk and liquidity, and stress-test the plan. Built from [docs/requirements.md](docs/requirements.md) as a BCom
Financial Analytics capstone.

> **Important**
> - **Illustrative simulation, not investment advice.** Results depend on the data, assumptions, and methodology used. Historical outcomes do not
>   guarantee future performance.
> - The market data is **synthetic sample data** (`fo/data.py`), not real NSE, AMFI or RBI data. The three demo families are fictional and their
>   numbers are drafts ([docs/personas-and-assumptions.md](docs/personas-and-assumptions.md)).
> - **Use synthetic data only.** Never enter real client data, a real statement or a real password. Real data stays blocked until the gate in
>   [docs/production-readiness.md](docs/production-readiness.md) is closed. Nothing here claims regulatory compliance, independent validation or
>   production authentication.

## Two versions

| | React + FastAPI | Streamlit |
|---|---|---|
| Branch | `react-migration` (all eight phases built; **not pushed**) | `main` (the live mentor demo) |
| Entry | `api/main.py` + `web/` | `app.py` |
| Docs | everything in [docs/](docs/README.md) | [Streamlit sections below](#streamlit-version-main), [docs/deployment.md](docs/deployment.md) |

Both run the same financial engine (`fo/`). Its numbers are protected by a golden-master test ([docs/protected-assumptions.md](docs/protected-assumptions.md)).

## Quick start: React + FastAPI

Needs Python 3.12 and Node 24 (npm 11) on Windows PowerShell. Microsoft Edge is needed only for the browser tests. Details, timings and
troubleshooting: [docs/setup.md](docs/setup.md).

```powershell
cd D:\family-office-intelligence
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-api.txt -r requirements-dev.txt
.\.venv\Scripts\python.exe tools\fetch_embedding_model.py     # optional: 66 MB local model for the Assistant, fetched once into data\models\
cd web
npm ci
```

Run it in two terminals (the API uses port 8100; 8000 is often taken):

```powershell
# terminal 1: API
cd D:\family-office-intelligence
.\.venv\Scripts\python.exe -m uvicorn api.main:app --port 8100

# terminal 2: web app
cd D:\family-office-intelligence\web
npm run dev
```

Open http://localhost:5173 and pick one of the demo families under "Or explore a demo family". The API's interactive pages are at http://127.0.0.1:8100/docs. Nothing is required
in the way of settings ([docs/configuration.md](docs/configuration.md)); the database defaults to `data/app.db`, shared with the Streamlit app.

Checks (all should pass; results and timings in [docs/testing.md](docs/testing.md)):

```powershell
.\.venv\Scripts\python.exe -m pytest -q            # engine, golden master, API, security, documentation, Streamlit app
cd web
npm run typecheck; npm test; npm run build         # types, component tests, production build
npm run e2e                                        # browser tests in Edge (own ports and a throwaway database)
```

After changing an API model: `.\.venv\Scripts\python.exe tools\export_openapi.py`, `.\.venv\Scripts\python.exe tools\export_api_docs.py`, then
`npm run gen:api` in `web/` (tests fail until you do).

## Documentation

Start at [docs/README.md](docs/README.md). The essentials:

| | |
|---|---|
| [Architecture](docs/architecture.md) | What it is, how it is built, one request end to end |
| [Setup](docs/setup.md) | Clean-machine install, startup, what was verified |
| [Configuration](docs/configuration.md) | Every setting (environment variable) |
| [Database](docs/database.md) | Tables, migrations, backup |
| [API](docs/api.md) | All 32 operations (generated from the code) |
| [Methodology](docs/methodology.md) | The financial method, assumptions and limits |
| [Holdings import](docs/holdings-import.md) | CSV / Excel format and rules |
| [Testing](docs/testing.md) | How to run and extend the tests |
| [Deployment](docs/deployment-react.md) | How a host would run it (designed, not deployed) |
| [Production readiness](docs/production-readiness.md) | What stands between this and real data |
| [Limitations](docs/limitations.md) | Built / partly built / not built; known defects |
| [Handover](docs/handover.md) | Taking over the project; troubleshooting |
| [Change log](CHANGELOG.md) · [Phase reports](docs/migration/phase-8-report.md) · [Decisions](docs/adr/README.md) | History and reasons |

## What is in the app

| Page | What it does | In Streamlit |
|---|---|---|
| **Overview** | Family corpus and projection, allocation, the buy and sell plan, key numbers, insights, planned outflows. In the React version a dashboard of four modules chosen from eight | yes |
| **Plan my money** | A six-step guided flow in plain language (wealth, spending, upcoming commitments, comfort with a bad year, safety net, what you own), ending in Strategy A, B and C with typical-year range, worst year, a severe-crash result, and what to buy. New accounts start here | yes |
| **Recommendation** | Choose Growth, Balanced or Defensive; see the allocation, the action plan with amounts, why, and a comparison with the current mix | yes |
| **Risk and liquidity** | Drawdown against your limit, historical replay, CVaR, and a year-by-year liquidity ladder | yes |
| **Scenarios** | Five preset stress tests, a build-your-own scenario, and a side-by-side comparison of your current mix and the three options under any of them | yes |
| **Family profile** | Edit every input (corpus, holdings, outflows, limits, illiquid assets, targets); keep several profiles per account | yes |
| **Holdings** | Import a statement as CSV or Excel (synthetic files only), see everything consolidated by asset class and account, and choose whether to use it in a profile | React only |
| **Assistant** | Choose or type a question about the family's results and get an answer written from the model's own numbers, with the evidence behind each figure. It never predicts or advises, uses no language model, and does not store the question | React only |

## Streamlit version (`main`)

```powershell
cd D:\family-office-intelligence
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt        # requirements.txt is the runtime set a host installs; -dev adds the test tools
streamlit run app.py                       # then open http://localhost:8501
```

- **Explore a demo family** with one click on the login screen (Legacy-conservative, Business-heavy, Next-gen growth, and the ₹1,000 Cr liquidity-gap
  example, which opens with the stricter liquidity cover on so its shortfall shows at once). Demo accounts have no password.
- **Create your own account** on the "Create account" tab. Passwords are hashed with scrypt and stored in a local SQLite file (`data/app.db`). Each
  account sees only its own profiles. Refreshing the browser page signs you out; that is how Streamlit sessions work.
- The sidebar switches between your profiles and has a "Stricter liquidity cover" toggle.
- **Put it online:** [docs/deployment.md](docs/deployment.md) (recommended route: Streamlit Community Cloud). Optional settings, as environment variables or
  Streamlit secrets: `FO_ACCESS_CODE` (visitors must enter a code first), `FO_MAX_ACCOUNTS` (cap on sign-ups, default 200), `FO_DB_PATH` (where the
  database lives; use a persistent volume when hosting). The `Dockerfile` is for this version only and has not been build-tested.

## Layout

| Path | Purpose |
|---|---|
| `fo/engine.py` | Estimation, constrained optimiser, drawdown replay, liquidity, scenarios, action plan, insights |
| `fo/data.py`, `fo/personas.py`, `fo/plan.py` | Synthetic returns (loads a real snapshot if `data/snapshot/daily_returns.csv` exists), the profile model and demo families, the guided plan |
| `fo/accounts.py`, `fo/security.py`, `fo/settings.py` | Accounts and per-user profiles (SQLite, scrypt); login and request throttling; Streamlit settings |
| `fo/profile_form.py`, `fo/holdings_import.py` | Profile validation and the holdings parser, shared by both front ends and the API |
| `fo/question_*.py` | The Assistant's question router (word matcher, optional local embedding model, hybrid) |
| `api/` | FastAPI back end: routers, schemas, sessions, guards, migrations, cached engine service, Assistant answers |
| `web/` | React + Vite + TypeScript front end, its generated API types and its browser tests (`e2e/`) |
| `app.py`, `app_pages/`, `fo/ui.py`, `fo/session.py`, `.streamlit/` | The Streamlit app |
| `tools/` | Generators (golden master, OpenAPI, API reference, formatter vectors), model fetcher, question evaluation |
| `tests/` | Engine, golden master, accounts, API, security, documentation and Streamlit app tests |
| `docs/` | Documentation, decision records (`adr/`), phase reports (`migration/`) |
| `Dockerfile`, `.dockerignore` | Container setup for the Streamlit app (not build-tested) |

## Look and feel

The style is inspired by IndMoney's public website: white canvas, near-black text, one green accent, soft cards and pill buttons. Only layout
and style patterns are borrowed; there are no logos, names or assets. See [docs/design-system.md](docs/design-system.md).

## Known simplifications and limits

The full, current list is [docs/limitations.md](docs/limitations.md). In short:

- The three risk levels sit 75%, 50% and 25% of the way, in volatility, from the lowest-risk to the highest-return mix the class limits allow
  (a refinement of ADR-0004).
- The sample data is calibrated so each class's realised average return equals its target (12%, 14%, 7%, 8%, 6%). That is a property of the sample,
  not evidence about real markets.
- The drawdown replay holds constant weights (daily rebalancing) with no costs; illiquid holdings accrue smoothly, so real drawdowns would look worse.
- Scenario shock sizes are fixed placeholders, not calibrated from data.
- With the drafted personas, the liquidity-cover constraint never binds (the class limits already keep far more than the needed cash counted). How to
  fix that is still to be decided with the project owner.
- Not built: a real data snapshot, a walk-forward backtest, a cross-check against PyPortfolioOpt, password reset, account deletion and data export,
  encryption at rest, a Linux or container run. See [docs/production-readiness.md](docs/production-readiness.md).
