"""The FastAPI application.

Run locally:  uvicorn api.main:app --port 8100
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from fo.data import load_returns
from fo.security import Throttle

from . import db, errors
from .analysis import AnalysisService
from .config import Settings
from .routers import auth, meta, profiles

UNSAFE = {"POST", "PUT", "PATCH", "DELETE"}


def _throttles() -> dict[str, Throttle]:
    # In memory and per process, like the Streamlit app's. A shared store is a Phase 7 item.
    return {
        "login_user": Throttle(5, 600),
        "login_ip": Throttle(30, 600),
        "signup_ip": Throttle(10, 3600),
        "demo_ip": Throttle(30, 3600),
    }


def create_app(settings: Settings | None = None) -> FastAPI:
    cfg = settings or Settings.from_env()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        db.migrate()
        daily, source = load_returns()
        app.state.analysis = AnalysisService(daily, source, cfg.analysis_timeout)
        yield
        app.state.analysis.close()

    app = FastAPI(
        title="Family Office Intelligence API", version="0.1.0", lifespan=lifespan,
        docs_url="/docs" if cfg.docs else None, redoc_url=None, openapi_url="/openapi.json" if cfg.docs else None,
    )
    app.state.settings = cfg
    app.state.throttles = _throttles()
    errors.install(app)

    allowed_origins = set(cfg.cors_origins)

    @app.middleware("http")
    async def guard(request: Request, call_next):
        if request.method in UNSAFE:
            raw_length = request.headers.get("content-length", "0")
            length = int(raw_length) if raw_length.isdigit() else 0
            if length > cfg.max_body_bytes:
                return JSONResponse({"detail": "That request is too large.", "problems": None}, status_code=413)
            if length > 0 and not request.headers.get("content-type", "").lower().startswith("application/json"):
                return JSONResponse({"detail": "Send JSON.", "problems": None}, status_code=415)
            origin = request.headers.get("origin")
            if origin and origin not in allowed_origins and origin != f"{request.url.scheme}://{request.headers.get('host', '')}":
                return JSONResponse({"detail": "This origin is not allowed.", "problems": None}, status_code=403)
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        if request.url.path.startswith("/api"):
            response.headers["Cache-Control"] = "no-store"
        return response

    app.add_middleware(
        CORSMiddleware, allow_origins=list(cfg.cors_origins), allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"], allow_headers=["Content-Type", "X-CSRF-Token"],
    )

    app.include_router(meta.router)
    app.include_router(auth.router)
    app.include_router(profiles.router)
    return app


app = create_app()
