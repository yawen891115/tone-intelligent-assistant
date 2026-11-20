"""Okapi BM25 稀疏检索，用倒排索引 + numpy 实现（不依赖 rank_bm25）。

对文档 d、查询 q：
    score(d, q) = Σ_{t ∈ q}  idf(t) · tf(t,d)·(k1+1) / ( tf(t,d) + k1·(1 - b + b·|d|/avgdl) )
    idf(t)      = ln( 1 + (N - n_t + 0.5) / (n_t + 0.5) )      # Lucene 的写法，永远 > 0

    tf(t,d)  词 t 在文档 d 里出现的次数      n_t   包含词 t 的文档数
    |d|      文档 d 的长度（词数）            avgdl 平均文档长度
    k1=1.5   控制 tf 饱和速度                 b=0.75 控制长度归一化力度
"""
from __future__ import annotations

import math
from collections import Counter, defaultdict

import numpy as np


class BM25:
    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1, self.b = k1, b

    def fit(self, corpus_tokens: list[list[str]]) -> "BM25":
        self.n_docs = len(corpus_tokens)
        self.doc_len = np.array([len(toks) for toks in corpus_tokens], dtype=np.float32)
        self.avgdl = float(self.doc_len.mean()) if self.n_docs else 0.0

        # 倒排索引：词 -> (出现在哪些文档, 每篇出现几次)
        postings: dict[str, list[tuple[int, int]]] = defaultdict(list)
        for doc_idx, toks in enumerate(corpus_tokens):
            for term, tf in Counter(toks).items():
                postings[term].append((doc_idx, tf))

        self.index: dict[str, tuple[np.ndarray, np.ndarray, float]] = {}
        for term, plist in postings.items():
            ids = np.array([i for i, _ in plist], dtype=np.int32)
            tfs = np.array([tf for _, tf in plist], dtype=np.float32)
            n_t = len(plist)
            idf = math.log(1 + (self.n_docs - n_t + 0.5) / (n_t + 0.5))
            self.index[term] = (ids, tfs, idf)
        return self

    def get_scores(self, query_tokens: list[str]) -> np.ndarray:
        scores = np.zeros(self.n_docs, dtype=np.float32)
        for term in set(query_tokens):  # 查询里重复的词只算一次
            if term not in self.index:
                continue
            ids, tfs, idf = self.index[term]
            norm = 1 - self.b + self.b * self.doc_len[ids] / self.avgdl
            scores[ids] += idf * tfs * (self.k1 + 1) / (tfs + self.k1 * norm)
        return scores

    def search(self, query_tokens: list[str], top_n: int) -> list[tuple[int, float]]:
        """返回 [(文档下标, 分数), ...]，只保留分数 > 0 的（一个词都没匹配上的不要）。"""
        scores = self.get_scores(query_tokens)
        top_n = min(top_n, self.n_docs)
        idx = np.argpartition(-scores, top_n - 1)[:top_n] if top_n else []
        idx = sorted(idx, key=lambda i: -scores[i])
        return [(int(i), float(scores[i])) for i in idx if scores[i] > 0]
