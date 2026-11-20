"""第 2 步（b）：逐题人工审核候选问题，产出最终评测集 eval.jsonl。

每道题会显示：问题、出题用的原文片段，以及「候选相关文档」——
它们是 dense 和 sparse 各自前 5 名的并集（pooling），并且打乱了顺序，
这样审核的人看不出哪篇来自哪一路检索，标注就不会偏向任何一种方法。

操作：
    回车 / y   保留            n        丢弃（问题不清楚、答案不在文档里……）
    e          修改问题文字     a 1 3    把候选 1、3 也标为相关文档
    t          切换题型 keyword/semantic                q   保存并退出
每一步都会自动保存，可以随时退出、下次接着审。

用法：
    python scripts/review_eval.py --in data/eval/candidates.jsonl --out data/eval/eval.jsonl --target 150
"""
import argparse
import random
import textwrap

from _common import load_retriever, read_jsonl, write_jsonl

p = argparse.ArgumentParser()
p.add_argument("--in", dest="inp", default="data/eval/candidates.jsonl")
p.add_argument("--out", default="data/eval/eval.jsonl")
p.add_argument("--target", type=int, default=150)
p.add_argument("--pool-k", type=int, default=5)
args = p.parse_args()

rows = read_jsonl(args.inp)
r = load_retriever()
chunk_by_id = {c.chunk_id: c for c in r.chunks}
rng = random.Random(0)


def where(c) -> str:
    return f"{c.title} > {c.section}" if c.section else c.title


def pooled_candidates(question: str, labeled: list[str]) -> list[tuple[str, str]]:
    seen, docs = set(labeled), []
    for mode in ("dense", "sparse"):
        for h in r.search(question, mode=mode, k=args.pool_k):
            if h.chunk.doc_id not in seen:
                seen.add(h.chunk.doc_id)
                docs.append((h.chunk.doc_id, where(h.chunk)))
    rng.shuffle(docs)
    return docs


def save() -> int:
    write_jsonl(args.inp, rows)
    ok = [x for x in rows if x["review"] == "ok"]
    write_jsonl(args.out, [
        {"qid": f"q{i:03d}", "question": x["question"], "relevant_doc_ids": x["relevant_doc_ids"],
         "type": x["type"], "source": x.get("source", "llm")}
        for i, x in enumerate(ok, start=1)
    ])
    return len(ok)


n_ok = sum(1 for x in rows if x["review"] == "ok")
for row in rows:
    if row["review"] != "todo":
        continue
    if n_ok >= args.target:
        print(f"已经有 {n_ok} 道题了，达到目标。")
        break
    src = chunk_by_id.get(row.get("source_chunk_id", ""))
    print("\n" + "=" * 70)
    print(f"[{n_ok}/{args.target}] {row['qid']}  ({row['type']})  {row['question']}")
    if src:
        print(f"出题片段《{where(src)}》\n" + textwrap.indent(textwrap.shorten(src.text, 300), "    "))
    print(f"当前相关文档：{row['relevant_doc_ids']}")
    cands = pooled_candidates(row["question"], row["relevant_doc_ids"])
    for i, (doc_id, w) in enumerate(cands, start=1):
        print(f"  候选 {i}: {doc_id}  《{w}》")

    while True:
        cmd = input("[回车保留 / n 丢弃 / e 改问题 / a 编号… 加相关 / t 换题型 / q 退出] > ").strip()
        if cmd in ("", "y"):
            row["review"] = "ok"
            n_ok = save()
            break
        if cmd == "n":
            row["review"] = "drop"
            save()
            break
        if cmd == "e":
            row["question"] = input("新的问题：").strip() or row["question"]
        elif cmd.startswith("a"):
            for tok in cmd[1:].split():
                if tok.isdigit() and 1 <= int(tok) <= len(cands):
                    row["relevant_doc_ids"].append(cands[int(tok) - 1][0])
            print(f"当前相关文档：{row['relevant_doc_ids']}")
        elif cmd == "t":
            row["type"] = "semantic" if row["type"] == "keyword" else "keyword"
            print(f"题型改为 {row['type']}")
        elif cmd == "q":
            print(f"已保存，当前 {save()} 道题 → {args.out}")
            raise SystemExit(0)

print(f"\n审核完成：{save()} 道题 → {args.out}")
