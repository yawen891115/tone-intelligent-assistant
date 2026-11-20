"""第 2 步（a）：让大模型从文档片段里「出题」，生成候选问题，之后再人工审核。

每个片段出 2 道题：
    keyword  —— 用户知道术语，问题里会出现片段中的命令 / 配置名 / 专有名词
    semantic —— 用户不知道术语，用自己的话描述现象（故意不照抄原文）
这样评测集不会只偏向某一种检索方式（只出 keyword 题，BM25 会显得特别强）。

用法（需要先在 .env 里配置 LLM_*）：
    python scripts/gen_eval_candidates.py --n-chunks 120 --out data/eval/candidates.jsonl
"""
import argparse
import json
import random
from collections import defaultdict

from _common import Settings, write_jsonl

from rag.llm import LLMClient
from rag.retriever import load_index

PROMPT = """下面是 T-One 测试平台 / 龙蜥社区文档里的一个片段。请站在真实用户的角度，提出 2 个能用这个片段回答的问题：
1. keyword 类：用户知道具体名称，问题里带上片段中的关键术语、命令或配置名；
2. semantic 类：用户不知道专业术语，用自己的话描述遇到的情况或想做的事，尽量不要照抄片段里的词。
每个问题 8~40 个字，不要出现"本文""这个片段"之类的字眼。
只输出 JSON：{{"questions": [{{"type": "keyword", "question": "..."}}, {{"type": "semantic", "question": "..."}}]}}

【文档】《{where}》
{text}"""


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--n-chunks", type=int, default=120, help="抽多少个片段来出题（每个出 2 题）")
    p.add_argument("--min-chars", type=int, default=80, help="太短的片段不适合出题")
    p.add_argument("--out", default="data/eval/candidates.jsonl")
    p.add_argument("--seed", type=int, default=42)
    args = p.parse_args()

    s = Settings()
    if not s.llm_enabled:
        raise SystemExit("请先在 backend/.env 里配置 LLM_BASE_URL / LLM_API_KEY / LLM_MODEL")
    llm = LLMClient(s.llm_base_url, s.llm_api_key, s.llm_model)
    chunks, _, _ = load_index(s.index_dir)

    # 分层抽样：按文档轮流抽，保证每篇文档都有题，而不是全挤在最长的几篇里
    rng = random.Random(args.seed)
    by_doc = defaultdict(list)
    for c in chunks:
        if len(c.text) >= args.min_chars:
            by_doc[c.doc_id].append(c)
    for lst in by_doc.values():
        rng.shuffle(lst)
    picked = []
    while len(picked) < args.n_chunks and any(by_doc.values()):
        for doc_id in sorted(by_doc):
            if by_doc[doc_id] and len(picked) < args.n_chunks:
                picked.append(by_doc[doc_id].pop())

    rows = []
    for n, c in enumerate(picked, start=1):
        where = f"{c.title} > {c.section}" if c.section else c.title
        raw = llm.chat([{"role": "user", "content": PROMPT.format(where=where, text=c.text)}],
                       temperature=0.7, json_mode=True)
        try:
            items = json.loads(raw[raw.find("{"): raw.rfind("}") + 1])["questions"]
        except (ValueError, KeyError, TypeError):
            print(f"  ✗ 解析失败，跳过 {c.chunk_id}")
            continue
        for item in items:
            rows.append({
                "qid": f"c{len(rows) + 1:04d}",
                "question": str(item.get("question", "")).strip(),
                "type": item.get("type", "unknown"),
                "relevant_doc_ids": [c.doc_id],  # 先默认「出题的那篇文档」是答案，审核时再补充
                "source_chunk_id": c.chunk_id,
                "review": "todo",
            })
        print(f"[{n}/{len(picked)}] {c.chunk_id}")

    write_jsonl(args.out, rows)
    print(f"\n生成 {len(rows)} 道候选题 → {args.out}")
    print("下一步：python scripts/review_eval.py 逐题审核，留下 150 道左右写进 data/eval/eval.jsonl")


if __name__ == "__main__":
    main()
