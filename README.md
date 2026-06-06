# chinese-epub-typo-fixer

> 一个 Claude 技能：校对中文 EPUB 电子书的 OCR 错别字，并把旧用字整理成可选的现代化建议。
> A Claude skill for proofreading OCR typos in **Chinese** EPUB e-books, plus optional modernization of archaic character usage.

处理完给你两样东西：一本**修正后的 EPUB**，和一份**逐条改动明细**。
You get two outputs: a **corrected EPUB** and a **detailed change report**.

---

## 中文说明

### 它做什么

针对**图片 OCR 扫描生成的中文电子书**，把两类问题分开处理：

1. **确信的 OCR 错别字**（形近字、繁简混入，如「莨蓿→莨菪」「傍睌→傍晚」）——**默认改掉**。
2. **旧用字现代化**（如「象→像」这种现代读者会觉得别扭、甚至误以为是错字的旧写法）——
   **默认只列出、不改**，由你决定要不要统一成现代写法。

### 设计原则

- **极端保守，拿不准就不改。** 适合处理本就高质量、错误稀少的书；漏改远比误改安全。
- **真正"找错字"的是 Claude（模型），脚本只做机械活**（拆包、精确回写、重打包、出报告）。
- **形近 ≠ 义近。** OCR 按字形猜，错的都是"长得像"的字（晚→睌），不会把"机器"错成"机械"。
- **多义字逐处判断。** "象"当"像"用才改，"大象/象征/想象"绝不动——绝非查找替换。
- **多重护栏。** 定位不唯一 / 找不到 / 改动过大 / 前后不一致，一律不强行改，列入报告交人工确认。
- **零外部依赖、不联网。** EPUB 本质是 ZIP，只用标准库 + BeautifulSoup/lxml。
- **输出一律简体中文**（含与用户对话、报告），不漂移到其他语言。

### 安装

```bash
# Claude Code（用户级）—— 直接 clone 到 skills 目录
git clone https://github.com/kqw8/chinese-epub-typo-fixer ~/.claude/skills/chinese-epub-typo-fixer
# 或项目级
git clone https://github.com/kqw8/chinese-epub-typo-fixer .claude/skills/chinese-epub-typo-fixer
```

依赖（多数环境已自带）：`pip install beautifulsoup4 lxml`

打包成可分发的 `.skill`（可选）：`bash scripts/build_skill.sh`

### 用法

把 `.epub` 交给 Claude，说「帮我校对这本中文书的 OCR 错别字」即可。手动两步：

```bash
# 1) 拆书
python3 scripts/extract_epub.py 书.epub 工作目录

# （中间：Claude 逐章阅读 工作目录/chapters/*.txt，按原则找错，写出 fixes.json）

# 2) 回写（第一遍：改OCR错字，旧用字只列出）
python3 scripts/apply_fixes.py 工作目录/manifest.json fixes.json 输出.epub

# 3)（可选）你同意现代化旧用字后，加 flag 重跑
python3 scripts/apply_fixes.py 工作目录/manifest.json fixes.json 输出.epub --apply-modernization
```

产出：`输出.epub`、`工作目录/changes_report.md`（分三区：OCR修正 / 旧用字现代化 / 护栏未应用）。

### 处理规模与并行

`extract_epub.py` 按全书字数给出建议 agent 数（上限 10）：< 5 万→1，5–15 万→2，15–30 万→3，
30–60 万→5，> 60 万→5–10。并行只在支持子代理的环境（Claude Code / Cowork）且书大时才有意义，
否则自动单 agent 串行。**任务很轻，能用 1 个就别用 5 个。**

### fixes.json 格式

```json
{
  "fixes": [
    {"category": "ocr_error", "chapter_index": 7,
     "original": "但对于莨蓿制剂和鸦片却知之甚详", "corrected": "但对于莨菪制剂和鸦片却知之甚详",
     "wrong": "莨蓿", "right": "莨菪", "reason": "形近字，据上下文应为'莨菪'"},
    {"category": "modernization", "chapter_index": 6,
     "original": "所以就象空气一样的自由", "corrected": "所以就像空气一样的自由",
     "wrong": "象", "right": "像", "reason": "此处'象'当'像'用"}
  ]
}
```

详见 `SKILL.md`；判别标准与边界情况见 `references/ocr-error-guide.md`。

---

## English

### What it does

For **Chinese e-books produced by image OCR**, it handles two categories separately:

1. **Confident OCR typos** (visually-similar character confusions, simplified/traditional mix-ups)
   — **applied by default**.
2. **Archaic-usage modernization** (e.g. old 象 used where modern Chinese writes 像, which today's
   readers may mistake for typos) — **listed only by default**; you decide whether to apply.

### Principles

- **Extremely conservative — when in doubt, don't change.** Built for already-high-quality books;
  a missed fix is far safer than a wrong one.
- **Claude (the model) finds the errors; scripts only do mechanical work** (unpack, precise rewrite,
  repack, report).
- **Visually-similar ≠ semantically-similar.** OCR guesses by glyph shape, so its errors look alike.
- **Per-occurrence judgment for polysemous characters.** Only 象-as-像 is changed; 大象/象征/想象
  are never touched. This is not find-and-replace.
- **Multiple guardrails.** Non-unique match / not found / oversized change / inconsistency are never
  force-applied — they go into the report for human review.
- **Zero external deps, no network.** EPUB is just a ZIP; uses stdlib + BeautifulSoup/lxml only.
- **All user-facing output is in Simplified Chinese** by design (this is a Chinese-book tool).

### Install

```bash
git clone https://github.com/kqw8/chinese-epub-typo-fixer ~/.claude/skills/chinese-epub-typo-fixer
```
Deps: `pip install beautifulsoup4 lxml`. Build a distributable bundle (optional): `bash scripts/build_skill.sh`

### Usage

Give Claude the `.epub` and ask it to proofread. Or run manually:

```bash
python3 scripts/extract_epub.py book.epub workdir
# Claude reads workdir/chapters/*.txt, writes fixes.json
python3 scripts/apply_fixes.py workdir/manifest.json fixes.json out.epub
# Optional, after you approve modernization:
python3 scripts/apply_fixes.py workdir/manifest.json fixes.json out.epub --apply-modernization
```

Outputs: `out.epub` and `workdir/changes_report.md` (three sections: OCR fixes / modernization /
guardrail-skipped). See `SKILL.md` and `references/ocr-error-guide.md` for details.

---

## 目录结构 / Structure

```
chinese-epub-typo-fixer/
├── SKILL.md                   # 技能主文件（中文）/ skill manifest (Chinese)
├── README.md                  # 本文件（中英双语）/ this file (bilingual)
├── LICENSE                    # MIT
├── references/
│   └── ocr-error-guide.md     # 判别指南（中文）/ judgment guide (Chinese)
└── scripts/
    ├── extract_epub.py        # 拆书 / unpack & analyze
    ├── apply_fixes.py         # 回写+护栏+报告 / apply + guardrails + report
    └── lib/epub_utils.py      # EPUB 读写工具 / EPUB I/O utils
```

## 许可 / License

MIT，见 `LICENSE`。欢迎 fork、改进、分享 / Fork and contribute freely.

---

*这是一个社区 Claude 技能，并非 Anthropic 官方产品。*
*A community Claude skill, not an official Anthropic product.*
