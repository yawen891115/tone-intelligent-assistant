import math

import pytest

from rag.bm25 import BM25
from rag.fusion import linear, rrf
from rag.metrics import paired_bootstrap, recall_at_k, reciprocal_rank
from rag.text import tokenize


# ---------------- 分词 ----------------
def test_tokenize_keeps_identifiers_and_drops_stopwords():
    toks = tokenize("如何用 tone-cli 查看 /etc/yum.repos.d 的配置？")
    assert "tone-cli" in toks and "tone" in toks and "cli" in toks
    assert "etc/yum.repos.d" in toks and "yum" in toks
    assert "如何" not in toks and "的" not in toks


# ---------------- BM25 ----------------
def test_bm25_exact_term_wins():
    corpus = ["tone-cli archive 打包测试结果", "安装 ToneAgent 服务", "配置 yum 软件源"]
    bm25 = BM25().fit([tokenize(t) for t in corpus])
    top = bm25.search(tokenize("tone archive 怎么用"), top_n=3)
    assert top[0][0] == 0
    assert bm25.search(tokenize("完全无关的词汇"), top_n=3) == []  # 一个词都没命中就不返回


def test_bm25_idf_is_positive_even_for_common_terms():
    bm25 = BM25().fit([["测试"], ["测试"], ["测试", "机器"]])
    assert bm25.index["测试"][2] > 0  # 出现在所有文档里的词，idf 仍然 > 0（Lucene 写法）
    assert bm25.index["机器"][2] > bm25.index["测试"][2]  # 越稀有的词 idf 越大


# ---------------- RRF（和教程里手算的例子一致）----------------
def test_rrf_hand_computed_example():
    fused = rrf({"dense": ["A", "B", "C"], "sparse": ["C", "A", "D"]}, k=60)
    assert [d for d, _ in fused] == ["A", "C", "B", "D"]
    scores = dict(fused)
    assert scores["A"] == pytest.approx(1 / 61 + 1 / 62)
    assert scores["C"] == pytest.approx(1 / 63 + 1 / 61)
    assert scores["D"] == pytest.approx(1 / 63)


def test_linear_fusion_min_max():
    fused = dict(linear({"dense": [("A", 0.9), ("B", 0.5)], "sparse": [("B", 20.0), ("C", 10.0)]},
                        {"dense": 0.5, "sparse": 0.5}))
    assert fused["A"] == pytest.approx(0.5)  # dense 归一化后 1.0 × 0.5
    assert fused["B"] == pytest.approx(0.5)  # dense 0 + sparse 1.0 × 0.5
    assert fused["C"] == pytest.approx(0.0)


# ---------------- 评测指标 ----------------
def test_recall_and_mrr():
    ranked = ["a", "b", "a", "c"]  # 第 i 个 chunk 来自哪篇文档
    assert recall_at_k(ranked, {"c"}, 3) == 0.0
    assert recall_at_k(ranked, {"c"}, 4) == 1.0
    assert recall_at_k(ranked, {"a", "c"}, 3) == 0.5
    assert reciprocal_rank(ranked, {"b"}) == 0.5
    assert reciprocal_rank(ranked, {"z"}) == 0.0


def test_paired_bootstrap():
    same = paired_bootstrap([1, 0, 1, 0], [1, 0, 1, 0])
    assert same["diff"] == 0 and same["ci_low"] == 0 and same["ci_high"] == 0
    better = paired_bootstrap([0] * 50, [1] * 25 + [0] * 25)
    assert math.isclose(better["diff"], 0.5) and better["ci_low"] > 0 and better["p_value"] < 0.01
    # Both informative pairs must favor system B under random score swaps.
    assert paired_bootstrap([0, 0, 0], [0, 1, 1])["p_value"] == pytest.approx(0.25, abs=0.02)
