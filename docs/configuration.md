# Configuration reference

Every setting is optional. With none set, the application runs locally with safe defaults. Settings are **environment variables**: nothing
reads a `.env` file by itself (`.env.example` is only a reference list; `python-dotenv` is not installed). Set them in the shell that starts
the server, or in the host's environment-variable settings.

```powershell
# PowerShell: set for this window only, then start the API
$env:FO_API_DOCS = "0"
.\.venv\Scripts\python.exe -m uvicorn api.main:app --port 8100
```

A value that is not a number falls back to the default; a number below the minimum is raised to the minimum. For the on/off switches, only the
exact text shown below changes the default.

## API and shared settings

| Variable | Default | Minimum | Effect |
|---|---|---|---|
| `FO_DB_PATH` | `data/app.db` (inside the project) | n/a | The SQLite file. The API and the Streamlit app share it. Point it at a persistent disk when hosting; the folder must exist and be writable. |
| `FO_MAX_ACCOUNTS` | `200` | 0 | Cap on self-registered accounts (demo copies do not count). Reaching it answers sign-up with "Sign-ups are closed for this preview." `0` closes sign-up. |
| `FO_API_CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | n/a | Comma-separated browser origins allowed to call the API with cookies. Also the allowlist for the `Origin` check on `POST`, `PUT` and `DELETE`. A request whose `Origin` equals the address the server itself sees (scheme and host) also passes, but behind a proxy that address depends on the forwarded headers, so **list the public origin explicitly** (for example `https://fo.example.org`). |
| `FO_API_COOKIE_SECURE` | off | n/a | Exactly `1` marks the session cookie `Secure` and turns on the `Strict-Transport-Security` header. The cookie is also made `Secure` on any request the server sees as HTTPS, but behind a TLS-terminating proxy that depends on the proxy's `X-Forwarded-Proto` header being trusted, so **set this to `1` explicitly whenever the public site is HTTPS**. |
| `FO_API_SESSION_HOURS` | `12` | 0.1 | How long a sign-in lasts. |
| `FO_API_DEMO_LOGIN` | on | n/a | Exactly `0` turns off the one-click demo families (`/api/auth/demo` answers 404 and `/api/meta` lists none). Turn it off for any pilot that holds real data. |
| `FO_API_DEMO_HOURS` | `24` | 0.1 | Age after which a private demo copy is deleted. The clean-up runs when the next visitor starts a demo, not on a timer. |
| `FO_API_MAX_PROFILES` | `25` | 1 | Family profiles one account may hold. |
| `FO_API_MAX_BODY_KB` | `256` | 1 | Largest JSON request body accepted. A holdings file is limited separately to 150 KB (see [holdings-import.md](holdings-import.md)). |
| `FO_API_ANALYSIS_TIMEOUT` | `90` | 1 | Seconds a request waits for the allocation model before answering 503 "busy". |
| `FO_API_DOCS` | on | n/a | Exactly `0` hides the interactive `/docs` page and `/openapi.json`. Hide them on any public host. |

## Assistant question router (optional local model)

| Variable | Default | Effect |
|---|---|---|
| `FO_EMBED` | on | Exactly `0` ignores the local model even when its files are present, so questions are matched by words only. |
| `FO_EMBED_DIR` | `data/models` | Folder holding the model files that `tools/fetch_embedding_model.py` downloaded. The server never downloads anything: if the folder is missing or a file fails its SHA-256 check, the word matcher is used and the server still starts. |

Measured effect of the model: 79% of fresh test questions routed correctly with it, 71% with word matching alone, against a target of 85%
([Phase 6 report](migration/phase-6-report.md)). The safety refusals (advice, predictions, instructions to act, attempts to break the rules)
are fixed patterns and work either way.

## Streamlit app only

| Variable | Default | Effect |
|---|---|---|
| `FO_ACCESS_CODE` | none | If set, visitors must enter this code before seeing anything, including the demo buttons. May also be a Streamlit secret. |

`FO_DB_PATH` and `FO_MAX_ACCOUNTS` are read from the environment first, then from Streamlit secrets (`.streamlit/secrets.toml`).

## Web app (development and preview only)

| Variable | Default | Effect |
|---|---|---|
| `FO_API_URL` | `http://127.0.0.1:8100` | Where the Vite dev server (`npm run dev`) and `vite preview` proxy `/api` to. Read by `web/vite.config.ts` from the environment or `web/.env.local`. It has no effect on a production build: the built files call the relative path `/api`, so the host's reverse proxy decides where that goes ([deployment-react.md](deployment-react.md)). |

Fixed ports, not variables: the dev server uses 5173 (`strictPort`, so it fails rather than moving), `vite preview` 5181. The browser tests
use their own API (8110), dev server (5180) and preview (5181), and a throwaway database at `%TEMP%\fo-e2e.db`, so they never touch a dev
database or a dev server you have open. Port 8100 for the API is a convention of this project (port 8000 was already in use on the
development machine); any free port works if `FO_API_URL` follows.

## Files that hold state or secrets

| Path | What | In git? |
|---|---|---|
| `data/app.db` (+ `-wal`, `-shm`) | Accounts (scrypt password hashes), sessions (hashed tokens), profiles, holdings imports, dashboard choices | No (ignored) |
| `data/models/` | Optional local embedding model, about 66 MB | No (ignored) |
| `data/snapshot/daily_returns.csv` | If present, replaces the synthetic sample returns | No (ignored; may be licensed data, ADR-0011) |
| `.streamlit/secrets.toml` | Streamlit secrets | No (ignored) |
| `.env`, `.env.*` | Not read by anything; ignored in case someone creates one | No (ignored) |

The application has **no API keys, tokens or third-party credentials**: it calls no external service at run time. Nothing in the repository holds
a secret; there is no signing key to rotate (the CSRF token is derived from each session's own token).
