"""API settings, read from environment variables. Every one is optional; local development needs none.

FO_API_CORS_ORIGINS    Comma-separated browser origins allowed to call the API with cookies.
                       Default: the Vite dev server (http://localhost:5173 and http://127.0.0.1:5173).
FO_API_COOKIE_SECURE   "1" to mark the session cookie Secure. Set it whenever the site is served over HTTPS.
FO_API_SESSION_HOURS   How long a sign-in lasts (default 12).
FO_API_DEMO_LOGIN      "0" turns off the one-click demo families (default on; turn off for any real-data pilot).
FO_API_DEMO_HOURS      How long a private demo copy lives before it is deleted (default 24).
FO_API_MAX_PROFILES    Family profiles one account may hold (default 25).
FO_API_MAX_BODY_KB     Largest JSON request body accepted (default 256).
FO_API_ANALYSIS_TIMEOUT  Seconds a request waits for the allocation model before answering "busy" (default 90).
FO_API_DOCS            "0" hides the interactive /docs page and the OpenAPI file (default on locally).
FO_MAX_ACCOUNTS        Cap on self-registered accounts (default 200; same setting as the Streamlit app).
FO_DB_PATH             SQLite file (same setting as the Streamlit app).
"""
from __future__ import annotations

import os
from dataclasses import dataclass

DEFAULT_ORIGINS = ("http://localhost:5173", "http://127.0.0.1:5173")


def _number(name: str, default: float, minimum: float = 0.0) -> float:
    try:
        return max(minimum, float(os.environ.get(name) or default))
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    cors_origins: tuple[str, ...] = DEFAULT_ORIGINS
    cookie_secure: bool = False
    session_hours: float = 12.0
    demo_login: bool = True
    demo_hours: float = 24.0
    max_profiles: int = 25
    max_body_bytes: int = 256 * 1024
    max_accounts: int = 200
    docs: bool = True
    analysis_timeout: float = 90.0

    @classmethod
    def from_env(cls) -> "Settings":
        origins = tuple(o.strip() for o in (os.environ.get("FO_API_CORS_ORIGINS") or "").split(",") if o.strip())
        return cls(
            cors_origins=origins or DEFAULT_ORIGINS,
            cookie_secure=os.environ.get("FO_API_COOKIE_SECURE") == "1",
            session_hours=_number("FO_API_SESSION_HOURS", 12.0, 0.1),
            demo_login=os.environ.get("FO_API_DEMO_LOGIN", "1") != "0",
            demo_hours=_number("FO_API_DEMO_HOURS", 24.0, 0.1),
            max_profiles=int(_number("FO_API_MAX_PROFILES", 25, 1)),
            max_body_bytes=int(_number("FO_API_MAX_BODY_KB", 256, 1) * 1024),
            max_accounts=int(_number("FO_MAX_ACCOUNTS", 200, 0)),
            docs=os.environ.get("FO_API_DOCS", "1") != "0",
            analysis_timeout=_number("FO_API_ANALYSIS_TIMEOUT", 90.0, 1.0),
        )
