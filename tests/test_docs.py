"""The documentation must not drift from the code it describes, and must not claim more than the project has done."""
import re
from pathlib import Path

import pytest

from api.config import Settings
from fo import engine

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
MARKDOWN = [ROOT / "README.md", ROOT / "CHANGELOG.md", *sorted(DOCS.rglob("*.md"))]

DISCLAIMER = "Illustrative simulation, not investment advice"


def text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def pct(value: float) -> str:
    return f"{value * 100:g}%"


# ---- links -------------------------------------------------------------------------------------------------------------
_LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")


def _local_links(path: Path):
    body = re.sub(r"```.*?```", "", text(path), flags=re.S)  # code samples may contain bracket-and-parenthesis text that is not a link
    for target in _LINK.findall(body):
        if re.match(r"^[a-z]+:", target) or target.startswith("#"):
            continue
        yield target.split("#", 1)[0]


@pytest.mark.parametrize("path", MARKDOWN, ids=lambda p: str(p.relative_to(ROOT)))
def test_every_relative_link_points_at_a_file_that_exists(path):
    missing = [t for t in _local_links(path) if t and not (path.parent / t).resolve().exists()]
    assert not missing, f"{path.relative_to(ROOT)} links to files that do not exist: {missing}"


# ---- settings ----------------------------------------------------------------------------------------------------------
SETTING_SOURCES = [*ROOT.glob("api/*.py"), *ROOT.glob("fo/*.py"), *ROOT.glob("tools/*.py"), ROOT / "web" / "vite.config.ts"]


def _settings_in_code() -> set[str]:
    names: set[str] = set()
    for source in SETTING_SOURCES:
        names |= set(re.findall(r"\b(FO_[A-Z0-9_]+)\b", text(source)))
    return {n for n in names if not n.endswith("_")}  # a prefix such as "FO_" in a comment is not a setting


def test_the_code_reads_the_settings_we_expect():
    assert {"FO_DB_PATH", "FO_API_DOCS", "FO_EMBED", "FO_EMBED_DIR", "FO_API_URL", "FO_ACCESS_CODE"} <= _settings_in_code()


def test_every_setting_the_code_reads_is_documented_and_in_the_example_file():
    configuration, example = text(DOCS / "configuration.md"), text(ROOT / ".env.example")
    for name in sorted(_settings_in_code()):
        assert f"`{name}`" in configuration, f"{name} is read by the code but missing from docs/configuration.md"
        assert name in example, f"{name} is read by the code but missing from .env.example"


def test_the_documented_defaults_are_the_real_defaults():
    configuration, defaults = text(DOCS / "configuration.md"), Settings()
    expected = {
        "FO_API_SESSION_HOURS": f"{defaults.session_hours:g}",
        "FO_API_DEMO_HOURS": f"{defaults.demo_hours:g}",
        "FO_API_MAX_PROFILES": f"{defaults.max_profiles}",
        "FO_API_MAX_BODY_KB": f"{defaults.max_body_bytes // 1024}",
        "FO_API_ANALYSIS_TIMEOUT": f"{defaults.analysis_timeout:g}",
        "FO_MAX_ACCOUNTS": f"{defaults.max_accounts}",
    }
    for name, default in expected.items():
        row = next(line for line in configuration.splitlines() if line.startswith(f"| `{name}`"))
        assert f"| `{default}` |" in row, f"{name}: docs/configuration.md does not show the default {default}"
    origins = next(line for line in configuration.splitlines() if line.startswith("| `FO_API_CORS_ORIGINS`"))
    assert all(origin in origins for origin in defaults.cors_origins)


# ---- assumptions ---------------------------------------------------------------------------------------------------------
def test_the_assumption_table_matches_the_engine():
    doc = text(DOCS / "protected-assumptions.md")
    large, mid, debt, gold, cash = engine.LARGE, engine.MID, engine.DEBT, engine.GOLD, engine.CASH
    priors, cuts = engine.PRIOR_RETURNS, engine.HAIRCUTS
    assert f"{pct(engine.INFLATION)} a year" in doc
    assert f"Large-cap {pct(priors[large])}, mid-cap {pct(priors[mid])}, debt {pct(priors[debt])}, gold {pct(priors[gold])}, cash {pct(priors[cash])}" in doc
    assert f"Cash {pct(cuts[cash])}, debt {pct(cuts[debt])}, gold {pct(cuts[gold])}, large-cap {pct(cuts[large])}, mid-cap {pct(cuts[mid])}" in doc
    assert " / ".join(pct(p) for _, p in engine.RISK_POSITIONS) in doc
    assert f"x{engine.LAMBDA_STEP:g} per step, up to {engine.MAX_STEPS} steps" in doc


def test_the_methodology_quotes_the_same_numbers():
    doc = text(DOCS / "methodology.md")
    assert f"lambda is multiplied by {engine.LAMBDA_STEP:g}" in doc and f"up to {engine.MAX_STEPS} times" in doc
    for label, position in engine.RISK_POSITIONS:
        assert f"{label} {pct(position)}" in doc


# ---- deployment ------------------------------------------------------------------------------------------------------------
def _web_headers() -> dict[str, str]:
    source = text(ROOT / "web" / "security-headers.ts")
    csp_block = re.search(r"export const CSP = \[(.*?)\]\.join", source, re.S).group(1)
    headers = {"Content-Security-Policy": "; ".join(re.findall(r'"([^"]+)"', csp_block))}
    body = re.search(r"SECURITY_HEADERS[^=]*= \{(.*?)\};", source, re.S).group(1)
    for name, value in re.findall(r'"([A-Za-z-]+)":\s*"([^"]+)"', body):
        headers.setdefault(name, value)
    return headers


def test_the_proxy_example_sends_the_headers_the_web_app_was_tested_with():
    doc = text(DOCS / "deployment-react.md")
    for name, value in _web_headers().items():
        assert f'{name} "{value}"' in doc, f"deployment-react.md does not carry the {name} header from web/security-headers.ts"


def test_the_api_and_proxy_agree_on_hsts():
    assert 'Strict-Transport-Security "max-age=15552000"' in text(DOCS / "deployment-react.md")
    assert "max-age=15552000" in text(ROOT / "api" / "main.py")


# ---- honesty -------------------------------------------------------------------------------------------------------------------
OVERCLAIMS = [
    "guaranteed return", "guaranteed profit", "bank-grade", "military-grade", "fully secure", "unhackable", "production-ready system",
    "sebi-compliant", "sebi compliant", "regulatory compliant", "fully compliant", "independently validated", "externally validated model",
    "audited by", "penetration-tested", "pen-tested", "certified secure",
]


@pytest.mark.parametrize("path", MARKDOWN, ids=lambda p: str(p.relative_to(ROOT)))
def test_no_document_claims_what_the_project_has_not_done(path):
    lowered = text(path).lower()
    negation = re.compile(r"\b(not|no|nor|never|nothing|without|neither|cannot)\b")
    found = []
    for phrase in OVERCLAIMS:
        for hit in re.finditer(re.escape(phrase), lowered):
            if not negation.search(lowered[max(0, hit.start() - 60): hit.start()]):  # "nothing here is independently validated" says the opposite
                found.append(phrase)
    assert not found, f"{path.relative_to(ROOT)} makes a claim the project cannot support: {found}"


@pytest.mark.parametrize("name", ["README.md", "docs/architecture.md", "docs/methodology.md", "docs/limitations.md"])
def test_the_disclaimer_is_visible_where_a_reader_starts(name):
    assert DISCLAIMER.lower() in text(ROOT / name).lower().replace("*", "")


def test_every_handover_document_exists_and_is_indexed():
    index = text(DOCS / "README.md")
    required = ["architecture", "setup", "configuration", "database", "api", "methodology", "holdings-import", "testing",
                "deployment-react", "production-readiness", "limitations", "handover"]
    for name in required:
        assert (DOCS / f"{name}.md").exists(), f"docs/{name}.md is missing"
        assert f"({name}.md)" in index, f"docs/README.md does not link to {name}.md"
