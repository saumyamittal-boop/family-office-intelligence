"""Sign up, sign in, sign out, private demo families, and "who am I"."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response

from fo import accounts

from .. import deps, sessions
from .. import schemas as s
from ..config import Settings
from ..errors import ApiError

router = APIRouter(prefix="/api/auth", tags=["auth"], responses=s.ERRORS)

NOT_FOUND_OR_WRONG = "Wrong username or password."


def _default_basis(user: dict) -> str:
    """The demo family built around a liquidity gap opens with the stricter cover on, as in the Streamlit app."""
    parts = user["username"].split("-")
    return "strict" if user["is_demo"] and len(parts) == 3 and parts[1] in accounts.STRICT_COVER_DEMOS else "all"


def _open_session(user: dict, request: Request, response: Response, cfg: Settings) -> s.SessionOut:
    """A fresh token every time. The one this browser held before (if any) is retired, so nothing planted earlier survives a sign-in."""
    sessions.destroy(deps.session_token(request))
    sessions.purge_expired()
    token = sessions.create(user["id"], cfg.session_hours)
    response.set_cookie(
        sessions.COOKIE, token, max_age=int(cfg.session_hours * 3600), httponly=True, samesite="lax",
        secure=cfg.cookie_secure or request.url.scheme == "https", path="/",  # never in the clear over https, whether or not the flag was set
    )
    return s.SessionOut(
        user=s.UserOut(**user), csrf_token=sessions.csrf_for(token), default_basis=_default_basis(user)
    )


def _wait_message(seconds: float) -> str:
    minutes = max(1, round(seconds / 60))
    return f"Too many attempts. Try again in about {minutes} minute{'s' if minutes != 1 else ''}."


def _check(throttle, key: str) -> None:
    wait = throttle.blocked_for(key)
    if wait > 0:
        raise ApiError(429, _wait_message(wait), headers={"Retry-After": str(int(wait) + 1)})


@router.post("/login", response_model=s.SessionOut)
def login(body: s.Credentials, request: Request, response: Response, cfg: Settings = Depends(deps.settings)):
    limits = request.app.state.throttles
    ip, name = deps.client_ip(request), body.username.strip().lower()
    _check(limits["login_user"], name)
    _check(limits["login_ip"], ip)
    user = accounts.authenticate(body.username, body.password)
    if user is None:
        limits["login_user"].record_failure(name)
        limits["login_ip"].record_failure(ip)
        raise ApiError(401, NOT_FOUND_OR_WRONG)
    limits["login_user"].reset(name)
    return _open_session(user, request, response, cfg)


@router.post("/signup", response_model=s.SessionOut, status_code=201)
def signup(body: s.Credentials, request: Request, response: Response, cfg: Settings = Depends(deps.settings)):
    limits = request.app.state.throttles
    ip = deps.client_ip(request)
    _check(limits["signup_ip"], ip)
    limits["signup_ip"].record_failure(ip)  # every attempt counts, successful or not
    try:
        user = accounts.create_user(body.username, body.password, max_accounts=cfg.max_accounts)
    except ValueError as err:
        raise ApiError(422, str(err)) from None
    return _open_session(user, request, response, cfg)


@router.post("/demo", response_model=s.SessionOut)
def demo(body: s.DemoRequest, request: Request, response: Response, cfg: Settings = Depends(deps.settings)):
    """A private, throwaway copy of a demo family: edits never reach anyone else's copy."""
    if not cfg.demo_login:
        raise ApiError(404, "Not found.")
    limits = request.app.state.throttles
    ip = deps.client_ip(request)
    _check(limits["demo_ip"], ip)
    limits["demo_ip"].record_failure(ip)
    accounts.purge_throwaways(cfg.demo_hours)
    user = accounts.create_throwaway_demo(body.family)
    if user is None:
        raise ApiError(404, "Not found.")
    return _open_session(user, request, response, cfg)


@router.get("/me", response_model=s.SessionOut)
def me(request: Request, user: dict = Depends(deps.current_user)):
    token = deps.session_token(request)
    return s.SessionOut(user=s.UserOut(**user), csrf_token=sessions.csrf_for(token), default_basis=_default_basis(user))


@router.post("/logout", status_code=204)
def logout(request: Request, response: Response, user: dict = Depends(deps.user_with_csrf)):
    sessions.destroy(deps.session_token(request))
    response.delete_cookie(sessions.COOKIE, path="/")
