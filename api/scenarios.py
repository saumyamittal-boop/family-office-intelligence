"""Stress scenarios: the built-in ones, the "build your own" dials, and one scenario applied to every option.

The numbers all come from the engine (`engine.SCENARIOS`, `engine.scenario_row`, `engine.compare_options`); this module
only describes them and translates the six dials into the engine's scenario shape.
"""
from __future__ import annotations

from fo import engine
from fo.data import ASSET_CLASSES
from fo.personas import Profile

from . import convert
from . import schemas as s

# Plain-language descriptions of the built-in scenarios (the same wording the Streamlit page uses).
DESCRIPTIONS = {
    "Equities fall 25%": "Shares fall 25% and nothing else changes.",
    "Market crash": "Equities fall sharply and illiquid assets are marked down.",
    "Inflation and rate spike": "Rates and prices jump. Bonds and equities both fall.",
    "Large unexpected expense": "A one-off bill of 8% of the corpus arrives.",
    "Lost decade": "Returns run 4 points a year lower for the whole horizon.",
}
CUSTOM_NAME = "Your scenario"
CUSTOM_DESCRIPTION = "The shocks set above, applied once to today's holdings."
MID_CAP_MULTIPLE = 1.25  # mid-cap falls (or rises) a quarter more than large-cap, never below -95%
MID_CAP_FLOOR = -0.95


def preset(name: str) -> s.ScenarioPreset:
    sc = engine.SCENARIOS[name]
    return s.ScenarioPreset(
        name=name, description=DESCRIPTIONS.get(name, ""), shocks={c: float(sc["shocks"][c]) for c in ASSET_CLASSES},
        illiquid=float(sc["illiquid"]), extra_outflow=float(sc["extra_outflow"]), return_drag=float(sc["return_drag"]),
    )


def presets() -> list[s.ScenarioPreset]:
    return [preset(name) for name in engine.SCENARIOS]


def custom_ranges() -> dict[str, s.Range]:
    """The limits of each dial, read from the request model so there is one definition."""
    out: dict[str, s.Range] = {}
    for key, field in s.CustomScenario.model_fields.items():
        bounds = {type(m).__name__: m for m in field.metadata}
        out[key] = s.Range(min=bounds["Ge"].ge, max=bounds["Le"].le, default=field.default)
    return out


def to_engine(c: s.CustomScenario) -> dict:
    large, mid, debt, gold, cash = ASSET_CLASSES
    return {
        "shocks": {
            large: c.equity_shock, mid: max(c.equity_shock * MID_CAP_MULTIPLE, MID_CAP_FLOOR),
            debt: c.debt_shock, gold: c.gold_shock, cash: 0.0,
        },
        "illiquid": c.illiquid_markdown,
        "extra_outflow": c.one_off_expense,
        "return_drag": c.return_drag,
    }


def resolve(request: s.ScenarioRequest) -> tuple[str, str, bool, dict, s.ScenarioPreset]:
    """Name, description, is-custom, the engine's scenario, and the shape sent back. Raises ValueError on a bad request."""
    if (request.preset is None) == (request.custom is None):
        raise ValueError("Send either a built-in scenario or a custom one, not both and not neither.")
    if request.preset is not None:
        if request.preset not in engine.SCENARIOS:
            raise ValueError(f"Unknown scenario. Choose one of: {', '.join(engine.SCENARIOS)}.")
        applied = preset(request.preset)
        return applied.name, applied.description, False, engine.SCENARIOS[request.preset], applied
    scenario = to_engine(request.custom)
    applied = s.ScenarioPreset(
        name=CUSTOM_NAME, description=CUSTOM_DESCRIPTION, shocks={c: float(scenario["shocks"][c]) for c in ASSET_CLASSES},
        illiquid=float(scenario["illiquid"]), extra_outflow=float(scenario["extra_outflow"]),
        return_drag=float(scenario["return_drag"]),
    )
    return CUSTOM_NAME, CUSTOM_DESCRIPTION, True, scenario, applied


def compare(
    profile_id: int, profile: Profile, basis: str, request: s.ScenarioRequest,
    current: engine.Portfolio, options: list[engine.Portfolio],
) -> s.ScenarioComparison:
    name, description, is_custom, scenario, applied = resolve(request)
    table = engine.compare_options(profile, [current] + options, scenario)
    return s.ScenarioComparison(
        profile_id=profile_id, basis=basis, name=name, description=description, is_custom=is_custom, applied=applied,
        rows=convert.compare_rows(table), insights=convert.insights_out(engine.comparison_insights(table)),
    )
