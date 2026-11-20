"""读取一个目录下的 Markdown 文档。

支持文件开头可选的 front matter（只解析简单的 key: value）：

    ---
    title: 测试机器接入说明
    url: https://tone.openanolis.cn/help_doc/14
    ---
    正文……
"""
from __future__ import annotations

import re
from pathlib import Path

from .schema import Document

DOC_SUFFIXES = {".md", ".markdown", ".txt"}
_FRONT_MATTER = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.S)
_H1 = re.compile(r"^#\s+(.+)$", re.M)


def parse_front_matter(raw: str) -> tuple[dict[str, str], str]:
    """返回 (元数据字典, 去掉 front matter 之后的正文)。"""
    m = _FRONT_MATTER.match(raw)
    if not m:
        return {}, raw
    meta = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            meta[key.strip()] = value.strip().strip("'\"")
    return meta, raw[m.end():]


def load_documents(docs_dir: str | Path, url_template: str = "") -> list[Document]:
    docs_dir = Path(docs_dir)
    if not docs_dir.exists():
        raise FileNotFoundError(f"文档目录不存在: {docs_dir}")

    documents = []
    for path in sorted(docs_dir.rglob("*")):
        if path.suffix.lower() not in DOC_SUFFIXES or not path.is_file() or path.name.startswith("_"):
            continue  # 以 _ 开头的文件（比如 _README.txt）当作说明文件，不进索引
        rel = path.relative_to(docs_dir).as_posix()  # 例如 "tone/machine-access.md"
        meta, body = parse_front_matter(path.read_text(encoding="utf-8"))
        h1 = _H1.search(body)
        title = meta.get("title") or (h1.group(1).strip() if h1 else path.stem)
        url = meta.get("url") or (url_template.format(path=rel) if url_template else "")
        documents.append(Document(doc_id=rel.rsplit(".", 1)[0], title=title, url=url, text=body))
    return documents
