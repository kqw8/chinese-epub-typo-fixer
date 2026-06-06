#!/usr/bin/env python3
"""
apply_fixes.py — 中文 EPUB 校对流水线第 2 步：回写 + 重打包 + 出明细。

输入：
  - manifest.json   (extract_epub.py 生成的)
  - fixes.json      (模型逐章校对后写出的改动清单)

输出：
  - 一个修正后的 EPUB
  - changes_report.md  (人类可读，分三区)
  - changes_report.json(结构化)

两类改动，区别对待：
  - category = "ocr_error"   ：确信的 OCR 形近错字 —— 默认应用（带护栏）。
  - category = "modernization"：旧用字现代化（如 象→像）—— 默认【只列出、不应用】，
                                需加 --apply-modernization 才会真正写回。
  缺省 category 按 ocr_error 处理。

核心理念：保守、透明、可追溯。拿不准 / 定位不唯一 / 找不到 / 改动过大 / 前后不一致，
一律【不强行修改】，原样保留并写进报告，交回人判断。

fixes.json 格式见 SKILL.md。
"""

import os
import re
import sys
import json

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib"))
import epub_utils as eu  # noqa: E402

# 单条改动的「最大允许差异字符数」。OCR 错字修正应是小改动；超过则判为可疑，不自动应用。
MAX_DIFF_CHARS = 6

OK_STATUSES = {"ok_string", "ok_fallback"}


def _diff_char_count(a, b):
    la, lb = len(a), len(b)
    common = min(la, lb)
    pos_diff = sum(1 for i in range(common) if a[i] != b[i])
    return abs(la - lb) + pos_diff


def _tolerant_pattern(s):
    sep = r"(?:\s|<[^>]*>)*"
    return sep.join(re.escape(c) for c in s)


def apply_one_fix(xhtml, fix):
    """
    把一条改动应用到章节 XHTML 字符串上。返回 (new_xhtml, status, note)。
    status: ok_string / ok_fallback / skip_ambiguous / skip_not_found /
            skip_suspicious / skip_inconsistent
    """
    original = fix.get("original", "")
    corrected = fix.get("corrected", "")
    wrong = fix.get("wrong", "")
    right = fix.get("right", "")

    if not original or not corrected:
        return xhtml, "skip_not_found", "缺少 original/corrected"
    if _diff_char_count(original, corrected) > MAX_DIFF_CHARS:
        return xhtml, "skip_suspicious", "改动幅度过大，疑似过度修改"
    if wrong and right:
        if original.replace(wrong, right) != corrected:
            return xhtml, "skip_inconsistent", "original/corrected 与 wrong/right 不一致"

    # 主路径：整片段精确、唯一替换
    n = xhtml.count(original)
    if n == 1:
        return xhtml.replace(original, corrected, 1), "ok_string", ""
    if n > 1:
        return xhtml, "skip_ambiguous", f"片段在本章出现 {n} 次，无法唯一定位"

    # 降级：整片段可能被内联标签打断 -> 对错词做唯一替换
    if wrong and right:
        wn = xhtml.count(wrong)
        if wn == 1:
            return xhtml.replace(wrong, right, 1), "ok_fallback", "整片段未命中，按错词唯一替换"
        if wn == 0:
            pat = _tolerant_pattern(original)
            matches = list(re.finditer(pat, xhtml))
            if len(matches) == 1:
                span = matches[0].span()
                seg = xhtml[span[0]:span[1]]
                if wrong in seg and seg.count(wrong) == 1:
                    new_seg = seg.replace(wrong, right, 1)
                    return xhtml[:span[0]] + new_seg + xhtml[span[1]:], "ok_fallback", "容错定位后替换"
            return xhtml, "skip_not_found", "错词在本章未出现，疑似片段有误"
        pat = _tolerant_pattern(original)
        matches = list(re.finditer(pat, xhtml))
        if len(matches) == 1:
            span = matches[0].span()
            seg = xhtml[span[0]:span[1]]
            if seg.count(wrong) == 1:
                new_seg = seg.replace(wrong, right, 1)
                return xhtml[:span[0]] + new_seg + xhtml[span[1]:], "ok_fallback", "容错定位后替换"
        return xhtml, "skip_ambiguous", f"错词在本章出现 {wn} 次，无法唯一定位"

    return xhtml, "skip_not_found", "整片段未命中且无 wrong/right 可降级"


def main():
    args = [a for a in sys.argv[1:]]
    apply_modern = False
    if "--apply-modernization" in args:
        apply_modern = True
        args.remove("--apply-modernization")

    if len(args) < 2:
        print("用法: python3 apply_fixes.py <manifest.json> <fixes.json> [输出epub] [--apply-modernization]")
        sys.exit(1)

    manifest_path = args[0]
    fixes_path = args[1]

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)
    with open(fixes_path, "r", encoding="utf-8") as f:
        fixes_doc = json.load(f)

    fixes = fixes_doc.get("fixes", [])
    work_dir = manifest["work_dir"]
    unpack_dir = manifest["unpack_dir"]

    src = manifest["source_epub"]
    base, ext = os.path.splitext(os.path.basename(src))
    default_out = os.path.join(work_dir, f"{base}_corrected{ext}")
    out_epub = args[2] if len(args) > 2 else default_out

    by_index = {ch["index"]: ch for ch in manifest["chapters"]}

    # 按章节分组，保序
    grouped = {}
    for fx in fixes:
        grouped.setdefault(fx.get("chapter_index"), []).append(fx)

    results = []
    n_ocr_applied = 0
    n_modern_applied = 0
    n_modern_listed = 0
    n_skipped = 0

    for ci, fx_list in grouped.items():
        ch = by_index.get(ci)
        if ch is None:
            for fx in fx_list:
                results.append({
                    "category": fx.get("category", "ocr_error"),
                    "chapter_index": ci, "chapter_href": "?",
                    "wrong": fx.get("wrong", ""), "right": fx.get("right", ""),
                    "original": fx.get("original", ""), "corrected": fx.get("corrected", ""),
                    "reason": fx.get("reason", ""),
                    "status": "skip_not_found", "applied": False,
                    "note": f"manifest 中无 chapter_index={ci}",
                })
                n_skipped += 1
            continue

        xhtml_path = ch["xhtml_path"]
        with open(xhtml_path, "r", encoding="utf-8") as f:
            xhtml = f.read()

        for fx in fx_list:
            category = fx.get("category", "ocr_error")
            rec = {
                "category": category,
                "chapter_index": ci, "chapter_href": ch["href"],
                "wrong": fx.get("wrong", ""), "right": fx.get("right", ""),
                "original": fx.get("original", ""), "corrected": fx.get("corrected", ""),
                "reason": fx.get("reason", ""),
            }

            # 旧用字现代化：默认不应用，只列出
            if category == "modernization" and not apply_modern:
                rec.update({"status": "listed_not_applied", "applied": False,
                            "note": "旧用字现代化建议，默认未应用，待用户确认"})
                results.append(rec)
                n_modern_listed += 1
                continue

            # 其余（ocr_error，或已同意现代化）：走护栏应用
            new_xhtml, status, note = apply_one_fix(xhtml, fx)
            applied = status in OK_STATUSES
            if applied:
                xhtml = new_xhtml
                if category == "modernization":
                    n_modern_applied += 1
                else:
                    n_ocr_applied += 1
            else:
                n_skipped += 1
            rec.update({"status": status, "applied": applied, "note": note})
            results.append(rec)

        with open(xhtml_path, "w", encoding="utf-8") as f:
            f.write(xhtml)

    eu.repack_epub(unpack_dir, out_epub)

    report_json = os.path.join(work_dir, "changes_report.json")
    report_md = os.path.join(work_dir, "changes_report.md")
    summary = {
        "source_epub": src,
        "output_epub": os.path.abspath(out_epub),
        "total_proposed": len(results),
        "ocr_applied": n_ocr_applied,
        "modernization_applied": n_modern_applied,
        "modernization_listed": n_modern_listed,
        "skipped": n_skipped,
        "apply_modernization_flag": apply_modern,
    }
    with open(report_json, "w", encoding="utf-8") as f:
        json.dump({"summary": summary, "changes": results}, f, ensure_ascii=False, indent=2)
    _write_markdown_report(report_md, summary, results)

    # 控制台汇报（中文）
    print("=" * 56)
    print("改动应用完成")
    print("=" * 56)
    print(f"建议改动总数      : {len(results)}")
    print(f"OCR 错字·已应用   : {n_ocr_applied}")
    if apply_modern:
        print(f"旧用字现代化·已应用: {n_modern_applied}")
    else:
        print(f"旧用字现代化·已列出: {n_modern_listed}  (默认未应用，待用户确认)")
    print(f"护栏跳过(需人工)  : {n_skipped}")
    print(f"修正后 EPUB       : {os.path.abspath(out_epub)}")
    print(f"改动明细(md)      : {os.path.abspath(report_md)}")
    if n_modern_listed and not apply_modern:
        print("-" * 56)
        print("发现旧用字现代化建议（默认未改），如需统一为现代写法，")
        print("请加 --apply-modernization 重新运行。")


def _status_cn(s):
    return {
        "ok_string": "✅ 已应用",
        "ok_fallback": "✅ 已应用(降级)",
        "listed_not_applied": "🔵 建议·未应用",
        "skip_ambiguous": "⚠️ 跳过·定位不唯一",
        "skip_not_found": "⚠️ 跳过·未找到",
        "skip_suspicious": "⚠️ 跳过·改动过大",
        "skip_inconsistent": "⚠️ 跳过·前后不一致",
    }.get(s, s)


def _write_markdown_report(path, summary, results):
    L = []
    L.append("# 中文 EPUB 校对 · 改动明细\n")
    L.append(f"- 源文件：`{os.path.basename(summary['source_epub'])}`")
    L.append(f"- 输出文件：`{os.path.basename(summary['output_epub'])}`")
    L.append(f"- 建议改动：**{summary['total_proposed']}** 处")
    L.append(f"- OCR 错字已应用：**{summary['ocr_applied']}** 处")
    if summary["apply_modernization_flag"]:
        L.append(f"- 旧用字现代化已应用：**{summary['modernization_applied']}** 处")
    else:
        L.append(f"- 旧用字现代化建议（默认未应用）：**{summary['modernization_listed']}** 处")
    L.append(f"- 护栏跳过（需人工确认）：**{summary['skipped']}** 处\n")

    ocr_applied = [r for r in results if r["category"] != "modernization" and r["applied"]]
    modern = [r for r in results if r["category"] == "modernization"]
    skipped = [r for r in results if r["category"] != "modernization" and not r["applied"]]

    # 区1：已应用的 OCR 修正
    if ocr_applied:
        L.append("## 一、已应用的 OCR 错字修正\n")
        L.append("| 章节 | 原字 | 改为 | 所在句子 | 理由 |")
        L.append("|---|---|---|---|---|")
        for r in ocr_applied:
            ctx = r["original"].replace("|", "\\|")
            L.append(f"| 第{r['chapter_index']}章 | {r['wrong']} | {r['right']} | …{ctx}… | {r['reason']} |")
        L.append("")

    # 区2：旧用字现代化
    if modern:
        if summary["apply_modernization_flag"]:
            L.append("## 二、旧用字现代化（已按你的确认应用）\n")
        else:
            L.append("## 二、旧用字现代化建议（默认未应用，请你定夺）\n")
            L.append("> 以下是「现代读者可能觉得别扭/像错字」的旧用字。它们本身不算错误，故默认未改。")
            L.append("> 如需统一改成现代写法，加 `--apply-modernization` 重新运行即可。\n")
        L.append("| 章节 | 原字 | 拟改为 | 状态 | 所在句子 | 理由 |")
        L.append("|---|---|---|---|---|---|")
        for r in modern:
            ctx = r["original"].replace("|", "\\|")
            L.append(f"| 第{r['chapter_index']}章 | {r['wrong']} | {r['right']} | {_status_cn(r['status'])} | …{ctx}… | {r['reason']} |")
        L.append("")

    # 区3：护栏未应用
    if skipped:
        L.append("## 三、未自动应用（请人工确认）\n")
        L.append("| 章节 | 原字 | 拟改为 | 状态 | 说明 |")
        L.append("|---|---|---|---|---|")
        for r in skipped:
            L.append(f"| 第{r['chapter_index']}章 | {r['wrong']} | {r['right']} | {_status_cn(r['status'])} | {r['note']} |")
        L.append("")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(L))


if __name__ == "__main__":
    main()
