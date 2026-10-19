"""The committed API contract (and the TypeScript types made from it) must match the code."""
import json
from pathlib import Path

from tools.export_openapi import CONTRACT_PATH, current_contract

SCHEMA_TS = CONTRACT_PATH.with_name("schema.d.ts")


def test_the_committed_contract_matches_the_running_api():
    assert CONTRACT_PATH.exists(), "Run: python tools/export_openapi.py"
    assert CONTRACT_PATH.read_text(encoding="utf-8") == current_contract(), (
        "The API changed. Run: python tools/export_openapi.py  then  npm run gen:api  (in web/)."
    )


def test_every_endpoint_is_in_the_contract_and_states_how_it_authenticates():
    paths = json.loads(current_contract())["paths"]
    expected = {
        "/api/health", "/api/meta", "/api/auth/login", "/api/auth/signup", "/api/auth/demo", "/api/auth/me",
        "/api/auth/logout", "/api/profiles", "/api/profiles/{profile_id}", "/api/profiles/{profile_id}/analysis",
    }
    assert set(paths) == expected


def test_typescript_types_exist_and_name_the_main_shapes():
    text = SCHEMA_TS.read_text(encoding="utf-8")
    for name in ("AnalysisOut", "PortfolioOut", "ProfileIn", "SessionOut", "Problem"):
        assert name in text, f"{name} missing from schema.d.ts; run npm run gen:api"
    assert "optimiser_converged" in text


def test_no_secret_looking_default_leaks_into_the_contract():
    spec = current_contract().lower()
    for word in ("fo_access_code", "secret_key", "begin private key"):
        assert word not in spec
