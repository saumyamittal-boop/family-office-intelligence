"""Request dependencies: who is signed in, and whether a state-changing request carries the CSRF token."""
from __future__ import annotations

import hmac

from fastapi import Depends, Request

from . import sessions
from .analysis import AnalysisService
from .config import Settings
from .errors import ApiError


def settings(request: Request) -> Settings:
    return request.app.state.settings


def service(request: Request) -> AnalysisService:
    return request.app.state.analysis


def session_token(request: Request) -> str | None:
    return request.cookies.get(sessions.COOKIE)


def current_user(request: Request) -> dict:
    """The signed-in user, taken from the server-side session. Never from anything the client sends."""
    user = sessions.lookup(session_token(request))
    if user is None:
        raise ApiError(401, "Please sign in.")
    return user


def user_with_csrf(request: Request, user: dict = Depends(current_user)) -> dict:
    """For POST/PUT/DELETE: the signed-in user, plus proof the request came from our own page."""
    sent = request.headers.get(sessions.CSRF_HEADER, "")
    expected = sessions.csrf_for(session_token(request) or "")
    if not hmac.compare_digest(sent.encode("utf-8"), expected.encode("utf-8")):
        raise ApiError(403, "This request could not be verified. Reload the page and try again.")
    return user


def client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"
