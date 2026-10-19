"""Write the API's OpenAPI contract to web/src/api/openapi.json.

Run from the project root:  python tools/export_openapi.py
Then, in web/:              npm run gen:api     (regenerates src/api/schema.d.ts)

tests/test_openapi_contract.py fails whenever the committed file no longer matches the code.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from api.config import Settings  # noqa: E402
from api.main import create_app  # noqa: E402

CONTRACT_PATH = ROOT / "web" / "src" / "api" / "openapi.json"


def current_contract() -> str:
    spec = create_app(Settings(docs=True)).openapi()
    return json.dumps(spec, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def main() -> None:
    CONTRACT_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONTRACT_PATH.write_text(current_contract(), encoding="utf-8", newline="\n")
    print(f"Wrote {CONTRACT_PATH}")


if __name__ == "__main__":
    main()
