"""检索评测指标（文档级）。

检索返回的是 chunk，标注的是「哪篇文档能回答这个问题」，所以先把 chunk 映射回 doc_id：
    ranked = ["tone/machine-access", "tone/agent", "tone/machine-access", ...]   # 第 i 个 chunk 属于哪篇文档

Recall@k = |前 k 个 chunk 覆盖到的相关文档| / |相关文档|
    —— 问的是：塞给大模型的前 k 个片段里，有没有包含能回答问题的文档？
    每题只有 1 篇相关文档时，Recall@k 就等于 Hit@k（命中 = 1，没命中 = 0）。
MRR@k    = 1 / 第一个相关 chunk 的名次（前 k 个里没有就是 0）
"""
from __future__ import annotations

import numpy as np


def recall_at_k(ranked: list[str], relevant: set[str], k: int) -> float:
    if not relevant:
        return 0.0
    return len(relevant & set(ranked[:k])) / len(relevant)


def reciprocal_rank(ranked: list[str], relevant: set[str], k: int = 10) -> float:
    for i, doc_id in enumerate(ranked[:k], start=1):
        if doc_id in relevant:
            return 1.0 / i
    return 0.0


def paired_bootstrap(a: list[float], b: list[float], n_boot: int = 10000, seed: int = 0) -> dict:
    """配对 bootstrap：同一批问题上，系统 b 比系统 a 好多少？这个提升是不是噪声？

    做法：从 n 道题里有放回地抽 n 道，算一次 mean(b - a)；重复 n_boot 次，
    取 2.5% 和 97.5% 分位数就是 95% 置信区间。区间不跨过 0 → 提升大概率是真的。
    """
    a_arr, b_arr = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    if a_arr.shape != b_arr.shape or not len(a_arr) or n_boot < 1:
        raise ValueError("paired scores must have equal, nonzero length and n_boot must be positive")
    delta = b_arr - a_arr
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(a_arr), size=(n_boot, len(a_arr)))
    diffs = delta[idx].mean(axis=1)
    # Under the paired randomization null, either system could have received
    # either score for each question. The bootstrap above estimates the CI.
    signs = 2 * rng.integers(0, 2, size=(n_boot, len(delta)), dtype=np.int8) - 1
    effect = delta.mean()
    # Compare sums to avoid rounding bias for ties involving fractional recall.
    null_sums = (signs * delta).sum(axis=1)
    threshold = np.nextafter(delta.sum(), -np.inf)
    return {
        "diff": float(effect),
        "ci_low": float(np.percentile(diffs, 2.5)),
        "ci_high": float(np.percentile(diffs, 97.5)),
        "p_value": float((1 + np.count_nonzero(null_sums >= threshold)) / (n_boot + 1)),
    }
