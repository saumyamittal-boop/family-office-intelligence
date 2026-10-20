"""Holdings import and consolidation. Every route is scoped to the signed-in account; a profile that is not theirs is simply not found."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Path, Request

from fo import accounts
from fo.personas import Profile

from .. import deps, holdings_service, holdings_store
from .. import holdings_schemas as hs
from .. import schemas as s
from ..errors import ApiError

router = APIRouter(prefix="/api", tags=["holdings"], responses=s.ERRORS)

ProfileId = Path(ge=1, le=2**31 - 1)
ImportId = Path(ge=1, le=2**31 - 1)
NOT_FOUND = "Profile not found."  # also what somebody else's profile gets: its existence is not revealed
BUSY = "You are uploading very quickly. Wait a few seconds and try again."


def _own(user: dict, profile_id: int) -> Profile:
    profile = accounts.get_profile(user["id"], profile_id)
    if profile is None:
        raise ApiError(404, NOT_FOUND)
    return profile


@router.get("/holdings/template", response_model=hs.TemplateOut)
def template():
    """A small, valid example file. Public: it contains no one's data."""
    return holdings_service.template()


@router.post("/profiles/{profile_id}/holdings/preview", response_model=hs.PreviewOut)
def preview(body: hs.FileIn, request: Request, profile_id: int = ProfileId, user: dict = Depends(deps.user_with_csrf)):
    """Read the file and say what it holds and what is wrong. Stores nothing."""
    _own(user, profile_id)
    deps.throttle(request, user, "holdings_user", BUSY)
    return holdings_service.preview(user["id"], profile_id, body)


@router.post("/profiles/{profile_id}/holdings/imports", response_model=hs.ImportOut, status_code=201)
def add_import(body: hs.ImportIn, request: Request, profile_id: int = ProfileId, user: dict = Depends(deps.user_with_csrf)):
    """Read the file again and, if nothing blocks it, store it."""
    _own(user, profile_id)
    deps.throttle(request, user, "holdings_user", BUSY)
    return holdings_service.import_file(user["id"], profile_id, body)


@router.get("/profiles/{profile_id}/holdings/imports", response_model=list[hs.ImportOut])
def list_imports(profile_id: int = ProfileId, user: dict = Depends(deps.current_user)):
    _own(user, profile_id)
    return holdings_store.list_imports(user["id"], profile_id)


@router.delete("/profiles/{profile_id}/holdings/imports/{import_id}", status_code=204)
def delete_import(profile_id: int = ProfileId, import_id: int = ImportId, user: dict = Depends(deps.user_with_csrf)):
    _own(user, profile_id)
    if not holdings_store.delete_import(user["id"], profile_id, import_id):
        raise ApiError(404, "Import not found.")


@router.get("/profiles/{profile_id}/holdings/consolidation", response_model=hs.ConsolidationOut)
def consolidation(profile_id: int = ProfileId, user: dict = Depends(deps.current_user)):
    return holdings_service.consolidation(user["id"], profile_id, _own(user, profile_id))


@router.post("/profiles/{profile_id}/holdings/apply/preview", response_model=hs.ApplyOut)
def apply_preview(body: hs.ApplyIn, profile_id: int = ProfileId, user: dict = Depends(deps.user_with_csrf)):
    """What the profile would look like if the imported holdings were used. Changes nothing."""
    return holdings_service.apply(user["id"], profile_id, _own(user, profile_id), body, save=False)


@router.post("/profiles/{profile_id}/holdings/apply", response_model=hs.ApplyOut)
def apply(body: hs.ApplyIn, profile_id: int = ProfileId, user: dict = Depends(deps.user_with_csrf)):
    """Make the profile's holdings the imported ones. The person chooses this on purpose; nothing else ever does."""
    return holdings_service.apply(user["id"], profile_id, _own(user, profile_id), body, save=True)
