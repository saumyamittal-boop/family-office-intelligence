"""Number formatting shared by the Streamlit app and the API.

One rule for every displayed number: round half up on the decimal text, so 13.75% shows as 13.8% (plain float
formatting would print 13.7) and 137.25 shows as 137.3. Pure Python, no UI imports.
"""
from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal


def half_up(value: float, digits: int) -> str:
    """Round half up on the decimal text. NaN and infinity give "n/a"."""
    value = float(value)  # numpy floats have a repr that Decimal cannot read
    if value != value or value in (float("inf"), float("-inf")):
        return "n/a"
    exact = Decimal(str(round(value, 9)))
    return str(exact.quantize(Decimal(1).scaleb(-digits), rounding=ROUND_HALF_UP))


def with_commas(text: str) -> str:
    """Group the whole-number part of a decimal string in thousands: '-1234.50' -> '-1,234.50'."""
    sign = "-" if text.startswith("-") else ""
    whole, _, fraction = text.lstrip("-").partition(".")
    return f"{sign}{int(whole):,}" + (f".{fraction}" if fraction else "")


def cr(value: float, digits: int = 1) -> str:
    text = half_up(value, digits)
    return text if text == "n/a" else f"₹{with_commas(text)} Cr"


def pct(value: float, digits: int = 1) -> str:
    text = half_up(value * 100, digits)
    return text if text == "n/a" else f"{text}%"


def signed_cr(value: float, digits: int = 1) -> str:
    text = half_up(abs(float(value)), digits)
    if text == "n/a":
        return text
    return f"{'+' if value >= 0 else '−'}₹{with_commas(text)} Cr"


def signed_pct(value: float, digits: int = 1) -> str:
    text = half_up(abs(float(value)) * 100, digits)
    if text == "n/a":
        return text
    return f"{'+' if value >= 0 else '−'}{text}%"
