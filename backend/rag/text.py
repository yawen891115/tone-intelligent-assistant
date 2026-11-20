"""给 BM25 用的分词器：中文用 jieba，英文/命令/路径用正则整体保留。

为什么要单独处理英文？技术文档里有大量 "tone-cli"、"/etc/yum.repos.d"、"E1002"
这类 token，jieba 会把它们拆碎（tone / - / cli），BM25 就失去了精确匹配的优势。
所以先用正则把它们整体抠出来，同时再加上拆开后的子词，两种写法都能匹配上。
"""
from __future__ import annotations

import logging
import re
import warnings
from functools import lru_cache
from pathlib import Path

warnings.filterwarnings("ignore", category=SyntaxWarning)  # jieba 老代码在 Python 3.12+ 上的无害警告
import jieba  # noqa: E402

jieba.setLogLevel(logging.WARNING)

_TECH = re.compile(r"[a-z0-9][a-z0-9_.\-/:]*")  # 已经 lower() 过，所以只写小写
_SUBWORD = re.compile(r"[_.\-/:]+")
_PUNCT = re.compile(r"[\s\W_]+")

STOPWORDS = set(
    "的 了 是 在 和 与 或 及 就 都 也 还 而 并 但 被 把 让 给 对 从 到 向 于 为 以 "
    "我 你 他 她 它 我们 你们 这 那 这个 那个 这些 那些 哪 哪个 哪些 "
    "吗 呢 吧 啊 呀 么 嘛 "
    "一 一个 一下 有 没有 会 能 能够 可以 可 要 需要 应该 请 请问 用 "
    "如何 怎么 怎样 怎么样 什么 为什么 为何 是否 多少 几 时候 "
    "a an the is are to of in on for and or how what why do does can i".split()
)

_USER_DICT = Path(__file__).resolve().parents[1] / "data" / "userdict.txt"


@lru_cache(maxsize=1)
def _init_jieba() -> None:
    """加载领域词典（"弹性机器池"、"测试套件" 这种词，jieba 默认会切开）。"""
    if _USER_DICT.exists():
        jieba.load_userdict(str(_USER_DICT))


def tokenize(text: str) -> list[str]:
    _init_jieba()
    text = text.lower()
    tokens: list[str] = []

    # 1) 英文 / 数字 / 命令 / 路径：整体保留 + 拆开的子词
    for m in _TECH.finditer(text):
        tok = m.group().strip("._-/:")
        if not tok:
            continue
        tokens.append(tok)
        parts = [p for p in _SUBWORD.split(tok) if p]
        if len(parts) > 1:
            tokens.extend(parts)

    # 2) 剩下的中文交给 jieba（搜索引擎模式会额外切出短词，召回更高）
    for w in jieba.lcut_for_search(_TECH.sub(" ", text)):
        w = w.strip()
        if w and w not in STOPWORDS and not _PUNCT.fullmatch(w):
            tokens.append(w)

    return [t for t in tokens if t not in STOPWORDS]
