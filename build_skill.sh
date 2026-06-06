#!/usr/bin/env bash
# build_skill.sh — 把本仓库的 skill 打包成一个独立可分发的 .skill 包。
# A .skill bundle is just a zip containing a top-level <skill-name>/ folder.
#
# 多数人不需要这个：推荐用 plugin marketplace 安装（见 README）。
# Most users don't need this — prefer the plugin marketplace install (see README).
# 这个脚本只是给想要一个离线 .skill 文件（如发 GitHub Release）的人用。
#
# 用法 / usage:
#   bash build_skill.sh            # 生成 ./chinese-epub-typo-fixer.skill
set -euo pipefail

SKILL_NAME="chinese-epub-typo-fixer"
REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"
SKILL_SRC="${REPO_ROOT}/skills/${SKILL_NAME}"
OUT="${REPO_ROOT}/${SKILL_NAME}.skill"
STAGE="$(mktemp -d)/${SKILL_NAME}"

if [ ! -f "${SKILL_SRC}/SKILL.md" ]; then
  echo "找不到 skill 源：${SKILL_SRC}/SKILL.md" >&2
  exit 1
fi

# 把整个 skill 目录拷到打包暂存区 / copy the whole skill dir into the staging area
mkdir -p "$(dirname "${STAGE}")"
cp -r "${SKILL_SRC}" "${STAGE}"
find "${STAGE}" -name '__pycache__' -type d -prune -exec rm -rf {} +

rm -f "${OUT}"
( cd "$(dirname "${STAGE}")" && zip -r -q "${OUT}" "${SKILL_NAME}" )
echo "已生成 / built: ${OUT}"
