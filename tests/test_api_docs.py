"""docs/api.md is generated from the application; it must match the code, and say who may call what."""
from api.config import Settings
from api.main import create_app
from tools.export_api_docs import DOC_PATH, PURPOSE, operations, render


def test_the_committed_api_reference_matches_the_running_api():
    assert DOC_PATH.exists(), "Run: python tools/export_api_docs.py"
    assert DOC_PATH.read_text(encoding="utf-8") == render(), "The API changed. Run: python tools/export_api_docs.py"


def test_every_operation_is_described_and_nothing_extra():
    app = create_app(Settings(docs=True))
    actual = {f"{m} {r.path}" for r in operations(app) for m in r.methods - {"HEAD", "OPTIONS"}}
    assert len(actual) == 32
    assert actual == set(PURPOSE)


def test_the_reference_states_who_may_call_each_operation():
    text = render()
    for public in ("GET /api/health", "GET /api/meta", "POST /api/auth/login", "GET /api/plan/config", "GET /api/explain/catalog"):
        row = next(line for line in text.splitlines() if line.startswith(f"| `{public}`"))
        assert "| Public |" in row, public
    for guarded in ("PUT /api/profiles/{profile_id}", "POST /api/profiles/{profile_id}/explain", "DELETE /api/dashboard"):
        row = next(line for line in text.splitlines() if line.startswith(f"| `{guarded}`"))
        assert "Signed in + CSRF token" in row, guarded


def test_the_reference_does_not_claim_more_than_the_service_does():
    text = render().lower()
    for word in ("guaranteed", "optimal", "production-ready", "certified"):
        assert word not in text
