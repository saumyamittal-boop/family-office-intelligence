# The shared demo (React web app + FastAPI + password gate) as one container, for Render's free web service.
# Build context: the repository root. On Render: Language "Docker", Dockerfile path "deploy/cloud/Dockerfile".
# NOTE: written on a machine without Docker; the first build-test is Render's own build.

# 1. Build the web app (web/dist). Node is needed only here.
FROM node:24-slim AS web
WORKDIR /src/web
COPY web/package.json web/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY web/ ./
RUN npm run build

# 2. The server: the app's Python packages, the code it runs, and the built web app. No database, no market snapshot
#    (the app then uses its built-in synthetic sample, as the laptop demo does), no tests or docs.
FROM python:3.12-slim
# FO_EMBED=0: Render's free plan has 512 MB of memory and the assistant's language model alone takes about 250 MB, so it is off and the
# assistant uses its word matcher (the API runs fine without the model; see requirements-api.txt). On a bigger plan, remove it.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    FO_EMBED=0
WORKDIR /app
COPY requirements.txt requirements-api.txt ./
RUN pip install -r requirements.txt -r requirements-api.txt
COPY api/ api/
COPY fo/ fo/
COPY demo/gate.py demo/gate.py
COPY deploy/cloud/ deploy/cloud/
COPY --from=web /src/web/dist web/dist

RUN useradd --create-home --uid 10001 app && chown -R app:app /app
USER app

# The host sets $PORT (Render: 10000). The password comes from FO_GATE_PASSWORD, set in the host's environment variables.
CMD ["python", "deploy/cloud/run.py"]
