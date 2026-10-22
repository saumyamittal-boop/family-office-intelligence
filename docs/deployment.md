# Deployment guide

> This guide is for the **Streamlit app on `main`**. For the React + FastAPI version (branch `react-migration`) see
> [deployment-react.md](deployment-react.md). The opening paragraphs below were written before the Streamlit app was deployed on 18 Oct 2026;
> the section "Deployed on 18 Oct 2026" is the current state.

Goal: give the mentor a link he can open on any day, as he asked on the 17 Oct call. The app is ready to deploy
(see "What is already done"). What is left needs **your accounts and decisions**: a GitHub account, a hosting
choice, and whether the link should be private. Nothing has been published or pushed.

## What is already done

| Item | State |
|---|---|
| Pinned runtime dependencies | `requirements.txt` (runtime only); tests need `requirements-dev.txt` |
| Repository hygiene | `.gitignore` keeps the user database, the licensed market snapshot (`data/snapshot/`) and secrets out of any repo |
| Optional access code | `FO_ACCESS_CODE`: nothing, not even the demo buttons, is reachable without it |
| Sign-up cap | `FO_MAX_ACCOUNTS` (default 200); demo families do not count |
| Login and code throttling | 5 wrong passwords for a username, or 8 wrong access codes, locks that key for 10 minutes |
| Configurable database location | `FO_DB_PATH`, for a persistent volume |
| Container setup | `Dockerfile`, `.dockerignore`, health check on `/_stcore/health` (the endpoint answers 200 "ok"). **The image has not been build-tested: Docker is not installed on this machine** |
| Tests | 102 pass, including the gate, throttle and cap |

## The options

| | Streamlit Community Cloud | Your own PC plus a tunnel | VM or container host (Docker) | College server |
|---|---|---|---|---|
| Cost | Free | Free | A few dollars a month | Free if they offer it |
| Setup | About 15 minutes | About 30 minutes | A few hours | Depends on the department |
| Stays up | Sleeps after 12 idle hours; any viewer can wake it | Only while your PC is on and awake | Always on | Depends |
| Accounts survive restarts | **No**: local files can be deleted at any time | Yes | Yes, on a volume | Depends |
| Demo families | Always return on start | Yes | Yes | Yes |
| Privacy | Private app (email viewers) or public plus access code | Public URL plus access code | Public plus access code | Their rules |

### Recommendation

**Use Streamlit Community Cloud for the mentor link now.** It's the fastest route, it costs nothing, and the mentor uses
the demo families, which come back after every restart. Move to a Docker host later if accounts people create must
persist, or if the 12-hour sleep becomes a problem. The team's engineer has also talked to the data-science department; if they offer
a VM with a persistent disk, the Dockerfile is the way to use it.

## Steps for Community Cloud (you do these)

1. **Create a GitHub repository** (for example `family-office-intelligence`). We planned a private one, but ended up using a
   public one: see "Deployed on 18 Oct 2026" below for why.
2. **Push the project.** In PowerShell:
   ```powershell
   cd D:\family-office-intelligence
   git init
   git add .
   git status
   ```
   Read the `git status` list. It must **not** show `.venv`, `data/app.db`, `data/snapshot` or `.streamlit/secrets.toml`.
   If it does, stop and ask. Then:
   ```powershell
   git commit -m "Family Office Intelligence prototype"
   git branch -M main
   git remote add origin https://github.com/<your-username>/family-office-intelligence.git
   git push -u origin main
   ```
3. **Deploy** at share.streamlit.io: sign in with GitHub, choose **Create app**, pick the repo, branch `main`, main file
   `app.py`. In **Advanced settings** choose **Python 3.12** (the pinned packages are built for it; the version can't be
   changed later without redeploying).
4. **Secrets** (same Advanced settings box). Paste, with your own code:
   ```toml
   FO_ACCESS_CODE = "choose-something-only-the-mentor-knows"
   FO_MAX_ACCOUNTS = "100"
   ```
5. **Share.** Either keep the app private and add the mentor's email under Sharing (he signs in with Google or an
   emailed link), or make it public and send him the URL plus the access code. Private apps are limited to one at a time.
6. **Smoke test** from a private browser window: gate (if used), the four demo buttons, Plan my money, and the Scenarios
   comparison for the ₹1,000 Cr example.

**To update:** push to GitHub and the app redeploys. **If it misbehaves:** reboot it from the app's menu, or delete and
redeploy.

## Tell the mentor

- The first visit after a long quiet spell shows a "wake up" button. Press it; it takes a short while.
- Demo families are always there. Accounts created live may disappear when the app restarts.
- All data is synthetic and it is an illustrative simulation, not advice.

## The Docker path (for later; not yet tested)

```powershell
docker build -t family-office .
docker run -p 8501:8501 -v fo-data:/data -e FO_ACCESS_CODE="your-code" family-office
```

The volume `/data` holds the accounts database. Put the container behind HTTPS (a platform that provides it, or a reverse
proxy such as Caddy), back up `/data` regularly, and check the health status before you rely on it. Build it once on a machine
with Docker and fix anything that fails before the mentor depends on it.

## Known limits (be honest about these)

- **Demo accounts have no password.** Anyone who reaches the app can use and edit them. That's the reason for the access
  code. Saving a plan on a demo account changes it for everyone.
- **No password reset or email verification**, and the throttle lives in memory (it resets when the server restarts).
- **Refreshing signs you out**: Streamlit sessions are not persistent.
- **Synthetic data only.** Real client or market data needs the licensing step (ADR-0011) and a privacy review first. If
  real personal financial data is ever involved, India's Digital Personal Data Protection Act, 2023 becomes relevant.
- **Persistent multi-user accounts at scale** need an external database instead of SQLite. That is a later decision.

## Deployed on 18 Oct 2026

- **Live app:** the address is in the owner's Streamlit dashboard, and is deliberately **not written in this public repo**.
  The access-code lockout is shared by all visitors (8 wrong codes lock the gate for 10 minutes), so a stranger who knew the
  address could lock the mentor out by guessing. The random address and the code are the two layers that prevent that.
- **The repository was made public.** Streamlit can only see public repos by default. Deploying a private one needs a GitHub
  OAuth grant described as "full control of private repositories", and that grant covers *every* private repo on the
  account, not just this one. The owner has another private project, so the grant was declined. The repo was checked first:
  no secrets, database, market data or personal names. The access code lives only in Streamlit's Secrets box and the local
  `.env`, so a public repo does not expose it.
- **The access code is what protects the app.** Anyone can read the code on GitHub; nobody can use the app without the code.
- **Python 3.12** was selected (Streamlit offered 3.14 by default; everything was tested on 3.12).
- **Secrets take about a minute to apply after a first deploy.** The very first page load showed the sign-in screen without
  the gate; a reload a minute later showed the gate. Before sharing a link, reload it and confirm the gate appears.
- **To change the access code:** edit the Secrets in the app's settings on share.streamlit.io, reboot the app, and update
  `.env` to match.
- **To update the app:** push to the `main` branch; it redeploys by itself.

## Facts checked on 18 Oct 2026

- Apps with no traffic for 12 hours go to sleep, anyone with view access can wake one, and there is no always-on tier:
  [Manage your app](https://docs.streamlit.io/deploy/streamlit-community-cloud/manage-your-app) and
  [a forum discussion of sleep behaviour](https://discuss.streamlit.io/t/how-to-prevent-the-app-enter-the-sleep-mode/87959/12).
  A forum post from 5 Oct 2026 reports apps stalling at startup after waking in some cases, so expect the odd reboot.
- A private repo gives a private app, viewers are added by email, and domain-wide allow-lists are not supported:
  [Share your app](https://docs.streamlit.io/deploy/streamlit-community-cloud/share-your-app).
- Dependencies come from `requirements.txt` (among others); Python version is chosen at deploy time; secrets are pasted
  in Advanced settings and root-level ones are also exposed as environment variables; local file storage is not guaranteed
  to persist:
  [App dependencies](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/app-dependencies) and
  [Secrets management](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management).
