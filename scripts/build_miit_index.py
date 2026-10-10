#!/usr/bin/env python3
"""Embed MIIT JSONL notes and write data/miit/index.json."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tutor.env_bootstrap import load_project_env

load_project_env()

from tutor.config import GEMINI_EMBED_MODEL, MIIT_DIR, MIIT_INDEX_PATH
from tutor.gemini_client import GeminiClient
from tutor.knowledge import clear_miit_caches, index_document_from_rows, load_miit_chunks


def main() -> int:
    chunks = load_miit_chunks(MIIT_DIR)
    if not chunks:
        print(f"No chunks under {MIIT_DIR}", file=sys.stderr)
        return 1

    rows = [
        {"id": chunk.id, "text": chunk.text, "sources": list(chunk.sources)}
        for chunk in chunks
    ]
    texts = [row["text"] for row in rows]

    client = GeminiClient()
    vectors = client.embed(texts)
    document = index_document_from_rows(rows, embed_model=GEMINI_EMBED_MODEL, vectors=vectors)

    MIIT_INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    MIIT_INDEX_PATH.write_text(
        json.dumps(document, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    clear_miit_caches()
    print(f"Wrote {len(rows)} chunks to {MIIT_INDEX_PATH} (model={GEMINI_EMBED_MODEL})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
