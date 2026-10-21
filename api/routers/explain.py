"""The explainer. Scoped to the signed-in account like every other profile route; the question is not stored."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Path, Request

from fo import accounts
from fo.personas import Profile

from .. import deps, explain_answers, explain_intents, explain_schemas as es, explain_service, holdings_service
from .. import schemas as s
from ..analysis import AnalysisService
from ..errors import ApiError
from .profiles import _run

router = APIRouter(prefix="/api", tags=["explain"], responses=s.ERRORS)

ProfileId = Path(ge=1, le=2**31 - 1)
NOT_FOUND = "Profile not found."
BUSY = "You are asking very quickly. Wait a few seconds and try again."


def _own(user: dict, profile_id: int) -> Profile:
    profile = accounts.get_profile(user["id"], profile_id)
    if profile is None:
        raise ApiError(404, NOT_FOUND)
    return profile


@router.get("/explain/catalog", response_model=es.CatalogOut)
def catalog():
    """The questions that can be asked, grouped, and the parameters they take. Public: it holds no one's data."""
    return explain_intents.catalog()


@router.post("/profiles/{profile_id}/explain", response_model=es.ReplyOut)
def ask(
    body: es.AskIn,
    request: Request,
    profile_id: int = ProfileId,
    user: dict = Depends(deps.user_with_csrf),
    svc: AnalysisService = Depends(deps.service),
):
    """Answer a question about this family's results, from the engine's own numbers. POST so the question never sits in a URL."""
    profile = _own(user, profile_id)
    deps.throttle(request, user, "explain_user", BUSY)
    ctx = explain_answers.Ctx(
        profile,
        analyse=lambda: _run(lambda: svc.analyse(profile_id, profile, body.basis)),
        history=lambda: _run(lambda: svc.history(profile_id, profile, body.basis)),
        consolidation=lambda: holdings_service.consolidation(user["id"], profile_id, profile),
    )
    return explain_service.ask(body, ctx)
