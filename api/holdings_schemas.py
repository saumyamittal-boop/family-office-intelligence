"""Request and response shapes for holdings import and consolidation (ADR-0020). Money is INR crore, shares are fractions."""
from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field

from fo import holdings_import as hi

from .schemas import Strict

AssetClass = Literal["Large-cap equity", "Mid-cap equity", "Debt", "Gold", "Cash & liquid", "Illiquid"]
Unit = Literal["cr", "lakh", "inr"]
Severity = Literal["error", "warning"]

MAX_BASE64 = (hi.MAX_FILE_BYTES * 4) // 3 + 8
MAX_IMPORTS_PER_PROFILE = 20
MAX_LINES_PER_PROFILE = 5000
PREVIEW_LINES = 200


class FileIn(Strict):
    """A holdings file sent as JSON, so the API's JSON-only and size guards stay whole."""

    filename: Annotated[str, Field(min_length=1, max_length=255)]
    content_base64: Annotated[str, Field(min_length=1, max_length=MAX_BASE64)]
    unit: Unit = "cr"
    class_overrides: dict[Annotated[str, Field(min_length=1, max_length=60)], AssetClass] = Field(
        default_factory=dict, max_length=50, description="Asset-class label as written in the file -> the class the person assigned to it."
    )


class ImportIn(FileIn):
    label: Annotated[str, Field(min_length=1, max_length=60)] | None = Field(None, description="Defaults to the file name.")


class ProblemOut(BaseModel):
    severity: Severity
    message: str
    row: int | None = None
    field: str | None = None


class LineOut(BaseModel):
    row: int
    name: str
    asset_class: AssetClass
    account: str
    value_cr: float


class MappedLabel(BaseModel):
    label: str
    asset_class: AssetClass
    rows: int


class UnrecognisedLabel(BaseModel):
    label: str
    rows: int


class ClassTotal(BaseModel):
    asset_class: AssetClass
    total_cr: float
    share: float
    lines: int


class PreviewOut(BaseModel):
    ok: bool = Field(description="True when nothing blocks importing.")
    filename: str
    file_kind: Literal["csv", "xlsx"]
    unit: Unit
    unit_label: str
    columns: dict[str, str] = Field(description="Which of the file's columns was used for name, asset_class, value and account.")
    ignored_columns: list[str]
    rows_read: int
    line_count: int
    total_cr: float
    lines: list[LineOut] = Field(description=f"At most {PREVIEW_LINES} lines; line_count is the full number.")
    by_class: list[ClassTotal]
    mapped: list[MappedLabel]
    unrecognised: list[UnrecognisedLabel]
    problems: list[ProblemOut]
    already_imported: bool = Field(description="The same data is already stored for this profile.")


class ImportOut(BaseModel):
    id: int
    label: str
    filename: str
    file_kind: Literal["csv", "xlsx"]
    unit: Unit
    row_count: int
    total_cr: float
    created: str


class AccountTotal(BaseModel):
    account: str
    total_cr: float
    share: float
    lines: int


class PositionOut(BaseModel):
    name: str
    asset_class: AssetClass
    accounts: int
    value_cr: float
    share: float


class ClassCompare(BaseModel):
    asset_class: AssetClass
    imported_share: float
    profile_share: float
    difference: float


class ConsolidationOut(BaseModel):
    profile_id: int
    imports: int
    lines: int
    total_cr: float
    by_class: list[ClassTotal]
    by_account: list[AccountTotal]
    top_positions: list[PositionOut] = Field(description="The largest holdings, with the same name added up across accounts.")
    profile_corpus_cr: float
    difference_cr: float = Field(description="Imported total minus the profile's corpus.")
    compare: list[ClassCompare]


class TemplateOut(BaseModel):
    filename: str
    content: str


class ApplyIn(Strict):
    set_corpus: bool = Field(False, description="Also set the profile's corpus to the imported total.")


class HoldingsView(BaseModel):
    corpus_cr: float
    shares: dict[str, float]


class ApplyOut(BaseModel):
    before: HoldingsView
    after: HoldingsView
    changed: bool
    saved: bool
    notes: list[str]
