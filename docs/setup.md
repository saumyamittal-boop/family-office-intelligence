# Installation and local setup

How to get the React + FastAPI version running on a clean Windows machine, and how to confirm it works. Every command below was run from a
**fresh clone** of the repository during Phase 8 (record in section 6). Linux and macOS have not been tried; see [limitations.md](limitations.md).

## 1. Requirements

| Needed | Version verified | Used for |
|---|---|---|
| Windows 10/11 and PowerShell | Windows 11, PowerShell 5.1 | everything (paths in this guide are Windows paths) |
| Python | 3.12.10 | engine and API (pins were resolved on 3.12; other versions untested) |
| Node.js and npm | 24.21.0 and 11.19.0 | web app build and tests |
| Microsoft Edge | already installed | browser tests only (`npm run e2e`); nothing is downloaded |
| Git | any recent | getting the code |
| Internet | once | installing packages and, optionally, the 66 MB model |

About 1 GB of disk once installed (measured: `.venv` 671 MB, `web/node_modules` 206 MB, model 65 MB, the code itself a few MB).

## 2. Get the code

```powershell
git clone --branch react-migration <path or address of the repository> D:\family-office-intelligence
cd D:\family-office-intelligence
```

The branch `react-migration` exists only on the machine it was made on (it has not been pushed); clone from that folder or copy it. The Streamlit
app is on `main`.

## 3. Install

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-api.txt -r requirements-dev.txt
.\.venv\Scripts\python.exe tools\fetch_embedding_model.py
cd web
npm ci
```

| Step | What it does | Took (verified) |
|---|---|---|
| `python -m venv .venv` | Private Python environment in the project folder. The browser tests expect it exactly there | 10 s |
| `pip install …` | `requirements.txt` (engine, Streamlit), `requirements-api.txt` (FastAPI, Excel reading, the optional embedding library), `requirements-dev.txt` (pytest). All versions are pinned | 2 min 20 s |
| `fetch_embedding_model.py` | **Optional.** Downloads the 66 MB model that lets the Assistant understand paraphrases into `data\models\` and checks its SHA-256. Without it the Assistant still works with word matching, which is less accurate (71% against 79% on the test questions) | 22 s |
| `npm ci` | Installs exactly the versions in `package-lock.json`. Use `npm ci`, not `npm install`, which may change the lock file | 32 s |

No database setup is needed: the API creates `data\app.db`, applies the numbered migrations and seeds the demo families the first time it starts
([database.md](database.md)). No `.env` file is read; settings are environment variables and all are optional ([configuration.md](configuration.md)).

**A note on `python`.** Throughout these documents a command that starts with `python` means the project's own interpreter: either run
`.\.venv\Scripts\Activate.ps1` once in the terminal (then `python` and `pip` are the project's), or write `.\.venv\Scripts\python.exe` in full, as
the commands above do. The system Python does not have the packages.

## 4. Start it

Two terminals.

```powershell
# terminal 1: the API (port 8100; 8000 is often taken)
cd D:\family-office-intelligence
.\.venv\Scripts\python.exe -m uvicorn api.main:app --port 8100

# terminal 2: the web app (port 5173, which is fixed)
cd D:\family-office-intelligence\web
npm run dev
```

Then open http://localhost:5173. The dev server forwards `/api` to the API, so the browser sees one origin. If the API runs elsewhere, set
`FO_API_URL` (see [configuration.md](configuration.md)). The API's interactive documentation is at http://127.0.0.1:8100/docs.

First start takes a few seconds longer (database creation, loading the model). In the API terminal you should see `Application startup complete.`

## 5. Check that it works

By hand (1 minute):

1. `http://127.0.0.1:8100/api/health` shows `{"status":"ok"}`.
2. `http://localhost:5173` shows the sign-in page with the note "Prototype with synthetic data only."
3. Choose a demo family, open **Recommendation**: three allocations appear within a couple of seconds, with the disclaimer
   "Illustrative simulation, not investment advice."
4. Open **Assistant**, click "Is my liquidity enough?": an answer appears with an "evidence" list.

Automatically (about 10 minutes in total on a quiet development laptop; see [testing.md](testing.md) for what each proves):

```powershell
.\.venv\Scripts\python.exe -m pytest -q
cd web
npm run typecheck
npm test
npm run build
npm run e2e
```

## 6. Clean-room verification record (Phase 8, 2026-10-22)

The repository was cloned afresh into an empty folder (`git clone --branch react-migration`, committed state only: no `data\app.db`, no model, no
`node_modules`, no `.venv`) and the steps of sections 3 and 5 were run in order. Results:

| Step | Result | Time |
|---|---|---|
| clone | ok | 2 s |
| venv | ok | 10 s |
| pip install | ok | 139 s |
| fetch model | ok | 22 s |
| npm ci | ok | 32 s |
| `npm run typecheck` | ok (app and browser-test configs) | 18 s |
| `npm test` | 548 passed in 24 files | 126 s |
| `npm run build` | ok, `dist` about 960 KB of JavaScript (285 KB gzipped); chunk-size warning is expected | 16 s |
| `pytest` | 774 passed, 1 expected failure (the documentation tests added later bring this to 900) | 875 s (the laptop was also busy with other jobs) |
| `npm run e2e` | first run 28 passed, 1 failed (a slow page load while the laptop was busy); second run on a quiet machine 29 passed | 172 s, then 78 s |

Problems found while doing this, and what was done about them:

| Problem | Fix |
|---|---|
| The README said `npm install`; that can rewrite the lock file | README and this guide now say `npm ci` |
| `.env.example` said "copy to .env"; **nothing reads a `.env` file** (python-dotenv is not installed) | `.env.example` and [configuration.md](configuration.md) now say settings are environment variables, with examples; a test fails if a setting is missing from either |
| `FO_EMBED`, `FO_EMBED_DIR` and `FO_API_URL` were read by the code but undocumented | Added to both; `tests/test_docs.py` now checks every `FO_*` name in the code |
| The README mixed the Streamlit and React instructions and still said "Phase 6 of 8" | README restructured around two clearly separated versions |

Not covered by the clean room: Linux, macOS, a different Python or Node version, a machine without Edge (the browser tests need it), and a host
other than the development laptop.
