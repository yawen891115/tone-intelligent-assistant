"""T-One 智能助手的检索增强生成 (RAG) 服务。

模块一览（数据流从上到下）：
    loader     读取 Markdown 文档
    chunker    按标题切分成 chunk
    text       中文分词（给 BM25 用）
    bm25       稀疏检索 sparse retrieval
    dense      稠密检索 dense retrieval（embedding）
    fusion     RRF 融合
    retriever  把上面几步串起来：build / load / search
    answer     拼 prompt、调大模型、解析 follow-ups
    api        FastAPI 接口
"""
