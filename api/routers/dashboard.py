"""The person's dashboard choice: which four modules, in what order. Always their own, taken from the session."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from .. import dashboard, deps
from .. import schemas as s
from ..errors import ApiError

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"], responses=s.ERRORS)


@router.get("", response_model=s.DashboardOut)
def get_dashboard(user: dict = Depends(deps.current_user)):
    return dashboard.load(user["id"])


@router.put("", response_model=s.DashboardOut)
def save_dashboard(body: s.DashboardIn, user: dict = Depends(deps.user_with_csrf)):
    unavailable = [m for m in body.modules if m not in dashboard.AVAILABLE]
    if unavailable:
        raise ApiError(422, "That module isn't available yet.", [f"modules: {m} arrives in a later phase" for m in unavailable])
    return dashboard.save(user["id"], list(body.modules))


@router.delete("", response_model=s.DashboardOut)
def reset_dashboard(user: dict = Depends(deps.user_with_csrf)):
    """Back to the default four."""
    return dashboard.reset(user["id"])
