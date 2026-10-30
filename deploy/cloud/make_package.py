"""Build the zip that is uploaded to Azure App Service. Run on the laptop, from the repository:

    .venv\\Scripts\\python.exe deploy\\cloud\\make_package.py            (writes ..\\foi-azure-package\\fo-azure.zip)

It builds the web app (web/dist), then zips what the server needs and nothing else:
  * api/, fo/, demo/gate.py and deploy/cloud/ (tracked files plus new ones Git does not ignore, so uncommitted changes are included);
  * web/dist (the built app) and data/models (the assistant's model files, which Git ignores; fetched once by tools/fetch_embedding_model.py);
  * one requirements.txt: the app's packages plus the API's, because App Service installs only that file.
No database, no market snapshot (the app then uses its built-in synthetic sample, as the laptop demo does), no tests, docs or web sources.
Paths inside the zip use forward slashes, which Linux needs (PowerShell 5's Compress-Archive writes backslashes).
"""
from __future__ import annotations

import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT.parent / "foi-azure-package" / "fo-azure.zip"
CODE = ("api/", "fo/", "deploy/cloud/", "demo/gate.py", "demo/__init__.py")
SKIP = ("__pycache__", ".pyc")


def _files() -> list[str]:
    listed = subprocess.run(["git", "ls-files", "-co", "--exclude-standard"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.splitlines()
    return [p for p in listed if p.startswith(CODE) and not any(s in p for s in SKIP) and (ROOT / p).is_file()]


def _tree(folder: Path) -> list[Path]:
    return [p for p in sorted(folder.rglob("*")) if p.is_file() and not any(s in str(p) for s in SKIP)]


def main() -> int:
    vite = ROOT / "web" / "node_modules" / "vite" / "bin" / "vite.js"
    if "--skip-web" not in sys.argv:
        print("Building the web app...")
        subprocess.run(["node", str(vite), "build", "--logLevel", "error"], cwd=ROOT / "web", check=True)
    dist, models = ROOT / "web" / "dist", ROOT / "data" / "models"
    for needed, how in ((dist / "index.html", "the web build"), (models, "python tools/fetch_embedding_model.py")):
        if not needed.exists():
            print(f"Missing {needed}; run {how} first.")
            return 1

    requirements = "\n".join(
        (ROOT / name).read_text(encoding="utf-8") for name in ("requirements.txt", "requirements-api.txt")
    )
    OUT.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
        for rel in _files():
            z.write(ROOT / rel, rel)
        for folder in (dist, models):
            for path in _tree(folder):
                z.write(path, path.relative_to(ROOT).as_posix())
        z.writestr("requirements.txt", requirements)
        count = len(z.namelist())
    print(f"Wrote {OUT} ({count} files, {OUT.stat().st_size / 2**20:.0f} MB).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
