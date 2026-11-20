"""多轮对话：把依赖上下文的追问改写成「独立问题」再去检索。

例子：
    第 1 轮  用户：ToneAgent 怎么安装？
    第 2 轮  用户：那它的日志在哪看？        ← 直接拿去检索，"它"是谁？BM25 和向量都不知道
    改写后        ：ToneAgent 的日志在哪看？  ← 用这个去检索

有大模型时让大模型改写；没有（或调用失败）时用兜底规则：把上一个问题拼在前面。
只有「看起来缺上下文」的问题才改写，完整的问题原样返回，省一次大模型调用。
"""
from __future__ import annotations

REFERENCE_WORDS = ("它", "他们", "它们", "这个", "那个", "这些", "那些", "上面", "上述", "刚才", "前面", "该", "这里", "那里")

REWRITE_PROMPT = """你是检索助手。根据对话历史，把用户最后一个问题改写成一个独立、完整、可以直接拿去搜索文档的问题：
把"它""这个"等指代换成具体名称，补全省略的主语。只输出改写后的问题，不要解释；如果问题本来就完整，原样输出。"""


def needs_context(question: str) -> bool:
    """很短的问题或者带指代词的问题，大概率要结合上文才能看懂。"""
    q = question.strip()
    return len(q) <= 6 or any(w in q for w in REFERENCE_WORDS)


def last_user_question(history: list[dict]) -> str:
    for turn in reversed(history or []):
        if turn.get("role") == "user" and turn.get("content", "").strip():
            return turn["content"].strip()
    return ""


def standalone_query(question: str, history: list[dict] | None, llm=None) -> str:
    """返回用于检索的查询语句（不影响回答时给大模型看的原问题）。"""
    question = question.strip()
    previous = last_user_question(history or [])
    if not previous or not needs_context(question):
        return question

    if llm is not None:
        messages = [{"role": "system", "content": REWRITE_PROMPT}]
        for turn in (history or [])[-4:]:
            if turn.get("role") in ("user", "assistant") and turn.get("content"):
                messages.append({"role": turn["role"], "content": turn["content"][:500]})
        messages.append({"role": "user", "content": f"需要改写的问题：{question}"})
        try:
            rewritten = llm.chat(messages, temperature=0).strip().strip("\"'“”「」")
            if 0 < len(rewritten) <= 200:
                return rewritten
        except Exception:  # 改写失败不影响主流程，走下面的兜底
            pass

    return f"{previous} {question}"  # 兜底：把上一个问题拼上，让检索拿到被省略的主语
