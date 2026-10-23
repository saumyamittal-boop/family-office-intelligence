# Handover and troubleshooting guide

For whoever picks this project up next (including the project owner in six months). Read [architecture.md](architecture.md) first, then
[setup.md](setup.md) to get it running, then this page when something does not work or you need to change something.

## State of the repository

- Branch **`react-migration`** holds the React + FastAPI version. It has **never been pushed**: there is no upstream; GitHub has only `main`
  (the Streamlit app, which is the live mentor demo). Pushing is the project owner's decision (the GitHub repository is public).
- Work was done in eight approval-gated phases; each has a report in `docs/migration/` (`phase-1-report.md` … `phase-8-report.md`) saying what
  changed, what was tested, what is not done. Decisions are numbered in `docs/adr/` (0017 to 0021 cover the migration).
- `sample-statement.csv` in the project root is the owner's own file (untracked); do not commit or delete it.
- Everything is synthetic. Never put real client data, a real password or a real statement into the database, a test or a document.

## Things you must not change without the project owner

| What | Why | How it is protected |
|---|---|---|
| Any value in the engine's assumptions (inflation, priors, haircuts, risk positions, shock sizes, comfort levels) | They define every number on screen | `tests/golden/engine_golden.json` + `tests/test_golden.py`, `tests/test_api_parity.py`. After an approved change: `python tools/make_golden.py` and a changelog line saying who approved it |
| `tests/golden/questions.txt` splits | They are the unseen test sets for the Assistant's router; tuning on them invalidates the accuracy figure | Hashes pinned in `tests/test_explain_golden.py` |
| `data/app.db` | The live development database, shared with the Streamlit app | Tests use temporary databases; use a **copy** to experiment (`FO_DB_PATH`) |
| The disclaimer wording | "Illustrative simulation, not investment advice…" must stay visible | Web tests check it appears |

## Everyday tasks

| Task | Do this |
|---|---|
| Run it | [setup.md](setup.md) |
| Show it to someone in person | Double-click `demo\start-demo.cmd` (a fresh private database, the built app, a check of every figure the script quotes), follow [demo-script-react.md](demo-script-react.md), stop with `demo\stop-demo.cmd`. If a number on screen changes, `tests/test_demo_script.py` fails until the script is updated |
| Run all checks | `docs/testing.md` |
| Change an API model or add an endpoint | Edit the code, then `python tools/export_openapi.py`, `python tools/export_api_docs.py` (add a one-line purpose for a new operation in that script), and `npm run gen:api` in `web/`. Three tests fail until you do |
| Add a database table or column | New numbered file in `api/migrations/`; see [database.md](database.md) |
| Add a setting | Read it in `api/config.py`, add it to `.env.example` and [configuration.md](configuration.md); `tests/test_docs.py` fails if a `FO_*` name used in code is missing from either |
| Refresh the Assistant's model files | `python tools\fetch_embedding_model.py` (needs internet once) |
| Re-measure the Assistant | `python tools\eval_questions.py` (add `--split heldout\|confirm\|calib\|final`, and `--lexical` for word matching only). The `final` split has been used for its one honest run; an honest new measurement needs a fresh question set written before any tuning ([protocol](migration/phase-6-evaluation-protocol.md)) |
| Back up the database | [database.md](database.md) |

## Troubleshooting

| Symptom | Cause and fix |
|---|---|
| Web app shows "Couldn't answer. Can't reach the server…" or a red banner | The API is not running, or is on another port. Start it (`python -m uvicorn api.main:app --port 8100`) or set `FO_API_URL` to its address and restart `npm run dev` |
| `npm run dev` says port 5173 is in use | Another dev server is running. The port is strict on purpose (the API's default origin list expects 5173). Stop the other one; find it with `Get-NetTCPConnection -LocalPort 5173` |
| API fails to start: address already in use | Something else holds the port. Use another (`--port 8101`) and set `FO_API_URL` to match. Port 8000 is often taken |
| Opening `web/dist/index.html` by double-click shows a blank page | The built app needs a server for `/api` and for page routes. Use `npm run dev`, or `vite preview` (needs the API on `FO_API_URL`), or the proxy in [deployment-react.md](deployment-react.md) |
| Every call returns 403 "could not be verified" | The CSRF header is missing: reload the page to get a fresh token. For scripts, take `csrf_token` from the sign-in response and send it as `X-CSRF-Token`. Also check the `Origin` is in `FO_API_CORS_ORIGINS` |
| Signed out unexpectedly after a deployment | Sessions last 12 hours (`FO_API_SESSION_HOURS`). The cookie is `Secure` over HTTPS: if the site is served over HTTPS but the API thinks it is HTTP, set `FO_API_COOKIE_SECURE=1` |
| 429 "Too many attempts" or "asking very quickly" | A rate limit. Wait `Retry-After` seconds, or restart the API (counters are in memory). Limits are listed in [api.md](api.md) |
| 503 "The allocation model is busy" | Another analysis is running on the single engine thread, or one is stuck. It retries by itself; raise `FO_API_ANALYSIS_TIMEOUT` if the machine is slow |
| API process uses a full CPU core and stops answering analyses | The HiGHS solver hang (Windows, SciPy 1.18.1) when a thread that used it exits. Restart the API. Never run engine code on short-lived threads; see `api/analysis.py` |
| Assistant answers are less strict, or paraphrases are not understood | The optional local model is not in use. Check with `.\.venv\Scripts\python.exe -c "from fo import question_embed as q; print('model active' if q.load() else 'word matcher only')"`. If it says word matcher only: run `tools\fetch_embedding_model.py`, make sure `FO_EMBED` is not `0` and `FO_EMBED_DIR` is right. A "does not match its recorded hash" line in the API's console means a file was altered or incomplete: delete `data/models` and fetch again |
| `fetch_embedding_model.py` fails | It needs internet and about 66 MB. A proxy or firewall may block Hugging Face. The app works without it |
| Holdings upload refused "Excel import is switched off…" | `defusedxml` is not installed. `pip install -r requirements-api.txt` |
| `npm run e2e` fails to start | It needs Microsoft Edge installed, ports 8110, 5180 and 5181 free, and `.venv` at the project root. It builds the web app first, so allow a couple of minutes |
| `npm test` prints "Not implemented: HTMLCanvasElement's getContext()" many times | Harmless noise from the test environment; look at the summary line, not the noise |
| `git status` shows many files modified but `git diff` is empty | Windows line endings (CRLF in the working tree, `eol=lf` in `.gitattributes`). Not a real change; confirm with `git diff --stat` (empty) before worrying |
| `database is locked` | Another process holds a write on `app.db` (a second API, a Streamlit session, a DB browser). Close it. Only one API process should use a file |
| A test fails with a golden-master difference | A number changed. If you did not mean to change one, you changed the engine or its inputs. If you did and it is approved, regenerate with `tools/make_golden.py` and say so in the changelog |
| `test_openapi_contract` or `test_api_docs` fails | Regenerate: `python tools/export_openapi.py`, `python tools/export_api_docs.py`, `npm run gen:api` |
| Streamlit app freezes on "Running…" on Windows | The same HiGHS thread problem; the Streamlit app is not protected. Reload; or use the React version |
| Pip install fails on a very old/new Python | Use Python 3.12 (pins were verified there) and Node 24 with npm 11 |

## Where the documents are

| Question | Document |
|---|---|
| What is this and how is it built? | [architecture.md](architecture.md), [requirements.md](requirements.md) |
| How do I run it? | [setup.md](setup.md) |
| What can I configure? | [configuration.md](configuration.md), `.env.example` |
| What is in the database? | [database.md](database.md) |
| What does the API offer? | [api.md](api.md) (generated) |
| How does the maths work, what are the assumptions? | [methodology.md](methodology.md), [protected-assumptions.md](protected-assumptions.md), [personas-and-assumptions.md](personas-and-assumptions.md) |
| What file can I import? | [holdings-import.md](holdings-import.md) |
| How is it tested? | [testing.md](testing.md) |
| How would I host it? | [deployment-react.md](deployment-react.md) (React version), [deployment.md](deployment.md) (Streamlit) |
| Can it be used with real data? | [production-readiness.md](production-readiness.md) |
| What is missing or wrong? | [limitations.md](limitations.md) |
| What changed and when? | `CHANGELOG.md`, `docs/migration/phase-*-report.md` |
| Why was it decided that way? | `docs/adr/` |
| Look and feel | [design-system.md](design-system.md), [dev-tooling.md](dev-tooling.md) |
| Demo for the mentor | [demo-script.md](demo-script.md) |
