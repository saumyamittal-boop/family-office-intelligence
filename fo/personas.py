"""Profile model and the three synthetic personas.

All figures come from docs/personas-and-assumptions.md and are DRAFT placeholders. The personas are
fictional. Amounts are in INR crore. Holdings are shares of total corpus; class limits are shares of
the liquid sleeve (everything except the illiquid bucket).
"""
from __future__ import annotations

from dataclasses import dataclass

from .data import ASSET_CLASSES

LARGE, MID, DEBT, GOLD, CASH = ASSET_CLASSES
ILLIQUID = "Illiquid"


@dataclass(frozen=True)
class IlliquidBucket:
    description: str
    expected_return: float
    volatility: float
    lock_in_years: int
    corr_with_equity: float


@dataclass(frozen=True)
class Profile:
    key: str
    name: str
    deciding_constraint: str
    corpus_cr: float
    holdings: dict  # share of total corpus by class name, including "Illiquid"
    illiquid: IlliquidBucket
    annual_spending_cr: float
    one_offs: tuple  # ((year, amount_cr), ...)
    horizon_years: int
    max_drawdown: float
    cover_months: int
    limits: dict  # class -> (min, max), as shares of the liquid sleeve
    target_real_return: float

    @property
    def illiquid_share(self) -> float:
        return self.holdings[ILLIQUID]

    @property
    def sleeve_share(self) -> float:
        return 1.0 - self.illiquid_share


def profile_to_dict(p: Profile) -> dict:
    """JSON-friendly form of a profile, for storage."""
    return {
        "name": p.name,
        "deciding_constraint": p.deciding_constraint,
        "corpus_cr": p.corpus_cr,
        "holdings": dict(p.holdings),
        "illiquid": {
            "description": p.illiquid.description,
            "expected_return": p.illiquid.expected_return,
            "volatility": p.illiquid.volatility,
            "lock_in_years": p.illiquid.lock_in_years,
            "corr_with_equity": p.illiquid.corr_with_equity,
        },
        "annual_spending_cr": p.annual_spending_cr,
        "one_offs": [[int(y), float(a)] for y, a in p.one_offs],
        "horizon_years": p.horizon_years,
        "max_drawdown": p.max_drawdown,
        "cover_months": p.cover_months,
        "limits": {c: [lo, hi] for c, (lo, hi) in p.limits.items()},
        "target_real_return": p.target_real_return,
    }


def profile_from_dict(d: dict, key: str = "user") -> Profile:
    ill = d["illiquid"]
    return Profile(
        key=key,
        name=d["name"],
        deciding_constraint=d.get("deciding_constraint", ""),
        corpus_cr=float(d["corpus_cr"]),
        holdings={c: float(v) for c, v in d["holdings"].items()},
        illiquid=IlliquidBucket(
            ill["description"], float(ill["expected_return"]), float(ill["volatility"]),
            int(ill["lock_in_years"]), float(ill["corr_with_equity"]),
        ),
        annual_spending_cr=float(d["annual_spending_cr"]),
        one_offs=tuple((int(y), float(a)) for y, a in d["one_offs"]),
        horizon_years=int(d["horizon_years"]),
        max_drawdown=float(d["max_drawdown"]),
        cover_months=int(d["cover_months"]),
        limits={c: (float(lo), float(hi)) for c, (lo, hi) in d["limits"].items()},
        target_real_return=float(d["target_real_return"]),
    )


def starter_profile(name: str = "My family office") -> Profile:
    """A neutral starting point for a new account's first profile."""
    return Profile(
        key="starter",
        name=name,
        deciding_constraint="",
        corpus_cr=100,
        holdings={LARGE: 0.20, MID: 0.10, DEBT: 0.30, GOLD: 0.05, CASH: 0.10, ILLIQUID: 0.25},
        illiquid=IlliquidBucket("Real estate", 0.08, 0.12, 2, 0.2),
        annual_spending_cr=3,
        one_offs=((3, 5),),
        horizon_years=15,
        max_drawdown=0.15,
        cover_months=24,
        limits={LARGE: (0.05, 0.40), MID: (0.0, 0.20), DEBT: (0.10, 0.60), GOLD: (0.0, 0.15), CASH: (0.05, 0.30)},
        target_real_return=0.04,
    )


PERSONAS: dict[str, Profile] = {
    "A": Profile(
        key="A",
        name="A: Legacy-conservative",
        deciding_constraint="Liquidity cover (large recurring spending plus dated one-offs)",
        corpus_cr=250,
        holdings={LARGE: 0.15, MID: 0.05, DEBT: 0.40, GOLD: 0.10, CASH: 0.10, ILLIQUID: 0.20},
        illiquid=IlliquidBucket("Real estate", 0.08, 0.12, 2, 0.2),
        annual_spending_cr=8,
        one_offs=((2, 12), (4, 20), (7, 15)),
        horizon_years=15,
        max_drawdown=0.12,
        cover_months=36,
        limits={LARGE: (0.05, 0.25), MID: (0.0, 0.10), DEBT: (0.25, 0.60), GOLD: (0.0, 0.15), CASH: (0.10, 0.30)},
        target_real_return=0.03,
    ),
    "B": Profile(
        key="B",
        name="B: Business-heavy",
        deciding_constraint="Illiquid holdings and concentration (half the corpus cannot be sold)",
        corpus_cr=400,
        holdings={LARGE: 0.15, MID: 0.05, DEBT: 0.15, GOLD: 0.05, CASH: 0.10, ILLIQUID: 0.50},
        illiquid=IlliquidBucket("Family business and real estate", 0.12, 0.22, 6, 0.5),
        annual_spending_cr=8,
        one_offs=((1, 25), (3, 15), (6, 30)),
        horizon_years=12,
        max_drawdown=0.20,
        cover_months=24,
        limits={LARGE: (0.10, 0.35), MID: (0.0, 0.15), DEBT: (0.15, 0.45), GOLD: (0.0, 0.10), CASH: (0.05, 0.20)},
        target_real_return=0.05,
    ),
    "D": Profile(
        key="D",
        name="D: ₹1,000 Cr liquidity gap",
        deciding_constraint="Liquidity: ₹50 Cr of easy money against ₹120 Cr needed in the next 12 months",
        corpus_cr=1000,
        holdings={LARGE: 0.55, MID: 0.0, DEBT: 0.0, GOLD: 0.0, CASH: 0.05, ILLIQUID: 0.40},
        illiquid=IlliquidBucket("Real estate and private holdings", 0.08, 0.12, 5, 0.3),
        annual_spending_cr=20,
        one_offs=((1, 100),),
        horizon_years=15,
        max_drawdown=0.15,
        cover_months=12,
        limits={LARGE: (0.10, 0.70), MID: (0.0, 0.20), DEBT: (0.0, 0.60), GOLD: (0.0, 0.15), CASH: (0.05, 0.40)},
        target_real_return=0.04,
    ),
    "C": Profile(
        key="C",
        name="C: Next-gen growth",
        deciding_constraint="Drawdown tolerance (high return goal against a limit on losses)",
        corpus_cr=150,
        holdings={LARGE: 0.30, MID: 0.20, DEBT: 0.15, GOLD: 0.05, CASH: 0.10, ILLIQUID: 0.20},
        illiquid=IlliquidBucket("Private equity and VC funds", 0.15, 0.28, 8, 0.5),
        annual_spending_cr=3,
        one_offs=((3, 10), (8, 15)),
        horizon_years=25,
        max_drawdown=0.25,
        cover_months=12,
        limits={LARGE: (0.15, 0.50), MID: (0.05, 0.35), DEBT: (0.0, 0.30), GOLD: (0.0, 0.15), CASH: (0.03, 0.15)},
        target_real_return=0.07,
    ),
}
