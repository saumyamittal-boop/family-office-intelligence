"""The React demo script quotes figures; every one must be what the application shows, and the demo kit must be in place."""
from pathlib import Path

import pytest

from tools import demo_check

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = demo_check.SCRIPT


@pytest.fixture()
def figures(make_client):
    return demo_check.figures(make_client)


def test_every_figure_in_the_demo_script_is_what_the_application_shows(figures):
    absent = demo_check.missing(figures, SCRIPT.read_text(encoding="utf-8"))
    assert not absent, f"docs/demo-script-react.md does not contain these figures (or they changed): {absent}"


def test_the_script_states_how_many_figures_the_launcher_will_report(figures):
    assert f"{len(figures)} of {len(figures)} figures in docs/demo-script-react.md match the running application" in SCRIPT.read_text(encoding="utf-8")


def test_the_demo_statement_is_the_synthetic_thousand_crore_file():
    lines = demo_check.STATEMENT.read_text(encoding="utf-8").splitlines()
    assert lines[0].startswith("Name,Asset class,Account,Value")
    assert len(lines) == 8  # a header and seven holdings, one of them labelled with the ambiguous word "Equity"
    assert any(line.split(",")[1] == demo_check.AMBIGUOUS_LABEL for line in lines[1:])
    assert sum(float(line.split(",")[3]) for line in lines[1:]) == 1000.0


def test_the_demo_kit_is_complete_and_leaves_the_development_database_alone():
    for name in ("start-demo.cmd", "start-demo.ps1", "stop-demo.cmd", "stop-demo.ps1", "share-demo.cmd", "share-demo.ps1", "gate.py"):
        assert (ROOT / "demo" / name).exists(), f"demo/{name} is missing"
    for name in ("start-demo.ps1", "stop-demo.ps1", "share-demo.ps1"):
        assert (ROOT / "demo" / name).read_text(encoding="utf-8").isascii(), f"{name}: Windows PowerShell 5.1 misreads non-ASCII characters in a script without a byte-order mark"
    launcher = (ROOT / "demo" / "start-demo.ps1").read_text(encoding="utf-8")
    sharer = (ROOT / "demo" / "share-demo.ps1").read_text(encoding="utf-8")
    assert "-Shared" in sharer and "gate.py" in sharer and "401" in sharer  # shared mode, through the gate, and it proves the gate refuses a visitor with no password
    assert "FO_API_COOKIE_SECURE" in launcher and "FO_API_DOCS" in launcher and "FO_MAX_ACCOUNTS" in launcher
    assert "demo/bin/" in (ROOT / ".gitignore").read_text(encoding="utf-8")  # the downloaded tunnel program is never committed
    assert "FO_DB_PATH" in launcher and "demo.db" in launcher  # its own database, never data\app.db
    assert "data\\app.db" not in launcher.replace("data\\app.db is not touched", "")
    assert "demo_check.py" in launcher  # it checks the figures before the browser opens
    script = SCRIPT.read_text(encoding="utf-8")
    assert "demo\\start-demo.cmd" in script and "demo\\stop-demo.cmd" in script
