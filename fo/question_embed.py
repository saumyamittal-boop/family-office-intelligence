"""A small local embedding model for the question router (ADR-0021, decision 4: the step taken because the word matcher missed its bars).

It turns a sentence into a vector so that two phrasings of the same question land near each other even when they share no words. It only
ever helps *choose which question was asked*; it never writes an answer or a number. Everything is optional: if the library or the model
files are missing, or fail their hash check, `load()` returns None and the router carries on with the plain word matcher.

Nothing is downloaded here. `tools/fetch_embedding_model.py` fetches the model once, on purpose; this module reads it from disk only.
"""
from __future__ import annotations

import hashlib
import logging
import os
import pathlib
import threading

import numpy as np

log = logging.getLogger("fo.embed")

MODEL = "BAAI/bge-small-en-v1.5"  # MIT licence; the quantised ONNX build from Qdrant/bge-small-en-v1.5-onnx-Q, about 67 MB
# sha256 of the files that matter, recorded when the model was first fetched. A file that does not match is never loaded.
EXPECTED_SHA256: dict[str, str] = {
    "model_optimized.onnx": "51f1bd0addd6e859e42c2c8021a5e5461385bb676a649f4b269aa445449f2431",
    "tokenizer.json": "d241a60d5e8f04cc1b2b3e9ef7a4921b27bf526d9f6050ab90f9267a1f9e5c66",
    "tokenizer_config.json": "0b29c7bfc889e53b36d9dd3e686dd4300f6525110eaa98c76a5dafceb2029f53",
    "special_tokens_map.json": "5d5b662e421ea9fac075174bb0688ee0d9431699900b90662acd44b2a350503a",
    "config.json": "13582bcf2effc85b7bf3d3f5532e686bc1c9ce86bb009d10f0ec33cbe92299dd",
}
_REPO = pathlib.Path(__file__).resolve().parent.parent


def model_dir() -> pathlib.Path:
    return pathlib.Path(os.environ.get("FO_EMBED_DIR") or _REPO / "data" / "models")


class Embedder:
    """Sentence to unit-length vector. One ONNX session, one thread, guarded by a lock (the router is called from several request threads)."""

    def __init__(self, model) -> None:
        self._model = model
        self._lock = threading.Lock()

    def embed(self, texts: list[str]) -> np.ndarray:
        with self._lock:
            vectors = np.asarray(list(self._model.embed(texts)), dtype=np.float32)
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        return vectors / np.where(norms == 0, 1.0, norms)


def _verified(folder: pathlib.Path) -> bool:
    if not EXPECTED_SHA256:
        return True  # nothing recorded yet (only while the model is first being fetched)
    found = {p.name: p for p in folder.rglob("*") if p.is_file() and p.name in EXPECTED_SHA256}
    for name, digest in EXPECTED_SHA256.items():
        path = found.get(name)
        if path is None or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            log.warning("embedding model file %s is missing or does not match its recorded hash; not using the model", name)
            return False
    return True


def load(folder: pathlib.Path | None = None) -> Embedder | None:
    """The embedder, or None when it cannot be used (library absent, files absent or altered). Never downloads."""
    folder = folder or model_dir()
    if os.environ.get("FO_EMBED") == "0" or not folder.exists():
        return None
    try:
        from fastembed import TextEmbedding
    except ImportError:
        return None
    if not _verified(folder):
        return None
    try:
        return Embedder(TextEmbedding(model_name=MODEL, cache_dir=str(folder), threads=1, local_files_only=True))
    except Exception as err:  # a damaged or incomplete download must not take the assistant down
        log.warning("embedding model could not be loaded (%s); using the word matcher only", type(err).__name__)
        return None
