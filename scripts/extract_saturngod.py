#!/usr/bin/env python3
"""Extract candidate training samples from Saturngod HTML books."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from urllib.parse import urljoin

import requests
import yaml
from bs4 import BeautifulSoup, NavigableString, Tag

ROOT = Path(__file__).resolve().parents[1]
LANG_SUFFIX = "မြန်မာဘာသာဖြင့်သာ ရှင်းပြပါ"

MYANMAR_RE = re.compile(r"[\u1000-\u109F]")
CODE_KEYWORDS = (
    "print(",
    "def ",
    "class ",
    "SELECT ",
    "INSERT ",
    "UPDATE ",
    "DELETE ",
    "CREATE ",
    "function ",
    "const ",
    "let ",
    "var ",
    "<?php",
    "<script",
    "import ",
)


def load_sources() -> dict:
    with open(ROOT / "data" / "sources.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def fetch_html(url: str) -> str:
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    return response.text


def myanmar_ratio(text: str) -> float:
    if not text:
        return 0.0
    myanmar_count = len(MYANMAR_RE.findall(text))
    return myanmar_count / max(len(text.replace(" ", "")), 1)


def clean_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    return text


def extract_article(soup: BeautifulSoup) -> Tag | None:
    article = soup.find("article", class_="reading-area")
    if article:
        return article
    return soup.find("article")


def iter_blocks(article: Tag):
    """Yield sequential content blocks from article."""
    for child in article.children:
        if isinstance(child, NavigableString):
            text = clean_text(str(child))
            if text:
                yield "text", text
            continue
        if not isinstance(child, Tag):
            continue
        name = child.name
        if name in {"h1", "h2", "h3"}:
            yield "heading", clean_text(child.get_text(" ", strip=True))
        elif name == "pre":
            code = child.get_text("\n", strip=False).strip()
            if code:
                yield "code", code
        elif name == "p":
            text = clean_text(child.get_text(" ", strip=True))
            if text and not text.startswith("http"):
                yield "text", text
        elif name in {"ul", "ol"}:
            for li in child.find_all("li", recursive=False):
                text = clean_text(li.get_text(" ", strip=True))
                if text:
                    yield "text", f"- {text}"


def sectionize(blocks: list[tuple[str, str]]) -> list[dict]:
    sections: list[dict] = []
    current = {"title": "Introduction", "paragraphs": [], "codes": []}

    for kind, value in blocks:
        if kind == "heading":
            if current["paragraphs"] or current["codes"]:
                sections.append(current)
            current = {"title": value, "paragraphs": [], "codes": []}
        elif kind == "code":
            current["codes"].append(value)
        else:
            current["paragraphs"].append(value)

    if current["paragraphs"] or current["codes"]:
        sections.append(current)
    return sections


def guess_terms(text: str) -> list[str]:
    lowered = text.lower()
    terms = []
    mapping = {
        "variable": ["variable", "ကြေညာ"],
        "function": ["function", "def ", "function("],
        "loop": ["loop", "for ", "while "],
        "array": ["array", "list", "စာရင်း"],
        "database": ["database", "ဒေတာဘေ့စ်"],
        "table": ["table", "ဇယား"],
        "query": ["query", "sql"],
        "class": ["class "],
        "string": ["string", "စာသား"],
        "integer": ["integer", "ကိန်းပြည့်"],
    }
    for term, hints in mapping.items():
        if any(h in lowered or h in text for h in hints):
            terms.append(term)
    return terms[:5] if terms else ["programming"]


def make_concept_sample(
    *,
    section: dict,
    book: dict,
    chapter: str,
    idx: int,
) -> dict | None:
    paragraphs = [p for p in section["paragraphs"] if myanmar_ratio(p) >= 0.15]
    if len(paragraphs) < 1:
        return None
    title = section["title"]
    if myanmar_ratio(title) < 0.1 and paragraphs:
        title = paragraphs[0][:80]
    output = "\n\n".join(paragraphs[:4])
    if len(output) < 80:
        return None
    domain = book["domain"]
    prefix = {"programming_basic": "pb", "database": "db"}.get(domain, "sg")
    return {
        "id": f"{prefix}_cand_{idx:04d}",
        "task_type": "concept_qa",
        "domain": domain,
        "instruction": f"{title} ဆိုတာ ဘာလဲ? {LANG_SUFFIX}",
        "input": "",
        "output": output,
        "source_book": book["title"],
        "source_chapter": chapter,
        "terms": guess_terms(output),
        "split": "train",
        "_extraction_status": "raw",
    }


def make_explain_sample(
    *,
    section: dict,
    book: dict,
    chapter: str,
    idx: int,
) -> dict | None:
    if not section["codes"]:
        return None
    code = section["codes"][0]
    paragraphs = [p for p in section["paragraphs"] if myanmar_ratio(p) >= 0.1]
    if not paragraphs:
        return None
    output = "\n\n".join(paragraphs[:5])
    if len(output) < 60:
        return None
    domain = book["domain"]
    prefix = {"programming_basic": "pb", "database": "db"}.get(domain, "sg")
    return {
        "id": f"{prefix}_cand_{idx:04d}",
        "task_type": "explain_code",
        "domain": domain,
        "instruction": f"ဒီ code ကို Myanmar ဘာသာနဲ့ အဆင့်လိုက် ရှင်းပြပေးပါ။ {LANG_SUFFIX}",
        "input": code,
        "output": output,
        "source_book": book["title"],
        "source_chapter": chapter,
        "terms": guess_terms(output + " " + code),
        "split": "train",
        "_extraction_status": "raw",
    }


def make_debug_sample(
    *,
    section: dict,
    book: dict,
    chapter: str,
    idx: int,
) -> dict | None:
    if not section["codes"]:
        return None
    code = section["codes"][0]
    if "print(" not in code and "def " not in code and "SELECT" not in code.upper():
        return None
    broken = code
    bug_note = ""
    if "print(" in code and '"' in code:
        broken = code.replace('"', "'", 1) if '"' in code else code + "\n# missing quote"
        bug_note = "string quote မမှန်ခြင်း"
    elif "def " in code and ":" not in code:
        broken = code + "\n    pass"
        bug_note = "function body မှာ syntax မပြည့်စုံခြင်း"
    elif "SELECT" in code.upper() and "FROM" not in code.upper():
        broken = code + " users"
        bug_note = "SQL statement မပြည့်စုံခြင်း"
    else:
        return None
    paragraphs = [p for p in section["paragraphs"] if myanmar_ratio(p) >= 0.1]
    context = paragraphs[0] if paragraphs else "code မှာ error ဖြစ်နိုင်ပါတယ်။"
    output = (
        f"ဒီ code မှာ {bug_note} ကြောင့် error ဖြစ်နိုင်ပါတယ်။\n\n"
        f"{context}\n\n"
        f"မှန်ကန်သော code:\n{broken if broken != code else code}"
    )
    domain = book["domain"]
    prefix = {"programming_basic": "pb", "database": "db"}.get(domain, "sg")
    return {
        "id": f"{prefix}_cand_{idx:04d}",
        "task_type": "debug_explain",
        "domain": domain,
        "instruction": f"ဒီ code မှာ ဘာမှားနေလဲ Myanmar ဘာသာနဲ့ ရှင်းပြပြီး မှန်အောင် ပြင်ပေးပါ။ {LANG_SUFFIX}",
        "input": broken,
        "output": output,
        "source_book": book["title"],
        "source_chapter": chapter,
        "terms": guess_terms(output + " " + code),
        "split": "train",
        "_extraction_status": "raw",
    }


def chapter_urls(book: dict) -> list[tuple[str, str]]:
    base = book["base_url"]
    urls: list[tuple[str, str]] = []
    intro_pages = book.get("intro_pages") or []
    for page in intro_pages:
        urls.append((page.replace(".html", ""), urljoin(base, page)))
    start, end = book.get("chapter_range", [1, 1])
    pattern = book.get("chapter_pattern", "Chapter{num:02d}.html")
    for num in range(start, end + 1):
        if "{num:02d}" in pattern:
            fname = pattern.format(num=num)
        else:
            fname = pattern.format(num=num)
        chapter_name = fname.replace(".html", "")
        urls.append((chapter_name, urljoin(base, fname)))
    if book["id"] == "saturngod_programming_basic":
        urls = []
        for num in range(1, 19):
            fname = f"_pb{num}.html"
            urls.append((f"pb{num}", urljoin(base, fname)))
    return urls


def extract_book(book: dict, max_samples: int) -> list[dict]:
    samples: list[dict] = []
    idx = 0
    for chapter_name, url in chapter_urls(book):
        try:
            html = fetch_html(url)
        except requests.RequestException as exc:
            print(f"WARN: skip {url}: {exc}", file=sys.stderr)
            continue
        soup = BeautifulSoup(html, "html.parser")
        article = extract_article(soup)
        if not article:
            continue
        blocks = list(iter_blocks(article))
        sections = sectionize(blocks)
        chapter_label = chapter_name
        h1 = article.find("h1")
        if h1:
            chapter_label = clean_text(h1.get_text())

        for section in sections:
            if len(samples) >= max_samples:
                return samples
            candidates = [
                make_explain_sample(section=section, book=book, chapter=chapter_label, idx=idx),
                make_concept_sample(section=section, book=book, chapter=chapter_label, idx=idx + 1),
                make_debug_sample(section=section, book=book, chapter=chapter_label, idx=idx + 2),
            ]
            for cand in candidates:
                if cand and len(samples) < max_samples:
                    samples.append(cand)
                    idx += 1
    return samples


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract Saturngod HTML book candidates")
    parser.add_argument("--output", type=Path, default=ROOT / "data" / "raw" / "saturngod_candidates.jsonl")
    args = parser.parse_args()

    sources = load_sources()
    all_samples: list[dict] = []
    for book in sources["books"]:
        if book["format"] != "html":
            continue
        print(f"Extracting {book['title']}...")
        rows = extract_book(book, book["mvp_target_samples"])
        print(f"  -> {len(rows)} candidates")
        all_samples.extend(rows)

    write_jsonl(args.output, all_samples)
    print(f"Wrote {len(all_samples)} candidates to {args.output}")


if __name__ == "__main__":
    main()
