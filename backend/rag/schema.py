"""三种核心数据结构：Document（一篇文档）→ Chunk（一个片段）→ Hit（一次检索命中）。"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass
class Document:
    doc_id: str  # 相对路径去掉扩展名，例如 "tone/machine-access"，评测标注就用它
    title: str
    url: str  # 前端「来源链接」跳转的地址
    text: str  # Markdown 正文


@dataclass
class Chunk:
    chunk_id: str  # f"{doc_id}#{序号}"
    doc_id: str
    title: str  # 文档标题
    section: str  # 标题路径，例如 "2. 添加机器 > 2.3 机器池"
    url: str
    text: str  # 片段正文

    def index_text(self) -> str:
        """真正拿去建索引的文本：把「标题 + 小节路径」拼在正文前面。

        很多片段正文里不会再重复它属于哪个功能（比如只写"点击提交"），
        加上标题路径后，BM25 和 embedding 都能知道它在讲什么。
        """
        head = self.title if not self.section else f"{self.title} > {self.section}"
        return f"{head}\n{self.text}"

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Hit:
    chunk: Chunk
    score: float
    rank: int  # 从 1 开始
    detail: dict = field(default_factory=dict)  # 例如 {"dense_rank": 3, "sparse_rank": 1}
