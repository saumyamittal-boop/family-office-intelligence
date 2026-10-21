"""The only way a number gets into an answer.

A template asks the builder for a figure (`b.pct(...)`) and gets back the exact text to put in its sentence. The builder records the
figure with its label, the unrounded value, and where in the engine's results it came from, so an answer can list its evidence and
a test can check that no digit appears in an answer without one. Formatting lives here and in `fo.formatting`, nowhere else.
"""
from __future__ import annotations

from contextlib import contextmanager

from fo import formatting as fmt

from . import explain_schemas as es

# Page names as the menu shows them.
OVERVIEW, RECOMMENDATION, RISK, SCENARIOS, PROFILE, HOLDINGS = "Overview", "Recommendation", "Risk and liquidity", "Scenarios", "Family profile", "Holdings"
PATHS = {OVERVIEW: "/", RECOMMENDATION: "/recommendation", RISK: "/risk", SCENARIOS: "/scenarios", PROFILE: "/profile", HOLDINGS: "/holdings"}


class Builder:
    def __init__(self) -> None:
        self.figures: dict[str, es.FigureOut] = {}
        self._table = False

    @contextmanager
    def table(self):
        """Figures registered inside belong to a table the person sees as a table, not as a sentence."""
        before, self._table = self._table, True
        try:
            yield
        finally:
            self._table = before

    def _add(self, key: str, label: str, shown: str, value: float | None, unit: es.Unit, field: str, page: str, derived: bool) -> str:
        figure = es.FigureOut(key=key, label=label, shown=shown, value=value, unit=unit, field=field, page=page, derived=derived, in_table=self._table)
        known = self.figures.get(key)
        if known is not None and (known.shown != shown or known.label != label):
            raise ValueError(f"Figure {key!r} registered twice with different content.")  # a template bug, never user input
        self.figures[key] = figure
        return shown

    def cr(self, key, label, value, field, page, digits: int = 1, derived: bool = False) -> str:
        return self._add(key, label, fmt.cr(value, digits), float(value), "cr", field, page, derived)

    def signed_cr(self, key, label, value, field, page, digits: int = 1, derived: bool = False) -> str:
        return self._add(key, label, fmt.signed_cr(value, digits), float(value), "cr", field, page, derived)

    def pct(self, key, label, value, field, page, digits: int = 1, derived: bool = False) -> str:
        return self._add(key, label, fmt.pct(value, digits), float(value), "percent", field, page, derived)

    def signed_pct(self, key, label, value, field, page, digits: int = 1, derived: bool = False) -> str:
        return self._add(key, label, fmt.signed_pct(value, digits), float(value), "percent", field, page, derived)

    def ratio(self, key, label, value, field, page, digits: int = 1, derived: bool = False) -> str:
        return self._add(key, label, f"{fmt.half_up(value, digits)}x", float(value), "ratio", field, page, derived)

    def months(self, key, label, value, field, page, digits: int = 0, derived: bool = False) -> str:
        text = fmt.half_up(value, digits)
        return self._add(key, label, f"{text} month{'' if text == '1' else 's'}", float(value), "months", field, page, derived)

    def years(self, key, label, value, field, page, derived: bool = False) -> str:
        n = int(value)
        return self._add(key, label, f"{n} year{'' if n == 1 else 's'}", float(n), "years", field, page, derived)

    def year(self, key, label, value, field, page, derived: bool = False) -> str:
        """A calendar year or a year number in a plan ("year 3"): printed bare."""
        return self._add(key, label, str(int(value)), float(value), "count", field, page, derived)

    def count(self, key, label, value, field, page, derived: bool = False) -> str:
        return self._add(key, label, f"{int(value):,}", float(value), "count", field, page, derived)

    def number(self, key, label, value, field, page, digits: int = 2, derived: bool = False) -> str:
        return self._add(key, label, fmt.half_up(value, digits), float(value), "ratio", field, page, derived)

    def text(self, key, label, shown: str, field, page, derived: bool = False) -> str:
        """A name or a date that carries digits (a scenario called "Equities fall 25%", a holding called "Nifty 50 fund")."""
        return self._add(key, label, str(shown), None, "date" if label.lower().startswith("date") else "text", field, page, derived)

    def listing(self) -> list[es.FigureOut]:
        return sorted(self.figures.values(), key=lambda f: f.in_table)  # sentence figures first, table figures after
