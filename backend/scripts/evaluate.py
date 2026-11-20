"""第 3 步：用标注好的问题集评测检索效果（dense-only vs sparse-only vs hybrid）。

标注文件是 JSONL，每行一道题：
    {"qid": "q001", "question": "怎么把自己的服务器接入 T-One？",
     "relevant_doc_ids": ["tone/machine-access"], "type": "semantic"}

用法：
    python scripts/evaluate.py --eval data/eval/demo_eval.jsonl
    python scripts/evaluate.py --eval data/eval/eval.jsonl --sweep      # 再加一组 RRF k / 线性权重的对比
输出：终端打印表格；--out 目录下保存 summary.json 和 per_question.csv（逐题对比，做 error analysis 用）
"""
import argparse
import csv
import json
from collections import defaultdict
from functools import lru_cache
from pathlib import Path

from _common import load_retriever, read_jsonl

from rag.metrics import paired_bootstrap, recall_at_k, reciprocal_rank

parser = argparse.ArgumentParser()
parser.add_argument("--eval", required=True, help="标注好的问题集 JSONL")
parser.add_argument("--modes", nargs="+", choices=("dense", "sparse", "hybrid"), default=["dense", "sparse", "hybrid"])
parser.add_argument("--ks", nargs="+", type=int, default=[1, 3, 5, 10])
parser.add_argument("--main-k", type=int, default=5, help="主指标用 Recall@几")
parser.add_argument("--out", default="results")
parser.add_argument("--sweep", action="store_true", help="额外对比不同的 RRF k 和线性融合权重")
args = parser.parse_args()
if min(*args.ks, args.main_k) < 1:
    parser.error("Recall cutoffs must be positive")
ks = sorted(set([*args.ks, args.main_k]))

retriever = load_retriever()
# 同一个问题在不同模式下会重复算 query 向量，缓存一下
retriever.embedder.encode_query = lru_cache(maxsize=None)(retriever.embedder.encode_query)

# ---------- 读题 + 检查标注 ----------
known_docs = {c.doc_id for c in retriever.chunks}
questions, bad = [], []
seen_qids = set()
for q in read_jsonl(args.eval):
    if not isinstance(q.get("qid"), str) or not q["qid"].strip() or q["qid"] in seen_qids:
        parser.error(f"missing or duplicate question ID: {q.get('qid')!r}")
    seen_qids.add(q["qid"])
    if not isinstance(q.get("question"), str) or not q["question"].strip():
        parser.error(f"{q['qid']}: question must be a non-empty string")
    labels = q.get("relevant_doc_ids")
    if not isinstance(labels, list) or not labels or not all(isinstance(doc, str) and doc for doc in labels):
        parser.error(f"{q['qid']}: relevant_doc_ids must contain at least one document ID")
    rel = set(labels)
    (questions if rel <= known_docs else bad).append(q)
for q in bad:
    print(f"⚠️  {q['qid']} 标注的文档不在索引里：{set(q['relevant_doc_ids']) - known_docs}（跳过这题，检查标注）")
if not questions:
    parser.error("no labeled questions match the indexed corpus")
print(f"评测集：{args.eval}，有效题目 {len(questions)} 道，语料 {len(known_docs)} 篇文档 / {len(retriever.chunks)} 个 chunk\n")

max_k = max(10, max(ks))


def run(mode: str, **kw) -> list[dict]:
    """对每道题检索一次，记录各项指标。"""
    rows = []
    for q in questions:
        hits = retriever.search(q["question"], mode=mode, k=max_k, **kw)
        ranked = [h.chunk.doc_id for h in hits]
        rel = set(q["relevant_doc_ids"])
        row = {f"R@{k}": recall_at_k(ranked, rel, k) for k in ks}
        row["MRR@10"] = reciprocal_rank(ranked, rel, 10)
        row["first_hit"] = next((i for i, d in enumerate(ranked, 1) if d in rel), None)
        rows.append(row)
    return rows


def mean(xs) -> float:
    return sum(xs) / len(xs) if xs else 0.0


results = {mode: run(mode) for mode in args.modes}
metric_names = [f"R@{k}" for k in ks] + ["MRR@10"]

# ---------- 总表 ----------
print("| mode   | " + " | ".join(f"{m:>6}" for m in metric_names) + " |")
print("|--------|" + "|".join("-" * 8 for _ in metric_names) + "|")
summary = {"eval_file": args.eval, "n_questions": len(questions), "n_skipped": len(bad),
           "embed_model": retriever.embedder.name, "num_chunks": len(retriever.chunks),
           "main_k": args.main_k, "overall": {}, "by_type": {}}
for mode, rows in results.items():
    vals = {m: mean([r[m] for r in rows]) for m in metric_names}
    summary["overall"][mode] = vals
    print(f"| {mode:<6} | " + " | ".join(f"{vals[m]:6.3f}" for m in metric_names) + " |")

# ---------- 按问题类型拆开看 ----------
main = f"R@{args.main_k}"
by_type = defaultdict(list)
for i, q in enumerate(questions):
    by_type[q.get("type", "unknown")].append(i)
print(f"\n按问题类型（{main}）：")
print("| type     |   n | " + " | ".join(f"{m:>6}" for m in args.modes) + " |")
for t, idxs in sorted(by_type.items()):
    vals = {m: mean([results[m][i][main] for i in idxs]) for m in args.modes}
    summary["by_type"][t] = {"n": len(idxs), **vals}
    print(f"| {t:<8} | {len(idxs):>3} | " + " | ".join(f"{vals[m]:6.3f}" for m in args.modes) + " |")

# ---------- hybrid 比 dense 好，是不是噪声？ ----------
if "dense" in results and "hybrid" in results:
    a = [r[main] for r in results["dense"]]
    b = [r[main] for r in results["hybrid"]]
    bs = paired_bootstrap(a, b)
    wins = sum(1 for x, y in zip(a, b) if y > x)
    losses = sum(1 for x, y in zip(a, b) if y < x)
    summary["hybrid_vs_dense"] = {**bs, "wins": wins, "losses": losses}
    print(f"\nhybrid vs dense（{main}，配对 bootstrap 10000 次）：")
    print(f"  提升 {bs['diff']:+.3f}，95% 置信区间 [{bs['ci_low']:+.3f}, {bs['ci_high']:+.3f}]，配对随机化检验单侧 p≈{bs['p_value']:.4f}")
    print(f"  hybrid 召回率更高：{wins} 题；dense 召回率更高：{losses} 题")

# ---------- 可选：融合方式 / 参数对比 ----------
if args.sweep:
    print(f"\n融合参数对比（{main}）：")
    sweep = {}
    for k in (10, 30, 60, 100):
        sweep[f"rrf k={k}"] = mean([r[main] for r in run("hybrid", rrf_k=k)])
    for alpha in (0.3, 0.5, 0.7):
        sweep[f"linear α={alpha}"] = mean([r[main] for r in run("hybrid", fusion="linear", alpha=alpha)])
    for name, v in sweep.items():
        print(f"  {name:<14} {v:.3f}")
    summary["sweep"] = sweep

# ---------- 保存 ----------
out = Path(args.out)
out.mkdir(parents=True, exist_ok=True)
(out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
with open(out / "per_question.csv", "w", newline="", encoding="utf-8-sig") as f:  # utf-8-sig：Excel 打开不乱码
    w = csv.writer(f)
    w.writerow(["qid", "type", "question", "relevant"] + [f"{m}_{main}" for m in args.modes]
               + [f"{m}_first_hit" for m in args.modes])
    for i, q in enumerate(questions):
        w.writerow([q["qid"], q.get("type", ""), q["question"], ";".join(q["relevant_doc_ids"])]
                   + [results[m][i][main] for m in args.modes] + [results[m][i]["first_hit"] for m in args.modes])
print(f"\n已保存：{out / 'summary.json'}、{out / 'per_question.csv'}")
