[English](README.md) | 简体中文

# chinese-epub-typo-fixer

一个保守校对中文 EPUB OCR 错别字的 Claude 技能，产出修正后的 EPUB 和逐条改动明细。

## 安装

在 Claude Code 中运行：

```text
/plugin marketplace add kqw8/chinese-epub-typo-fixer
/plugin install chinese-epub-typo-fixer@kqw8-skills
```

脚本需要 Python 3 和两个依赖：

```bash
python3 -m pip install beautifulsoup4 lxml
```

## 使用

将 `.epub` 文件交给 Claude，然后说：

> 帮我校对这本中文书的 OCR 错别字；旧用字现代化只列建议，不修改。

安装后技能自动注册。Claude 审阅文本，脚本负责拆包、应用通过校验的修改、重新打包。
产出包括修正后的 EPUB、`changes_report.md` 和 `changes_report.json`。
对话和报告一律使用简体中文。

## 关键限制

- **拿不准就不改。** 适合高质量、错误稀少的书，不做润色或改写。
- 确信的 OCR 错字通过校验后修改；旧用字现代化默认只列建议，经同意才应用。
- 脚本不执行图片 OCR，也不独立找错字；不确定的修改会跳过，留待人工检查。
- Python 脚本不发起网络请求；Claude 服务和安装过程的联网要求另计。
- **源 EPUB 与输出必须分开。** 拆包会替换 `workdir/unpacked`；
  应用修改会改动拆包后的章节，并覆盖输出 EPUB 和报告。
  需要完整的新报告时先重新提取原书；`fixes.json` 放在 `workdir/unpacked` 之外。

## 详细说明

[使用指南](docs/guide.zh-CN.md) 包含手动安装、脚本命令、默认参数、`fixes.json`、
篇幅与代理数建议及打包方法。[技能说明](skills/chinese-epub-typo-fixer/SKILL.md)
和 [OCR 判别指南](skills/chinese-epub-typo-fixer/references/ocr-error-guide.md) 说明完整审阅流程与判断标准。

## 许可证

MIT，见 [LICENSE](LICENSE)。欢迎 fork 和贡献改进。

这是社区开发的 Claude 技能，并非 Anthropic 官方产品。
