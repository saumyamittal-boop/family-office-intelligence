"""Request and response shapes for the explainer (ADR-0021). Every number in an answer is a `FigureOut` with its source."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

from fo import question_match as qm

from .schemas import Basis

Option = Literal["Current", "Growth", "Balanced", "Defensive"]
Unit = Literal["cr", "percent", "ratio", "months", "years", "count", "date", "text"]
ReplyKind = Literal["answer", "clarify", "refusal", "out_of_scope", "empty"]

MAX_SLOTS = 4
MAX_SLOT_VALUE = 60


class FigureOut(BaseModel):
    key: str
    label: str
    shown: str = Field(description="Exactly how the figure appears in the answer.")
    value: float | None = Field(description="The unrounded number behind `shown`, when it is a number.")
    unit: Unit
    field: str = Field(description="Where it comes from in the engine's results (a path into the analysis, the profile, the history, the holdings), or how it was derived.")
    page: str = Field(description="The page of the app where the same figure can be seen.")
    derived: bool = Field(description="True when it is a simple sum, difference or ratio of figures that come straight from the engine.")
    in_table: bool = False


class SectionOut(BaseModel):
    heading: str
    lines: list[str]
    from_engine: bool = Field(default=False, description="True when the lines are the model's own wording, passed through unchanged.")


class TableOut(BaseModel):
    caption: str
    columns: list[str]
    rows: list[list[str]]


class LinkOut(BaseModel):
    label: str
    to: str = Field(description="A path inside the app.")


class ChipOut(BaseModel):
    intent: str
    label: str
    slots: dict[str, str] = Field(default_factory=dict)


class AnswerOut(BaseModel):
    intent: str
    title: str
    lead: str = Field(description="The result in one plain sentence.")
    sections: list[SectionOut]
    tables: list[TableOut]
    figures: list[FigureOut]
    caveats: list[str]
    notes: list[str] = Field(description="What was assumed because the question did not say (for example which mix).")
    links: list[LinkOut]
    follow_ups: list[ChipOut]


class ReplyOut(BaseModel):
    kind: ReplyKind
    intent: str | None = None
    confidence: float | None = Field(default=None, description="How close the question was to the matched question type (0 to 1). Absent for chips.")
    message: str | None = None
    answer: AnswerOut | None = None
    suggestions: list[ChipOut] = Field(default_factory=list)


class AskIn(BaseModel):
    """A typed question, or a chosen question type (a chip or a "Why?" button) with its parameters."""

    question: str | None = Field(default=None, max_length=qm.MAX_QUESTION)
    intent: str | None = Field(default=None, max_length=40, pattern=r"^[a-z_]+$")
    slots: dict[str, str] = Field(default_factory=dict)
    basis: Basis = "all"

    @field_validator("slots")
    @classmethod
    def _slots(cls, value: dict[str, str]) -> dict[str, str]:
        if len(value) > MAX_SLOTS or any(len(k) > 20 or len(v) > MAX_SLOT_VALUE for k, v in value.items()):
            raise ValueError("Too many or too long parameters.")
        return value


class CatalogGroup(BaseModel):
    title: str
    chips: list[ChipOut]


class CatalogOut(BaseModel):
    groups: list[CatalogGroup]
    options: list[str]
    scenarios: list[str]
    max_question_length: int
