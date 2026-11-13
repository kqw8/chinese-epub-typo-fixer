[English](guide.md) | 简体中文

[返回首页](../README.zh-CN.md)

# chinese-epub-typo-fixer

一个 Claude 技能：校对中文 EPUB 电子书的 OCR 错别字，并把旧用字整理成可选的现代化建议。处理后产出一本**修正后的 EPUB** 和一份**逐条改动明细**。

## 它做什么

针对正文由图片 OCR 生成的中文电子书，把两类问题分开处理：

1. **确信的 OCR 错别字**，如形近字、繁简混入（`莨蓿 → 莨菪`、`傍睌 → 傍晚`），通过校验后默认改掉。
2. **旧用字现代化**，如旧版中当作 `像` 使用的 `象`，默认只列出、不修改，由你决定是否采用现代写法。

### 原则与限制

- **极端保守，拿不准就不改。** 适合本就高质量、错误稀少的书；漏改远比误改安全。这是校对，不是润色或改写。
- **真正找错字的是 Claude，脚本只做机械工作**：拆包、回写、重打包和生成报告。脚本不执行图片 OCR，也不会独立识别错别字。
- **形近不等于义近。** OCR 按字形识别，错误通常是长得像的字，而不是近义词替换。
- **多义字逐处判断。** `象` 当 `像` 用才列为现代化候选，`大象`、`象征`、`想象` 不动，不能全局替换。
- **护栏跳过不确定的修改。** 定位不唯一、找不到、差异超过六个字符，或 `original`/`corrected` 与 `wrong`/`right` 不一致，都列入报告交人工检查。
- **本地脚本，少量依赖。** Python 脚本只用标准库、BeautifulSoup 和 lxml，不发起网络请求；Claude 服务和安装过程的联网要求另计。
- **技能的用户可见输出一律简体中文**，包括对话和报告。

## 安装

### Claude Code 插件安装（推荐）

在 Claude Code 中输入：

```text
/plugin marketplace add kqw8/chinese-epub-typo-fixer
/plugin install chinese-epub-typo-fixer@kqw8-skills
```

安装后技能自动注册，把 `.epub` 交给 Claude，说“帮我校对这本中文书的 OCR 错别字”即可。

脚本需要 Python 3 和以下依赖：

```bash
python3 -m pip install beautifulsoup4 lxml
```

### 手动安装

将技能目录复制到 Claude 的技能目录：

```bash
git clone https://github.com/kqw8/chinese-epub-typo-fixer
mkdir -p ~/.claude/skills
cp -r chinese-epub-typo-fixer/skills/chinese-epub-typo-fixer ~/.claude/skills/
```

可选：在仓库根目录运行 `bash build_skill.sh`，生成供分发的 ZIP 格式文件 `chinese-epub-typo-fixer.skill`。打包需要 Bash 和 `zip`，只包含技能文件，不包含 Python 依赖。

## 用法

直接把 `.epub` 交给 Claude 并要求校对即可。也可以从仓库根目录开始，手动执行机械处理步骤：

```bash
cd skills/chinese-epub-typo-fixer

# 1. 拆包并提取章节文本。
python3 scripts/extract_epub.py book.epub workdir

# 2. Claude 阅读 workdir/chapters/*.txt，写出 fixes.json。

# 3. 应用 OCR 修正，旧用字现代化只列出、不修改。
python3 scripts/apply_fixes.py workdir/manifest.json fixes.json out.epub

# 4. 可选：同意现代化后，从原书重新拆包，确保报告记录相对原文的全部改动。
python3 scripts/extract_epub.py book.epub workdir
python3 scripts/apply_fixes.py workdir/manifest.json fixes.json out.epub --apply-modernization
```

将 `book.epub` 换成实际输入路径。拆包时省略工作目录则使用 `_epubwork`；应用修改时省略输出路径，则在工作目录生成 `<原文件名>_corrected.epub`。

产出包括修正后的 EPUB、`workdir/changes_report.md` 和 `workdir/changes_report.json`。Markdown 报告分别列出已应用的 OCR 修正、现代化建议或结果，以及被跳过的 OCR 修正。

**文件处理行为：** 拆包会替换 `workdir/unpacked`；应用修改会直接改动其中的章节文件，并覆盖输出 EPUB 和报告。源 EPUB 与输出应使用不同路径。对已修改的工作目录重跑时，先前修正的项目可能被报告为找不到；需要完整的新报告时，应先重新提取原书。把 `fixes.json` 放在 `workdir/unpacked` 之外。

### 篇幅与并行

拆包脚本按全书汉字数记录建议代理数：

| 字数 | 建议代理数 |
| --- | --- |
| 少于 50,000 | 1 |
| 50,000–149,999 | 2 |
| 150,000–299,999 | 3 |
| 300,000–599,999 | 5 |
| 600,000 及以上 | 从 5 开始，每增加 200,000 字加 1，上限 10 |

这只是建议，脚本不会自动启动代理。技能只在支持子代理的环境（如 Claude Code / Cowork）且书较大时并行审阅，否则单代理顺序处理。能用一个就不必用多个。

### `fixes.json` 格式

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

应填写所有字段。`chapter_index` 来自 `manifest.json`；`original` 应是能在该章唯一定位的整句或足够长的片段，`corrected` 是修改后的同一片段；`wrong`/`right` 标明具体改动，`reason` 说明理由。省略 `category` 时脚本按 `ocr_error` 处理。并行审阅的结果通过拼接 `fixes` 数组合并；没有错误的章节不要编造改动。

完整流程见[技能说明](../skills/chinese-epub-typo-fixer/SKILL.md)，判断标准和边界情况见 [OCR 判别指南](../skills/chinese-epub-typo-fixer/references/ocr-error-guide.md)。

## 仓库结构

本仓库同时是一个 Claude Code 插件市场，以及该市场收录的单个插件。

```text
chinese-epub-typo-fixer/
├── .claude-plugin/
│   ├── marketplace.json           # 市场名称：kqw8-skills
│   └── plugin.json                # 插件元数据
├── skills/chinese-epub-typo-fixer/
│   ├── SKILL.md                   # 技能说明
│   ├── references/ocr-error-guide.md
│   └── scripts/
│       ├── extract_epub.py        # 拆包与分析
│       ├── apply_fixes.py         # 回写、校验与报告
│       └── lib/epub_utils.py      # 共用 EPUB 工具
├── README.md
├── README.zh-CN.md
├── docs/                         # 双语详细指南
├── LICENSE
└── build_skill.sh                 # 可选的独立打包脚本
```

## 许可证

MIT，见 [LICENSE](../LICENSE)。欢迎 fork 和贡献改进。

这是社区开发的 Claude 技能，并非 Anthropic 官方产品。
