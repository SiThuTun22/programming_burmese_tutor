# Results Directory

## Files

| File | Description |
|------|-------------|
| `metrics_summary.json` | Before/after automatic metrics |
| `predictions_base.jsonl` | Base model predictions on 50 test prompts |
| `predictions_finetuned.jsonl` | Fine-tuned model predictions |
| `demo_examples.md` | 5 qualitative examples for presentation |

## Important: Replace Stub Predictions

Current predictions use **pipeline validation stubs**:

- **Base:** English template responses (simulates untrained model)
- **Fine-tuned:** Gold reference oracle (upper bound placeholder)

**Before final presentation**, run on Kaggle:

1. `notebooks/01_train_qlora.ipynb` — train adapter
2. `notebooks/02_eval_inference.ipynb` — real inference
3. Copy outputs to this directory
4. Run: `python scripts/evaluate.py`

## Expected Real Metrics (MVP targets)

| Metric | Base Gemma | Fine-tuned target |
|--------|------------|-------------------|
| Myanmar script ratio | ~0.45–0.55 | ≥ 0.75 |
| Mix penalty | ~0.50–0.70 | ≤ 0.20 |
| Heuristic rubric | ~2.0–2.5 | ≥ 3.2 |
| Instruction follow rate | ~0.50–0.60 | ≥ 0.80 |
