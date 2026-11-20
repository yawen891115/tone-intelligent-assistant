from fastapi.testclient import TestClient

from conftest import DEMO_DOCS
from rag.api import create_app
from rag.config import Settings
from rag.conversation import needs_context, standalone_query

HISTORY = [
    {"role": "user", "content": "ToneAgent 怎么安装？"},
    {"role": "assistant", "content": "下载 rpm 包后用 rpm -ivh 安装 [1]"},
]


class RewriteLLM:
    def __init__(self, reply="ToneAgent 的日志在哪看？", fail=False):
        self.reply, self.fail, self.calls = reply, fail, 0

    def chat(self, messages, **kw):
        self.calls += 1
        if self.fail:
            raise TimeoutError("timeout")
        return self.reply


def test_needs_context():
    assert needs_context("那它的日志在哪看？")  # 有指代词
    assert needs_context("怎么卸载")  # 太短
    assert not needs_context("ToneAgent 的日志用什么命令查看")


def test_complete_question_is_not_rewritten():
    llm = RewriteLLM()
    assert standalone_query("ToneAgent 的日志用什么命令查看", HISTORY, llm) == "ToneAgent 的日志用什么命令查看"
    assert llm.calls == 0  # 完整的问题不浪费一次大模型调用


def test_rewrite_with_llm():
    assert standalone_query("那它的日志在哪看？", HISTORY, RewriteLLM()) == "ToneAgent 的日志在哪看？"


def test_rewrite_fallback_without_llm_or_on_error():
    expected = "ToneAgent 怎么安装？ 那它的日志在哪看？"
    assert standalone_query("那它的日志在哪看？", HISTORY, None) == expected
    assert standalone_query("那它的日志在哪看？", HISTORY, RewriteLLM(fail=True)) == expected


def test_first_turn_never_rewritten():
    assert standalone_query("它怎么用？", [], RewriteLLM()) == "它怎么用？"


def test_chat_endpoint_returns_rewritten_query(demo_retriever):
    app = create_app(settings=Settings(docs_dir=DEMO_DOCS), retriever=demo_retriever)
    with TestClient(app) as client:
        body = client.post("/api/assistant/chat", json={"question": "那它的日志在哪看？", "history": HISTORY}).json()
        assert body["data"]["query"] == "ToneAgent 怎么安装？ 那它的日志在哪看？"
        assert any(s["doc_id"] == "tone/toneagent" for s in body["data"]["sources"])
