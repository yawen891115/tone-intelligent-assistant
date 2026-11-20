"""第 1 步：读取文档 → 切分 → 计算向量 → 保存索引。

用法（在 backend/ 目录下）：
    python scripts/build_index.py                         # 用 .env 里的 DOCS_DIR / INDEX_DIR
    python scripts/build_index.py --docs data/tone_docs   # 指定文档目录
"""
import argparse
import statistics
from pathlib import Path

from _common import Retriever, Settings, make_embedder

parser = argparse.ArgumentParser(description="切分文档并建立检索索引")
parser.add_argument("--docs", help="文档目录，默认读 .env 里的 DOCS_DIR")
parser.add_argument("--index", help="索引输出目录，默认读 .env 里的 INDEX_DIR")
args = parser.parse_args()

s = Settings()
if args.docs:
    s.docs_dir = Path(args.docs).resolve()
if args.index:
    s.index_dir = Path(args.index).resolve()

print(f"文档目录 : {s.docs_dir}\n索引目录 : {s.index_dir}\nEmbedding: {s.embed_model}")
retriever = Retriever.build(s, make_embedder(s))

lengths = [len(c.text) for c in retriever.chunks]
n_docs = len({c.doc_id for c in retriever.chunks})
print(f"完成：{n_docs} 篇文档 → {len(lengths)} 个 chunk，向量维度 {retriever.dense.emb.shape[1]}")
print(f"chunk 长度（字符）：最短 {min(lengths)} / 中位数 {int(statistics.median(lengths))} / 最长 {max(lengths)}")
