# Context-Aware Myanmar Language Tutor for Computer Engineering

Burmese answers for **computer-engineering** (CSE/ECE) subject questions and coding via Gemini, plus programme notes (curriculum, admission, faculty, campus) via RAG. Institute facts retrieve `data/miit` with **gemini-embedding-001** after `make miit-index`. Biology, general physics, and other non-CE topics are refused.

## Quick start

```bash
uv sync --extra app
cp .env.example .env   # set GEMINI_API_KEY
make miit-index        # embed MIIT notes (needs network + API key)
make preflight
make app    # http://127.0.0.1:7860
```

After you edit `data/miit/*.jsonl`, run `make miit-index` again.

Open the URL and ask a question. Click the ear under a reply to hear it (edge-tts; needs internet). Gemini chat needs a VPN where Google APIs are blocked.

Chats are logged locally to `results/tutor_sessions.jsonl` (gitignored).

Mac setup: [docs/LAPTOP_SETUP.md](docs/LAPTOP_SETUP.md). Step-by-step ask path: [docs/WORKFLOW.md](docs/WORKFLOW.md).

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

## Makefile targets

| Target | Purpose |
|--------|---------|
| `make app` / `make serve` | Gradio UI |
| `make serve-api` | Litestar API |
| `make chat` | CLI |
| `make test` | Python tests |
| `make miit-index` | Build `data/miit/index.json` from JSONL notes |
| `make smoke-hybrid` | 15-prompt Gemini smoke |
| `make eval` | Route Accuracy/F1, Recall@3/MRR, span EM (writes `results/eval_report.json`) |
