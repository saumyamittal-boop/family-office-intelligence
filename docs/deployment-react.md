# Deployment: React + FastAPI version

> **Status: designed, not deployed.** No host has run this version. Nothing here has been run on Linux, macOS or in a container (WSL and Docker
> are not installed on the development machine). Each step below is marked **[verified locally]** (run on the Windows development machine
> during Phase 8), **[verified, simulated]** (checked with a stand-in, such as a header sent by hand) or **[untested]**. Do not host real family data
> until every item in [production-readiness.md](production-readiness.md) is closed or knowingly accepted.

The Streamlit app on `main` has its own guide, [deployment.md](deployment.md) (Streamlit Community Cloud). **Community Cloud cannot host this
version**: it needs a FastAPI process, a reverse proxy and a disk that persists.

## Shape of a deployment

```
 Internet --HTTPS--> reverse proxy (Caddy / nginx / any)
                        |  /        -> static files in web/dist   (with the security headers from web/security-headers.ts)
                        |  /api/*   -> http://127.0.0.1:8100       (one uvicorn process)
                        v
                     uvicorn api.main:app  -->  SQLite file on a persistent disk (FO_DB_PATH)
```

Rules that follow from how the application is built ([architecture.md](architecture.md)):

1. **Exactly one API process** (`--workers 1`, one instance). Rate limits, the result cache and the engine thread live in that process, and SQLite
   is a single file on one disk.
2. **A persistent disk** for the database (and for backups elsewhere).
3. **Same origin.** Serve the web files and `/api` from one host name, so the cookie stays `SameSite=Lax` and no CORS is needed.
4. **HTTPS only**, with `FO_API_COOKIE_SECURE=1` set explicitly. Behind a proxy that terminates TLS the API itself only sees plain HTTP; it learns
   the original scheme from `X-Forwarded-Proto`, and the setting means the cookie is `Secure` whether or not that header arrives.
5. **API bound to `127.0.0.1`** so that only the proxy can reach it.

## 1. Build

On the build machine (Python 3.12, Node 24 with npm 11):

```powershell
# Python side [verified locally on Windows]
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-api.txt
.\.venv\Scripts\python.exe tools\fetch_embedding_model.py     # optional, 66 MB, run here, never on the live server

# Web side [verified locally on Windows]
cd web
npm ci
npm run build                                                 # type-checks, then writes web/dist (about 960 KB of JavaScript, 285 KB gzipped)
```

`web/dist` is the whole front end: static files, no server code. `requirements-dev.txt` and the test tools are not needed on a host.
On Linux the same commands apply with `.venv/bin/python` **[untested]**. `requirements-api.txt` pins versions that include the optional embedding
library; the server starts without the model files (it then matches questions by words only, see [configuration.md](configuration.md)).

## 2. Run the API

```powershell
$env:FO_DB_PATH = "D:\fo-data\app.db"            # persistent folder; it must exist and be writable
$env:FO_API_COOKIE_SECURE = "1"
$env:FO_API_CORS_ORIGINS = "https://fo.example.org"
$env:FO_API_DOCS = "0"
$env:FO_API_DEMO_LOGIN = "0"                      # for anything holding real data
.\.venv\Scripts\python.exe -m uvicorn api.main:app --host 127.0.0.1 --port 8100 --workers 1 --no-server-header
```

[verified locally] for the start, `--no-server-header` (the `Server` header disappears) and the variables taking effect; the HTTPS parts are
[untested] because they need a real certificate. Keep the process alive and restarted with whatever the host provides (a Windows service
wrapper, systemd, a supervisor). Start-up takes about a second longer while the embedding model loads (if its files are present).

**Client address behind the proxy [verified, simulated].** Uvicorn trusts `X-Forwarded-For` from `127.0.0.1` by default, and the application's
per-address limits use the address uvicorn reports. With a proxy on the same machine, a request carrying `X-Forwarded-For: 9.9.9.9` was
counted separately from one carrying `8.8.8.8` (the sign-up limit refused the 11th attempt from the first address and still allowed the second).
This relies on the proxy **overwriting** (Caddy does by default) or appending to that header. If the proxy runs on another machine, add
`--forwarded-allow-ips <proxy address>`; never `*` on a port reachable from outside.

**Health check.** `GET /api/health` returns `{"status":"ok"}` and fails if the database cannot be opened. `HEAD /api/health` answers 405, so
configure probes to use GET.

## 3. Reverse proxy

An example for Caddy **[untested: Caddy is not installed on the development machine]**. Replace the host name, the two paths and keep the headers
identical to `web/security-headers.ts` (a test, `tests/test_docs.py`, compares this block's Content-Security-Policy with that file).

```caddyfile
fo.example.org {
	encode gzip
	root * /srv/fo/web/dist

	header {
		Content-Security-Policy "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'"
		X-Content-Type-Options "nosniff"
		X-Frame-Options "DENY"
		Referrer-Policy "no-referrer"
		Permissions-Policy "camera=(), microphone=(), geolocation=(), payment=(), usb=()"
		Strict-Transport-Security "max-age=15552000"
	}

	handle /api/* {
		reverse_proxy 127.0.0.1:8100 {
			transport http {
				read_timeout 120s
				write_timeout 120s
			}
		}
	}

	handle {
		try_files {path} /index.html
		file_server
	}
}
```

Notes for any proxy: forward `Host`, `X-Forwarded-For` and `X-Forwarded-Proto`; set request-header and body **time-outs** (the application does not
stop a deliberately slow client, [Phase 7 limitation 9](migration/phase-7-report.md)); cap request bodies at the API's own limit or slightly above
(256 KB by default); cache hashed files under `/assets/` for a long time but never `index.html` or any `/api` response (the API already sends
`Cache-Control: no-store`); route every unknown non-API path to `index.html` (the app uses browser routing).

An nginx equivalent is straightforward (`location /api/ { proxy_pass http://127.0.0.1:8100; proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for; ... }`,
`location / { try_files $uri /index.html; add_header ... always; }`) but has not been written out or tested here.

## 4. Smoke test after a deployment

Run these by hand; none has been run against a real host **[untested]**:

1. `GET https://<host>/api/health` returns `{"status":"ok"}` with `Cache-Control: no-store`, and no `Server` header.
2. The home page loads and its response carries the Content-Security-Policy above. The browser console shows no policy violation on any page
   (`web/e2e/csp.spec.ts` proves this against `vite preview`; its address is fixed in the file, so against a real host it has to be edited or the
   check done by eye).
3. Sign-up works, the cookie is `HttpOnly; Secure; SameSite=Lax`, and signing out clears it.
4. `/api/auth/demo` answers 404 when `FO_API_DEMO_LOGIN=0`. FastAPI serves its interactive pages at `/docs` and `/openapi.json`, which the proxy
   above does not forward (only `/api/*` is), so through the proxy those paths return the web app's own page; directly on `127.0.0.1:8100` they
   answer 404 when `FO_API_DOCS=0`. Keep that port closed to the outside either way.
5. Create a profile, open the analysis (about a second), then sign in as a second account and confirm the first account's profile id answers 404.
6. Restart the API process: sign-in survives (sessions live in the database), while rate-limit counters reset (they are in memory).

## 5. Update, rollback, backup

- **Update:** stop the API (or accept a short outage), back up the database ([database.md](database.md)), pull the new code, `pip install`, `npm ci`,
  `npm run build`, start the API (migrations apply automatically), reload the proxy's files.
- **Roll back:** restore the previous code and `web/dist`, and restore the database backup if a migration ran (migrations are forward-only).
- **Back up** the database file regularly with SQLite's backup command and test a restore. **No schedule, off-site copy or restore test exists yet.**

## 6. Hosting choices (not decided)

Any small virtual machine with a persistent disk, a proxy and a process manager fits. Free tiers with ephemeral disks lose all accounts on
restart. The choice of host, domain, TLS, region and backup storage is open, and for real family data it is also a data-protection decision
(who operates the server, where the data sits, who can read the disk). Streamlit's `Dockerfile` in the repository does not apply to this version;
no `Dockerfile` or compose file exists for the API, because none could be built or tested here.
