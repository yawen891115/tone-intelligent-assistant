import pytest

from rag.chunker import chunk_document, split_long, split_sections
from rag.schema import Document

DOC = """# ToneAgent 安装

## 1. 安装
下载 rpm 包后安装：

```bash
# 这一行是 shell 注释，不是标题
rpm -ivh toneagent.rpm
```

## 2. 配置
### 2.1 填写 TSN
把平台生成的 TSN 写进配置文件。
"""


def test_heading_path_and_code_fence():
    sections = split_sections(DOC)
    paths = [p for p, _ in sections]
    assert paths == ["ToneAgent 安装 > 1. 安装", "ToneAgent 安装 > 2. 配置 > 2.1 填写 TSN"]
    assert "# 这一行是 shell 注释" in sections[0][1]  # 代码块里的 # 没被当成标题


def test_chunk_document_strips_doc_title():
    doc = Document(doc_id="tone/agent", title="ToneAgent 安装", url="u", text=DOC)
    chunks = chunk_document(doc)
    assert [c.section for c in chunks] == ["1. 安装", "2. 配置 > 2.1 填写 TSN"]
    assert chunks[0].chunk_id == "tone/agent#0"
    assert chunks[1].index_text().startswith("ToneAgent 安装 > 2. 配置 > 2.1 填写 TSN\n")


def test_long_section_is_split_with_overlap():
    paras = [("第%d段。" % i) + "测试内容很长。" * 25 for i in range(3)]  # 每段约 180 字
    pieces = split_long("\n\n".join(paras), max_chars=400, overlap=80)
    assert len(pieces) >= 2
    assert all(len(p) <= 400 for p in pieces)
    # 重叠：第二块的开头来自第一块的结尾
    assert pieces[1][:20] in pieces[0]


def test_long_sentence_keeps_original_order_and_chunk_limit():
    text = "前言。" + "x" * 21 + "。结尾"
    pieces = split_long(text, max_chars=10, overlap=0)
    assert "".join(pieces).replace("\n", "") == text
    assert all(len(p) <= 10 for p in split_long(text, max_chars=10, overlap=3))


def test_overlap_must_leave_space_for_new_text():
    with pytest.raises(ValueError):
        split_long("文档内容", max_chars=2, overlap=2)
