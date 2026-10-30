# Putting the 24 Oct version online (Render, free)

This puts the version the mentor saw (commit 469682f) at a permanent address, `https://<name>.onrender.com`, behind one shared password. The app is the same as the laptop demo. The data is the built-in synthetic sample, and every demo family is a private throwaway copy. Nothing in the app code changed. This folder adds only:

- the start script, `run.py`;
- a small web server, `static_site.py`;
- the container recipe, `Dockerfile`;
- a zip builder for Azure, `make_package.py`, which isn't needed for Render.

**What the free plan means**

- **No card is needed.** The service gets 512 MB of memory. The app uses about 240 MB with the assistant's language model switched off (`FO_EMBED=0` in the Dockerfile). Without the model, the assistant matches questions with its word matcher instead, which is a little less sharp than on 24 Oct. Everything else is the same.
- **It sleeps after 15 minutes without visitors.** The next visit wakes it, which takes about a minute or two. Open the link a few minutes before a meeting.
- **It has a small share of a processor,** so pages and analyses are slower than on the laptop.
- **Accounts reset on every restart.** The database lives in `/tmp` on purpose, like the laptop demo's fresh database. The demo families always come back.

## Steps

1. **Code on GitHub** (done by Claude once you approve). The `deploy-cloud` branch, which is the 24 Oct code plus this folder, is pushed to `saumyamittal-boop/family-office-intelligence`. The repository is public, so this code becomes visible there. `main` (the Streamlit app) is not touched.
2. **You: create the account.** Sign up at https://render.com. "Sign up with GitHub" is simplest because it also links the repository.
3. **You: create the service.** Click **New > Web Service**, pick the `family-office-intelligence` repository, and fill in:

   | Field | Value |
   |---|---|
   | Name | For example `fo-intelligence-demo`. This becomes the address. |
   | Branch | `deploy-cloud` |
   | Language | Docker |
   | Dockerfile Path (under Advanced) | `deploy/cloud/Dockerfile` |
   | Instance Type | Free |
   | Environment Variables | `FO_GATE_PASSWORD` set to a password you choose |

   Then click **Create Web Service**. The first build takes about 10 to 15 minutes. Wait until the log says `Serving on port 10000`.
4. **Open it.** Go to `https://<name>.onrender.com`, enter any user name and your password, and pick a demo family.

If it does not start, the **Logs** tab says which part stopped.

## Azure instead (paid tier from the student credit, model on)

`make_package.py` builds `..\foi-azure-package\fo-azure.zip` for Azure App Service. To set it up:

1. Create a Web App with Python 3.12, Linux and Basic B1, in a region your subscription allows.
2. Set `FO_GATE_PASSWORD`, and set `SCM_DO_BUILD_DURING_DEPLOYMENT=true`.
3. Set the startup command to `python deploy/cloud/run.py`.
4. Upload the zip with `az webapp deploy --type zip` from Cloud Shell.

B1 costs about US$13 a month from the US$100 credit. Stopping the app does not stop the charge; scale the plan down to Free F1 or delete the resource group.
