#!/usr/bin/env python3
"""Extract DSA candidates from Hlaing Tin Htun articles (same repo as the v2.1 PDF).

The PDF text layer is broken (glyph mapping). Markdown articles are the readable book text.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
LANG_SUFFIX = "မြန်မာဘာသာဖြင့်သာ ရှင်းပြပါ"
MYANMAR_RE = re.compile(r"[\u1000-\u109F]")
ARTICLES_API = (
    "https://api.github.com/repos/HlaingTinHtun/Data-Structure-Algorithm-In-Burmese/"
    "contents/articles?ref=master"
)
LEFTOVER = re.compile(
    r"(http://|https://|bit\.ly|photos credit|Photo attach|flowchart)",
    re.I,
)


def myanmar_ratio(text: str) -> float:
    if not text:
        return 0.0
    compact = text.replace(" ", "")
    return len(MYANMAR_RE.findall(text)) / max(len(compact), 1)


def clean_markdown(text: str) -> str:
    text = re.sub(r"!\[.*?\]\(.*?\)", " ", text)
    text = re.sub(r"\[([^\]]+)\]\(.*?\)", r"\1", text)
    text = re.sub(r"^#+ ", "", text, flags=re.M)
    text = re.sub(r"```.*?```", " ", text, flags=re.S)
    text = re.sub(r"`+", "", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def usable(sent: str) -> bool:
    sent = sent.strip()
    if not sent.endswith("။"):
        return False
    if len(sent) < 55 or len(sent) > 420:
        return False
    if myanmar_ratio(sent) < 0.28:
        return False
    if LEFTOVER.search(sent):
        return False
    if sent.count("#") >= 2:
        return False
    return True


def split_sentences(text: str) -> list[str]:
    parts = []
    for chunk in re.split(r"(?<=။)", text):
        sent = re.sub(r"\s+", " ", chunk).strip()
        if sent:
            parts.append(sent)
    return parts


def main() -> None:
    listing = requests.get(ARTICLES_API, timeout=60)
    listing.raise_for_status()
    files = [row for row in listing.json() if row.get("name", "").endswith(".md")]
    rows = []
    idx = 0
    for meta in sorted(files, key=lambda r: r["name"]):
        url = meta["download_url"]
        name = meta["name"]
        print(f"Fetch {name}...")
        body = requests.get(url, timeout=60)
        body.raise_for_status()
        chapter = Path(name).stem
        cleaned = clean_markdown(body.text)
        sents = [s for s in split_sentences(cleaned) if usable(s)]
        if not sents:
            continue
        paras = sents[:3]
        rows.append(
            {
                "id": f"dsa_cand_{idx:04d}",
                "task_type": "concept_qa",
                "domain": "dsa",
                "instruction": f"{chapter} အကြောင်း Myanmar ဘာသာနဲ့ ရှင်းပြပါ။ {LANG_SUFFIX}",
                "input": "",
                "output": "\n\n".join(paras),
                "source_book": "Data Structure & Algorithm In Burmese",
                "source_chapter": chapter,
                "terms": ["dsa"],
                "split": "train",
                "_extraction_status": "raw",
            }
        )
        idx += 1
        extra = sents[3:6]
        if extra:
            rows.append(
                {
                    "id": f"dsa_cand_{idx:04d}",
                    "task_type": "concept_qa",
                    "domain": "dsa",
                    "instruction": f"{chapter} နောက်ထပ် အကြောင်း Myanmar ဘာသာနဲ့ ရှင်းပြပါ။ {LANG_SUFFIX}",
                    "input": "",
                    "output": "\n\n".join(extra),
                    "source_book": "Data Structure & Algorithm In Burmese",
                    "source_chapter": chapter,
                    "terms": ["dsa"],
                    "split": "train",
                    "_extraction_status": "raw",
                }
            )
            idx += 1

    out = ROOT / "data" / "raw" / "hlaing_dsa_candidates.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"Wrote {len(rows)} -> {out}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(exc, file=sys.stderr)
        sys.exit(1)
