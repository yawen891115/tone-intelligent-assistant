"""按 Markdown 标题切分文档（heading-aware chunking）。

规则：
1. 先按标题把文档切成若干「小节」，记录标题路径，例如 "2. 添加机器 > 2.3 机器池"。
   代码块（``` 包起来的部分）里的 "# xxx" 是 shell 注释，不能当成标题。
2. 小节不超过 max_chars 就整体作为一个 chunk；
   超过的话按段落贪心装箱，相邻 chunk 之间保留 overlap 个字符的重叠。
"""
from __future__ import annotations

import re

from .schema import Chunk, Document

_HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
_FENCE = re.compile(r"^\s*(```|~~~)")
_SENTENCE_END = re.compile(r"(?<=[。！？；!?;\n])")
MIN_CHARS = 10  # 少于 10 个字的小节（比如只有"见下图"）直接丢掉


def split_sections(text: str) -> list[tuple[str, str]]:
    """把 Markdown 切成 [(标题路径, 正文), ...]。"""
    sections: list[tuple[str, str]] = []
    stack: list[tuple[int, str]] = []  # 当前所在的标题栈 [(级别, 标题), ...]
    body: list[str] = []
    in_code = False

    def flush() -> None:
        content = "\n".join(body).strip()
        if content:
            sections.append((" > ".join(h for _, h in stack), content))
        body.clear()

    for line in text.splitlines():
        if _FENCE.match(line):
            in_code = not in_code
        m = None if in_code else _HEADING.match(line)
        if m:  # 遇到新标题：先把上一个小节存起来，再更新标题栈
            flush()
            level = len(m.group(1))
            while stack and stack[-1][0] >= level:
                stack.pop()
            stack.append((level, m.group(2)))
        else:
            body.append(line)
    flush()
    return sections


def _paragraphs(text: str) -> list[str]:
    """按空行切段落，但代码块整体算一段，不在中间切开。"""
    paras, buf, in_code = [], [], False
    for line in text.splitlines():
        if _FENCE.match(line):
            in_code = not in_code
        if not line.strip() and not in_code:
            if buf:
                paras.append("\n".join(buf))
                buf = []
        else:
            buf.append(line)
    if buf:
        paras.append("\n".join(buf))
    return paras


def _hard_split(text: str, limit: int) -> list[str]:
    """单个段落仍然太长时，先按句子切，句子还太长就按字数切。"""
    if len(text) <= limit:
        return [text]
    pieces, cur = [], ""
    for sent in _SENTENCE_END.split(text):
        if cur and len(cur) + len(sent) > limit:
            pieces.append(cur)
            cur = ""
        while len(sent) > limit:  # 一句话比 limit 还长：直接按字数截断
            pieces.append(sent[:limit])
            sent = sent[limit:]
        cur += sent
    if cur.strip():
        pieces.append(cur)
    return [p.strip() for p in pieces if p.strip()]


def _tail(text: str, n: int) -> str:
    """取末尾 n 个字作为重叠部分，尽量从一句话的开头开始。"""
    tail = text[-n:]
    m = re.search(r"[。！？；!?;\n]", tail[: n // 2])
    return tail[m.end():].strip() if m else tail.strip()


def split_long(text: str, max_chars: int, overlap: int) -> list[str]:
    if not 0 <= overlap < max_chars:
        raise ValueError("chunk overlap must be non-negative and smaller than max_chars")
    if len(text) <= max_chars:
        return [text]
    pieces, cur = [], ""
    for para in _paragraphs(text):
        for part in _hard_split(para, max_chars - overlap):
            if cur and len(cur) + 2 + len(part) > max_chars:
                pieces.append(cur)
                room = min(overlap, max_chars - len(part) - 2)
                cur = _tail(cur, room) if room > 0 else ""
            cur = f"{cur}\n\n{part}" if cur else part
    if cur:
        pieces.append(cur)
    return pieces


def chunk_document(doc: Document, max_chars: int = 400, overlap: int = 80) -> list[Chunk]:
    chunks: list[Chunk] = []
    for path, body in split_sections(doc.text):
        # 一级标题通常就是文档标题，Chunk.title 里已经有了，这里去掉避免重复
        if path == doc.title:
            path = ""
        elif path.startswith(doc.title + " > "):
            path = path[len(doc.title) + 3:]
        if len(body.strip()) < MIN_CHARS:
            continue
        for piece in split_long(body, max_chars, overlap):
            chunks.append(
                Chunk(
                    chunk_id=f"{doc.doc_id}#{len(chunks)}",
                    doc_id=doc.doc_id,
                    title=doc.title,
                    section=path,
                    url=doc.url,
                    text=piece,
                )
            )
    return chunks


def chunk_documents(docs: list[Document], max_chars: int = 400, overlap: int = 80) -> list[Chunk]:
    return [c for d in docs for c in chunk_document(d, max_chars, overlap)]
