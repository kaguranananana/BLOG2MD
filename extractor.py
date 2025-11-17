"""Utilities for extracting the main article content from blog pages."""

from __future__ import annotations

import re
from typing import List, Optional, Tuple
from urllib.parse import urlparse

from bs4 import BeautifulSoup, Tag

UNWANTED_TAGS = {
    "header",
    "nav",
    "aside",
    "footer",
    "form",
    "noscript",
    "script",
    "style",
    "iframe",
}

UNWANTED_CLASS_KEYWORDS = {
    "share",
    "comment",
    "recommend",
    "related",
    "sidebar",
    "advert",
    "ad-",
    "reward",
    "meta",
    "profile",
}

DOMAIN_SPECIFIC_SELECTORS: List[Tuple[str, List[str]]] = [
    (
        "csdn.net",
        [
            "div.blog-content-box",
            "div#content_views",
            "div.article_content",
        ],
    ),
]

GENERIC_SELECTORS = [
    "article.post",
    "article.post-block",
    "article.article",
    "div.post-body",
    "div#article-container",
    "div.entry-content",
    "div.post-content",
    "main article",
]


def extract_main_content(soup: BeautifulSoup, url: str) -> Tuple[Tag, str]:
    """Extract the most likely article node from the soup."""
    domain = urlparse(url).netloc.lower()
    selectors = _selectors_for_domain(domain)
    for selector in selectors:
        node = soup.select_one(selector)
        if node and _text_length(node) > 150:
            clean_content(node)
            normalize_code_blocks(node, soup)
            return node, f"selector:{selector}"
    node = _heuristic_pick(soup)
    if node is None:
        raise ValueError("未能定位正文内容，请尝试指定不同的页面或稍后再试。")
    clean_content(node)
    normalize_code_blocks(node, soup)
    return node, "heuristic"


def _selectors_for_domain(domain: str) -> List[str]:
    selectors: List[str] = []
    for suffix, items in DOMAIN_SPECIFIC_SELECTORS:
        if domain.endswith(suffix):
            selectors.extend(items)
    selectors.extend(GENERIC_SELECTORS)
    return selectors


def _heuristic_pick(soup: BeautifulSoup) -> Optional[Tag]:
    for tag in soup.find_all(list(UNWANTED_TAGS)):
        tag.decompose()
    candidates: List[Tuple[int, Tag]] = []
    for node in soup.find_all(["article", "div", "main"]):
        if not isinstance(node, Tag):
            continue
        if _looks_like_noise(node):
            continue
        score = _score_node(node)
        if score > 0:
            candidates.append((score, node))
    if not candidates:
        return None
    candidates.sort(key=lambda item: item[0], reverse=True)
    best_score, best_node = candidates[0]
    return best_node if best_score >= 200 else None


def _looks_like_noise(node: Tag) -> bool:
    class_attr = " ".join(node.get("class", [])).lower()
    if any(keyword in class_attr for keyword in UNWANTED_CLASS_KEYWORDS):
        return True
    if node.name in {"ul", "ol"}:
        return True
    return False


def _score_node(node: Tag) -> int:
    text_len = _text_length(node)
    paragraphs = len(node.find_all("p"))
    headings = len(node.find_all(re.compile(r"h[1-6]")))
    return text_len + paragraphs * 50 + headings * 30


def _text_length(node: Tag) -> int:
    text = node.get_text(separator=" ", strip=True)
    return len(text)


def clean_content(node: Tag) -> None:
    """Remove unwanted sections like share buttons or recommendation panels."""
    for tag in node.find_all(list(UNWANTED_TAGS)):
        tag.decompose()
    for el in node.find_all(True):
        classes = " ".join(el.get("class", [])).lower()
        if any(keyword in classes for keyword in UNWANTED_CLASS_KEYWORDS):
            el.decompose()
            continue
        if el.name in {"div", "span"} and not el.get_text(strip=True) and not el.find("img"):
            el.decompose()


def normalize_code_blocks(node: Tag, soup: BeautifulSoup) -> None:
    """Ensure highlight blocks collapse to <pre><code>."""
    for wrapper in node.select(".highlight, .codeblock"):
        for gutter in wrapper.select(".gutter"):
            gutter.decompose()
        language = _detect_language_class(wrapper)
        code_section = wrapper.select_one(".code") or wrapper
        text = _extract_code_text(code_section)
        text = _clean_code_text(text)
        pre_tag = soup.new_tag("pre")
        code_tag = soup.new_tag("code")
        if language:
            code_tag["class"] = [f"language-{language}"]
        code_tag.string = text
        pre_tag.append(code_tag)
        wrapper.clear()
        wrapper.append(pre_tag)
    for pre in node.find_all("pre"):
        code = pre.find("code")
        if code is None:
            code = soup.new_tag("code")
            code.string = _clean_code_text(_extract_code_text(pre))
            pre.clear()
            pre.append(code)
        else:
            code.string = _clean_code_text(_extract_code_text(code))


def _detect_language_class(wrapper: Tag) -> str:
    classes = wrapper.get("class", [])
    for cls in classes:
        if cls.startswith("language-"):
            return cls.replace("language-", "")
        if cls.startswith("lang-"):
            return cls.replace("lang-", "")
    return ""


def _clean_code_text(text: str) -> str:
    lines = [line.rstrip() for line in text.splitlines()]
    return "\n".join(lines).strip("\n")


def _extract_code_text(section: Tag) -> str:
    """Extract code lines while respecting highlight structures."""
    for br in section.find_all("br"):
        br.replace_with("\n")
    line_nodes = section.select(".line")
    if line_nodes:
        lines = []
        for line in line_nodes:
            line_text = line.get_text("", strip=False)
            lines.append(line_text)
        return "\n".join(lines)
    return section.get_text("", strip=False)
