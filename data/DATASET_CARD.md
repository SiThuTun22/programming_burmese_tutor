# Dataset Card: Myanmar Web Programming Tutor MVP v0.5

## Overview

| Field | Value |
|-------|-------|
| **Name** | myanmar-web-programming-tutor-mvp |
| **Version** | 0.5.0 (catalog-gold spine + Python coverage) |
| **Purpose** | Instruction-tuning for Myanmar programming Q&A and code explanation |
| **Size** | 500 samples (train 406 / val 36 / test 58) |
| **Languages** | Myanmar (primary), code (Python/JS/PHP/SQL/etc.) |
| **License** | Academic use — source books © Ei Maung, Saturngod |

## Quality story

v0.1 was auto-extracted book text. An audit of those 400 rows found widespread leftovers: broken questions, code/explanation mismatch, truncated answers, and fake debug fixes.

v0.2 rewrote every sample to `data/GOLD_SPEC.md` so the audit passed, but many answers were telegraphic (dictionary Myanmar such as `ဒြပ်စင်များ ခြုံခြင်း`).

v0.3 kept the same 400 questions and used book sentences plus template connectors. **v0.4** was book-first (up to two book sentences replacing gold), which mixed leftovers into train answers.

**v0.5** keeps catalog gold as the answer spine. At most one on-topic book sentence may be prepended. Programming Basic quota is 180 (Python/CS basics). Terminology lint still enforces `TERMINOLOGY.md`.

| Gate | v0.1 | v0.2 | v0.3 | v0.4 | v0.5 |
|------|------|------|------|------|------|
| Schema validate | pass | pass | pass | pass | pass |
| Gold audit fail rate | 304/400 | **0/400** | **0/400** | **0/400** | **0/500** (rebuild) |
| Answer voice | messy extract | robotic | book + templates | book-first, glossary | catalog gold + optional garnish |

Rebuild:

```bash
make data
# or: build_book_voice_dataset.py → validate → audit_quality → lint_terminology → build_chat_format
```

Do not run `process_dataset.py` (that rebuilds the broken v0.1 extract). `build_gold_dataset.py` still holds the question/code catalogs; the book-voice script calls it internally.

## Sources

| Book | Author | Samples | Format (source material) |
|------|--------|---------|--------------------------|
| Programming Basic | Saturngod | 180 | HTML |
| Database Basic | Saturngod | 60 | HTML |
| JavaScript - On Point | Ei Maung | 50 | PDF |
| PHP - On Point | Ei Maung | 50 | PDF |
| React - On Point | Ei Maung | 40 | PDF |
| Laravel - On Point | Ei Maung | 40 | PDF |
| API - On Point | Ei Maung | 30 | PDF |
| Bootstrap - On Point | Ei Maung | 25 | PDF |
| Professional Web Developer 2023 | Ei Maung | 25 | PDF |

## Task Distribution

See latest `make data` printout. Last rebuild: 202 concept_qa, 244 explain_code, 54 debug_explain.

## Splits

- **Train:** 406
- **Val:** 36
- **Test:** 58

Per-domain held-out tail (see `SPLIT_QUOTA` in `scripts/gold_samples/common.py`) so test/val are not the same rows as train.

## Quality Controls

1. Gold spec: `data/GOLD_SPEC.md`
2. Hard schema + leftover gates: `scripts/validate_dataset.py`
3. Fail taxonomy audit: `scripts/audit_quality.py` → `data/qc/audit_report.json`
4. Terminology: `data/TERMINOLOGY.md`, `data/STYLE_GUIDE.md`
5. Term lint: `scripts/lint_terminology.py`
6. Human checklist: `data/qc/review_checklist.md`

## Files

```
data/gold/                   # gold rewrite copies
data/processed/train.jsonl
data/processed/val.jsonl
data/processed/test.jsonl
data/processed/chat/         # Chat format for SFT training
```

## Known Limitations (MVP)

- 500 textbook-grade samples (not expert-panel inter-rater gold)
- Target 1,500+ post-MVP
- SFT only — no DPO alignment yet
- 4B LoRA is not a general programming encyclopedia

## Citation

If using this dataset academically, cite source books:

- Ei Maung programming books: https://eimaung.com/
- Saturngod books: https://books.saturngod.net/

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 0.1.0 | MVP week | Initial 400-sample extraction dataset |
| 0.3.0 | 2026-09-10 | Book-voice answers: cleaned on-topic book sentences + spoken Myanmar; audit still 0/400 |
| 0.4.0 | 2026-09-21 | Book-first composition, terminology lint, style guide; retrain recommended |
| 0.5.0 | 2026-09-23 | Catalog gold is spine; Python/CS coverage; 500 samples |
