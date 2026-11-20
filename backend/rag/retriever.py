"""把 加载 → 切分 → 建索引 → 检索 串起来。

索引落盘只存两样东西（BM25 启动时现建，几秒钟）：
    index_dir/chunks.jsonl     每行一个 chunk
    index_dir/embeddings.npy   形状 (chunk 数, 向量维度)
    index_dir/meta.json        用的哪个 embedding 模型、多少 chunk
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Literal

import numpy as np

from .bm25 import BM25
from .chunker import chunk_documents
from .config import Settings
from .dense import DenseIndex, Embedder
from .fusion import linear, rrf
from .loader import load_documents
from .schema import Chunk, Hit
from .text import tokenize

Mode = Literal["hybrid", "dense", "sparse"]


def save_index(index_dir: Path, chunks: list[Chunk], embeddings: np.ndarray, meta: dict) -> None:
    index_dir.mkdir(parents=True, exist_ok=True)
    with open(index_dir / "chunks.jsonl", "w", encoding="utf-8") as f:
        for c in chunks:
            f.write(json.dumps(c.to_dict(), ensure_ascii=False) + "\n")
    np.save(index_dir / "embeddings.npy", embeddings)
    (index_dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


def load_index(index_dir: Path) -> tuple[list[Chunk], np.ndarray, dict]:
    if not (index_dir / "chunks.jsonl").exists():
        raise FileNotFoundError(f"索引不存在: {index_dir}，请先运行 scripts/build_index.py")
    with open(index_dir / "chunks.jsonl", encoding="utf-8") as f:
        chunks = [Chunk(**json.loads(line)) for line in f if line.strip()]
    embeddings = np.load(index_dir / "embeddings.npy")
    meta = json.loads((index_dir / "meta.json").read_text(encoding="utf-8"))
    return chunks, embeddings, meta


class Retriever:
    def __init__(self, chunks: list[Chunk], embeddings: np.ndarray, embedder: Embedder,
                 rrf_k: int = 60, candidates: int = 50):
        assert len(chunks) == len(embeddings), "chunk 数量和向量数量对不上，请重建索引"
        self.chunks = chunks
        self.embedder = embedder
        self.dense = DenseIndex(embeddings)
        self.bm25 = BM25().fit([tokenize(c.index_text()) for c in chunks])
        self.rrf_k = rrf_k
        self.candidates = candidates

    # ---------- 构建 / 加载 ----------
    @classmethod
    def build(cls, settings: Settings, embedder: Embedder) -> "Retriever":
        t0 = time.time()
        docs = load_documents(settings.docs_dir, settings.url_template)
        chunks = chunk_documents(docs, settings.chunk_max_chars, settings.chunk_overlap)
        if not chunks:
            raise ValueError(f"{settings.docs_dir} 里没有切出任何 chunk，检查一下文档目录")
        embeddings = embedder.encode_docs([c.index_text() for c in chunks])
        meta = {
            "embed_model": embedder.name,
            "num_docs": len(docs),
            "num_chunks": len(chunks),
            "dim": int(embeddings.shape[1]),
            "chunk_max_chars": settings.chunk_max_chars,
            "chunk_overlap": settings.chunk_overlap,
            "built_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "build_seconds": round(time.time() - t0, 1),
        }
        save_index(settings.index_dir, chunks, embeddings, meta)
        return cls(chunks, embeddings, embedder, settings.rrf_k, settings.candidates)

    @classmethod
    def load(cls, settings: Settings, embedder: Embedder) -> "Retriever":
        chunks, embeddings, meta = load_index(settings.index_dir)
        if meta.get("embed_model") != embedder.name:
            raise ValueError(
                f"索引是用 {meta.get('embed_model')} 建的，当前模型是 {embedder.name}，"
                "两边向量不兼容，请重新运行 scripts/build_index.py"
            )
        return cls(chunks, embeddings, embedder, settings.rrf_k, settings.candidates)

    @classmethod
    def load_or_build(cls, settings: Settings, embedder: Embedder) -> "Retriever":
        try:
            return cls.load(settings, embedder)
        except FileNotFoundError:
            return cls.build(settings, embedder)

    # ---------- 检索 ----------
    def dense_search(self, query: str, n: int) -> list[tuple[int, float]]:
        return self.dense.search(self.embedder.encode_query(query), n)

    def sparse_search(self, query: str, n: int) -> list[tuple[int, float]]:
        return self.bm25.search(tokenize(query), n)

    def search(self, query: str, mode: Mode = "hybrid", k: int = 5,
               fusion: str = "rrf", alpha: float = 0.5, rrf_k: int | None = None) -> list[Hit]:
        """mode: hybrid（默认）/ dense / sparse。返回前 k 个 Hit。"""
        if mode == "dense":
            ranked = self.dense_search(query, k)
            return [Hit(self.chunks[i], s, r, {"dense_rank": r, "dense_score": s})
                    for r, (i, s) in enumerate(ranked, start=1)]
        if mode == "sparse":
            ranked = self.sparse_search(query, k)
            return [Hit(self.chunks[i], s, r, {"sparse_rank": r, "sparse_score": s})
                    for r, (i, s) in enumerate(ranked, start=1)]

        # ---- hybrid：两路各取 candidates 个候选，再融合 ----
        dense = self.dense_search(query, self.candidates)
        sparse = self.sparse_search(query, self.candidates)
        if fusion == "linear":
            fused = linear({"dense": dense, "sparse": sparse}, {"dense": alpha, "sparse": 1 - alpha})
        else:
            fused = rrf({"dense": [i for i, _ in dense], "sparse": [i for i, _ in sparse]},
                        k=rrf_k or self.rrf_k)

        d_rank = {i: (r, s) for r, (i, s) in enumerate(dense, start=1)}
        s_rank = {i: (r, s) for r, (i, s) in enumerate(sparse, start=1)}
        hits = []
        for r, (i, score) in enumerate(fused[:k], start=1):
            detail = {
                "dense_rank": d_rank.get(i, (None, None))[0],
                "dense_score": d_rank.get(i, (None, None))[1],
                "sparse_rank": s_rank.get(i, (None, None))[0],
                "sparse_score": s_rank.get(i, (None, None))[1],
            }
            hits.append(Hit(self.chunks[i], score, r, detail))
        return hits
