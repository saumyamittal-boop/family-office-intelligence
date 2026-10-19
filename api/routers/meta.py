"""Public, non-sensitive facts about the running service."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from fo import accounts, engine
from fo.data import ASSET_CLASSES

from .. import deps
from .. import schemas as s
from ..analysis import AnalysisService
from ..config import Settings

router = APIRouter(prefix="/api", tags=["meta"])

VERSION = "0.1.0"
DISCLAIMER = "Illustrative simulation on synthetic data, not investment advice."


@router.get("/health")
def health():
    with accounts.connect() as con:
        con.execute("SELECT 1").fetchone()
    return {"status": "ok"}


@router.get("/meta", response_model=s.MetaOut)
def meta(cfg: Settings = Depends(deps.settings), svc: AnalysisService = Depends(deps.service)):
    return s.MetaOut(
        app="Family Office Intelligence", version=VERSION, data_source=svc.source, disclaimer=DISCLAIMER,
        asset_classes=ASSET_CLASSES, cover_bases=engine.COVER_BASES, demo_login=cfg.demo_login,
        demo_families=list(accounts.DEMO_ACCOUNTS) if cfg.demo_login else [],
    )
