# Myanmar Web Programming Tutor

NLP course MVP: v0.4 book-first Myanmar dataset, QLoRA on Gemma-3-4B-IT, evaluation, and a **Gradio web UI** with edge-tts read-aloud.

**Research write-up:** [REPORT.md](REPORT.md)

## Quick start

```bash
uv sync --extra app --extra train
cp .env.example .env   # edit values here; do not export in the shell
make preflight
make app    # http://0.0.0.0:7860
```

Open the URL, ask a question, enable **Read aloud** for Myanmar speech (edge-tts; needs internet).

You need the LoRA adapter at `outputs/lora_adapter/` (`make train` or copy onto the host). It is gitignored.

### Checklist

- [ ] `uv sync --extra app` and `cp .env.example .env`
- [ ] `outputs/lora_adapter/` on the GPU host
- [ ] Only **one** GPU-heavy process (no `make train` while `make app` runs)
- [ ] `make check` (Python tests + dataset validate)
- [ ] `make smoke` (one GPU generation)

## Other ways to run

| Surface | Command | Notes |
|---------|---------|--------|
| **Gradio UI** | `make app` or `make serve` | Default |
| **API** | `make serve-api` | `POST /v1/chat`, `GET /health` |
| CLI | `make chat` | Interactive |

**API example:**

```bash
curl -s http://localhost:8001/health
curl -s -X POST http://localhost:8001/v1/chat \
  -H 'Content-Type: application/json' \
  -d '{"question":"Fragment ဆိုတာ ဘာလဲ?"}'
```

Optional `TUTOR_API_KEY` for `POST /v1/chat`. `code` field max ~16k characters.

### Troubleshooting GPU memory

If the app fails with **“Some modules are dispatched on the CPU or the disk”**:

1. Run only **one** GPU job at a time.
2. `nvidia-smi` and `make preflight` (~5 GiB free).
3. `fuser -v /dev/nvidia0` and kill stale PIDs.
4. Retry `make app`.

## Setup details

CUDA PyTorch: `pytorch-cu124` index in [`pyproject.toml`](pyproject.toml). Env loaded via [`tutor/config.py`](tutor/config.py).

Dataset-only (no GPU):

```bash
uv sync --extra data
make data
```

If you change [`data/inference_prompt.md`](data/inference_prompt.md), rerun `scripts/build_chat_format.py` and `make train`.

## Makefile targets

| Target | Purpose |
|--------|---------|
| `make app` / `make serve` | Gradio UI |
| `make serve-api` | Litestar API (optional) |
| `make chat` | CLI |
| `make train` / `make eval` | Fine-tune and metrics |
| `make check` | Tests + dataset validate |
