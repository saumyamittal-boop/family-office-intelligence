"""Holdings import and consolidation logic (ADR-0020). The parser is fo.holdings_import; storage is holdings_store."""
from __future__ import annotations

import base64
import binascii
import math

from pydantic import ValidationError

from fo import accounts
from fo import holdings_import as hi
from fo.personas import Profile

from . import convert
from . import holdings_schemas as hs
from . import holdings_store as store
from . import schemas as s
from .errors import ApiError

EPS = 1e-9


def _parse(body: hs.FileIn) -> hi.Parsed:
    try:
        data = base64.b64decode(body.content_base64, validate=True)
    except (binascii.Error, ValueError):
        raise ApiError(422, "The file could not be decoded.") from None
    try:
        return hi.parse_holdings(data, body.filename, body.unit, dict(body.class_overrides))
    except hi.ImportRefused as why:
        raise ApiError(422, str(why)) from None


def class_totals(lines, total: float) -> list[hs.ClassTotal]:
    out = []
    for asset_class in hi.CLASSES:
        values = [l.value_cr for l in lines if l.asset_class == asset_class]
        amount = math.fsum(values)
        out.append(hs.ClassTotal(asset_class=asset_class, total_cr=amount, share=amount / total if total else 0.0, lines=len(values)))
    return out


def template() -> hs.TemplateOut:
    return hs.TemplateOut(filename="holdings-template.csv", content=hi.TEMPLATE_CSV)


def preview(user_id: int, profile_id: int, body: hs.FileIn) -> hs.PreviewOut:
    parsed = _parse(body)
    total = parsed.total_cr
    return hs.PreviewOut(
        ok=parsed.ok, filename=hi.safe_filename(body.filename), file_kind=parsed.file_kind, unit=parsed.unit, unit_label=hi.UNIT_LABEL[parsed.unit],
        columns=parsed.columns, ignored_columns=parsed.ignored_columns, rows_read=parsed.rows_read, line_count=len(parsed.lines), total_cr=total,
        lines=[hs.LineOut(row=l.row, name=l.name, asset_class=l.asset_class, account=l.account, value_cr=l.value_cr) for l in parsed.lines[: hs.PREVIEW_LINES]],
        by_class=class_totals(parsed.lines, total),
        mapped=[hs.MappedLabel(label=label, asset_class=cls, rows=rows) for label, cls, rows in parsed.mapped],
        unrecognised=[hs.UnrecognisedLabel(label=label, rows=rows) for label, rows in parsed.unrecognised.items()],
        problems=[hs.ProblemOut(severity=p.severity, message=p.message, row=p.row, field=p.field) for p in parsed.problems],
        already_imported=bool(parsed.lines) and store.has_fingerprint(user_id, profile_id, parsed.fingerprint()),
    )


def import_file(user_id: int, profile_id: int, body: hs.ImportIn) -> hs.ImportOut:
    parsed = _parse(body)  # parsed again here: nothing the browser says about the file is trusted
    if not parsed.ok:
        reasons = [p.message for p in parsed.errors][:20] or ["No holdings were found in the file."]
        raise ApiError(422, "This file has problems that must be fixed first.", reasons)
    label = hi._echo(body.label or hi.safe_filename(body.filename), 60) or "Holdings"
    try:
        return store.add_import(user_id, profile_id, label, hi.safe_filename(body.filename), parsed)
    except store.AlreadyImported:
        raise ApiError(409, "This data is already imported for this profile.") from None
    except store.LimitReached as why:
        raise ApiError(409, str(why)) from None


def consolidation(user_id: int, profile_id: int, profile: Profile) -> hs.ConsolidationOut:
    imports, lines = store.stored_lines(user_id, profile_id)
    total = math.fsum(l.value_cr for l in lines)
    accounts_: dict[str, list] = {}
    positions: dict[tuple[str, str], list] = {}
    for l in lines:
        entry = accounts_.setdefault(l.account, [0.0, 0])
        entry[0] += l.value_cr
        entry[1] += 1
        pos = positions.setdefault((l.name.casefold(), l.asset_class), [l.name, 0.0, set()])
        pos[1] += l.value_cr
        pos[2].add(l.account)
    by_class = class_totals(lines, total)
    shares = {c.asset_class: c.share for c in by_class}
    return hs.ConsolidationOut(
        profile_id=profile_id, imports=imports, lines=len(lines), total_cr=total, by_class=by_class,
        by_account=[hs.AccountTotal(account=a, total_cr=v[0], share=v[0] / total, lines=v[1]) for a, v in sorted(accounts_.items(), key=lambda kv: -kv[1][0])],
        top_positions=[
            hs.PositionOut(name=p[0], asset_class=cls, accounts=len(p[2]), value_cr=p[1], share=p[1] / total)
            for (_, cls), p in sorted(positions.items(), key=lambda kv: -kv[1][1])[:5]
        ],
        profile_corpus_cr=profile.corpus_cr, difference_cr=total - profile.corpus_cr if lines else 0.0,
        compare=[
            hs.ClassCompare(asset_class=c, imported_share=shares[c], profile_share=float(profile.holdings.get(c, 0.0)), difference=shares[c] - float(profile.holdings.get(c, 0.0)))
            for c in hi.CLASSES
        ] if lines else [],
    )


def _view(corpus: float, holdings: dict) -> hs.HoldingsView:
    return hs.HoldingsView(corpus_cr=corpus, shares={c: float(holdings.get(c, 0.0)) for c in hi.CLASSES})


def apply(user_id: int, profile_id: int, profile: Profile, body: hs.ApplyIn, save: bool) -> hs.ApplyOut:
    """Show (save=False) or make (save=True) the change: the profile's holding shares become the imported shares."""
    _, lines = store.stored_lines(user_id, profile_id)
    if not lines:
        raise ApiError(409, "Import holdings first.")
    total = math.fsum(l.value_cr for l in lines)
    shares = {c: math.fsum(l.value_cr for l in lines if l.asset_class == c) / total for c in hi.CLASSES}
    fields = convert.profile_to_out(profile_id, profile).model_dump(exclude={"id"})
    fields["holdings"] = shares
    if body.set_corpus:
        fields["corpus_cr"] = total
    refusal = "These holdings can't be applied to the profile."
    try:
        candidate = s.ProfileIn(**fields)
    except ValidationError:
        raise ApiError(422, refusal, ["The imported total is outside what a profile can hold (1 to 1,000,000 crore)."]) from None
    updated, problems = convert.to_domain(candidate, key=f"user{profile_id}")
    if problems or updated is None:
        raise ApiError(422, refusal, problems)

    before, after = _view(profile.corpus_cr, profile.holdings), _view(updated.corpus_cr, updated.holdings)
    changed = abs(before.corpus_cr - after.corpus_cr) > EPS or any(abs(before.shares[c] - after.shares[c]) > EPS for c in hi.CLASSES)
    notes = []
    if not body.set_corpus and abs(total - profile.corpus_cr) > 0.005 * profile.corpus_cr:
        notes.append(
            f"The imported total (₹{total:,.1f} Cr) differs from the profile's corpus (₹{profile.corpus_cr:,.1f} Cr). "
            "The imported shares are applied to the profile's corpus. Tick the box to set the corpus to the imported total as well."
        )
    if save and changed and not accounts.save_profile(user_id, profile_id, updated):
        raise ApiError(404, "Profile not found.")
    return hs.ApplyOut(before=before, after=after, changed=changed, saved=save and changed, notes=notes)
