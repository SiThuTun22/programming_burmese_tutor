# Laptop setup (Mac M2, clone from GitHub)

Use this when you develop on a **MacBook** (or any machine without NVIDIA CUDA) and run inference on a **GPU server** or **Kaggle**.

## What GitHub includes

- Source code, tests, dataset JSONL (`data/gold`, `data/processed`, `data/raw` extracts)
- **Not** in git: `.env`, `.venv`, PDF cache, `outputs/` (LoRA weights), Hugging Face base-model cache

## Clone and develop on Mac (no GPU)

```bash
git clone https://github.com/SiThuTun22/programming_burmese_tutor.git
cd programming_burmese_tutor
uv sync --extra data
cp .env.example .env
make check
```

`make check` runs tests and dataset validation without loading Gemma.

This repo’s tutor app requires **CUDA** ([`tutor/model.py`](../tutor/model.py)). Do not expect `make app` to work on Apple Silicon with 8 GB RAM.

## LoRA adapter (not in GitHub)

Download the fine-tuned adapter into `outputs/lora_adapter/` on any **CUDA** host:

```bash
uv sync --extra app
cp .env.example .env
# set HF_TOKEN if the Hub repo is private
# set TUTOR_ADAPTER_HF_REPO=SiThuTun22/programming-burmese-tutor-lora
uv run python scripts/download_adapter.py
```

Or train again: `make train` (Kaggle: [`notebooks/01_train_qlora.ipynb`](../notebooks/01_train_qlora.ipynb)).

Upload from a machine that already has `outputs/lora_adapter/` (requires `HF_TOKEN` in `.env`):

```bash
make upload-adapter
# or: uv run python scripts/upload_adapter.py --repo SiThuTun22/programming-burmese-tutor-lora
```

## Live demo from Mac browser (GPU on server)

1. On the GPU server: `make app` (after adapter is present).
2. On the Mac, SSH port-forward:

   ```bash
   ssh -L 7860:localhost:7860 YOUR_USER@YOUR_GPU_HOST
   ```

3. Open **http://localhost:7860** in the browser.

## Kaggle training

1. Push this repo to GitHub (or zip as a Kaggle Dataset).
2. Open [`notebooks/01_train_qlora.ipynb`](../notebooks/01_train_qlora.ipynb) with GPU + Internet.
3. After training, upload `/kaggle/working/lora_adapter` to Hugging Face (`scripts/upload_adapter.py` locally) or attach as a Kaggle Dataset for [`notebooks/02_eval_inference.ipynb`](../notebooks/02_eval_inference.ipynb).

## New CUDA machine checklist

```bash
git clone https://github.com/SiThuTun22/programming_burmese_tutor.git
cd programming_burmese_tutor
uv sync --extra app --extra train
cp .env.example .env
uv run python scripts/download_adapter.py
make preflight
make app
```
