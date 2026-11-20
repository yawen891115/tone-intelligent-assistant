"""调试工具：同一个问题，并排打印 dense / sparse / hybrid 三路的排名。

用法：
    python scripts/search.py "怎么把服务器加到 T-One 上跑测试" -k 5
"""
import argparse

from _common import load_retriever

from rag.text import tokenize

parser = argparse.ArgumentParser()
parser.add_argument("query")
parser.add_argument("-k", type=int, default=5)
args = parser.parse_args()

r = load_retriever()
print(f"查询：{args.query}")
print(f"BM25 看到的词：{tokenize(args.query)}\n")


def where(c) -> str:
    return f"{c.title} > {c.section}" if c.section else c.title


print("[dense 稠密检索：余弦相似度]")
for rank, (i, s) in enumerate(r.dense_search(args.query, args.k), start=1):
    print(f"  {rank}. {s:.4f}  {r.chunks[i].chunk_id:<32} {where(r.chunks[i])}")

print("\n[sparse BM25]")
sparse = r.sparse_search(args.query, args.k)
if not sparse:
    print("  （一个词都没匹配上）")
for rank, (i, s) in enumerate(sparse, start=1):
    print(f"  {rank}. {s:7.3f}  {r.chunks[i].chunk_id:<32} {where(r.chunks[i])}")

print(f"\n[hybrid RRF，k={r.rrf_k}，各取前 {r.candidates} 个候选]")
for h in r.search(args.query, mode="hybrid", k=args.k):
    d, sp = h.detail["dense_rank"], h.detail["sparse_rank"]
    tag = f"dense#{d or '-'} sparse#{sp or '-'}"
    print(f"  {h.rank}. {h.score:.4f}  ({tag:<18}) {h.chunk.chunk_id:<32} {where(h.chunk)}")
