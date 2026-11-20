# T-One 智能助手

[English README](README.md)

在龙蜥社区 T-One 测试平台的答疑助手中增加了「智能问答」标签页。输入「提交的测试一直在排队是怎么回事？」，可以从回答里的引用打开对应文档，也可以直接点击推荐问题继续追问。

## 检索与回答

- BM25 保留 `tone-cli` 等技术词，向量检索使用中文句向量匹配同义问法。两路各取最多 50 个片段，用 Reciprocal Rank Fusion（`k = 60`）融合，默认返回前 5 个。
- 每个片段保留文档标题、小节和来源地址。示例语料的链接在本地打开原文，导出的 T-One 帮助文档链接可返回原平台。
- FastAPI 把回答、引用和追问返回给 React/TypeScript 界面。配置兼容 OpenAI 的模型接口后可生成带引用的回答。使用默认配置时直接展示检索到的片段。

## 本地运行

从仓库根目录启动后端。第一次建索引会下载 `BAAI/bge-small-zh-v1.5`。

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/build_index.py
uvicorn rag.api:app --port 8000
```

在第二个终端从仓库根目录启动预览。

```bash
cd playground
npm ci
npm run dev
```

打开[聊天界面](http://localhost:5173)。可切换三种检索方式、查看回答出处，或直接调试 [FastAPI 接口](http://localhost:8000/docs)。配置项见 [backend/.env.example](backend/.env.example)。

## 评测

仓库提供 31 篇示例文档和 66 道带相关文档标注的问题，其中 35 道是关键词题、31 道是语义题。Recall@5 先计算每道题的前五个片段覆盖了多少比例的相关文档，再对题目取平均。MRR@10 看前十个片段中第一个相关结果的排名。

在 `backend/` 建好索引后运行：

```bash
python scripts/evaluate.py --eval data/eval/demo_eval.jsonl --sweep
pytest -q
```

默认 BGE 模型在这 66 题上的 Recall@5 从纯向量检索的 **0.924** 提升到混合检索的 **0.992**，MRR@10 从 **0.862** 提升到 **0.886**。[英文 README 的评测表](README.md#retrieval-evaluation)列出实测结果。评测命令会生成 `results/summary.json` 和 `results/per_question.csv`，便于检查每道题的检索结果。

要在真实 T-One 语料上评测，可通过 `scripts/export_tone_docs.py` 导出平台帮助文档，设置 `DOCS_DIR` 后重建索引，再用 `gen_eval_candidates.py` 和 `review_eval.py` 出题和人工审核。上游前端、项目新增代码和许可证的说明见 [NOTICE.md](NOTICE.md)。
