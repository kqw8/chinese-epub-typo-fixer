#!/usr/bin/env bash
# build_skill.sh — 把本仓库源文件打包成可分发 / 可安装的 .skill 包。
# A .skill bundle is just a zip containing a top-level <skill-name>/ folder.
#
# 用法 / usage:
#   bash scripts/build_skill.sh            # 生成 chinese-epub-typo-fixer.skill
set -euo pipefail

SKILL_NAME="chinese-epub-typo-fixer"
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="${REPO_ROOT}/${SKILL_NAME}.skill"
STAGE="$(mktemp -d)/${SKILL_NAME}"

mkdir -p "${STAGE}"
# 只把 skill 运行所需的文件纳入包内 / include only what the skill needs
cp "${REPO_ROOT}/SKILL.md"   "${STAGE}/"
cp "${REPO_ROOT}/README.md"  "${STAGE}/"
cp "${REPO_ROOT}/LICENSE"    "${STAGE}/"
cp -r "${REPO_ROOT}/references" "${STAGE}/"
cp -r "${REPO_ROOT}/scripts"    "${STAGE}/"
# 不把构建脚本自身打进包里 / drop the build script from the bundle
rm -f "${STAGE}/scripts/build_skill.sh"
find "${STAGE}" -name '__pycache__' -type d -prune -exec rm -rf {} +

rm -f "${OUT}"
( cd "$(dirname "${STAGE}")" && zip -r -q "${OUT}" "${SKILL_NAME}" )
echo "已生成 / built: ${OUT}"
