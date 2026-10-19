"""The guided plan: the questions, a live preview, three strategies, and saving one."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response

from .. import convert, deps, plan_service
from .. import plan_schemas as p
from .. import schemas as s
from ..analysis import AnalysisService, AnalysisTimeout
from ..config import Settings
from ..errors import ApiError

router = APIRouter(prefix="/api/plan", tags=["plan"], responses=s.ERRORS)


def _busy(request: Request, user: dict) -> None:
    """A person can ask for at most 40 strategy calculations a minute (cached repeats are cheap, new ones take seconds)."""
    limit = request.app.state.throttles["plan_user"]
    key = str(user["id"])
    wait = limit.blocked_for(key)
    if wait > 0:
        raise ApiError(429, "You are recalculating very quickly. Wait a few seconds and try again.", headers={"Retry-After": str(int(wait) + 1)})
    limit.record_failure(key)


@router.get("/config", response_model=p.PlanConfigOut)
def plan_config():
    """The questions, choices and bounds. Public: it describes the form, not anybody's data."""
    return plan_service.config()


@router.post("/preview", response_model=p.PlanPreviewOut)
def plan_preview(body: p.PlanAnswersIn, user: dict = Depends(deps.user_with_csrf)):
    """Instant read-out of what the answers mean so far. No optimiser, so it is safe to call as a person types."""
    return plan_service.preview(body)


@router.post("/strategies", response_model=p.PlanStrategiesOut)
def plan_strategies(
    body: p.PlanAnswersIn, request: Request, user: dict = Depends(deps.user_with_csrf), svc: AnalysisService = Depends(deps.service)
):
    _busy(request, user)
    try:
        return plan_service.strategies(body, svc)
    except ValueError as err:
        raise ApiError(422, "Please fix the highlighted problems.", [str(err)]) from None
    except AnalysisTimeout:
        raise ApiError(503, "The allocation model is busy. Please try again in a minute.", headers={"Retry-After": "30"}) from None


@router.post("/save", response_model=p.SaveOut)
def plan_save(
    body: p.SaveRequest, response: Response, user: dict = Depends(deps.user_with_csrf), cfg: Settings = Depends(deps.settings)
):
    try:
        profile_id, profile, created = plan_service.save(user["id"], body, cfg.max_profiles)
    except ValueError as err:
        raise ApiError(422, "Please fix the highlighted problems.", [str(err)]) from None
    except plan_service.ProfileLimitReached:
        raise ApiError(409, f"An account can hold at most {cfg.max_profiles} profiles.") from None
    response.status_code = 201 if created else 200
    return p.SaveOut(profile=convert.profile_to_out(profile_id, profile), created=created)
