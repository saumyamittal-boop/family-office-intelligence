"""Family profiles. Every query is scoped to the signed-in user, who comes from the session and nowhere else."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Path, Query

from fo import accounts, engine

from .. import convert, deps
from .. import schemas as s
from ..analysis import AnalysisService, AnalysisTimeout
from ..config import Settings
from ..errors import ApiError

router = APIRouter(prefix="/api/profiles", tags=["profiles"], responses=s.ERRORS)

ProfileId = Path(ge=1, le=2**31 - 1)
NOT_FOUND = "Profile not found."  # also what you get for somebody else's profile: its existence is not revealed


def _own(user: dict, profile_id: int):
    profile = accounts.get_profile(user["id"], profile_id)
    if profile is None:
        raise ApiError(404, NOT_FOUND)
    return profile


def _valid(body: s.ProfileIn, key: str):
    profile, problems = convert.to_domain(body, key)
    if problems:
        raise ApiError(422, "Please fix the highlighted problems.", problems)
    return profile


@router.get("", response_model=list[s.ProfileSummary])
def list_profiles(user: dict = Depends(deps.current_user)):
    return [s.ProfileSummary(id=pid, name=p.name, corpus_cr=p.corpus_cr) for pid, p in accounts.list_profiles(user["id"])]


@router.post("", response_model=s.ProfileOut, status_code=201)
def create_profile(body: s.ProfileIn, user: dict = Depends(deps.user_with_csrf), cfg: Settings = Depends(deps.settings)):
    if len(accounts.list_profiles(user["id"])) >= cfg.max_profiles:
        raise ApiError(409, f"An account can hold at most {cfg.max_profiles} profiles.")
    profile = _valid(body, key="user")
    pid = accounts.add_profile(user["id"], profile)
    return convert.profile_to_out(pid, profile)


@router.get("/{profile_id}", response_model=s.ProfileOut)
def get_profile(profile_id: int = ProfileId, user: dict = Depends(deps.current_user)):
    return convert.profile_to_out(profile_id, _own(user, profile_id))


@router.put("/{profile_id}", response_model=s.ProfileOut)
def update_profile(body: s.ProfileIn, profile_id: int = ProfileId, user: dict = Depends(deps.user_with_csrf)):
    _own(user, profile_id)
    profile = _valid(body, key=f"user{profile_id}")
    if not accounts.save_profile(user["id"], profile_id, profile):
        raise ApiError(404, NOT_FOUND)
    return convert.profile_to_out(profile_id, profile)


@router.delete("/{profile_id}", status_code=204)
def delete_profile(profile_id: int = ProfileId, user: dict = Depends(deps.user_with_csrf)):
    _own(user, profile_id)
    if not accounts.delete_profile(user["id"], profile_id):
        raise ApiError(409, "You always keep at least one profile.")


@router.get("/{profile_id}/analysis", response_model=s.AnalysisOut)
def analysis(
    profile_id: int = ProfileId,
    basis: s.Basis = Query("all", description="Which assets count towards the liquidity cover."),
    user: dict = Depends(deps.current_user),
    svc: AnalysisService = Depends(deps.service),
):
    profile = _own(user, profile_id)
    try:
        return svc.analyse(profile_id, profile, basis)
    except ValueError as err:  # e.g. class limits that cannot add up to 100%
        raise ApiError(422, f"This profile can't be analysed yet: {err}") from None
    except AnalysisTimeout:
        raise ApiError(503, "The allocation model is busy. Please try again in a minute.", headers={"Retry-After": "30"}) from None
