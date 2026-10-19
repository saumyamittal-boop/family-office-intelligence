"""Request and response shapes for the guided plan ("Plan my money")."""
from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from fo import plan as fo_plan
from fo.data import ASSET_CLASSES
from fo.personas import ILLIQUID

from .schemas import ActionRow, OutflowRow, PortfolioOut, ProfileOut, Strict, YearRange

RiskKey = Literal["Protect", "Balance", "Grow"]
CUSTOM_KIND = "Custom"
# The kinds of big upcoming spending a family can pick. The last is "Custom": the family names it themselves.
# (The shared fo.plan list still ends in "Other" for the Streamlit app; the engine ignores the kind either way.)
COMMITMENT_KINDS = [k for k in fo_plan.COMMITMENT_KINDS if k != "Other"] + [CUSTOM_KIND]
LABEL_MAX = 40
CLASSES = ASSET_CLASSES + [ILLIQUID]
Money = Annotated[float, Field(ge=0.0, le=1_000_000.0)]


# ---- Answers (the request) ---------------------------------------------------------------------------------------------
class CommitmentIn(Strict):
    kind: Annotated[str, Field(min_length=1, max_length=40)]
    year: Annotated[int, Field(ge=1, le=fo_plan.HORIZON_YEARS)]
    amount_cr: Annotated[float, Field(gt=0.0, le=10_000_000.0)]
    label: Annotated[str, Field(max_length=LABEL_MAX)] | None = Field(
        default=None, description="The family's own name for a custom expense. Only allowed when the kind is Custom."
    )

    @field_validator("kind")
    @classmethod
    def _known_kind(cls, v: str) -> str:
        if v not in COMMITMENT_KINDS:
            raise ValueError(f"kind must be one of: {', '.join(COMMITMENT_KINDS)}")
        return v

    @field_validator("label")
    @classmethod
    def _tidy_label(cls, v: str | None) -> str | None:
        return (v.strip() or None) if v is not None else None

    @model_validator(mode="after")
    def _only_custom_has_a_name(self) -> "CommitmentIn":
        if self.label and self.kind != CUSTOM_KIND:
            raise ValueError("Only a custom expense can have its own name.")
        return self


class PlanAnswersIn(Strict):
    name: Annotated[str, Field(min_length=1, max_length=60)]
    wealth: Annotated[float, Field(ge=1.0, le=1_000_000.0)]
    spending: Annotated[float, Field(ge=0.0, le=100_000.0)]
    commitments: Annotated[list[CommitmentIn], Field(max_length=10)] = []
    risk: RiskKey
    months: Annotated[int, Field(ge=3, le=36)]
    amounts: dict[str, Money] | None = Field(
        default=None, description="What the family owns today, in INR crore per class including 'Illiquid'. Omit for a typical split."
    )

    @field_validator("amounts")
    @classmethod
    def _known_classes(cls, v: dict | None) -> dict | None:
        if v is not None and not set(v) <= set(CLASSES):
            raise ValueError(f"amounts may only name these classes: {', '.join(CLASSES)}")
        return v


class SaveRequest(Strict):
    answers: PlanAnswersIn
    strategy: RiskKey


# ---- Configuration (the questions, in one place) -------------------------------------------------------------------------
class ComfortOption(BaseModel):
    key: RiskKey
    letter: str
    headline: str
    blurb: str
    max_drawdown: float
    target_real_return: float
    portfolio: str


class ClassInfo(BaseModel):
    name: str
    label: str
    description: str


class PlanDefaults(BaseModel):
    name: str
    wealth: float
    spending: float
    risk: RiskKey
    months: int


class Bounds(BaseModel):
    min: float
    max: float


class CrashInfo(BaseModel):
    label: str
    description: str


class PlanConfigOut(BaseModel):
    steps: list[str]
    comfort: list[ComfortOption]
    classes: list[ClassInfo]
    commitment_kinds: list[str]
    max_commitments: int
    horizon_years: int
    wealth: Bounds
    spending: Bounds
    months: Bounds
    defaults: PlanDefaults
    crash: CrashInfo


# ---- Live preview (instant; no optimiser) ---------------------------------------------------------------------------------
class ComfortLoss(BaseModel):
    key: RiskKey
    max_drawdown: float
    loss_cr: float | None


class SafetyNet(BaseModel):
    months: int
    required_cr: float
    spending_cr: float
    commitments_cr: float


class PlanPreviewOut(BaseModel):
    problems: list[str]
    typical_amounts: dict[str, float]
    comfort: list[ComfortLoss]
    corpus_cr: float | None = None
    liquid_cr: float | None = None
    illiquid_cr: float | None = None
    illiquid_share: float | None = None
    safety_net: SafetyNet | None = None
    outflows: list[OutflowRow] = []
    near_outflows_cr: float | None = None
    near_outflows_share_of_liquid: float | None = None
    amounts_total_cr: float | None = None
    amounts_differ_from_wealth: bool = False
    effects: list[str] = []


# ---- Strategies ---------------------------------------------------------------------------------------------------------------
class CrashResult(BaseModel):
    value_change: float
    value_change_cr: float


class PlanActionRow(ActionRow):
    instrument_name: str
    instrument_note: str


class StrategyOut(BaseModel):
    key: RiskKey
    letter: str
    headline: str
    blurb: str
    portfolio: PortfolioOut
    within_comfort_of: dict[str, bool] = Field(
        description="For each comfort level a family might choose: whether this strategy's worst historical fall fits it."
    )
    meets_goal_of: dict[str, bool] = Field(
        description="For each comfort level: whether this strategy's expected real return reaches that level's goal."
    )
    year_range: YearRange
    crash: CrashResult
    cover_ratio: float
    description: list[str]
    action_plan: list[PlanActionRow]
    illiquid_cr: float
    illiquid_name: str
    illiquid_note: str


class PlanStrategiesOut(BaseModel):
    profile_name: str
    corpus_cr: float
    strategies: list[StrategyOut]
    commitments: list[CommitmentIn]
    crash: CrashInfo
    basis_label: str
    data_source: str


class SaveOut(BaseModel):
    profile: ProfileOut
    created: bool
