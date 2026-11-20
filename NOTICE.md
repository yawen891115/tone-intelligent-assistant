# Notice: what comes from upstream and what this repository adds

## Upstream code

`tone-front/` is a modified copy of the T-One frontend from the OpenAnolis community
([gitee.com/anolis/tone-front](https://gitee.com/anolis/tone-front)), licensed under the
**Mulan Permissive Software License, Version 2** (see `tone-front/LICENSE`).
The copy starts from [commit `65a8a78` of Huanli-Gong/tone-front](https://github.com/Huanli-Gong/tone-front/commit/65a8a78e5268f0368682d696e41c7132021c06c5).

At that commit the help assistant (`src/components/HelperChatBoot/`) already contained:

- the floating "T-One答疑助手" panel with the 常见问题 (FAQ keyword match), 自助排查 (job self-diagnosis)
  and 意见反馈 (feedback) features — written by the T-One team (2024-03 to 2024-05);
- rendering of an LLM `response` with `<problem>` tags and help-doc `reference` links in
  `HelperContext/AnswerContent.tsx` — added in commit `65a8a78` (2024-09-22).

## Added in this repository

| Path | Description | License |
|---|---|---|
| `backend/` | Hybrid-retrieval RAG service, evaluation harness, labeling tools, tests, sample corpus | MIT |
| `playground/` | Standalone preview app for the chat view | MIT |
| `tone-front/src/components/HelperChatBoot/RagChat/` | New React/TypeScript chat view (智能问答 tab) | Mulan PSL v2 (same as the rest of `tone-front/`) |
| `tone-front/src/components/HelperChatBoot/HelperContext/index.tsx`, `HelperChatBoot/index.tsx`, `config/proxy.ts`, `package.json`, `pnpm-lock.yaml` | New default tab, API development proxy and package dependencies | Mulan PSL v2 |
| `tone-front/src/components/HelperChatBoot/HelperContext/AnswerContent.tsx`, `tone-front/config/config.ts` | Sanitize model output in the existing FAQ view and limit environment settings embedded in the frontend bundle | Mulan PSL v2 |

`tone-front.patch` is distributed under Mulan PSL v2 and is the complete diff of `tone-front/` against the upstream commit.

## Sample data

`backend/data/demo_docs/` contains short sample documents written for testing the pipeline offline.
They are **not** official T-One or Anolis documentation. Real documents can be exported with
`backend/scripts/export_tone_docs.py`; they belong to the OpenAnolis community and are not included here.
