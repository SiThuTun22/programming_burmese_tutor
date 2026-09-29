# Quality Control Review Checklist (v0.2 gold)

Use this checklist against `data/GOLD_SPEC.md`. Do **not** promote raw extractor output to processed.

## Per-Sample Review (2–3 minutes each)

### Instruction
- [ ] One clear question a student would type
- [ ] Includes: `မြန်မာဘာသာဖြင့်သာ ရှင်းပြပါ`
- [ ] Not a chopped paragraph + `ဆိုတာ ဘာလဲ?`
- [ ] Not an exercise title (`လေ့ကျင့်ခန်း`)
- [ ] Not truncated mid-word

### Input
- [ ] `concept_qa`: empty
- [ ] `explain_code`: complete code that the output explains
- [ ] `debug_explain`: intentionally broken; fix in output is different

### Output
- [ ] Three-part teaching: definition, 2–6 short steps, one concrete example
- [ ] Ends with `။` (complete sentence)
- [ ] No flowchart / အထက်ပါ / Discord / Telegram / multiple-choice leftovers
- [ ] Terminology matches [TERMINOLOGY.md](../TERMINOLOGY.md)
- [ ] Natural Myanmar (not machine-translated feel)

### Metadata
- [ ] Unique `id`, correct `task_type` / `domain` / `source_book` / `split`

### Reject If
- Vague one-line explanation
- Code and explanation do not match
- Debug “fix” equals the broken input
- Book navigation leftover
- Same Q + same code as another sample

## Batch Review
- [ ] Still 400 samples (320 / 30 / 50)
- [ ] Domain quotas match the dataset card
- [ ] Debug share is real fixes (~10–15%), not padded junk
- [ ] `python3 scripts/validate_dataset.py` passes
- [ ] `python3 scripts/audit_quality.py` reports `failed: 0`

## Reviewer Sign-off Template

```
Reviewer: ___________
Date: ___________
Batch: gold domain ________ samples ________
Approved: __ / __
Rejected: __
Notes: ___________
```
