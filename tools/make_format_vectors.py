"""Record what the Python formatter (fo.ui) prints for many numbers, so the TypeScript formatter can be checked
against it. Run from the project root:  python tools/make_format_vectors.py
"""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from fo import ui  # noqa: E402

VECTORS_PATH = ROOT / "web" / "src" / "test" / "format_vectors.json"

TIES = [0.1375, 0.0875, 0.125, 0.0005, 0.00049999, 0.995, 0.9995, 1.0, 0.0, 0.00001, 0.045, 0.0455, 0.04549999, 0.15, 0.085,
        0.0725, 0.01, 0.2, 0.3, 0.1 + 0.2, 1 / 3, 2 / 3, 1.2345, 12.345]
MONEY = [0.0, 0.05, 0.04999, 0.95, 137.5, 137.25, 137.35, 1000.0, 1234.56, 12345.678, 999999.95, 0.1 + 0.2, 45.0, 63.7, 39.7]


def build() -> dict:
    rng = random.Random(7)
    fractions = TIES + [-v for v in TIES] + [rng.uniform(-1.5, 1.5) for _ in range(150)]
    amounts = MONEY + [-v for v in MONEY] + [rng.uniform(0, 5000) for _ in range(60)]
    return {
        "pct": [{"value": v, "digits": d, "expected": ui.pct(v, d)} for v in fractions for d in (0, 1, 2)],
        "signed_pct": [{"value": v, "digits": d, "expected": ui.signed_pct(v, d)} for v in fractions for d in (1, 2)],
        "cr": [{"value": v, "digits": d, "expected": ui.cr(v, d)} for v in amounts for d in (0, 1)],
        "signed_cr": [{"value": v, "digits": d, "expected": ui.signed_cr(v, d)} for v in amounts for d in (0, 1)],
    }


def main() -> None:
    VECTORS_PATH.parent.mkdir(parents=True, exist_ok=True)
    VECTORS_PATH.write_text(json.dumps(build(), indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    print(f"Wrote {VECTORS_PATH}")


if __name__ == "__main__":
    main()
