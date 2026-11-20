"""脚本公用的小工具：让 `python scripts/xxx.py` 能直接 import rag 包。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from rag.config import Settings  # noqa: E402
from rag.dense import SentenceTransformerEmbedder  # noqa: E402
from rag.retriever import Retriever  # noqa: E402


def make_embedder(s: Settings) -> SentenceTransformerEmbedder:
    return SentenceTransformerEmbedder(s.embed_model, s.embed_device, s.embed_query_prefix)


def load_retriever(s: Settings | None = None) -> Retriever:
    s = s or Settings()
    return Retriever.load(s, make_embedder(s))


def read_jsonl(path: str | Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def write_jsonl(path: str | Path, rows: list[dict]) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
