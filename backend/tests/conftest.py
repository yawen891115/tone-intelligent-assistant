import sys
import zlib
from pathlib import Path

import numpy as np
import pytest

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from rag.config import Settings  # noqa: E402
from rag.retriever import Retriever  # noqa: E402

DEMO_DOCS = BACKEND / "data" / "demo_docs"


class FakeEmbedder:
    """测试专用：把字符 bigram 哈希到 256 维再归一化。不用下载模型，结果固定可复现。"""

    name = "fake-hash-embedder"
    dim = 256

    def _vec(self, text: str) -> np.ndarray:
        v = np.zeros(self.dim, dtype=np.float32)
        t = text.lower()
        for a, b in zip(t, t[1:]):
            v[zlib.crc32((a + b).encode()) % self.dim] += 1.0
        n = np.linalg.norm(v)
        return v / n if n else v

    def encode_docs(self, texts):
        return np.stack([self._vec(t) for t in texts])

    def encode_query(self, text):
        return self._vec(text)


@pytest.fixture(scope="session")
def demo_retriever(tmp_path_factory) -> Retriever:
    settings = Settings(docs_dir=DEMO_DOCS, index_dir=tmp_path_factory.mktemp("index"))
    return Retriever.build(settings, FakeEmbedder())
