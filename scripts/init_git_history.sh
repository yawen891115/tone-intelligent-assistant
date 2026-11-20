#!/usr/bin/env bash
# 可选：建立一个清楚的 git 历史再推到 GitHub。
#   commit 1  上游 tone-front 原样导入（不是你写的代码）
#   commit 2  你对 tone-front 的改动（智能问答标签页）—— 在 GitHub 上点开就是完整 diff
#   commit 3  RAG 后端、评测、playground、文档
# 用法（在仓库根目录）：bash scripts/init_git_history.sh
set -euo pipefail
cd "$(dirname "$0")/.."

if [ -d .git ]; then
  echo "这里已经是 git 仓库了，脚本只用于第一次初始化。" >&2
  exit 1
fi

git init -q -b main

# 1) 先把 tone-front 还原成上游原样，单独提交
git apply -R --directory=tone-front tone-front.patch
git add tone-front
git add -f tone-front/mock   # 上游的 .gitignore 写了 /mock，但上游仓库里其实提交了这些文件
git commit -q -m "Import OpenAnolis tone-front @65a8a78 (Mulan PSL v2, unmodified)"

# 2) 重新应用改动，单独提交
git apply --directory=tone-front tone-front.patch
git add tone-front
git commit -q -m "tone-front: add 智能问答 tab (React/TS RagChat) backed by the hybrid RAG service"

# 3) 其余文件
git add -A
git commit -q -m "Add hybrid sparse+dense RAG backend, retrieval evaluation, playground and docs"

git log --oneline
echo
echo "下一步：在 GitHub 上新建一个空仓库，然后"
echo "  git remote add origin git@github.com:<你的用户名>/tone-intelligent-assistant.git"
echo "  git push -u origin main"
