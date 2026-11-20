"""生成回答：拼 prompt → 调大模型 → 解析出 answer 和 follow_ups → 整理来源。

没配大模型（或者调用失败）时不会报错，而是退化成「抽取式回答」：
直接把最相关的几个片段返回，follow-ups 用其它片段的小节标题。
这样检索和前端可以在完全离线的情况下跑通。
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from .schema import Hit

SYSTEM_PROMPT = """你是 T-One 测试平台和龙蜥（OpenAnolis）社区的智能助手，只能根据【参考资料】回答问题。
要求：
1. 用简洁的中文回答；步骤类问题用编号列表，命令放进代码块。
2. 每个关键结论后用 [编号] 标注出处，例如 [1] 或 [2][3]；只能引用参考资料里给出的编号。
3. 参考资料里没有答案时，直接回答"文档中没有找到相关说明"，不要编造。
4. 另外给出 3 个用户接下来可能会问的问题 follow_ups：每个不超过 25 个字，能被参考资料回答，不要和当前问题重复。
只输出一个 JSON 对象：{"answer": "Markdown 格式的回答", "follow_ups": ["问题1", "问题2", "问题3"]}"""

NO_RESULT = "文档中没有找到相关内容。可以换个关键词再问，或者点上方「意见反馈」告诉我们。"
_CITE = re.compile(r"\[(\d{1,2})\]")
_LIST_MARK = re.compile(r"^\s*(?:[-*•]|\d+[.、)])\s*")
_NUM_PREFIX = re.compile(r"^[\d.、\s]+")


@dataclass
class Reply:
    answer: str
    sources: list[dict]
    follow_ups: list[str]
    llm_used: bool
    warning: str | None = None
    extra: dict = field(default_factory=dict)


def where(hit: Hit) -> str:
    c = hit.chunk
    return f"{c.title} > {c.section}" if c.section else c.title


def build_messages(question: str, hits: list[Hit], history: list[dict] | None = None) -> list[dict]:
    context = "\n\n".join(f"[{i}] 《{where(h)}》\n{h.chunk.text}" for i, h in enumerate(hits, start=1))
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for turn in (history or [])[-4:]:  # 只带最近 2 轮，控制 prompt 长度
        if turn.get("role") in ("user", "assistant") and turn.get("content"):
            messages.append({"role": turn["role"], "content": turn["content"][:1000]})
    messages.append({"role": "user", "content": f"【参考资料】\n{context}\n\n【问题】{question}"})
    return messages


def parse_llm_json(raw: str) -> tuple[str, list[str]]:
    """模型有时会在 JSON 外面包 ```json ... ```，或者夹杂解释文字，这里尽量抠出 JSON。"""
    m = re.search(r"\{.*\}", raw, re.S)
    if m:
        try:
            obj = json.loads(m.group())
        except json.JSONDecodeError:
            pass
        else:
            answer = obj.get("answer")
            if not isinstance(answer, str) or not answer.strip():
                raise ValueError("Empty or invalid model answer")
            candidates = obj.get("follow_ups")
            follow_ups = [q for q in candidates if isinstance(q, str)] if isinstance(candidates, list) else []
            return answer.strip(), follow_ups
    if not raw.strip():
        raise ValueError("Empty model response")
    return raw.strip(), []  # 实在解析不了，就把整段文本当回答


def clean_follow_ups(candidates: list[str], question: str, limit: int = 3) -> list[str]:
    out: list[str] = []
    for q in candidates:
        q = _LIST_MARK.sub("", q).strip()
        if q and q != question.strip() and q not in out and len(q) <= 40:
            out.append(q)
    return out[:limit]


def follow_ups_from_hits(hits: list[Hit], question: str, limit: int = 3) -> list[str]:
    """兜底方案：把其它命中片段的小节标题当成推荐问题（点一下就能检索到那一节）。"""
    names = []
    for h in hits[1:]:
        name = h.chunk.section.split(" > ")[-1] if h.chunk.section else h.chunk.title
        names.append(_NUM_PREFIX.sub("", name).strip())
    return clean_follow_ups(names, question, limit)


def extractive_answer(hits: list[Hit], n: int = 3) -> str:
    lines = ["以下是检索到的相关文档片段："]
    for i, h in enumerate(hits[:n], start=1):
        snippet = " ".join(h.chunk.text.split())[:160]
        lines.append(f"**{where(h)}** [{i}]\n\n{snippet}…")
    return "\n\n".join(lines)


def make_sources(hits: list[Hit], cited: set[int]) -> list[dict]:
    sources = []
    for i, h in enumerate(hits, start=1):
        c = h.chunk
        sources.append({
            "index": i,  # 和回答里的 [i] 一一对应
            "chunk_id": c.chunk_id,
            "doc_id": c.doc_id,
            "title": c.title,
            "section": c.section,
            "url": c.url,
            "snippet": " ".join(c.text.split())[:120],
            "score": round(float(h.score), 4),
            "cited": i in cited,
        })
    return sources


def answer_question(question: str, hits: list[Hit], llm=None, history: list[dict] | None = None) -> Reply:
    if not hits:
        return Reply(NO_RESULT, [], [], llm_used=False)

    warning = None
    if llm is not None:
        try:
            raw = llm.chat(build_messages(question, hits, history), json_mode=True)
            answer, follow_ups = parse_llm_json(raw)
            cited = {int(n) for n in _CITE.findall(answer) if 1 <= int(n) <= len(hits)}
            return Reply(
                answer=answer,
                sources=make_sources(hits, cited),
                follow_ups=clean_follow_ups(follow_ups, question) or follow_ups_from_hits(hits, question),
                llm_used=True,
            )
        except Exception as e:  # 网络超时、额度用完……都不应该让整个接口挂掉
            warning = f"大模型调用失败（{type(e).__name__}），先返回检索到的文档片段"

    shown = min(3, len(hits))
    return Reply(
        answer=extractive_answer(hits, shown),
        sources=make_sources(hits, set(range(1, shown + 1))),
        follow_ups=follow_ups_from_hits(hits, question),
        llm_used=False,
        warning=warning,
    )
