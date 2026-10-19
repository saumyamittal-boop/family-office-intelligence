# Family Office Intelligence (prototype)

A capital-allocation decision-support app for a family office: see the whole picture, get a buy and sell plan
towards a mix that fits your limits, check risk and liquidity, and stress-test the plan. Built from
[docs/requirements.md](docs/requirements.md).

**Important**
- The market data is **synthetic sample data** (`fo/data.py`), not real NSE, AMFI or RBI data.
- The three demo families are fictional, and their numbers are drafts (docs/personas-and-assumptions.md).
- Output is an **illustrative simulation, not investment advice**. Use synthetic data only; never enter real
  client data or reuse a real password.

## Set up on a new machine (Windows PowerShell)

```powershell
cd D:\family-office-intelligence
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
```

(`requirements.txt` is the runtime set that a host installs; `requirements-dev.txt` adds the test tools.)

## Run it (Windows PowerShell)

```powershell
cd D:\family-office-intelligence
.\.venv\Scripts\Activate.ps1
streamlit run app.py
```

Then open http://localhost:8501.

## Signing in

- **Explore a demo family** with one click on the login screen (Legacy-conservative, Business-heavy,
  Next-gen growth, and the ₹1,000 Cr liquidity-gap example, which opens with the stricter liquidity cover on so
  its shortfall shows at once). Demo accounts have no password.
- **Create your own account** on the "Create account" tab. Passwords are hashed with scrypt and stored in a
  local SQLite file (`data/app.db`). Each account sees only its own profiles.
- Refreshing the browser page signs you out. That is how Streamlit sessions work; it is a known limitation.

## What is in the app

| Page | What it does |
|---|---|
| **Overview** | Family corpus and projection, allocation donut, the buy and sell plan, key numbers, insights, planned outflows |
| **Plan my money** | A six-step guided flow in plain language (wealth, spending, upcoming commitments, comfort with a bad year, safety net, what you own), ending in Strategy A, B and C with typical-year range, worst year, a 2020-style crash, and what to buy. New accounts start here |
| **Recommendation** | Choose Growth, Balanced or Defensive; see the allocation, the action plan with amounts, why, and a comparison with the current mix |
| **Risk and liquidity** | Drawdown against your limit, historical replay, CVaR, and a year-by-year liquidity ladder |
| **Scenarios** | Five preset stress tests, a build-your-own scenario, and a side-by-side comparison of your current mix and the three options under any of them |
| **Family profile** | Edit every input (corpus, holdings, outflows, limits, illiquid assets, targets); keep several profiles per account |

The sidebar switches between your profiles and has a "Stricter liquidity cover" toggle.

## React + FastAPI version (branch `react-migration`, Phase 2 of 8)

A new front end (React, Vite, TypeScript) and back end (FastAPI) over the same engine. Streamlit stays on `main`.
Decisions: [ADR-0017](docs/adr/0017-react-fastapi-migration.md). Status and evidence:
[Phase 1](docs/migration/phase-1-report.md) and [Phase 2](docs/migration/phase-2-report.md). Look and feel: [docs/design-system.md](docs/design-system.md).
Protected assumptions: [docs/protected-assumptions.md](docs/protected-assumptions.md).

Needs Python 3.12 and Node 24 (npm 11). One-time setup:

```powershell
cd D:\family-office-intelligence
.\.venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-api.txt -r requirements-dev.txt
cd web
npm install
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

Open http://localhost:5173. The API docs are at http://127.0.0.1:8100/docs. Settings are listed in
[.env.example](.env.example); none is required. The database defaults to `data/app.db`, shared with the Streamlit app.

Checks (all should pass):

```powershell
.\.venv\Scripts\python.exe -m pytest -q            # engine, golden master, API, security, Streamlit app
cd web
npm run typecheck; npm test; npm run build         # types, component tests, production build
```

After changing an API model: `python tools/export_openapi.py`, then `npm run gen:api` in `web/`
(`tests/test_openapi_contract.py` fails until you do).

## Put it online

See [docs/deployment.md](docs/deployment.md): options, the recommended route (Streamlit Community Cloud), step-by-step
instructions, and the known limits. Optional settings, supplied as environment variables or Streamlit secrets:

| Setting | Effect |
|---|---|
| `FO_ACCESS_CODE` | Visitors must enter this code before seeing anything, including the demo buttons |
| `FO_MAX_ACCOUNTS` | Cap on self-registered accounts (default 200) |
| `FO_DB_PATH` | Where the SQLite database lives (use a persistent volume when hosting) |

## Run the tests

```powershell
cd D:\family-office-intelligence
.\.venv\Scripts\python.exe -m pytest -q
```

## Layout

| Path | Purpose |
|---|---|
| `app.py` | Entry point: theme, sign-in gate, top navigation, sidebar |
| `app_pages/` | The pages, the login screen and the optional access-code gate |
| `fo/engine.py` | Estimation, constrained optimiser, drawdown replay, liquidity, scenarios, action plan, insights |
| `fo/accounts.py` | Accounts and per-user profile storage (SQLite, scrypt) |
| `fo/session.py` | Shared state and cached analysis for the pages |
| `fo/settings.py`, `fo/security.py` | Deployment settings; login and access-code throttling |
| `Dockerfile`, `.dockerignore` | Container setup for a persistent host (not yet build-tested) |
| `fo/ui.py` | Look and feel: CSS, cards, rows, pills, charts |
| `fo/data.py` | Synthetic sample returns; loads a real snapshot if `data/snapshot/daily_returns.csv` exists |
| `fo/personas.py` | Profile model, the three demo families, serialisation |
| `.streamlit/config.toml` | Theme: Inter font, one green accent, large radii, pill buttons |
| `fo/profile_form.py` | Profile validation rules shared by the Streamlit page and the API |
| `api/` | FastAPI backend: routers, schemas, sessions, migrations, cached engine service |
| `web/` | React + Vite + TypeScript front end and its generated API types |
| `tools/` | Golden-master, OpenAPI and formatter-vector generators |
| `tests/` | Engine, golden master, accounts, API, security and end-to-end app tests |
| `docs/` | Requirements, decision records, protected assumptions, migration reports |

## Look and feel

The style is inspired by IndMoney's public website: white canvas, near-black text, one green accent, soft
cards and pill buttons. Only layout and style patterns are borrowed; there are no logos, names or assets.

## Known simplifications and limits

- The three risk levels sit 75%, 50% and 25% of the way, in volatility, from the lowest-risk to the
  highest-return mix the class limits allow (a refinement of ADR-0004).
- The sample data is calibrated so each class's realised average return equals its target (12%, 14%, 7%, 8%,
  6%). That is a property of the sample, not evidence about real markets.
- The drawdown replay holds constant weights (daily rebalancing) with no costs; illiquid holdings accrue
  smoothly, so real drawdowns would look worse.
- Scenario shock sizes are fixed placeholders; the full build calibrates them from the data snapshot.
- With the drafted personas, the liquidity-cover constraint never binds (the class limits already keep far
  more than the needed cash counted). How to fix that is still to be decided with the project owner.
- Not built yet: a real data snapshot, the walk-forward backtest, the cross-check against PyPortfolioOpt,
  password reset, and staying signed in across a browser refresh.
