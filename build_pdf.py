#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Build clean, monochrome PDFs from the three Markdown design documents.

Pipeline:
  Markdown -> HTML (custom parser) -> headless Chrome -> raw PDF
  -> pypdf + reportlab footer overlay -> final PDF

Outputs:
  - 五维投资风险测评_完整文档.pdf
  - 01_问卷本体.pdf
  - 02_设计思路与评分标准.pdf
  - 03_数据结构设计.pdf
"""

from __future__ import annotations

import html
import io
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

ROOT = Path(r"D:\desktop\WENJUAN")
BUILD = ROOT / "build"
CHROME = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")

DOCS = [
    ("01_问卷本体.md", "问卷本体", "五维投资偏好与风险承受能力评估问卷"),
    ("02_设计思路与评分标准.md", "设计思路与评分标准", "设计思路与评分标准"),
    ("03_数据结构设计.md", "数据结构设计", "数据结构设计"),
]

CSS = r"""
@page {
  size: A4;
  margin: 20mm 17mm 22mm 17mm;
}
* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; background: #ffffff; }
body {
  font-family: "Microsoft YaHei", "微软雅黑", "PingFang SC", "SimSun", sans-serif;
  font-size: 10.4pt;
  line-height: 1.78;
  color: #161616;
  -webkit-print-color-adjust: exact;
  print-color-adjust: exact;
}
h1, h2, h3, h4 { page-break-after: avoid; break-after: avoid; }
h1 {
  font-size: 21pt;
  line-height: 1.35;
  margin: 0 0 18px;
  padding-bottom: 9px;
  border-bottom: 1.3pt solid #161616;
  letter-spacing: 0.01em;
}
h2 {
  font-size: 14.5pt;
  line-height: 1.45;
  margin: 27px 0 11px;
  padding-bottom: 4px;
  border-bottom: 0.55pt solid #c4c4c4;
}
h3 { font-size: 12.2pt; line-height: 1.5; margin: 21px 0 8px; }
h4 {
  font-size: 10.8pt;
  line-height: 1.55;
  margin: 17px 0 7px;
  padding-left: 8px;
  border-left: 3pt solid #161616;
}
p { margin: 0 0 9px; text-align: justify; }
strong { font-weight: 700; }
em { font-style: italic; }
a { color: #161616; text-decoration: none; border-bottom: 0.45pt solid #b8b8b8; }
code {
  font-family: "Consolas", "Microsoft YaHei", monospace;
  font-size: 0.9em;
  background: #f2f2f2;
  padding: 0.5px 3.5px;
  border-radius: 2px;
}
pre {
  margin: 7px 0 14px;
  padding: 8px 10px;
  background: #f7f7f7;
  border: 0.45pt solid #d8d8d8;
  font-size: 8pt;
  line-height: 1.52;
  white-space: pre-wrap;
  overflow-wrap: break-word;
  page-break-inside: auto;
}
pre code { background: none; padding: 0; border-radius: 0; font-size: inherit; }
table {
  width: 100%;
  border-collapse: collapse;
  margin: 6px 0 14px;
  font-size: 9.05pt;
  line-height: 1.55;
  page-break-inside: auto;
}
thead { display: table-header-group; }
tr { page-break-inside: avoid; }
th, td {
  border: 0.45pt solid #bdbdbd;
  padding: 4.5px 6px;
  vertical-align: top;
  text-align: left;
}
th { background: #eeeeee; font-weight: 700; }
blockquote {
  margin: 7px 0 14px;
  padding: 6px 10px;
  border-left: 2.4pt solid #a6a6a6;
  background: #fafafa;
  color: #333333;
  font-size: 9.3pt;
  line-height: 1.7;
  page-break-inside: auto;
}
blockquote p { margin: 0; }
ul, ol { margin: 5px 0 12px; padding-left: 21px; }
li { margin: 0 0 4.5px; }
hr { border: 0; border-top: 0.55pt solid #cfcfcf; margin: 19px 0; }

.cover {
  height: 250mm;
  position: relative;
  page-break-after: always;
  break-after: page;
  padding-top: 6mm;
}
.cover-rule { height: 1.3pt; background: #161616; margin-bottom: 8mm; }
.cover-kicker { font-size: 8pt; letter-spacing: 0.24em; color: #606060; }
.cover-title {
  font-size: 33pt;
  line-height: 1.32;
  font-weight: 700;
  margin: 19mm 0 7mm;
  letter-spacing: 0.01em;
}
.cover-sub { font-size: 12.3pt; color: #3d3d3d; letter-spacing: 0.12em; margin: 0 0 32mm; }
.cover-meta { font-size: 9.3pt; line-height: 2.05; color: #333333; }
.cover-meta div {
  width: 82mm;
  border-bottom: 0.4pt solid #d6d6d6;
  padding-bottom: 3px;
  margin-bottom: 4px;
}
.cover-foot {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  border-top: 0.5pt solid #cfcfcf;
  padding-top: 6px;
  font-size: 8pt;
  color: #6a6a6a;
  display: flex;
  justify-content: space-between;
}

.toc { page-break-after: always; break-after: page; padding-top: 1mm; }
.toc-kicker { font-size: 8pt; letter-spacing: 0.24em; color: #606060; }
.toc-title { font-size: 24pt; font-weight: 700; margin: 3mm 0 8mm; letter-spacing: 0.02em; }
.toc-part { margin: 0 0 5.2mm; }
.toc-h1 {
  display: block;
  font-size: 11pt;
  line-height: 1.35;
  font-weight: 700;
  padding: 0 0 3px;
  margin: 0 0 3px;
  border-bottom: 0.55pt solid #bdbdbd;
  color: #161616;
  text-decoration: none;
}
.toc-num { display: inline-block; width: 13mm; color: #8a8a8a; font-weight: 400; }
.toc-h2 {
  display: block;
  font-size: 9.3pt;
  line-height: 1.35;
  padding: 1.2px 0 1.2px 13mm;
  color: #333333;
  text-decoration: none;
  border-bottom: none;
}

.part-label {
  page-break-before: always;
  break-before: page;
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  border-top: 1.3pt solid #161616;
  padding-top: 6px;
  margin: 0 0 10mm;
  font-size: 8pt;
  letter-spacing: 0.16em;
  color: #5a5a5a;
}
.part-label.first { page-break-before: avoid; break-before: auto; }
.part-label .part-name { color: #161616; font-weight: 700; letter-spacing: 0.08em; }
.doc-kicker {
  border-top: 1.3pt solid #161616;
  padding-top: 6px;
  margin-bottom: 7mm;
  font-size: 8pt;
  letter-spacing: 0.12em;
  color: #5f5f5f;
}
"""


def inline(text: str) -> str:
    """Escape and apply the small inline subset used by the documents."""
    text = html.escape(text, quote=False)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)
    return text


def render_table(lines: list[str]) -> str:
    if len(lines) < 2:
        return ""

    def split_cells(row: str) -> list[str]:
        row = row.strip()
        if row.startswith("|"):
            row = row[1:]
        if row.endswith("|"):
            row = row[:-1]
        return [cell.strip() for cell in row.split("|")]

    header = split_cells(lines[0])
    rows = [split_cells(line) for line in lines[2:]]

    out = ["<table>", "<thead><tr>"]
    out.extend(f"<th>{inline(cell)}</th>" for cell in header)
    out.append("</tr></thead><tbody>")
    for row in rows:
        row = (row + [""] * len(header))[: len(header)]
        out.append("<tr>" + "".join(f"<td>{inline(cell)}</td>" for cell in row) + "</tr>")
    out.append("</tbody></table>")
    return "".join(out)


def parse_markdown(md: str, prefix: str) -> tuple[str, list[tuple[int, str, str]]]:
    lines = md.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    out: list[str] = []
    headings: list[tuple[int, str, str]] = []
    i = 0
    hcount = 0

    def is_block_start(s: str) -> bool:
        return bool(
            s.startswith("```")
            or s.startswith("|")
            or s.startswith(">")
            or re.match(r"^#{1,4}\s+", s)
            or re.match(r"^-{3,}\s*$", s)
            or re.match(r"^[-*]\s+", s)
            or re.match(r"^\d+\.\s+", s)
        )

    while i < len(lines):
        raw = lines[i]
        s = raw.strip()
        if not s:
            i += 1
            continue

        # Fenced code block
        if s.startswith("```"):
            lang = s[3:].strip()
            i += 1
            code_lines: list[str] = []
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code_lines.append(lines[i])
                i += 1
            i += 1  # closing fence
            code = html.escape("\n".join(code_lines))
            cls = f' class="language-{html.escape(lang)}"' if lang else ""
            out.append(f"<pre><code{cls}>{code}</code></pre>")
            continue

        # Heading
        m = re.match(r"^(#{1,4})\s+(.*)$", s)
        if m:
            level = len(m.group(1))
            text = m.group(2).strip()
            hcount += 1
            hid = f"{prefix}-h{hcount}"
            headings.append((level, text, hid))
            display = inline(text)
            # Long document titles with a subtitle: break at the colon.
            if level == 1 and len(text) > 24 and "：" in display:
                display = display.replace("：", "：<br>", 1)
            out.append(f'<h{level} id="{hid}">{display}</h{level}>')
            i += 1
            continue

        # Table
        if s.startswith("|"):
            table_lines: list[str] = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                table_lines.append(lines[i].strip())
                i += 1
            out.append(render_table(table_lines))
            continue

        # Blockquote
        if s.startswith(">"):
            bq: list[str] = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                bq.append(re.sub(r"^\s*>\s?", "", lines[i]).rstrip())
                i += 1
            parts: list[str] = []
            for line in bq:
                parts.append("<br>" if line.strip() == "" else inline(line))
            out.append("<blockquote>" + "<br>".join(parts) + "</blockquote>")
            continue

        # Horizontal rule
        if re.match(r"^-{3,}\s*$", s):
            out.append("<hr>")
            i += 1
            continue

        # Unordered list
        if re.match(r"^[-*]\s+", s):
            items: list[str] = []
            while i < len(lines) and re.match(r"^\s*[-*]\s+", lines[i]):
                item = re.sub(r"^\s*[-*]\s+", "", lines[i]).strip()
                items.append(f"<li>{inline(item)}</li>")
                i += 1
            out.append("<ul>" + "".join(items) + "</ul>")
            continue

        # Ordered list
        if re.match(r"^\d+\.\s+", s):
            items = []
            while i < len(lines) and re.match(r"^\s*\d+\.\s+", lines[i]):
                item = re.sub(r"^\s*\d+\.\s+", "", lines[i]).strip()
                items.append(f"<li>{inline(item)}</li>")
                i += 1
            out.append("<ol>" + "".join(items) + "</ol>")
            continue

        # Paragraph
        para = [s]
        i += 1
        while i < len(lines):
            nxt = lines[i].strip()
            if not nxt or is_block_start(nxt):
                break
            para.append(nxt)
            i += 1
        out.append("<p>" + inline(" ".join(para)) + "</p>")

    return "\n".join(out), headings


def page_html(body: str, title: str) -> str:
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>{html.escape(title)}</title>
<style>{CSS}</style>
</head>
<body>
{body}
</body>
</html>
"""


def build_toc(parsed: list[dict]) -> str:
    out = ['<section class="toc">', '<div class="toc-kicker">CONTENTS</div>', '<div class="toc-title">目录</div>']
    for item in parsed:
        out.append('<div class="toc-part">')
        h1 = next((h for h in item["headings"] if h[0] == 1), None)
        if h1:
            out.append(
                f'<a class="toc-h1" href="#{h1[2]}"><span class="toc-num">{item["idx"]:02d}</span>{inline(h1[1])}</a>'
            )
        for level, text, hid in item["headings"]:
            if level == 2:
                out.append(f'<a class="toc-h2" href="#{hid}">{inline(text)}</a>')
        out.append("</div>")
    out.append("</section>")
    return "".join(out)


def chrome_render(html_path: Path, pdf_path: Path) -> None:
    profile = Path(tempfile.mkdtemp(prefix="chrome-", dir=str(BUILD)))
    cmd = [
        str(CHROME),
        "--headless=new",
        "--disable-gpu",
        "--disable-extensions",
        "--hide-scrollbars",
        "--no-pdf-header-footer",
        f"--user-data-dir={profile}",
        "--virtual-time-budget=6000",
        f"--print-to-pdf={pdf_path}",
        html_path.as_uri(),
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        if not wait_for_file(pdf_path):
            raise RuntimeError(
                "Chrome did not produce a PDF.\n"
                f"STDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"
            )
    finally:
        shutil.rmtree(profile, ignore_errors=True)


def wait_for_file(path: Path, timeout: float = 20.0) -> bool:
    start = time.time()
    last_size = -1
    while time.time() - start < timeout:
        if path.exists():
            size = path.stat().st_size
            if size > 0 and size == last_size:
                return True
            last_size = size
        time.sleep(0.25)
    return path.exists() and path.stat().st_size > 0


_CJK_NAME: str | None = None


def register_cjk() -> str:
    global _CJK_NAME
    if _CJK_NAME:
        return _CJK_NAME
    try:
        pdfmetrics.registerFont(TTFont("CJK", r"C:\Windows\Fonts\msyh.ttc", subfontIndex=0))
        _CJK_NAME = "CJK"
    except Exception:
        _CJK_NAME = "Helvetica"
    return _CJK_NAME


def add_footer(
    src: Path,
    dst: Path,
    left_text: str,
    title: str,
    skip_first: bool = False,
    cover_footer: tuple[str, str] | None = None,
) -> None:
    reader = PdfReader(str(src))
    page_count = len(reader.pages)
    width = float(reader.pages[0].mediabox.width)
    height = float(reader.pages[0].mediabox.height)

    packet = io.BytesIO()
    c = canvas.Canvas(packet, pagesize=(width, height))
    font_name = register_cjk()

    for index in range(page_count):
        if index == 0 and cover_footer is not None:
            c.setStrokeGray(0.78)
            c.setLineWidth(0.4)
            c.line(17 * mm, 13.5 * mm, width - 17 * mm, 13.5 * mm)
            c.setFillGray(0.45)
            c.setFont(font_name, 7.6)
            c.drawString(17 * mm, 8.8 * mm, cover_footer[0])
            c.drawRightString(width - 17 * mm, 8.8 * mm, cover_footer[1])
        elif not (skip_first and index == 0):
            c.setStrokeGray(0.78)
            c.setLineWidth(0.4)
            c.line(17 * mm, 13.5 * mm, width - 17 * mm, 13.5 * mm)
            c.setFillGray(0.45)
            c.setFont(font_name, 7.6)
            c.drawString(17 * mm, 8.8 * mm, left_text)
            c.drawRightString(width - 17 * mm, 8.8 * mm, f"第 {index + 1} 页 / 共 {page_count} 页")
        c.showPage()
    c.save()
    packet.seek(0)

    overlay = PdfReader(packet)
    writer = PdfWriter()
    for index, page in enumerate(reader.pages):
        page.merge_page(overlay.pages[index])
        writer.add_page(page)

    writer.add_metadata(
        {
            "/Title": title,
            "/Author": "内部设计文档",
            "/Subject": "五维投资偏好与风险承受能力评估",
            "/Creator": "HTML/CSS + Chrome",
        }
    )
    with open(dst, "wb") as fh:
        writer.write(fh)


def main() -> None:
    if not CHROME.exists():
        raise SystemExit(f"Chrome not found: {CHROME}")
    BUILD.mkdir(parents=True, exist_ok=True)

    parsed: list[dict] = []
    for idx, (filename, part_name, title) in enumerate(DOCS, 1):
        md_path = ROOT / filename
        content, headings = parse_markdown(md_path.read_text(encoding="utf-8"), f"p{idx}")
        parsed.append(
            {
                "idx": idx,
                "filename": filename,
                "part_name": part_name,
                "title": title,
                "content": content,
                "headings": headings,
            }
        )

    cover = """
<section class="cover">
  <div class="cover-rule"></div>
  <div class="cover-kicker">INVESTOR RISK PROFILING · DESIGN DOCUMENT</div>
  <div class="cover-title">五维投资偏好与<br>风险承受能力评估</div>
  <div class="cover-sub">问卷设计 · 评分标准 · 数据结构</div>
  <div class="cover-meta">
    <div>文档版本　1.0.0</div>
    <div>生成日期　2026 年 11 月 10 日</div>
    <div>适用场景　AI 投顾 / 财富管理风险画像</div>
  </div>
</section>
"""

    combined_body = cover + build_toc(parsed)
    for item in parsed:
        first = " first" if item["idx"] == 1 else ""
        combined_body += (
            f'<div class="part-label{first}"><span>PART {item["idx"]:02d}</span>'
            f'<span class="part-name">{item["part_name"]}</span></div>'
        )
        combined_body += item["content"]

    combined_html = BUILD / "combined.html"
    combined_html.write_text(page_html(combined_body, "五维投资偏好与风险承受能力评估"), encoding="utf-8")

    raw_combined = BUILD / "combined_raw.pdf"
    chrome_render(combined_html, raw_combined)
    add_footer(
        raw_combined,
        ROOT / "五维投资风险测评_完整文档.pdf",
        "五维投资风险测评 · V1.0.0",
        "五维投资偏好与风险承受能力评估：完整文档",
        skip_first=True,
        cover_footer=("内部设计文档", "不构成投资建议"),
    )

    for item in parsed:
        body = (
            f'<div class="doc-kicker">五维投资风险测评 · 设计文档 · V1.0.0</div>'
            + item["content"]
        )
        html_path = BUILD / f"doc{item['idx']}.html"
        html_path.write_text(page_html(body, item["title"]), encoding="utf-8")
        raw_pdf = BUILD / f"doc{item['idx']}_raw.pdf"
        chrome_render(html_path, raw_pdf)
        add_footer(
            raw_pdf,
            ROOT / f"{item['idx']:02d}_{item['part_name']}.pdf",
            f"五维投资风险测评 · {item['idx']:02d} {item['part_name']}",
            item["title"],
        )

    print("Generated:")
    for path in sorted(ROOT.glob("*.pdf")):
        print(f"  {path.name}  ({path.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
