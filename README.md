English | [简体中文](README.zh-CN.md)

# chinese-epub-typo-fixer

A Claude skill that conservatively proofreads Chinese EPUB OCR typos and produces a corrected EPUB plus a detailed change report.

## Install

Run in Claude Code:

```text
/plugin marketplace add kqw8/chinese-epub-typo-fixer
/plugin install chinese-epub-typo-fixer@kqw8-skills
```

The scripts require Python 3 and two packages:

```bash
python3 -m pip install beautifulsoup4 lxml
```

## Use

Give Claude your `.epub` file and ask:

> 帮我校对这本中文书的 OCR 错别字；旧用字现代化只列建议，不修改。

The skill registers automatically. Claude reviews the text; scripts unpack, apply validated fixes,
and repack the book. Outputs include the corrected EPUB, `changes_report.md`, and `changes_report.json`.
Conversation and reports are in Simplified Chinese.

## Important limits

- **When in doubt, leave it unchanged.** Intended for high-quality books with sparse errors, not rewriting.
- Confident OCR fixes apply after validation; archaic-usage modernization is only listed unless approved.
- Scripts neither perform image OCR nor independently detect typos. Uncertain replacements are skipped for review.
- Python scripts make no network calls; Claude access and installation have their own connectivity requirements.
- **Keep the source EPUB separate from the output.** Extraction replaces `workdir/unpacked`;
  applying fixes changes unpacked chapters and overwrites the output EPUB and reports.
  Re-extract the original for a complete new report; keep `fixes.json` outside `workdir/unpacked`.

## Details

See the [guide](docs/guide.md) for manual installation, script commands, defaults, `fixes.json`,
book-size recommendations, and packaging. The [skill instructions](skills/chinese-epub-typo-fixer/SKILL.md)
and [OCR judgment guide](skills/chinese-epub-typo-fixer/references/ocr-error-guide.md) describe the full review workflow in Chinese.

## License

MIT — see [LICENSE](LICENSE). Forks and contributions are welcome.

A community Claude skill, not an official Anthropic product.
