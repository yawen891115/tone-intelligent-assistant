"""所有可调参数都从环境变量读取（可以写在 backend/.env 里）。"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

try:  # python-dotenv 是可选依赖：有就自动读取 .env
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
except ImportError:  # pragma: no cover
    pass

BACKEND_DIR = Path(__file__).resolve().parents[1]


def _env(name: str, default: str) -> str:
    return os.getenv(name, default).strip()


def _path(name: str, default: str) -> Path:
    p = Path(_env(name, default))
    return p if p.is_absolute() else BACKEND_DIR / p


@dataclass
class Settings:
    # ---- 数据 ----
    docs_dir: Path = field(default_factory=lambda: _path("DOCS_DIR", "data/demo_docs"))
    index_dir: Path = field(default_factory=lambda: _path("INDEX_DIR", "data/index"))
    # 文档 front matter 里没写 url 时，用这个模板拼「来源链接」，{path} 是文档的相对路径。
    # 默认指向本服务的 /api/assistant/doc/ 接口（直接返回文档原文）；
    # 用 anolis-docs 仓库时可以改成 https://gitee.com/anolis/anolis-docs/blob/master/{path}
    url_template: str = field(default_factory=lambda: _env("URL_TEMPLATE", "/api/assistant/doc/{path}"))

    # ---- 切分 ----
    chunk_max_chars: int = field(default_factory=lambda: int(_env("CHUNK_MAX_CHARS", "400")))
    chunk_overlap: int = field(default_factory=lambda: int(_env("CHUNK_OVERLAP", "80")))

    # ---- 稠密检索 ----
    embed_model: str = field(default_factory=lambda: _env("EMBED_MODEL", "BAAI/bge-small-zh-v1.5"))
    # bge 系列可选的 query 指令前缀；m3e 不需要，留空即可
    embed_query_prefix: str = field(default_factory=lambda: _env("EMBED_QUERY_PREFIX", ""))
    embed_device: str | None = field(default_factory=lambda: _env("EMBED_DEVICE", "") or None)

    # ---- 混合检索 ----
    rrf_k: int = field(default_factory=lambda: int(_env("RRF_K", "60")))
    candidates: int = field(default_factory=lambda: int(_env("CANDIDATES", "50")))
    top_k: int = field(default_factory=lambda: int(_env("TOP_K", "5")))

    # ---- 大模型（OpenAI 兼容接口：通义千问 / DeepSeek / OpenAI / vLLM / Ollama 都行）----
    llm_base_url: str = field(default_factory=lambda: _env("LLM_BASE_URL", ""))
    llm_api_key: str = field(default_factory=lambda: _env("LLM_API_KEY", ""))
    llm_model: str = field(default_factory=lambda: _env("LLM_MODEL", ""))

    # ---- 服务 ----
    cors_origins: list[str] = field(
        default_factory=lambda: [o for o in _env("CORS_ORIGINS", "http://localhost:5173").split(",") if o]
    )

    @property
    def llm_enabled(self) -> bool:
        return bool(self.llm_model and (self.llm_api_key or self.llm_base_url))
