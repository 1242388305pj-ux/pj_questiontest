#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Render the AI integration manual to a single PDF."""

import sys
from pathlib import Path

ROOT = Path(r"D:\desktop\WENJUAN")
sys.path.insert(0, str(ROOT))

import build_pdf as b


def main() -> None:
    b.BUILD.mkdir(parents=True, exist_ok=True)
    md = (ROOT / "04_AI对接手册.md").read_text(encoding="utf-8")
    content, _ = b.parse_markdown(md, "manual")
    body = '<div class="doc-kicker">五维投资风险画像 · AI 技术对接手册 · V1.0.0</div>' + content
    html_path = b.BUILD / "manual.html"
    html_path.write_text(
        b.page_html(body, "五维投资风险画像：AI 技术对接手册"),
        encoding="utf-8",
    )
    raw_pdf = b.BUILD / "manual_raw.pdf"
    b.chrome_render(html_path, raw_pdf)
    b.add_footer(
        raw_pdf,
        ROOT / "五维投资风险画像_AI技术对接手册.pdf",
        "五维投资风险画像 · AI 技术对接手册",
        "五维投资风险画像：AI 技术对接手册",
    )
    print("Generated: 五维投资风险画像_AI技术对接手册.pdf")


if __name__ == "__main__":
    main()
