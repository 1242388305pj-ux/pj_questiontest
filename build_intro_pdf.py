#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Render the concise design overview to a single PDF."""

import sys
from pathlib import Path

ROOT = Path(r"D:\desktop\WENJUAN")
sys.path.insert(0, str(ROOT))

import build_pdf as b


def main() -> None:
    b.BUILD.mkdir(parents=True, exist_ok=True)
    md = (ROOT / "00_设计概览.md").read_text(encoding="utf-8")
    content, _ = b.parse_markdown(md, "intro")
    body = '<div class="doc-kicker">五维投资风险测评 · 设计概览 · V1.0.0</div>' + content
    html_path = b.BUILD / "intro.html"
    html_path.write_text(
        b.page_html(body, "五维投资偏好与风险承受能力评估：设计概览"),
        encoding="utf-8",
    )
    raw_pdf = b.BUILD / "intro_raw.pdf"
    b.chrome_render(html_path, raw_pdf)
    b.add_footer(
        raw_pdf,
        ROOT / "五维投资风险测评_设计概览.pdf",
        "五维投资风险测评 · 设计概览",
        "五维投资偏好与风险承受能力评估：设计概览",
    )
    print("Generated: 五维投资风险测评_设计概览.pdf")


if __name__ == "__main__":
    main()
