# Book-Grounded Instruction Tuning for a Myanmar Web Programming Tutor

**NLP course research report**  
**September 2026**

---

## Abstract

We construct a Myanmar-language programming tutor from nine locally authored books (Ei Maung; Saturngod). The main contribution is the data, not a new architecture. Automatic extraction produced 400 schema-valid samples of which 304 failed a pedagogical audit. We wrote a gold specification, rebuilt answers in spoken book Myanmar (v0.3), then **v0.4** book-first composition. **v0.5** keeps catalog gold as the spine, expands Programming Basic (including `Python ဆိုတာ ဘာလဲ?`), and stops leftover book sentences from replacing correct answers.

We fine-tuned Gemma-3-4B-IT with 4-bit QLoRA on **406** training examples and evaluated greedy generation on **58** held-out prompts. **v0.5 SFT beats the same-run base** on language-compliance proxies: Myanmar-script ratio 0.657 → 0.698, mix penalty 0.537 → 0.492, heuristic rubric 4.09 → 4.23. Instruction follow is 1.0; layout **တစ်တန်း** misuse is 0/28 on `explain_code`. The 0.75 script and 0.20 mix targets are still not met. Smoke answers for Python are on-topic; some prompts still loop or misstate details.

---

## 1. Introduction

Large language models are widely used as programming assistants, yet Myanmar learners often receive English or mixed-script explanations. High-quality pedagogy already exists in local books covering JavaScript, PHP, Laravel, React, SQL, HTTP APIs, and Bootstrap. Those books are not an instruction-tuning corpus.

This study asks:

1. Does a curated book dataset change Myanmar explanation behaviour relative to the same base checkpoint?
2. On held-out book prompts, do script purity, mixing, and terminology improve?
3. How should book-domain supervised fine-tuning (SFT) be positioned against general Burmese coding models?

Success for this course is a defensible dataset, a completed fine-tune, and an honest before/after evaluation.

---

## 2. Related work

**Burmese-Coder-4B** (Nyein Naing) fine-tunes Gemma-3 4B with SFT and DPO on Python/MBPP-style tasks. Published figures include Pass@1 62.0%, an LLM rubric of 3.779, and mix penalty 0.02. It does not use the Ei Maung / Saturngod web stack.

**SEA-LION** provides strong general Myanmar modelling without programming-book supervision.

**This work** uses the same model family as Burmese-Coder-4B so that any change is attributable to our data. Coverage is web-development pedagogy and book-style, step-by-step Myanmar. Alignment (DPO) and Pass@1 are out of scope. The systems are complementary, not duplicates.

---

## 3. Data

### Sources

Nine books, academic use only (do not redistribute extracted text without permission).

| Domain | Book | Author | *n* |
|--------|------|--------|----:|
| programming_basic | Programming Basic | Saturngod | 180 |
| database | Database Basic | Saturngod | 60 |
| javascript | JavaScript — On Point | Ei Maung | 50 |
| php | PHP — On Point | Ei Maung | 50 |
| react | React — On Point | Ei Maung | 40 |
| laravel | Laravel — On Point | Ei Maung | 40 |
| api | API — On Point | Ei Maung | 30 |
| bootstrap | Bootstrap — On Point | Ei Maung | 25 |
| pwd | Professional Web Developer 2023 | Ei Maung | 25 |
| **Total** | | | **500** |

### Extraction failure and gold rewrite

Version 0.1 used HTML/PDF extractors. A fail taxonomy found **304/400** unusable rows: glued fragment questions, code that did not match the explanation, truncated sentences, book leftovers (flowcharts, Discord, multiple-choice letters), and debug “fixes” identical to the broken input.

Version 0.2 rewrites every sample so the audit can pass. Each item is a student question containing `မြန်မာဘာသာဖြင့်သာ ရှင်းပြပါ`; concept questions have empty code input; explain-code items attach the code they describe; debug items include a real correction distinct from the broken input. After rewrite, the audit fail rate is **0/400**. Those answers were still too short and dictionary-like (for example `ဒြပ်စင်များ ခြုံခြင်း` for React Fragment).

Version 0.3 keeps the same 400 questions, code, splits, and audit gates. Answers are rebuilt from cleaned on-topic sentences in the book extracts (`data/raw/*_candidates.jsonl`), with spoken connectors when a clean book sentence is missing.

**Version 0.5** (current gold) keeps **catalog gold as the spine**. Book-first v0.4 could replace a correct 3-part answer with two leftover book sentences. v0.5 prepends at most one on-topic book sentence. Programming Basic is **180** rows (Python and CS basics, including `Python ဆိုတာ ဘာလဲ?`). Audit rejects debug leftovers in concept/explain answers and requires identifier overlap for `explain_code`. `data/TERMINOLOGY.md` and `data/STYLE_GUIDE.md` still apply.

Task mix: 202 concept, 244 explain-code, 54 debug.

### Splits

Per-domain held-out tails: **406 train / 36 validation / 58 test**. Test prompts are never used for gradient updates.

---

## 4. Method

**Model.** Gemma-3-4B-IT. The official Hugging Face repository was gated for this account; we used `unsloth/gemma-3-4b-it` (same architecture and instruction checkpoint).

**Fine-tuning.** 4-bit QLoRA SFT. LoRA rank **16**, α **32** (8 GB headroom with longer user turns), dropout 0.05, `adamw_bnb_8bit`, targeting attention and MLP projections. Learning rate \(2 \times 10^{-4}\) with cosine decay. Loss is computed on assistant tokens only. Effective batch size 8, maximum length 1024, seed 42. Precision is fp16 (Quadro P4000, Pascal).

**SFT user turns (prompt-aligned).** Chat JSONL and inference both append the generalist guide from [`data/inference_prompt.md`](data/inference_prompt.md) via [`tutor/prompts.py`](tutor/prompts.py) when `TUTOR_STYLE_GUIDE=true` (default).

**Selection (v0.5 run).** Validation `eval_loss` logged 1.879 then **1.653** at epoch 3. Trainer stopped at **epoch 3** (153 steps; default 4). Wall-clock ~85 minutes on 8 GB VRAM.

**Evaluation.** Greedy decoding on the **58** test prompts, at most **384** new tokens. User prompts match SFT (Myanmar suffix + inference guide). Metrics, with fenced code removed:

| Metric | Meaning | Better | Pre-registered target |
|--------|---------|--------|------------------------|
| Myanmar-script ratio | Share of Myanmar Unicode | Higher | ≥ 0.75 |
| Mix penalty | English word density outside code | Lower | ≤ 0.20 |
| Heuristic rubric (1–5) | Fluency, length, overlap with gold | Higher | ≥ 3.2 |
| Instruction follow rate | Fraction with Myanmar ratio ≥ 0.25 | Higher | ≥ 0.80 |
| `explain_code` term misuse | `တစ်တန်း` outside layout context | Lower | 0 on code tasks |

These are language-compliance scores. They are not classification accuracy and not Pass@k.

**Release application.** Gradio UI ([`scripts/serve_gradio.py`](scripts/serve_gradio.py)) with edge-tts read-aloud; optional Litestar API ([`scripts/serve_api.py`](scripts/serve_api.py)); CLI ([`scripts/chat.py`](scripts/chat.py)). All inference uses [`tutor/`](tutor/) so prompts match batch eval.

---

## 5. Results

### Automatic scores (*n* = 58, v0.5 adapter)

| Metric | Base | Fine-tuned | Δ | Target met (FT) |
|--------|------:|----------:|--:|-----------------|
| Myanmar-script ratio | 0.6570 | 0.6983 | +0.0413 | No (≥ 0.75) |
| Mix penalty | 0.5368 | 0.4924 | −0.0444 | No (≤ 0.20) |
| Heuristic rubric | 4.087 | 4.227 | +0.140 | Yes (≥ 3.2) |
| Instruction follow | 1.000 | 1.000 | 0 | Yes |
| Term **တစ်တန်း** misuse (all) | 0 | 0 | 0 | Yes |
| Term misuse on `explain_code` | — | **0 / 28** | — | Yes |

Unlike v0.4, this adapter **improves every automatic score versus its own base run** on the expanded test set. Mix penalty is still above the 0.20 target because English API words remain in Myanmar explanations.

### Qualitative pattern

Smoke ([`results/smoke_quality.json`](results/smoke_quality.json)): `Python ဆိုတာ ဘာလဲ?` is a programming-language definition with a `print("Hello")` example, not a two-word stutter. Input/print explain-code stays on the snippet. Failures still happen: Variable can **repeat** the same paragraph; list vs dict wrongly calls dict immutable; one class answer mixed a Chinese character. The 4B LoRA is not a general programming encyclopedia.

### Research questions

Catalog-spine v0.5 gold plus a **programming (not web-only) inference guide** yields a small, honest gain over base on script, mix, and rubric. Terminology lint on `explain_code` preds stays at 0/28. Human spot checks and TTS remain the practical bar.

---

## 6. Limitations

The gold set is still small (500 rows; 406 for SFT). Optional book garnish remains heterogeneous; greedy decoding can loop. There is no human panel and no Pass@1. Official Gemma weights were gated. Source books remain copyrighted; this corpus is for academic use only.

---

## 7. Conclusion

We deliver **dataset v0.5** (catalog-gold spine, Python/CS coverage, terminology lint, inference style guide), a QLoRA adapter, and a before/after evaluation on **58** held-out prompts. Fine-tuned **beats base** on script ratio, mix penalty, and heuristic rubric; **တစ်တန်း** misuse on `explain_code` is **0/28**. Pre-registered script/mix targets are still unmet. Next steps: stop greedy loops, more reviewed rows, optional DPO, and human rubric + TTS review.

---

## References

Ei Maung. *On Point* programming books. https://eimaung.com/

Nyein Naing, W. Y. *Burmese-Coder-4B: Fine-Tuning a Small Language Model for Burmese Coding*. https://huggingface.co/WYNN747/burmese-coder-4b

Saturngod. *Programming Basic*; *Database Basic*. https://books.saturngod.net/
