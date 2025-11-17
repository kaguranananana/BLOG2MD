#!/usr/bin/env python3
"""Command line tool to convert blog posts to standalone Markdown drafts."""

from __future__ import annotations

import argparse
import datetime as dt
import os
import random
import re
import sys
import unicodedata

import requests
from bs4 import BeautifulSoup
from markdownify import MarkdownConverter

from extractor import extract_main_content

DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/121.0 Safari/537.36"
)


class FencedMarkdownConverter(MarkdownConverter):
    """Markdown converter that always emits fenced code blocks."""

    def convert_pre(self, el, text, convert_as_inline=False, parent_tags=None):
        code_tag = el.find("code")
        language = _detect_language(code_tag)
        if code_tag is not None:
            code_text = code_tag.get_text("\n")
        else:
            code_text = el.get_text("\n")
        code_text = code_text.strip("\n")
        fence = f"\n```{language}\n{code_text}\n```\n\n"
        return fence


def _detect_language(code_tag) -> str:
    if code_tag is None:
        return ""
    classes = code_tag.get("class", [])
    for cls in classes:
        if cls.startswith("language-"):
            return cls.replace("language-", "").strip()
        if cls.startswith("lang-"):
            return cls.replace("lang-", "").strip()
    return ""


def fetch_html(url: str, timeout: float, user_agent: str) -> str:
    headers = {"User-Agent": user_agent or DEFAULT_UA}
    try:
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise RuntimeError(f"请求失败：{exc}") from exc
    if not response.encoding:
        response.encoding = response.apparent_encoding or "utf-8"
    return response.text


def html_to_markdown(html: str) -> str:
    converter = FencedMarkdownConverter(heading_style="ATX")
    markdown = converter.convert(html)
    return markdown.strip()


def slugify(title: str) -> str:
    if title:
        text = unicodedata.normalize("NFKD", title)
        text = text.encode("ascii", "ignore").decode("ascii")
    else:
        text = ""
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    if text:
        return text
    fallback = f"post-{dt.datetime.utcnow():%Y%m%d-%H%M}{random.randint(100, 999)}"
    return fallback


def write_file(path: str, content: str) -> None:
    directory = os.path.dirname(os.path.abspath(path))
    if directory and not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(content)


def extract_title(soup: BeautifulSoup) -> str:
    if soup.title and soup.title.string:
        return soup.title.string.strip()
    first_h1 = soup.find("h1")
    if first_h1:
        return first_h1.get_text(strip=True)
    return ""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch a blog page and save HTML + Markdown drafts.")
    parser.add_argument("url", help="博客文章的完整 URL")
    parser.add_argument("--html-out", help="正文 HTML 输出路径（默认 <slug>.html）")
    parser.add_argument("--md-out", help="Markdown 输出路径（默认 <slug>.md）")
    parser.add_argument("--timeout", type=float, default=15.0, help="请求超时时间（秒），默认 15")
    parser.add_argument("--user-agent", default=DEFAULT_UA, help="覆盖默认 User-Agent")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        raw_html = fetch_html(args.url, args.timeout, args.user_agent)
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
    soup = BeautifulSoup(raw_html, "lxml")
    title = extract_title(soup)
    slug = slugify(title)
    html_path, md_path = resolve_output_paths(slug, args.html_out, args.md_out)
    try:
        content_tag, method = extract_main_content(soup, args.url)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
    inner_html = content_tag.decode()
    if content_tag.name != "article":
        inner_html = f"<article>\n{inner_html}\n</article>"
    markdown = html_to_markdown(inner_html)
    if title:
        markdown = f"# {title}\n\n{markdown}"
    approx_chars = len(content_tag.get_text(strip=True))
    print(f"[info] Extraction method: {method}")
    print(f"[info] Approximate characters: {approx_chars}")
    try:
        write_file(html_path, inner_html)
        print(f"[info] 正文 HTML 输出：{html_path}")
        write_file(md_path, markdown)
        print(f"[info] Markdown 输出：{md_path}")
    except OSError as exc:
        print(f"Error: 保存文件失败 - {exc}", file=sys.stderr)
        sys.exit(1)
    print("\n使用示例：")
    print(f"  python blog2md.py \"{args.url}\"")
    print("  python blog2md.py \"https://blog.csdn.net/xxxx\" --timeout 20 --md-out output.md")


def resolve_output_paths(slug: str, html_out: str | None, md_out: str | None) -> tuple[str, str]:
    """Determine default output paths under example/<slug>/ if not provided."""
    base_dir = os.path.join("example", slug)
    if html_out:
        html_path = html_out
    else:
        html_path = os.path.join(base_dir, f"{slug}.html")
    if md_out:
        md_path = md_out
    else:
        md_path = os.path.join(base_dir, f"{slug}.md")
    return html_path, md_path


if __name__ == "__main__":
    main()
