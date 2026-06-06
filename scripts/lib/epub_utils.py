#!/usr/bin/env python3
"""
epub_utils.py — EPUB 读写的共享工具。

设计原则：
- 只依赖 Python 标准库 (zipfile, os, re) 和 BeautifulSoup (bs4) / lxml。
  不依赖 ebooklib，所以在任何装了 bs4 的环境里都能跑，可移植性强。
- EPUB 本质是一个 ZIP：mimetype + META-INF/container.xml + 内容文档(XHTML)。
  我们顺着 container.xml -> OPF -> spine 拿到「按阅读顺序排列」的章节文件。
"""

import os
import re
import zipfile
import shutil
import warnings

from bs4 import BeautifulSoup

# 我们刻意用 HTML 解析器读 XHTML（更宽容，能容忍不规范标签，利于提取正文）。
# bs4 会就此发出 XMLParsedAsHTMLWarning，这里主动静音，保持输出干净。
try:
    from bs4 import XMLParsedAsHTMLWarning
    warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)
except Exception:
    pass

# 视为「段落级」的标签：提取纯文本时在它们之后补换行，方便人和模型阅读。
_BLOCK_TAGS = {
    "p", "div", "h1", "h2", "h3", "h4", "h5", "h6",
    "li", "blockquote", "br", "tr", "section", "article",
    "figcaption", "td", "th", "pre",
}


# ---------------------------------------------------------------------------
# 解压 / 重打包
# ---------------------------------------------------------------------------

def unzip_epub(epub_path, dest_dir):
    """把 EPUB 解压到 dest_dir（会先清空 dest_dir）。返回 dest_dir。"""
    if os.path.exists(dest_dir):
        shutil.rmtree(dest_dir)
    os.makedirs(dest_dir, exist_ok=True)
    with zipfile.ZipFile(epub_path, "r") as z:
        z.extractall(dest_dir)
    return dest_dir


def repack_epub(src_dir, out_path):
    """
    把 src_dir 重新打包成合规 EPUB。
    关键规则：mimetype 必须是 ZIP 的第一个条目，且以 STORED(不压缩) 方式写入，
    否则部分阅读器/校验器会拒绝识别。
    """
    if os.path.exists(out_path):
        os.remove(out_path)

    mimetype_path = os.path.join(src_dir, "mimetype")
    with zipfile.ZipFile(out_path, "w") as z:
        # 1) mimetype 先写，且 STORED
        if os.path.exists(mimetype_path):
            z.write(mimetype_path, "mimetype", compress_type=zipfile.ZIP_STORED)
        else:
            z.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)

        # 2) 其余文件按目录遍历写入，全部 DEFLATED
        for root, _dirs, files in os.walk(src_dir):
            for fn in files:
                full = os.path.join(root, fn)
                arc = os.path.relpath(full, src_dir)
                if arc == "mimetype":
                    continue
                z.write(full, arc, compress_type=zipfile.ZIP_DEFLATED)
    return out_path


# ---------------------------------------------------------------------------
# 解析 OPF / spine
# ---------------------------------------------------------------------------

def find_opf_path(epub_dir):
    """读 META-INF/container.xml，返回 OPF 文件的绝对路径。"""
    container = os.path.join(epub_dir, "META-INF", "container.xml")
    with open(container, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f.read(), "xml")
    rootfile = soup.find("rootfile")
    if rootfile is None or not rootfile.get("full-path"):
        raise ValueError("container.xml 中找不到 rootfile/full-path")
    return os.path.join(epub_dir, rootfile["full-path"])


def get_content_documents(epub_dir):
    """
    返回按 spine 阅读顺序排列的内容文档列表，每项是 dict:
      { "id": <manifest id>,
        "href": <相对 OPF 的 href>,
        "abs_path": <磁盘绝对路径>,
        "media_type": <媒体类型> }
    只保留 application/xhtml+xml（正文），跳过封面图片、css 等。
    """
    opf_path = find_opf_path(epub_dir)
    opf_dir = os.path.dirname(opf_path)
    with open(opf_path, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f.read(), "xml")

    # manifest: id -> (href, media_type)
    manifest = {}
    for item in soup.select("manifest > item"):
        iid = item.get("id")
        href = item.get("href")
        mtype = item.get("media-type", "")
        if iid and href:
            manifest[iid] = (href, mtype)

    docs = []
    for itemref in soup.select("spine > itemref"):
        idref = itemref.get("idref")
        if idref in manifest:
            href, mtype = manifest[idref]
            if "xhtml" in mtype or href.lower().endswith((".xhtml", ".html", ".htm")):
                docs.append({
                    "id": idref,
                    "href": href,
                    "abs_path": os.path.normpath(os.path.join(opf_dir, href)),
                    "media_type": mtype,
                })
    return docs


# ---------------------------------------------------------------------------
# 文本提取 / 统计
# ---------------------------------------------------------------------------

def extract_text_from_xhtml(xhtml_str):
    """
    从 XHTML 字符串里提取「可读纯文本」，段落之间用换行分隔。
    只用于给模型阅读 / 统计字数，不用于回写。
    """
    soup = BeautifulSoup(xhtml_str, "lxml")
    # 去掉明显的非正文
    for tag in soup(["script", "style", "head"]):
        tag.decompose()

    body = soup.body if soup.body else soup
    parts = []

    def walk(node):
        for child in node.children:
            name = getattr(child, "name", None)
            if name is None:  # 文本节点
                txt = str(child)
                if txt.strip():
                    parts.append(txt)
            else:
                walk(child)
                if name in _BLOCK_TAGS:
                    parts.append("\n")

    walk(body)
    text = "".join(parts)
    # 规整连续空行/行内多余空白
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n[ \t]+", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


_CJK_RE = re.compile(
    r"[\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff]"  # 常用+扩展A+兼容汉字
)


def count_cjk_chars(text):
    """统计中日韩汉字数量（用于估算篇幅，比 len() 更贴近「字数」）。"""
    return len(_CJK_RE.findall(text))


def recommend_agent_count(total_cjk):
    """
    依据总汉字数给出建议的并行 agent 数。
    原则（与设计讨论一致）：任务很轻，能少则少；只有大书才值得并行。
    单个 agent 上限并行 10。
    """
    if total_cjk < 50_000:
        return 1
    elif total_cjk < 150_000:
        return 2
    elif total_cjk < 300_000:
        return 3
    elif total_cjk < 600_000:
        return 5
    else:
        return min(10, 5 + (total_cjk - 600_000) // 200_000)
