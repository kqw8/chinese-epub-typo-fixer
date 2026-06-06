#!/usr/bin/env python3
"""
extract_epub.py — EPUB 校对流水线第 1 步：拆书。

做的事：
  1. 把 EPUB 解压到一个工作目录（后面 apply_fixes 还要用它来回写、重打包）。
  2. 按 spine 阅读顺序找出所有正文章节。
  3. 把每章的纯文本写成 chapters/<序号>__<id>.txt，供模型逐章阅读。
  4. 统计每章 / 全书汉字数，给出建议的并行 agent 数。
  5. 写一份 manifest.json 记录全部元信息。

用法：
  python3 extract_epub.py <book.epub> [工作目录]
  工作目录默认 = ./_epubwork

设计说明：
  真正「找错别字」的是模型(Claude)，不是这个脚本。脚本只负责机械、确定性
  的拆解与统计，把书整理成模型好读、之后好精确回写的形态。
"""

import os
import sys
import json

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib"))
import epub_utils as eu  # noqa: E402


def main():
    if len(sys.argv) < 2:
        print("用法: python3 extract_epub.py <book.epub> [工作目录]")
        sys.exit(1)

    epub_path = sys.argv[1]
    work_dir = sys.argv[2] if len(sys.argv) > 2 else "_epubwork"

    if not os.path.exists(epub_path):
        print(f"找不到文件: {epub_path}")
        sys.exit(1)

    unpack_dir = os.path.join(work_dir, "unpacked")
    chapters_dir = os.path.join(work_dir, "chapters")
    os.makedirs(chapters_dir, exist_ok=True)

    # 1) 解压
    eu.unzip_epub(epub_path, unpack_dir)

    # 2) 取按阅读顺序的章节
    docs = eu.get_content_documents(unpack_dir)
    if not docs:
        print("警告：没有在 spine 里找到 XHTML 正文文档。")

    manifest = {
        "source_epub": os.path.abspath(epub_path),
        "work_dir": os.path.abspath(work_dir),
        "unpack_dir": os.path.abspath(unpack_dir),
        "chapters": [],
        "total_cjk_chars": 0,
    }

    total_cjk = 0
    for idx, doc in enumerate(docs, start=1):
        with open(doc["abs_path"], "r", encoding="utf-8") as f:
            xhtml = f.read()
        text = eu.extract_text_from_xhtml(xhtml)
        cjk = eu.count_cjk_chars(text)
        total_cjk += cjk

        # 章节文本落盘，文件名带序号便于排序、带 id 便于回查
        safe_id = doc["id"].replace("/", "_").replace("\\", "_")
        chap_fname = f"{idx:03d}__{safe_id}.txt"
        chap_path = os.path.join(chapters_dir, chap_fname)
        with open(chap_path, "w", encoding="utf-8") as f:
            f.write(text)

        manifest["chapters"].append({
            "index": idx,
            "id": doc["id"],
            "href": doc["href"],
            "xhtml_path": doc["abs_path"],
            "text_path": os.path.abspath(chap_path),
            "cjk_chars": cjk,
        })

    manifest["total_cjk_chars"] = total_cjk
    rec = eu.recommend_agent_count(total_cjk)
    manifest["recommended_agents"] = rec

    manifest_path = os.path.join(work_dir, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    # 汇报
    print("=" * 56)
    print("EPUB 拆解完成")
    print("=" * 56)
    print(f"源文件        : {manifest['source_epub']}")
    print(f"章节数        : {len(manifest['chapters'])}")
    print(f"全书汉字数    : {total_cjk:,}")
    print(f"建议并行 agent: {rec}  (1 = 单 agent 串行处理，最省额度)")
    print(f"manifest      : {os.path.abspath(manifest_path)}")
    print("-" * 56)
    print("各章篇幅：")
    for ch in manifest["chapters"]:
        print(f"  [{ch['index']:>3}] {ch['cjk_chars']:>7,} 字  <- {ch['href']}")
    print("-" * 56)
    print("下一步：逐章阅读 chapters/ 下的 .txt，按 SKILL.md 的原则找 OCR 错字，")
    print("       把改动写成 fixes.json，再交给 apply_fixes.py。")


if __name__ == "__main__":
    main()
