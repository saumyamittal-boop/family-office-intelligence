"""Guided planning: plain-language answers become a Profile, and results become plain-language strategies.

The guided flow never asks a family for returns or volatility. It asks about wealth, spending, upcoming
commitments, comfort with a bad year, and how much cash should always be within reach.
"""
from __future__ import annotations

from dataclasses import replace

import numpy as np

from .data import ASSET_CLASSES
from .personas import ILLIQUID, IlliquidBucket, Profile

LARGE, MID, DEBT, GOLD, CASH = ASSET_CLASSES

# Comfort levels. `max_dd` is the worst fall the family says it can sit through; `target` is a
# modest real return that goes with that outlook. Strategy letters follow the mentor's A, B, C.
RISK_CHOICES = {
    "Protect": {
        "strategy": "A", "portfolio": "Defensive", "max_dd": 0.08, "target": 0.02,
        "headline": "Protect what we have",
        "blurb": "We would rather grow slowly than see our wealth fall much in a bad year.",
    },
    "Balance": {
        "strategy": "B", "portfolio": "Balanced", "max_dd": 0.15, "target": 0.04,
        "headline": "Balance safety and growth",
        "blurb": "A fall in a bad year is acceptable if the wealth grows well over time.",
    },
    "Grow": {
        "strategy": "C", "portfolio": "Growth", "max_dd": 0.25, "target": 0.06,
        "headline": "Grow as much as is sensible",
        "blurb": "We can ride out big falls because we have time and a safety net.",
    },
}
STRATEGY_FOR_PORTFOLIO = {v["portfolio"]: (k, v["strategy"]) for k, v in RISK_CHOICES.items()}

# Plain instrument categories. These are illustrative kinds of product, not named securities or advice.
INSTRUMENTS = {
    LARGE: ("Large-cap index fund", "Holds India's biggest listed companies, for example a fund tracking the Nifty 50."),
    MID: ("Mid-cap index fund", "Holds mid-sized listed companies, for example a fund tracking the Nifty Midcap 150."),
    DEBT: ("Government or high-quality bond fund", "Lends to the government and strong companies. Steadier than shares."),
    GOLD: ("Gold ETF", "Follows the price of gold and is easy to sell."),
    CASH: ("Liquid fund or savings", "Money you can reach within a day or two."),
    ILLIQUID: ("Property, business and other holdings", "Kept as they are. They cannot be sold quickly."),
}

COMMITMENT_KINDS = ["Education", "Wedding", "Property purchase", "Business investment", "Medical or emergency", "Other"]

# Wide limits so the answers, not hidden rules, drive the result. Shares of the liquid part.
GUIDED_LIMITS = {LARGE: (0.0, 0.60), MID: (0.0, 0.25), DEBT: (0.0, 0.80), GOLD: (0.0, 0.15), CASH: (0.03, 0.40)}
HORIZON_YEARS = 25  # family wealth is mostly perpetual, so this is a long planning window, not a question
MAX_COMMITMENTS = 3

_TYPICAL = {LARGE: 0.20, MID: 0.08, DEBT: 0.27, GOLD: 0.05, CASH: 0.10, ILLIQUID: 0.30}


def typical_split(wealth: float) -> dict[str, float]:
    """A starting guess at what a family might own, in the same units as `wealth`."""
    return {name: round(wealth * share, 2) for name, share in _TYPICAL.items()}


def default_answers() -> dict:
    return {"name": "My family", "wealth": 100.0, "spending": 3.0, "commitments": [], "risk": "Balance",
            "months": 12, "amounts": None}


def validate_answers(a: dict) -> list[str]:
    errors = []
    amounts = a.get("amounts") or {}
    total = sum(amounts.values())
    if total <= 0:
        errors.append("Add what the family owns today.")
    elif amounts.get(ILLIQUID, 0) / total > 0.95:
        errors.append("At least 5% of the wealth needs to be in things that can be sold, so there is something to plan with.")
    if a.get("spending", 0) < 0:
        errors.append("Spending cannot be negative.")
    if len(a.get("commitments", [])) > MAX_COMMITMENTS:
        errors.append(f"Enter at most {MAX_COMMITMENTS} upcoming commitments.")
    for _, year, amount in a.get("commitments", []):
        if not 1 <= year <= HORIZON_YEARS:
            errors.append(f"A commitment in year {year} is outside the next {HORIZON_YEARS} years.")
        if amount <= 0:
            errors.append("Commitment amounts must be above zero.")
    return errors


def profile_from_answers(a: dict) -> Profile:
    """Build a Profile from guided answers. `a["amounts"]` holds rupee amounts including "Illiquid"."""
    problems = validate_answers(a)
    if problems:
        raise ValueError(" ".join(problems))
    amounts = a["amounts"]
    corpus = float(sum(amounts.values()))
    risk = RISK_CHOICES[a["risk"]]
    return Profile(
        key="plan",
        name=(a.get("name") or "My plan").strip() or "My plan",
        deciding_constraint="",
        corpus_cr=corpus,
        holdings={c: amounts.get(c, 0.0) / corpus for c in ASSET_CLASSES + [ILLIQUID]},
        illiquid=IlliquidBucket("Property, business and other holdings you can't sell quickly", 0.08, 0.15, 5, 0.3),
        annual_spending_cr=float(a["spending"]),
        one_offs=tuple(sorted((int(year), float(amount)) for _, year, amount in a.get("commitments", []))),
        horizon_years=HORIZON_YEARS,
        max_drawdown=risk["max_dd"],
        cover_months=int(a["months"]),
        limits=dict(GUIDED_LIMITS),
        target_real_return=risk["target"],
    )


def variant_profile(profile: Profile, risk: str) -> Profile:
    """The same family, planned for one comfort level. Each strategy is built for its own level."""
    spec = RISK_CHOICES[risk]
    return replace(profile, max_drawdown=spec["max_dd"], target_real_return=spec["target"])


def describe_strategy(profile: Profile, pf, risk: str) -> list[str]:
    """Plain-language reasons for a strategy, without technical terms."""
    spec = RISK_CHOICES[risk]
    w = pf.weights_total
    shares, bonds = w[LARGE] + w[MID], w[DEBT]
    lines = [
        f"Built so that a bad year costs about {spec['max_dd']:.0%} of your wealth or less "
        f"(₹{profile.corpus_cr * spec['max_dd']:,.1f} Cr on ₹{profile.corpus_cr:,.0f} Cr). "
        + (
            f"In the history it fell at most {pf.max_dd:.1%}."
            if pf.dd_ok
            else f"Even the safest mix fell {pf.max_dd:.1%} in the history, so this is the closest it can get."
        ),
        f"Your money would be about {shares:.0%} in shares (index funds), {bonds:.0%} in bonds, {w[GOLD]:.0%} in gold "
        f"and {w[CASH]:.0%} in cash and liquid funds. The other {w['Illiquid']:.0%} stays in property and business.",
        f"Money you can reach quickly covers the next {profile.cover_months} months of spending and commitments "
        f"{pf.available_cover_cr / pf.required_cover_cr:.1f} times.",
        f"It is expected to grow about {pf.exp_return:.1%} a year, or {pf.exp_real:.1%} after inflation. "
        + (
            f"That meets the {spec['target']:.0%} real-return goal for this comfort level."
            if pf.exp_real >= spec["target"]
            else f"That is a little under the {spec['target']:.0%} real-return goal for this comfort level."
        ),
    ]
    return lines


def rolling_year_range(returns, window: int = 252) -> dict:
    """How a year has turned out in the history: typical range (10th to 90th percentile), median, worst."""
    c = np.log1p(np.asarray(returns)).cumsum()
    years = np.exp(c[window:] - c[:-window]) - 1.0
    return {
        "low": float(np.quantile(years, 0.10)),
        "median": float(np.quantile(years, 0.50)),
        "high": float(np.quantile(years, 0.90)),
        "worst": float(years.min()),
        "best": float(years.max()),
    }
