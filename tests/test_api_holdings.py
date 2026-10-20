"""Holdings import, consolidation and applying them to a profile (ADR-0020). Synthetic files only."""
import base64
import io
import sqlite3
import zipfile

import pytest

from api import holdings_schemas as hs
from fo import holdings_import as hi
from tests.helpers import sign_up
from tests.test_holdings_import import xlsx_bytes

CSV = (
    "Name,Asset class,Account,Value (Cr)\n"
    "Fund A,Large-cap equity,Demat 1,40\n"
    "Fund B,Mid-cap equity,Demat 1,10\n"
    "Bonds C,Debt,Bank 2,30\n"
    "Gold ETF,Gold,Demat 1,5\n"
    "Savings,Cash & liquid,Bank 2,5\n"
    "Office,Real estate,,10\n"
)  # 100 crore: 40 / 10 / 30 / 5 / 5 / 10 percent
SHARES = {"Large-cap equity": 0.40, "Mid-cap equity": 0.10, "Debt": 0.30, "Gold": 0.05, "Cash & liquid": 0.05, "Illiquid": 0.10}


def b64(data: bytes | str) -> str:
    return base64.b64encode(data.encode("utf-8") if isinstance(data, str) else data).decode()


def payload(text: str = CSV, name: str = "statement.csv", **extra) -> dict:
    return {"filename": name, "content_base64": b64(text), **extra}


@pytest.fixture()
def me(client):
    headers = sign_up(client, "holder")
    pid = client.get("/api/profiles").json()[0]["id"]
    return client, headers, pid


def url(pid: int, tail: str) -> str:
    return f"/api/profiles/{pid}/holdings/{tail}"


def do_import(client, headers, pid, text=CSV, name="statement.csv", **extra):
    return client.post(url(pid, "imports"), json=payload(text, name, **extra), headers=headers)


# ---- Who may do what --------------------------------------------------------------------------------------------------
def test_every_holdings_route_but_the_template_needs_a_sign_in(client):
    assert client.get("/api/holdings/template").status_code == 200
    for method, tail in (("get", "imports"), ("get", "consolidation")):
        assert getattr(client, method)(url(1, tail)).status_code == 401
    for tail in ("preview", "imports", "apply", "apply/preview"):
        assert client.post(url(1, tail), json={}).status_code == 401
    assert client.delete(url(1, "imports/1")).status_code == 401


def test_changes_need_the_csrf_token(me):
    client, _, pid = me
    assert client.post(url(pid, "preview"), json=payload()).status_code == 403
    assert client.post(url(pid, "imports"), json=payload()).status_code == 403
    assert client.post(url(pid, "apply"), json={}).status_code == 403
    assert client.delete(url(pid, "imports/1")).status_code == 403


def test_another_accounts_profile_is_simply_not_found(make_client):
    owner, stranger = make_client(), make_client()
    h_owner, h_stranger = sign_up(owner, "owner_h"), sign_up(stranger, "stranger_h")
    pid = owner.get("/api/profiles").json()[0]["id"]
    imported = do_import(owner, h_owner, pid).json()

    assert stranger.get(url(pid, "imports")).status_code == 404
    assert stranger.get(url(pid, "consolidation")).status_code == 404
    assert stranger.post(url(pid, "preview"), json=payload(), headers=h_stranger).status_code == 404
    assert stranger.post(url(pid, "imports"), json=payload(), headers=h_stranger).status_code == 404
    assert stranger.post(url(pid, "apply"), json={}, headers=h_stranger).status_code == 404
    assert stranger.post(url(pid, "apply/preview"), json={}, headers=h_stranger).status_code == 404
    assert stranger.delete(url(pid, f"imports/{imported['id']}"), headers=h_stranger).status_code == 404
    assert len(owner.get(url(pid, "imports")).json()) == 1  # and nothing of the owner's was touched


def test_my_own_import_id_does_not_work_through_another_of_my_profiles(me):
    client, headers, pid = me
    body = client.get(f"/api/profiles/{pid}").json()
    body.pop("id")
    body["name"] = "Second family"
    other = client.post("/api/profiles", json=body, headers=headers).json()["id"]
    first = do_import(client, headers, pid).json()
    assert client.delete(url(other, f"imports/{first['id']}"), headers=headers).status_code == 404
    assert client.get(url(other, "consolidation")).json()["lines"] == 0


# ---- Template, preview ------------------------------------------------------------------------------------------------
def test_the_template_is_a_file_that_previews_clean(me):
    client, headers, pid = me
    t = client.get("/api/holdings/template").json()
    assert t["filename"].endswith(".csv") and t["content"].startswith("Name,Asset class")
    p = client.post(url(pid, "preview"), json=payload(t["content"], t["filename"]), headers=headers).json()
    assert p["ok"] and p["line_count"] == 6 and p["problems"] == []


def test_a_preview_reads_the_file_and_stores_nothing(me):
    client, headers, pid = me
    p = client.post(url(pid, "preview"), json=payload(), headers=headers).json()
    assert p["ok"] and p["file_kind"] == "csv" and p["unit"] == "cr" and p["line_count"] == 6 and p["rows_read"] == 6
    assert p["total_cr"] == pytest.approx(100.0) and p["already_imported"] is False
    assert {c["asset_class"]: c["share"] for c in p["by_class"]} == pytest.approx(SHARES)
    assert p["columns"] == {"name": "Name", "asset_class": "Asset class", "account": "Account", "value": "Value (Cr)"}
    assert {"label": "Real estate", "asset_class": "Illiquid", "rows": 1} in p["mapped"]
    assert client.get(url(pid, "imports")).json() == []


def test_the_preview_says_which_labels_it_could_not_place_and_accepts_an_assignment(me):
    client, headers, pid = me
    text = CSV + "Startup shares,Equity,,5\nOther,Small cap,,2\n"
    first = client.post(url(pid, "preview"), json=payload(text), headers=headers).json()
    assert not first["ok"] and {u["label"] for u in first["unrecognised"]} == {"Equity", "Small cap"}
    assert any("Assign one" in p["message"] for p in first["problems"])
    fixed = client.post(url(pid, "preview"), json=payload(text, class_overrides={"Equity": "Large-cap equity", "Small cap": "Mid-cap equity"}), headers=headers).json()
    assert fixed["ok"] and fixed["unrecognised"] == [] and fixed["line_count"] == 8 and fixed["total_cr"] == pytest.approx(107.0)


def test_a_unit_choice_scales_the_amounts(me):
    client, headers, pid = me
    text = "Name,Class,Value\nA,Debt,200\n"
    assert client.post(url(pid, "preview"), json=payload(text, unit="lakh"), headers=headers).json()["total_cr"] == pytest.approx(2.0)
    assert client.post(url(pid, "preview"), json=payload(text, unit="inr"), headers=headers).json()["total_cr"] == pytest.approx(200 * 1e-7)


def test_an_excel_file_previews_like_a_csv_file(me):
    client, headers, pid = me
    rows = [["Name", "Asset class", "Account", "Value (Cr)"], ["Fund A", "Large-cap equity", "Demat 1", 40], ["Bonds C", "Debt", "Bank 2", 60]]
    p = client.post(url(pid, "preview"), json={"filename": "s.xlsx", "content_base64": b64(xlsx_bytes(rows))}, headers=headers).json()
    assert p["ok"] and p["file_kind"] == "xlsx" and p["total_cr"] == pytest.approx(100.0)


# ---- Hostile and broken requests --------------------------------------------------------------------------------------
def macro_workbook() -> bytes:
    src = zipfile.ZipFile(io.BytesIO(xlsx_bytes([["Name", "Class", "Value"], ["A", "Debt", 1]])))
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as dst:
        for item in src.infolist():
            dst.writestr(item, src.read(item.filename))
        dst.writestr("xl/vbaProject.bin", b"x")
    return out.getvalue()


@pytest.mark.parametrize("body,fragment", [
    ({"filename": "m.xlsx", "content_base64": b64(macro_workbook())}, "macros"),
    ({"filename": "x.csv", "content_base64": "!!!not base64!!!"}, "could not be decoded"),
    ({"filename": "x.exe", "content_base64": b64("MZ")}, "Only .csv and .xlsx"),
    ({"filename": "x.csv", "content_base64": b64(b"a\x00b")}, "not plain text"),
    ({"filename": "x.csv", "content_base64": b64("Name,Value\nA,1\n")}, "needs a column"),
])
def test_files_that_cannot_be_used_get_a_plain_reason_from_both_preview_and_import(me, body, fragment):
    client, headers, pid = me
    for tail in ("preview", "imports"):
        r = client.post(url(pid, tail), json=body, headers=headers)
        assert r.status_code == 422 and fragment in r.json()["detail"], (tail, r.text)
    assert client.get(url(pid, "imports")).json() == []


def test_a_file_over_the_size_limit_is_refused_before_it_is_parsed(me):
    client, headers, pid = me
    big = "Name,Class,Value\n" + "A,Debt,1\n" * 20000
    r = client.post(url(pid, "preview"), json=payload(big), headers=headers)
    assert r.status_code in (413, 422)
    r = client.post(url(pid, "preview"), json={"filename": "x.csv", "content_base64": "A" * (hs.MAX_BASE64 + 1)}, headers=headers)
    assert r.status_code in (413, 422)


@pytest.mark.parametrize("body", [
    {}, {"filename": "x.csv"}, {"content_base64": "QQ=="}, {**payload(), "unit": "dollars"}, {**payload(), "extra": 1},
    {**payload(), "class_overrides": {"Equity": "Crypto"}}, {**payload(), "class_overrides": {"": "Debt"}}, {"filename": "", "content_base64": "QQ=="},
])
def test_malformed_requests_are_refused(me, body):
    client, headers, pid = me
    assert client.post(url(pid, "preview"), json=body, headers=headers).status_code == 422


def test_a_refusal_does_not_echo_what_was_sent(me):
    client, headers, pid = me
    r = client.post(url(pid, "preview"), json={"filename": "<script>alert(1)</script>.exe", "content_base64": b64("<script>alert(2)</script>")}, headers=headers)
    assert r.status_code == 422 and "<script>" not in r.text


def test_formula_injection_in_a_file_is_an_error_not_stored(me):
    client, headers, pid = me
    text = 'Name,Class,Value\n"=HYPERLINK(""http://evil.example"")",Debt,5\n'
    r = do_import(client, headers, pid, text)
    assert r.status_code == 422 and any("formula" in m for m in r.json()["problems"])
    assert client.get(url(pid, "imports")).json() == []


def test_the_upload_endpoints_are_rate_limited(me):
    client, headers, pid = me
    codes = [client.post(url(pid, "preview"), json=payload("Name,Class,Value\nA,Debt,1\n"), headers=headers).status_code for _ in range(62)]
    assert codes[:60] == [200] * 60 and codes[60] == 429


# ---- Importing and consolidating --------------------------------------------------------------------------------------
def test_confirming_stores_the_file_and_lists_it(me):
    client, headers, pid = me
    r = do_import(client, headers, pid, label="Statement, March")
    assert r.status_code == 201
    out = r.json()
    assert (out["label"], out["filename"], out["file_kind"], out["unit"], out["row_count"]) == ("Statement, March", "statement.csv", "csv", "cr", 6)
    assert out["total_cr"] == pytest.approx(100.0)
    assert client.get(url(pid, "imports")).json() == [out]
    assert do_import(client, headers, pid, name="other.csv").status_code == 409  # same data, whatever the file is called
    assert client.post(url(pid, "preview"), json=payload(), headers=headers).json()["already_imported"] is True


def test_the_label_defaults_to_the_file_name_and_is_cleaned(me):
    client, headers, pid = me
    assert do_import(client, headers, pid, name="C:\\docs\\march.csv").json()["label"] == "march.csv"
    r = do_import(client, headers, pid, CSV.replace("Fund A", "Fund Z"), label="  spaced   out  ")
    assert r.json()["label"] == "spaced out"


def test_a_file_with_errors_cannot_be_confirmed_even_if_the_browser_says_it_is_fine(me):
    client, headers, pid = me
    r = do_import(client, headers, pid, CSV + "Bad,Debt,,-3\n")
    assert r.status_code == 422 and any("above zero" in m for m in r.json()["problems"])
    assert client.get(url(pid, "imports")).json() == []


def test_the_consolidation_adds_up_across_imports_accounts_and_names(me):
    client, headers, pid = me
    do_import(client, headers, pid)
    second = "Name,Asset class,Account,Value (Cr)\nFund A,Large-cap equity,Demat 3,20\nBonds D,Debt,Bank 2,30\n"
    assert do_import(client, headers, pid, second, "second.csv").status_code == 201
    c = client.get(url(pid, "consolidation")).json()
    assert (c["imports"], c["lines"]) == (2, 8) and c["total_cr"] == pytest.approx(150.0)
    by_class = {x["asset_class"]: x for x in c["by_class"]}
    assert by_class["Large-cap equity"]["total_cr"] == pytest.approx(60.0) and by_class["Large-cap equity"]["share"] == pytest.approx(0.4)
    assert by_class["Debt"]["total_cr"] == pytest.approx(60.0) and by_class["Debt"]["lines"] == 2
    assert sum(x["share"] for x in c["by_class"]) == pytest.approx(1.0) and [x["asset_class"] for x in c["by_class"]] == list(hi.CLASSES)
    accounts_ = {a["account"]: a for a in c["by_account"]}
    assert accounts_["Bank 2"]["total_cr"] == pytest.approx(65.0) and accounts_["Demat 1"]["total_cr"] == pytest.approx(55.0) and accounts_[""]["total_cr"] == pytest.approx(10.0)
    assert [a["total_cr"] for a in c["by_account"]] == sorted((a["total_cr"] for a in c["by_account"]), reverse=True)
    top = c["top_positions"]
    assert top[0] == {"name": "Fund A", "asset_class": "Large-cap equity", "accounts": 2, "value_cr": pytest.approx(60.0), "share": pytest.approx(0.4)}  # added up across accounts
    assert len(top) == 5 and [p["value_cr"] for p in top] == sorted((p["value_cr"] for p in top), reverse=True)


def test_the_consolidation_compares_with_the_profile(me):
    client, headers, pid = me
    do_import(client, headers, pid)
    profile = client.get(f"/api/profiles/{pid}").json()
    c = client.get(url(pid, "consolidation")).json()
    assert c["profile_corpus_cr"] == profile["corpus_cr"] and c["difference_cr"] == pytest.approx(100.0 - profile["corpus_cr"])
    for row in c["compare"]:
        assert row["profile_share"] == pytest.approx(profile["holdings"][row["asset_class"]])
        assert row["difference"] == pytest.approx(row["imported_share"] - row["profile_share"])


def test_with_nothing_imported_the_consolidation_is_empty_not_an_error(me):
    client, _, pid = me
    c = client.get(url(pid, "consolidation")).json()
    assert (c["imports"], c["lines"], c["total_cr"], c["compare"], c["by_account"], c["top_positions"]) == (0, 0, 0.0, [], [], [])
    assert len(c["by_class"]) == 6 and all(x["share"] == 0.0 for x in c["by_class"])


def test_deleting_an_import_removes_its_lines_from_the_consolidation(me):
    client, headers, pid = me
    first = do_import(client, headers, pid).json()
    second = do_import(client, headers, pid, "Name,Class,Value\nOnly,Gold,7\n", "g.csv").json()
    assert client.delete(url(pid, f"imports/{first['id']}"), headers=headers).status_code == 204
    c = client.get(url(pid, "consolidation")).json()
    assert (c["imports"], c["lines"], c["total_cr"]) == (1, 1, pytest.approx(7.0))
    assert client.delete(url(pid, f"imports/{first['id']}"), headers=headers).status_code == 404
    assert client.delete(url(pid, f"imports/{second['id']}"), headers=headers).status_code == 204
    assert do_import(client, headers, pid).status_code == 201  # deleted data can be imported again


def test_import_count_and_line_limits(me, monkeypatch):
    client, headers, pid = me
    monkeypatch.setattr(hs, "MAX_IMPORTS_PER_PROFILE", 3)
    for i in range(3):
        assert do_import(client, headers, pid, f"Name,Class,Value\nA{i},Debt,{i + 1}\n", f"f{i}.csv").status_code == 201
    r = do_import(client, headers, pid, "Name,Class,Value\nZ,Debt,9\n", "z.csv")
    assert r.status_code == 409 and "at most 3 imports" in r.json()["detail"]
    monkeypatch.setattr(hs, "MAX_IMPORTS_PER_PROFILE", 20)
    monkeypatch.setattr(hs, "MAX_LINES_PER_PROFILE", 4)
    r = do_import(client, headers, pid, "Name,Class,Value\nA,Debt,11\nB,Debt,12\nC,Debt,13\n", "many.csv")
    assert r.status_code == 409 and "imported lines" in r.json()["detail"]


def test_deleting_a_profile_or_an_account_removes_its_imported_holdings(make_client, db_path):
    c = make_client()
    headers = sign_up(c, "cascade")
    body = c.get(f"/api/profiles/{c.get('/api/profiles').json()[0]['id']}").json()
    body.pop("id")
    body["name"] = "Second"
    second = c.post("/api/profiles", json=body, headers=headers).json()["id"]
    do_import(c, headers, second)
    count = lambda: sqlite3.connect(db_path).execute("SELECT (SELECT COUNT(*) FROM holdings), (SELECT COUNT(*) FROM holding_imports)").fetchone()
    assert count() == (6, 1)
    assert c.delete(f"/api/profiles/{second}", headers=headers).status_code == 204
    assert count() == (0, 0)
    user_id = c.get("/api/auth/me").json()["user"]["id"]
    first = c.get("/api/profiles").json()[0]["id"]
    do_import(c, headers, first)
    with sqlite3.connect(db_path) as con:
        con.execute("PRAGMA foreign_keys = ON")
        con.execute("DELETE FROM users WHERE id = ?", (user_id,))
    assert count() == (0, 0)


# ---- Using the holdings in the profile --------------------------------------------------------------------------------
def holdings_of(client, pid):
    p = client.get(f"/api/profiles/{pid}").json()
    return p["corpus_cr"], p["holdings"]


def test_nothing_changes_the_profile_until_the_person_applies_it(me):
    client, headers, pid = me
    before = holdings_of(client, pid)
    do_import(client, headers, pid)
    assert holdings_of(client, pid) == before  # importing alone never edits a profile
    preview = client.post(url(pid, "apply/preview"), json={}, headers=headers).json()
    assert preview["changed"] is True and preview["saved"] is False
    assert preview["before"]["shares"] == pytest.approx(before[1]) and preview["after"]["shares"] == pytest.approx(SHARES)
    assert holdings_of(client, pid) == before  # a preview does not save either


def test_applying_makes_the_imported_shares_the_profiles_and_the_numbers_reach_the_engine(me):
    client, headers, pid = me
    do_import(client, headers, pid)
    r = client.post(url(pid, "apply"), json={}, headers=headers).json()
    assert r["saved"] is True and r["after"]["shares"] == pytest.approx(SHARES)
    corpus, holdings = holdings_of(client, pid)
    assert holdings == pytest.approx(SHARES) and corpus == 100.0  # the starter profile's corpus happens to equal the file's total
    current = client.get(f"/api/profiles/{pid}/analysis").json()["current"]["weights_total"]
    assert current == pytest.approx(SHARES)  # what the optimiser starts from is exactly what was imported
    again = client.post(url(pid, "apply"), json={}, headers=headers).json()
    assert again["changed"] is False and again["saved"] is False  # applying twice changes nothing the second time


def test_the_corpus_changes_only_if_the_person_ticks_the_box_and_a_difference_is_flagged(me):
    client, headers, pid = me
    do_import(client, headers, pid, CSV.replace("Office,Real estate,,10", "Office,Real estate,,50"))  # 140 crore
    corpus_before, _ = holdings_of(client, pid)
    plain = client.post(url(pid, "apply"), json={}, headers=headers).json()
    assert holdings_of(client, pid)[0] == corpus_before and any("differs from the profile's corpus" in n for n in plain["notes"])
    ticked = client.post(url(pid, "apply"), json={"set_corpus": True}, headers=headers).json()
    assert ticked["after"]["corpus_cr"] == pytest.approx(140.0) and holdings_of(client, pid)[0] == pytest.approx(140.0) and ticked["notes"] == []


def test_an_apply_the_profile_rules_refuse_says_why_and_changes_nothing(me):
    client, headers, pid = me
    do_import(client, headers, pid, "Name,Class,Value\nBuilding,Real estate,96\nCash,Cash,4\n")
    before = holdings_of(client, pid)
    for tail in ("apply/preview", "apply"):
        r = client.post(url(pid, tail), json={}, headers=headers)
        assert r.status_code == 422 and any("95%" in p for p in r.json()["problems"])
    assert holdings_of(client, pid) == before


def test_a_total_too_small_for_a_corpus_is_refused_when_the_box_is_ticked(me):
    client, headers, pid = me
    do_import(client, headers, pid, "Name,Class,Value\nA,Debt,0.4\nB,Gold,0.1\n")
    r = client.post(url(pid, "apply"), json={"set_corpus": True}, headers=headers)
    assert r.status_code == 422 and "1 to 1,000,000" in r.json()["problems"][0]


def test_applying_with_nothing_imported_is_a_clear_conflict(me):
    client, headers, pid = me
    for tail in ("apply/preview", "apply"):
        r = client.post(url(pid, tail), json={}, headers=headers)
        assert r.status_code == 409 and "Import holdings first" in r.json()["detail"]
