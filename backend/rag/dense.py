"""稠密检索 dense retrieval：文本 -> 向量，查询向量和所有 chunk 向量做内积。

向量都做了 L2 归一化，所以「内积 = 余弦相似度」。
几千到几万个 chunk 用 numpy 暴力算就够快（一次矩阵乘法）；
上百万再换 FAISS / Milvus 这类 ANN 索引。
"""
from __future__ import annotations

from typing import Protocol

import numpy as np


class Embedder(Protocol):
    """任何能把文本变成向量的东西都可以（方便测试时换成假的 embedder）。"""

    name: str

    def encode_docs(self, texts: list[str]) -> np.ndarray: ...

    def encode_query(self, text: str) -> np.ndarray: ...


class SentenceTransformerEmbedder:
    """默认实现：sentence-transformers 加载 HuggingFace 上的中文 embedding 模型。"""

    def __init__(self, model_name: str, device: str | None = None, query_prefix: str = "", batch_size: int = 32):
        from sentence_transformers import SentenceTransformer  # 延迟导入：测试时不用装 torch

        self.name = model_name
        self.model = SentenceTransformer(model_name, device=device)
        self.query_prefix = query_prefix
        self.batch_size = batch_size

    def encode_docs(self, texts: list[str]) -> np.ndarray:
        vecs = self.model.encode(
            texts,
            batch_size=self.batch_size,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=len(texts) > 200,
        )
        return vecs.astype(np.float32)

    def encode_query(self, text: str) -> np.ndarray:
        vec = self.model.encode([self.query_prefix + text], normalize_embeddings=True, convert_to_numpy=True)
        return vec[0].astype(np.float32)


class DenseIndex:
    def __init__(self, embeddings: np.ndarray):
        self.emb = np.asarray(embeddings, dtype=np.float32)  # 形状 (N, dim)

    def search(self, query_vec: np.ndarray, top_n: int) -> list[tuple[int, float]]:
        scores = self.emb @ query_vec  # (N, dim) @ (dim,) -> (N,)
        top_n = min(top_n, len(scores))
        idx = np.argpartition(-scores, top_n - 1)[:top_n]  # 先粗选 top_n（O(N)）
        idx = idx[np.argsort(-scores[idx])]  # 再对这 top_n 个排序
        return [(int(i), float(scores[i])) for i in idx]
