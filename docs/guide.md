English | [简体中文](guide.zh-CN.md)

[Back to README](../README.md)

# chinese-epub-typo-fixer

A Claude skill for proofreading OCR typos in Chinese EPUB e-books, with optional modernization of archaic character usage. It produces a **corrected EPUB** and a **detailed change report**.

## What it does

For Chinese e-books whose text was produced by image OCR, it handles two categories separately:

1. **Confident OCR typos**, such as visually similar character confusions or simplified/traditional mix-ups (e.g. `莨蓿 → 莨菪`, `傍睌 → 傍晚`), are applied by default, subject to validation.
2. **Archaic-usage modernization**, such as old `象` used where modern Chinese writes `像`, is listed only by default. You decide whether to apply it.

### Principles and limits

- **Extremely conservative: when in doubt, leave it unchanged.** Intended for already-high-quality books with sparse errors. A missed fix is safer than an incorrect one; this is proofreading, not rewriting.
- **Claude finds the errors; scripts do the mechanical work** of unpacking, rewriting, repacking, and reporting. The scripts do not perform image OCR or independently detect typos.
- **Visually similar is not semantically similar.** OCR errors are based on glyph shapes, not synonyms.
- **Judge each occurrence.** Only `象` used as `像` is a modernization candidate; `大象`, `象征`, and `想象` are not. This is not a global find-and-replace.
- **Guardrails skip uncertain replacements.** Ambiguous or missing matches, changes exceeding six differing characters, and inconsistent `original`/`corrected` versus `wrong`/`right` pairs go into the report for review.
- **Local scripts, small dependency set.** The Python scripts use the standard library plus BeautifulSoup and lxml, with no network calls. Claude access and installation have their own connectivity requirements.
- **All user-facing skill output is in Simplified Chinese**, including conversation and reports.

## Installation

### Claude Code plugin (recommended)

Run these slash commands in Claude Code:

```text
/plugin marketplace add kqw8/chinese-epub-typo-fixer
/plugin install chinese-epub-typo-fixer@kqw8-skills
```

The skill registers automatically. Give Claude an `.epub` file and ask it to proofread the book's Chinese OCR text.

The scripts require Python 3 and these packages:

```bash
python3 -m pip install beautifulsoup4 lxml
```

### Manual installation

Copy the skill directory into your Claude skills directory:

```bash
git clone https://github.com/kqw8/chinese-epub-typo-fixer
mkdir -p ~/.claude/skills
cp -r chinese-epub-typo-fixer/skills/chinese-epub-typo-fixer ~/.claude/skills/
```

Optionally, run `bash build_skill.sh` from the repository root to build `chinese-epub-typo-fixer.skill`, a ZIP bundle for distribution. This requires Bash and `zip`; it packages the skill, not its Python dependencies.

## Usage

Give Claude the `.epub` and ask it to proofread. To run the mechanical steps manually, start from the repository root:

```bash
cd skills/chinese-epub-typo-fixer

# 1. Unpack the book and extract chapter text.
python3 scripts/extract_epub.py book.epub workdir

# 2. Claude reads workdir/chapters/*.txt and writes fixes.json.

# 3. Apply OCR fixes; list modernization suggestions without applying them.
python3 scripts/apply_fixes.py workdir/manifest.json fixes.json out.epub

# 4. Optional: after approving modernization, start again from the source book
#    so the report includes all fixes against the original text.
python3 scripts/extract_epub.py book.epub workdir
python3 scripts/apply_fixes.py workdir/manifest.json fixes.json out.epub --apply-modernization
```

Use your actual input path in place of `book.epub`. Extraction defaults to `_epubwork` if the working directory is omitted. Applying fixes defaults to `<source-name>_corrected.epub` in the working directory if the output path is omitted.

Outputs are the corrected EPUB, `workdir/changes_report.md`, and `workdir/changes_report.json`. The Markdown report separates applied OCR fixes, modernization suggestions or results, and skipped OCR fixes.

**File handling:** extraction replaces `workdir/unpacked`; applying fixes modifies those unpacked chapter files and replaces the output EPUB and reports. Keep the source EPUB separate from the output. Rerunning against an already-modified workspace can report previously applied fixes as missing, so re-extract the original first when you need a complete new report. Keep `fixes.json` outside `workdir/unpacked`.

### Book size and parallelism

Extraction records a recommended agent count based on the number of CJK characters:

| Characters | Recommended agents |
| --- | --- |
| Under 50,000 | 1 |
| 50,000–149,999 | 2 |
| 150,000–299,999 | 3 |
| 300,000–599,999 | 5 |
| 600,000 or more | 5, plus 1 per additional 200,000; capped at 10 |

This is a recommendation, not automatic process spawning by the script. The skill uses parallel review only for larger books in environments supporting subagents (such as Claude Code / Cowork); otherwise it reviews sequentially. Prefer one agent when sufficient.

### `fixes.json` format

Chinese text and reasons below are example data:

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

Include all fields. `chapter_index` comes from `manifest.json`; `original` should be a sentence or sufficiently long passage that uniquely identifies the location in that chapter. `corrected` is the same passage after correction, `wrong`/`right` identify the changed text, and `reason` explains the decision. An omitted `category` is treated as `ocr_error`. Combine parallel reviews by concatenating their `fixes` arrays; do not invent changes for chapters without errors.

See the [skill instructions](../skills/chinese-epub-typo-fixer/SKILL.md) and [OCR judgment guide](../skills/chinese-epub-typo-fixer/references/ocr-error-guide.md) for the full workflow and edge cases. Both documents are in Chinese.

## Repository structure

This repository is both a Claude Code plugin marketplace and the single plugin it lists.

```text
chinese-epub-typo-fixer/
├── .claude-plugin/
│   ├── marketplace.json           # Marketplace: kqw8-skills
│   └── plugin.json                # Plugin metadata
├── skills/chinese-epub-typo-fixer/
│   ├── SKILL.md                   # Skill instructions (Chinese)
│   ├── references/ocr-error-guide.md
│   └── scripts/
│       ├── extract_epub.py        # Unpack and analyze
│       ├── apply_fixes.py         # Apply, validate, and report
│       └── lib/epub_utils.py      # Shared EPUB utilities
├── README.md
├── README.zh-CN.md
├── docs/                         # Detailed bilingual guide
├── LICENSE
└── build_skill.sh                 # Optional standalone bundle
```

## License

MIT; see [LICENSE](../LICENSE). Forks and contributions are welcome.

A community Claude skill, not an official Anthropic product.
