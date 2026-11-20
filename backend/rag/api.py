"""FastAPI 接口。启动：在 backend/ 目录下运行
    uvicorn rag.api:app --port 8000 --reload
然后浏览器打开 http://localhost:8000/docs 可以直接调试。

返回格式和 T-One 现有接口保持一致：{"code": 200, "msg": "success", "data": {...}}
"""
from __future__ import annotations

import time
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field

from .answer import answer_question
from .config import Settings
from .conversation import standalone_query
from .dense import SentenceTransformerEmbedder
from .llm import LLMClient
from .loader import DOC_SUFFIXES
from .retriever import Retriever

ModeT = Literal["hybrid", "dense", "sparse"]


# ---------- 请求 / 响应的数据格式（前端 types.ts 和这里一一对应）----------
class Turn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=4000)


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=500, pattern=r"\S")
    history: list[Turn] = Field(default_factory=list, max_length=20)
    mode: ModeT = "hybrid"
    top_k: int = Field(default=5, ge=1, le=10)


class Source(BaseModel):
    index: int
    chunk_id: str
    doc_id: str
    title: str
    section: str
    url: str
    snippet: str
    score: float
    cited: bool


class ChatData(BaseModel):
    answer: str
    sources: list[Source]
    follow_ups: list[str]
    query: str  # 实际拿去检索的语句（多轮追问时是改写后的独立问题）
    mode: ModeT
    latency_ms: int
    llm_used: bool
    warning: str | None = None


class ChatResponse(BaseModel):
    code: int = 200
    msg: str = "success"
    data: ChatData


def create_app(settings: Settings | None = None, retriever: Retriever | None = None,
               llm: LLMClient | None = None) -> FastAPI:
    """retriever / llm 可以从外面传进来（单元测试里传假的），不传就按配置创建。"""
    settings = settings or Settings()
    state: dict = {"retriever": retriever, "llm": llm}

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        if state["retriever"] is None:
            embedder = SentenceTransformerEmbedder(
                settings.embed_model, settings.embed_device, settings.embed_query_prefix
            )
            state["retriever"] = Retriever.load_or_build(settings, embedder)
        if state["llm"] is None and settings.llm_enabled:
            state["llm"] = LLMClient(settings.llm_base_url, settings.llm_api_key, settings.llm_model)
        yield

    app = FastAPI(title="T-One Assistant RAG", version="1.0.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/assistant/health")
    def health() -> dict:
        r: Retriever = state["retriever"]
        return {"code": 200, "msg": "success", "data": {
            "chunks": len(r.chunks), "embed_model": r.embedder.name, "llm_enabled": state["llm"] is not None,
        }}

    @app.post("/api/assistant/chat", response_model=ChatResponse)
    def chat(req: ChatRequest) -> ChatResponse:  # 普通 def：FastAPI 会放到线程池里跑，不会卡住事件循环
        t0 = time.perf_counter()
        question = req.question.strip()
        history = [t.model_dump() for t in req.history]
        query = standalone_query(question, history, state["llm"])  # 多轮：先把追问改写成独立问题
        hits = state["retriever"].search(query, mode=req.mode, k=req.top_k)
        reply = answer_question(question, hits, state["llm"], history)
        data = ChatData(
            answer=reply.answer,
            sources=[Source(**s) for s in reply.sources],
            follow_ups=reply.follow_ups,
            query=query,
            mode=req.mode,
            latency_ms=int((time.perf_counter() - t0) * 1000),
            llm_used=reply.llm_used,
            warning=reply.warning,
        )
        return ChatResponse(data=data)

    @app.get("/api/assistant/search")
    def search(q: str = Query(min_length=1, max_length=500, pattern=r"\S"), mode: ModeT = "hybrid",
               k: int = Query(default=10, ge=1, le=50)) -> dict:
        """只做检索、不调大模型，调试检索效果用。"""
        hits = state["retriever"].search(q.strip(), mode=mode, k=k)
        return {"code": 200, "msg": "success", "data": [
            {"rank": h.rank, "score": round(h.score, 4), "chunk_id": h.chunk.chunk_id, "title": h.chunk.title,
             "section": h.chunk.section, "url": h.chunk.url, **h.detail} for h in hits
        ]}

    @app.get("/api/assistant/doc/{path:path}", response_class=PlainTextResponse)
    def doc(path: str) -> str:
        """返回文档原文，给前端的「来源链接」用（默认 URL_TEMPLATE 指向这里）。"""
        base = settings.docs_dir.resolve()
        file = (base / path).resolve()
        # 防路径穿越：解析后的路径必须还在文档目录里面，比如 ../../etc/passwd 就会被拒绝
        if not file.is_relative_to(base) or not file.is_file() or file.suffix.lower() not in DOC_SUFFIXES:
            raise HTTPException(status_code=404, detail="文档不存在")
        return file.read_text(encoding="utf-8")

    return app


app = create_app()
