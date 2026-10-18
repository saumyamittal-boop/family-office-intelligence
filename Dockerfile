# Family Office Intelligence: container image for hosting on a VM or a container platform.
# NOTE: written on a machine without Docker, so this file has not been build-tested yet. See docs/deployment.md.
FROM python:3.12-slim

# The accounts database lives on a volume so it survives restarts and new image versions.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    FO_DB_PATH=/data/app.db

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Run as an unprivileged user; the volume must be writable by it.
RUN useradd --create-home --uid 10001 app && mkdir -p /data && chown -R app:app /data /app
USER app
VOLUME ["/data"]
EXPOSE 8501

# Streamlit's built-in health endpoint.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import sys, urllib.request; sys.exit(0 if urllib.request.urlopen('http://localhost:8501/_stcore/health', timeout=4).status == 200 else 1)"

# Optional settings, passed as environment variables at run time: FO_ACCESS_CODE, FO_MAX_ACCOUNTS.
CMD ["streamlit", "run", "app.py", \
     "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true", \
     "--client.toolbarMode=viewer", "--browser.gatherUsageStats=false"]
