from fastapi.testclient import TestClient

from conftest import DEMO_DOCS
from rag.answer import NO_RESULT, answer_question, clean_follow_ups, parse_llm_json
from rag.api import create_app
from rag.config import Settings


class FakeLLM:
    def __init__(self, reply: str | Exception):
        self.reply = reply

    def chat(self, messages, **kw):
        if isinstance(self.reply, Exception):
            raise self.reply
        return self.reply


# ---------------- 解析大模型输出 ----------------
def test_parse_llm_json_with_code_fence():
    raw = '好的：\n```json\n{"answer": "执行 tone list [1]", "follow_ups": ["1. tone run 怎么用？"]}\n```'
    answer, fus = parse_llm_json(raw)
    assert answer == "执行 tone list [1]"
    assert clean_follow_ups(fus, "q") == ["tone run 怎么用？"]


def test_parse_llm_json_falls_back_to_raw_text():
    assert parse_llm_json("不是 JSON") == ("不是 JSON", [])


def test_clean_follow_ups_dedup_and_drop_same_question():
    assert clean_follow_ups(["A？", "A？", "当前问题", "- B？", "C？", "D？"], "当前问题") == ["A？", "B？", "C？"]


# ---------------- 生成回答 ----------------
def test_answer_with_llm_marks_cited_sources(demo_retriever):
    hits = demo_retriever.search("tone-cli 有哪些命令", k=5)
    llm = FakeLLM('{"answer": "用 tone list 查看 [2]，用 tone run 运行 [9]", "follow_ups": ["tone archive 是什么？"]}')
    reply = answer_question("tone-cli 有哪些命令", hits, llm)
    assert reply.llm_used and reply.follow_ups == ["tone archive 是什么？"]
    assert [s["cited"] for s in reply.sources] == [False, True, False, False, False]  # [9] 越界，不算


def test_answer_falls_back_when_llm_fails(demo_retriever):
    hits = demo_retriever.search("tone-cli 有哪些命令", k=5)
    reply = answer_question("tone-cli 有哪些命令", hits, FakeLLM(TimeoutError("timeout")))
    assert not reply.llm_used and "TimeoutError" in reply.warning
    assert reply.answer.startswith("以下是检索到的") and len(reply.follow_ups) > 0


def test_empty_model_answer_uses_excerpts(demo_retriever):
    hits = demo_retriever.search("tone-cli 有哪些命令", k=3)
    for raw in ("", '{"answer":null}'):
        reply = answer_question("tone-cli 有哪些命令", hits, FakeLLM(raw))
        assert not reply.llm_used and "[1]" in reply.answer
    assert parse_llm_json('{"answer":"可运行 tone list [1]", "follow_ups":"下一步"}')[1] == []


def test_answer_no_hits():
    assert answer_question("xxx", [], None).answer == NO_RESULT


# ---------------- HTTP 接口 ----------------
def make_client(demo_retriever) -> TestClient:
    app = create_app(settings=Settings(docs_dir=DEMO_DOCS), retriever=demo_retriever)
    return TestClient(app)


def test_chat_endpoint(demo_retriever):
    with make_client(demo_retriever) as client:
        res = client.post("/api/assistant/chat", json={"question": "tone-cli 有哪些命令", "top_k": 3})
        assert res.status_code == 200
        body = res.json()
        assert body["code"] == 200 and body["msg"] == "success"
        data = body["data"]
        assert len(data["sources"]) == 3 and data["sources"][0]["index"] == 1
        assert data["sources"][0]["url"].startswith("/api/assistant/doc/")
        assert isinstance(data["follow_ups"], list) and data["mode"] == "hybrid"


def test_chat_rejects_empty_question(demo_retriever):
    with make_client(demo_retriever) as client:
        assert client.post("/api/assistant/chat", json={"question": ""}).status_code == 422
        assert client.post("/api/assistant/chat", json={"question": "  \t"}).status_code == 422
        assert client.get("/api/assistant/search", params={"q": "  "}).status_code == 422


def test_search_and_doc_endpoints(demo_retriever):
    with make_client(demo_retriever) as client:
        res = client.get("/api/assistant/search", params={"q": "ToneAgent 日志", "mode": "sparse", "k": 3})
        assert res.status_code == 200 and res.json()["data"][0]["sparse_rank"] == 1

        doc = client.get("/api/assistant/doc/tone-cli/usage.md")
        assert doc.status_code == 200 and "tone archive" in doc.text
        # 路径穿越必须被拒绝
        assert client.get("/api/assistant/doc/%2e%2e/%2e%2e/rag/config.py").status_code == 404
