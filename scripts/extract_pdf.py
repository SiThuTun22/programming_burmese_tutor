#!/usr/bin/env python3
"""Extract candidate training samples from Ei Maung PDF books."""

from __future__ import annotations

import argparse
import io
import json
import re
import sys
from pathlib import Path

import requests
import yaml

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

ROOT = Path(__file__).resolve().parents[1]
LANG_SUFFIX = "မြန်မာဘာသာဖြင့်သာ ရှင်းပြပါ"
MYANMAR_RE = re.compile(r"[\u1000-\u109F]")
CHAPTER_RE = re.compile(
    r"(?:(?:Chapter|အခန်း|CHAPTER)\s*[\d\.]+[^\n]{0,60})",
    re.IGNORECASE,
)
CODE_LINE_RE = re.compile(
    r"^\s*(def |class |function |const |let |var |import |export |"
    r"<\?php|<?php|SELECT |INSERT |UPDATE |DELETE |CREATE |"
    r"public |private |protected |return |if\s*\(|for\s*\(|while\s*\()"
)


def load_sources() -> dict:
    with open(ROOT / "data" / "sources.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def myanmar_ratio(text: str) -> float:
    if not text:
        return 0.0
    return len(MYANMAR_RE.findall(text)) / max(len(text.replace(" ", "")), 1)


def clean_text(text: str) -> str:
    text = text.replace("\x00", "")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def download_pdf(url: str, cache_dir: Path, book_id: str) -> Path:
    cache_dir.mkdir(parents=True, exist_ok=True)
    path = cache_dir / f"{book_id}.pdf"
    if path.exists() and path.stat().st_size > 1000:
        return path
    print(f"Downloading {url}...")
    response = requests.get(url, timeout=120)
    response.raise_for_status()
    path.write_bytes(response.content)
    return path


def extract_pages(pdf_path: Path) -> list[tuple[int, str]]:
    if fitz is None:
        raise RuntimeError("PyMuPDF (fitz) is required. pip install pymupdf")
    doc = fitz.open(pdf_path)
    pages = []
    for i, page in enumerate(doc):
        text = page.get_text("text")
        if text.strip():
            pages.append((i + 1, clean_text(text)))
    doc.close()
    return pages


def split_into_sections(full_text: str) -> list[tuple[str, str]]:
    matches = list(CHAPTER_RE.finditer(full_text))
    if not matches:
        chunk_size = 2500
        return [(f"Section {i // chunk_size + 1}", full_text[i : i + chunk_size]) for i in range(0, len(full_text), chunk_size)]
    sections = []
    for i, match in enumerate(matches):
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(full_text)
        title = match.group(0).strip()
        body = full_text[start:end].strip()
        sections.append((title, body))
    return sections


def extract_code_blocks(section_text: str) -> list[str]:
    lines = section_text.splitlines()
    blocks: list[str] = []
    current: list[str] = []
    for line in lines:
        if CODE_LINE_RE.match(line) or (current and (line.startswith("    ") or line.startswith("\t"))):
            current.append(line.rstrip())
        else:
            if current:
                block = "\n".join(current).strip()
                if len(block) >= 10:
                    blocks.append(block)
                current = []
    if current:
        block = "\n".join(current).strip()
        if len(block) >= 10:
            blocks.append(block)
    return blocks[:3]


def prose_paragraphs(section_text: str, code_blocks: list[str]) -> list[str]:
    text = section_text
    for block in code_blocks:
        text = text.replace(block, "")
    paragraphs = []
    for para in re.split(r"\n\s*\n", text):
        para = clean_text(para)
        if len(para) < 60:
            continue
        if myanmar_ratio(para) < 0.12:
            continue
        paragraphs.append(para)
    return paragraphs[:6]


def guess_terms(text: str) -> list[str]:
    hints = {
        "javascript": ["javascript", "js", "dom", "function"],
        "php": ["php", "$_", "echo"],
        "react": ["react", "component", "jsx", "hook"],
        "laravel": ["laravel", "eloquent", "blade", "route"],
        "api": ["api", "rest", "endpoint", "json"],
        "bootstrap": ["bootstrap", "grid", "css"],
        "database": ["sql", "database", "query"],
        "dsa": [
            "array",
            "stack",
            "queue",
            "search",
            "sort",
            "tree",
            "hash",
            "linked",
            "heap",
            "big o",
            "bigo",
        ],
    }
    lowered = text.lower()
    found = []
    for term, keys in hints.items():
        if any(k in lowered for k in keys):
            found.append(term)
    return found[:5] if found else ["programming"]


def domain_prefix(domain: str) -> str:
    return {
        "javascript": "js",
        "php": "php",
        "react": "react",
        "laravel": "laravel",
        "api": "api",
        "bootstrap": "bs",
        "pwd": "pwd",
        "dsa": "dsa",
    }.get(domain, "em")


def build_samples(book: dict, sections: list[tuple[str, str]], max_samples: int) -> list[dict]:
    samples: list[dict] = []
    idx = 0
    domain = book["domain"]
    prefix = domain_prefix(domain)

    for section_title, section_text in sections:
        if len(samples) >= max_samples:
            break
        code_blocks = extract_code_blocks(section_text)
        paragraphs = prose_paragraphs(section_text, code_blocks)

        if paragraphs and len(samples) < max_samples:
            title = section_title if myanmar_ratio(section_title) > 0.05 else paragraphs[0][:80]
            samples.append(
                {
                    "id": f"{prefix}_cand_{idx:04d}",
                    "task_type": "concept_qa",
                    "domain": domain,
                    "instruction": f"{title} အကြောင်း Myanmar ဘာသာနဲ့ ရှင်းပြပါ။ {LANG_SUFFIX}",
                    "input": "",
                    "output": "\n\n".join(paragraphs[:3]),
                    "source_book": book["title"],
                    "source_chapter": section_title,
                    "terms": guess_terms("\n".join(paragraphs)),
                    "split": "train",
                    "_extraction_status": "raw",
                }
            )
            idx += 1

        if code_blocks and paragraphs and len(samples) < max_samples:
            samples.append(
                {
                    "id": f"{prefix}_cand_{idx:04d}",
                    "task_type": "explain_code",
                    "domain": domain,
                    "instruction": f"ဒီ code ကို Myanmar ဘာသာနဲ့ အဆင့်လိုက် ရှင်းပြပေးပါ။ {LANG_SUFFIX}",
                    "input": code_blocks[0],
                    "output": "\n\n".join(paragraphs[:4]),
                    "source_book": book["title"],
                    "source_chapter": section_title,
                    "terms": guess_terms(code_blocks[0] + "\n".join(paragraphs)),
                    "split": "train",
                    "_extraction_status": "raw",
                }
            )
            idx += 1

    return samples


def extract_pdf_book(book: dict, cache_dir: Path) -> list[dict]:
    pdf_path = download_pdf(book["url"], cache_dir, book["id"])
    pages = extract_pages(pdf_path)
    full_text = "\n\n".join(text for _, text in pages)
    sections = split_into_sections(full_text)
    return build_samples(book, sections, book["mvp_target_samples"])


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract PDF book candidates")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "data" / "raw")
    parser.add_argument("--cache-dir", type=Path, default=ROOT / "data" / "raw" / "pdf_cache")
    parser.add_argument("--book-id", default="", help="Extract only this sources.yaml id")
    args = parser.parse_args()

    sources = load_sources()
    combined: list[dict] = []
    for book in sources["books"]:
        if book["format"] != "pdf":
            continue
        if args.book_id and book["id"] != args.book_id:
            continue
        print(f"Extracting {book['title']}...")
        try:
            rows = extract_pdf_book(book, args.cache_dir)
        except Exception as exc:
            print(f"ERROR: {book['title']}: {exc}", file=sys.stderr)
            continue
        if book["id"].startswith("eimaung"):
            out_path = args.output_dir / f"eimaung_{book['domain']}_candidates.jsonl"
        else:
            out_path = args.output_dir / f"{book['id']}_candidates.jsonl"
        write_jsonl(out_path, rows)
        print(f"  -> {len(rows)} candidates -> {out_path}")
        if book["id"].startswith("eimaung"):
            combined.extend(rows)

    if combined:
        combined_path = args.output_dir / "eimaung_all_candidates.jsonl"
        write_jsonl(combined_path, combined)
        print(f"Total PDF candidates: {len(combined)}")


if __name__ == "__main__":
    main()
