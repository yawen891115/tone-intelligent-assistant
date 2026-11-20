"""把多路检索结果融合成一个排序。

RRF（Reciprocal Rank Fusion，倒数排名融合）：
    score(d) = Σ_r  w_r / (k + rank_r(d))
只看名次、不看原始分数，所以 BM25 分数（0~30）和余弦相似度（0~1）量纲不同也没关系。
k 一般取 60：k 越大，第 1 名和第 10 名之间的差距越小。

linear：先把每一路分数 min-max 归一化到 [0,1]，再按权重加起来。作为对照实验。
"""
from __future__ import annotations

from collections import defaultdict


def rrf(rankings: dict[str, list[str]], k: int = 60, weights: dict[str, float] | None = None) -> list[tuple[str, float]]:
    """rankings: {"dense": [id1, id2, ...], "sparse": [...]}，每个列表已按名次排好。"""
    scores: dict[str, float] = defaultdict(float)
    for name, ids in rankings.items():
        w = (weights or {}).get(name, 1.0)
        for rank, doc_id in enumerate(ids, start=1):
            scores[doc_id] += w / (k + rank)
    return sorted(scores.items(), key=lambda kv: kv[1], reverse=True)


def linear(score_lists: dict[str, list[tuple[str, float]]], weights: dict[str, float]) -> list[tuple[str, float]]:
    """score_lists: {"dense": [(id, 原始分), ...], ...}；没出现在某一路里的记 0 分。"""
    fused: dict[str, float] = defaultdict(float)
    for name, items in score_lists.items():
        if not items:
            continue
        vals = [s for _, s in items]
        lo, hi = min(vals), max(vals)
        for doc_id, s in items:
            norm = (s - lo) / (hi - lo) if hi > lo else 1.0
            fused[doc_id] += weights.get(name, 1.0) * norm
    return sorted(fused.items(), key=lambda kv: kv[1], reverse=True)
