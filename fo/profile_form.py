"""Turn form-style values (percentages, tables) into a validated Profile, or say what is wrong.

Pure Python, no UI imports, so the Streamlit page and the API apply exactly the same rules.
"""
from __future__ import annotations

from .personas import ILLIQUID, IlliquidBucket, Profile

MAX_ONE_OFFS = 3
MAX_ILLIQUID_SHARE = 0.95


def build_profile(raw: dict, key: str, deciding_constraint: str = "") -> tuple[Profile | None, list[str]]:
    """Validate `raw` and build a Profile.

    `raw` holds: name, corpus, spending, horizon, max_dd (%), cover (months), target (%), holdings
    ({class: %}), ill_desc, ill_ret (%), ill_vol (%), lock, corr, one_offs ([(year, amount), ...]) and
    limits ([(class, min %, max %), ...]). Returns (profile, []) or (None, [messages]).
    """
    errors: list[str] = []
    name = raw["name"].strip()
    if not name:
        errors.append("Give the profile a name.")

    holds = {c: v / 100 for c, v in raw["holdings"].items()}
    total = sum(holds.values())
    if abs(total - 1.0) > 0.005:
        errors.append(f"Holdings add up to {total * 100:.1f}%. They need to add up to 100%.")
    elif total > 0:
        holds = {c: v / total for c, v in holds.items()}
    if holds.get(ILLIQUID, 0) > MAX_ILLIQUID_SHARE:
        errors.append("Illiquid holdings can be at most 95% of the corpus; the model needs a liquid part to allocate.")

    limits = {}
    for asset_class, lo_pct, hi_pct in raw["limits"]:
        lo, hi = float(lo_pct) / 100, float(hi_pct) / 100
        if not (0 <= lo <= hi <= 1):
            errors.append(f"{asset_class}: the minimum must be between 0% and the maximum, and the maximum at most 100%.")
        limits[asset_class] = (lo, hi)
    if limits and (sum(v[0] for v in limits.values()) > 1 + 1e-9 or sum(v[1] for v in limits.values()) < 1 - 1e-9):
        errors.append("The class limits can't add up to 100% of the liquid part: minimums must total at most 100% "
                      "and maximums at least 100%.")

    one_offs = []
    rows = list(raw["one_offs"])
    if len(rows) > MAX_ONE_OFFS:
        errors.append("Enter at most three one-off outflows.")
    for year, amount in rows:
        year, amount = int(year), float(amount)
        if not 1 <= year <= raw["horizon"]:
            errors.append(f"A one-off outflow in year {year} is outside the {raw['horizon']}-year horizon.")
        if amount <= 0:
            errors.append("One-off amounts must be above zero.")
        one_offs.append((year, amount))

    if errors:
        return None, errors
    return (
        Profile(
            key=key, name=name, deciding_constraint=deciding_constraint, corpus_cr=raw["corpus"],
            holdings=holds,
            illiquid=IlliquidBucket(raw["ill_desc"].strip() or "Illiquid holdings", raw["ill_ret"] / 100,
                                    raw["ill_vol"] / 100, raw["lock"], raw["corr"]),
            annual_spending_cr=raw["spending"], one_offs=tuple(sorted(one_offs)), horizon_years=raw["horizon"],
            max_drawdown=raw["max_dd"] / 100, cover_months=raw["cover"], limits=limits,
            target_real_return=raw["target"] / 100,
        ),
        [],
    )
