"""Request and response shapes. These are the API contract; the frontend's TypeScript types are generated from them.

Conventions: shares and rates are fractions (0.15 = 15%); money is INR crore, in fields ending `_cr`;
JSON names are snake_case.
"""
from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from fo.data import ASSET_CLASSES
from fo.personas import ILLIQUID

Basis = Literal["all", "strict"]
DemoFamily = Literal["legacy", "business", "nextgen", "gap"]
Share = Annotated[float, Field(ge=0.0, le=1.0)]
Name = Annotated[str, Field(min_length=1, max_length=60)]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=False)


# ---- Auth ------------------------------------------------------------------------------------------------------------
class Credentials(Strict):
    username: Annotated[str, Field(min_length=1, max_length=64)]
    password: Annotated[str, Field(min_length=1, max_length=256)]


class DemoRequest(Strict):
    family: DemoFamily


class UserOut(BaseModel):
    id: int
    username: str
    is_demo: bool


class SessionOut(BaseModel):
    user: UserOut
    csrf_token: str
    default_basis: Basis = "all"


# ---- Profiles ------------------------------------------------------------------------------------------------------
class IlliquidModel(Strict):
    description: Annotated[str, Field(max_length=60)]
    expected_return: Annotated[float, Field(ge=-0.10, le=0.40)]
    volatility: Annotated[float, Field(ge=0.0, le=0.80)]
    lock_in_years: Annotated[int, Field(ge=0, le=30)]
    corr_with_equity: Share


class OneOffModel(Strict):
    year: Annotated[int, Field(ge=1, le=60)]
    amount_cr: Annotated[float, Field(gt=0.0, le=10_000_000.0)]


class LimitModel(Strict):
    min: Share
    max: Share


class ProfileIn(Strict):
    name: Name
    deciding_constraint: Annotated[str, Field(max_length=200)] = ""
    corpus_cr: Annotated[float, Field(ge=1.0, le=1_000_000.0)]
    annual_spending_cr: Annotated[float, Field(ge=0.0, le=100_000.0)]
    horizon_years: Annotated[int, Field(ge=1, le=60)]
    max_drawdown: Annotated[float, Field(ge=0.01, le=0.80)]
    cover_months: Annotated[int, Field(ge=1, le=240)]
    target_real_return: Annotated[float, Field(ge=-0.05, le=0.25)]
    holdings: dict[str, Share] = Field(description="Share of the whole corpus per class, including 'Illiquid'.")
    illiquid: IlliquidModel
    one_offs: Annotated[list[OneOffModel], Field(max_length=10)] = []
    limits: dict[str, LimitModel] = Field(description="Allowed share of the liquid part, per market class.")

    @field_validator("holdings")
    @classmethod
    def _holdings_cover_every_class(cls, v: dict) -> dict:
        if set(v) != set(ASSET_CLASSES) | {ILLIQUID}:
            raise ValueError(f"holdings must have exactly these classes: {', '.join(ASSET_CLASSES + [ILLIQUID])}")
        return v

    @field_validator("limits")
    @classmethod
    def _limits_cover_every_market_class(cls, v: dict) -> dict:
        if set(v) != set(ASSET_CLASSES):
            raise ValueError(f"limits must have exactly these classes: {', '.join(ASSET_CLASSES)}")
        return v


class ProfileOut(ProfileIn):
    id: int


class ProfileSummary(BaseModel):
    id: int
    name: str
    corpus_cr: float


# ---- Analysis ------------------------------------------------------------------------------------------------------
class PortfolioOut(BaseModel):
    label: str
    basis: Basis
    weights_total: dict[str, float]
    weights_sleeve: list[float]
    exp_return: float
    exp_real: float
    vol: float
    max_dd: float
    cvar21: float
    dd_ok: bool
    meets_target: bool
    target_gap: float
    required_cover_cr: float
    available_cover_cr: float
    cover_fraction: float
    liquidity_binding: bool
    liquidity_infeasible: bool
    cost_of_liquidity: float
    liquid_return: float
    lam_base: float | None
    lam_used: float | None
    bounds_hit: list[str]
    explanation: list[str]
    optimiser_converged: bool


class ActionRow(BaseModel):
    asset_class: str
    current_share: float
    recommended_share: float
    current_cr: float
    recommended_cr: float
    change_cr: float


class ScenarioRow(BaseModel):
    scenario: str
    value_change: float
    value_change_cr: float
    within_drawdown_limit: bool
    cover_ratio: float
    cover_held: bool
    real_corpus_multiple: float


class InsightOut(BaseModel):
    tone: Literal["good", "warn", "info"]
    title: str | None = None
    body: str


class LadderRow(BaseModel):
    year: int
    outflows_cr: float
    liquid_value_cr: float
    months_covered: float


class ProjectionRow(BaseModel):
    year: int
    nominal_cr: float
    real_cr: float


class OutflowRow(BaseModel):
    year: int
    spending_cr: float
    one_off_cr: float
    total_cr: float


class CompareRow(BaseModel):
    option: str
    value_change: float
    value_change_cr: float
    within_drawdown_limit: bool
    cover_ratio_after: float
    cover_held: bool
    real_corpus_multiple: float
    exp_return: float
    exp_real: float
    max_dd: float


class YearRange(BaseModel):
    """How a year has turned out in the sample history: the middle 80% of years, the median, and the extremes."""

    low: float
    median: float
    high: float
    worst: float
    best: float


class PortfolioDetail(BaseModel):
    portfolio: PortfolioOut
    action_plan: list[ActionRow]
    scenarios: list[ScenarioRow]
    insights: list[InsightOut]
    ladder: list[LadderRow]
    projection: list[ProjectionRow]
    year_range: YearRange


class AnalysisOut(BaseModel):
    profile_id: int
    basis: Basis
    basis_label: str
    data_source: str
    current: PortfolioOut
    current_projection: list[ProjectionRow]
    current_ladder: list[LadderRow]
    current_scenarios: list[ScenarioRow]
    options: list[PortfolioDetail]
    upcoming_outflows: list[OutflowRow]
    comparison_scenario: str
    comparison: list[CompareRow]
    comparison_insights: list[InsightOut]


# ---- History (the replay of the portfolio over the sample years) ------------------------------------------------------
class AnnualReturn(BaseModel):
    year: int
    portfolio_return: float
    trading_days: int
    partial: bool = Field(description="True when the sample holds only part of this calendar year.")


class PortfolioHistory(BaseModel):
    label: str
    value: list[float] = Field(description="Growth of 100 invested at the start, one point per entry in `dates`.")
    drawdown: list[float] = Field(description="Fall from the previous peak (zero or negative); the deepest day inside each step.")
    max_drawdown: float = Field(description="The worst fall over the whole sample, measured on every day (the engine's number).")
    cvar21: float
    annual: list[AnnualReturn]


class HistoryOut(BaseModel):
    profile_id: int
    basis: Basis
    data_source: str
    dates: list[str] = Field(description="ISO dates. The first is the base day (value 100); the rest close each step.")
    step_days: int = Field(description="Trading days between points. Drawdowns keep the deepest day in each step.")
    drawdown_limit: float
    portfolios: list[PortfolioHistory] = Field(description="The current mix first, then the three recommendations.")
    note: str


# ---- Scenarios -----------------------------------------------------------------------------------------------------
class ScenarioPreset(BaseModel):
    name: str
    description: str
    shocks: dict[str, float] = Field(description="One-off price change per market class.")
    illiquid: float = Field(description="One-off change in the illiquid holdings.")
    extra_outflow: float = Field(description="A one-off bill, as a share of the corpus.")
    return_drag: float = Field(description="Yearly reduction in expected return for the whole horizon.")


class Range(BaseModel):
    min: float
    max: float
    default: float


class CustomScenario(Strict):
    """The six dials of "build your own". The mid-cap shock is 1.25 times the equity shock, never worse than -95%."""

    equity_shock: Annotated[float, Field(ge=-0.60, le=0.20)] = -0.25
    debt_shock: Annotated[float, Field(ge=-0.20, le=0.10)] = -0.03
    gold_shock: Annotated[float, Field(ge=-0.30, le=0.40)] = 0.05
    illiquid_markdown: Annotated[float, Field(ge=-0.50, le=0.10)] = -0.10
    one_off_expense: Annotated[float, Field(ge=0.0, le=0.40)] = 0.05
    return_drag: Annotated[float, Field(ge=0.0, le=0.08)] = 0.0


class ScenarioRequest(Strict):
    basis: Basis = "all"
    preset: Annotated[str, Field(min_length=1, max_length=60)] | None = Field(None, description="Name of a built-in scenario.")
    custom: CustomScenario | None = None


class ScenarioComparison(BaseModel):
    profile_id: int
    basis: Basis
    name: str
    description: str
    is_custom: bool
    applied: ScenarioPreset = Field(description="Exactly what was applied, so the screen can show it.")
    rows: list[CompareRow] = Field(description="The current mix first, then the three recommendations, all hit by the same scenario.")
    insights: list[InsightOut]


# ---- Dashboard ------------------------------------------------------------------------------------------------------
ModuleId = Literal[
    "allocation_actions", "liquidity_commitments", "risk_exposure", "stress_scenarios",
    "net_worth_projection", "historical_performance", "recommendation_rationale", "holdings_consolidation",
]


class ModuleInfo(BaseModel):
    id: ModuleId
    available: bool = Field(description="False for modules whose data source is not built yet.")


class DashboardIn(Strict):
    modules: list[ModuleId] = Field(min_length=4, max_length=4, description="Exactly four different modules, in display order.")

    @field_validator("modules")
    @classmethod
    def _different(cls, v: list) -> list:
        if len(set(v)) != len(v):
            raise ValueError("choose four different modules")
        return v


class DashboardOut(BaseModel):
    modules: list[ModuleId]
    is_default: bool = Field(description="True until the person saves a choice of their own.")
    updated: str | None
    default_modules: list[ModuleId]
    catalog: list[ModuleInfo]


class MetaOut(BaseModel):
    app: str
    version: str
    data_source: str
    disclaimer: str
    asset_classes: list[str]
    cover_bases: dict[str, str]
    demo_login: bool
    demo_families: list[str]
    scenario_presets: list[ScenarioPreset]
    custom_scenario_ranges: dict[str, Range]


class Problem(BaseModel):
    """The one error shape every endpoint uses. `problems` lists field-level messages when there are several."""

    detail: str
    problems: list[str] | None = None


# Declared on the routers so the contract (and the generated TypeScript types) describe error responses too.
ERRORS: dict = {
    code: {"model": Problem, "description": text}
    for code, text in {
        401: "Not signed in.", 403: "Request could not be verified.", 404: "Not found.", 409: "Conflict.",
        422: "The request was not valid.", 429: "Too many attempts.", 503: "The allocation model is busy.",
    }.items()
}
