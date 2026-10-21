"""Download the small embedding model the question router can use, once, into data/models/ (never committed).

    python tools/fetch_embedding_model.py

Model: BAAI/bge-small-en-v1.5, quantised ONNX build published as Qdrant/bge-small-en-v1.5-onnx-Q on huggingface.co. MIT licence, about 67 MB.
This is the only time the app's code reaches out for it. The server itself never downloads anything: it loads the files from disk (and checks
their hashes against the ones recorded in fo/question_embed.py), or does without the model and uses the plain word matcher.
"""
from __future__ import annotations

import hashlib
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from fo import question_embed as qe  # noqa: E402


def main() -> int:
    from fastembed import TextEmbedding

    target = qe.model_dir()
    target.mkdir(parents=True, exist_ok=True)
    print(f"Downloading {qe.MODEL} into {target} ...")
    TextEmbedding(model_name=qe.MODEL, cache_dir=str(target), threads=1)
    found = {}
    for path in sorted(target.rglob("*")):
        if path.is_file() and not path.is_symlink() and path.suffix in {".onnx", ".json", ".txt"}:
            found[path.name] = (hashlib.sha256(path.read_bytes()).hexdigest(), path.stat().st_size)
    for name, (digest, size) in found.items():
        print(f"  {name:28s} {size:>10,d} bytes  sha256 {digest}")
    if qe.EXPECTED_SHA256:
        bad = [n for n, d in qe.EXPECTED_SHA256.items() if found.get(n, ("",))[0] != d]
        print("Hashes match the ones recorded in fo/question_embed.py." if not bad else f"MISMATCH for: {', '.join(bad)}")
        return 1 if bad else 0
    print("No hashes are recorded yet in fo/question_embed.py: copy the ones above into EXPECTED_SHA256.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
