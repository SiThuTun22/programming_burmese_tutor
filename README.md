# Context-Aware Myanmar Language Tutor for Computer Engineering

Burmese tutoring for **computer engineering** (CSE/ECE) and MIIT campus knowledge (curriculum, admission, faculty) via Gemini + RAG.

**Default stack:** `TUTOR_BACKEND=aaa` — LangGraph, Postgres chat sessions, pgvector over `knowledge/`. **UI:** React (`web/`) + Litestar API (`app/`). Set `TUTOR_BACKEND=hybrid` for the legacy local `data/miit/index.json` path (`make chat`).

## Quick start

```bash
make sync
cp .env.example .env    # GEMINI_API_KEYS, JWT_SECRET, DATABASE_URL, TUTOR_CORS_ORIGINS
make db-up && make db-migrate && make db-ingest   # first run (aaa)
make preflight
```

Two terminals:

```bash
make api    # http://127.0.0.1:8001
make web    # http://127.0.0.1:5173
```

Register in the UI, start a chat, ask questions. **Speak** on assistant replies uses edge-tts (spinner while speech prefetch runs). VPN may be required for Gemini/edge-tts.

After editing `data/miit/*.jsonl`: `make db-ingest` (aaa) or `make miit-index` (hybrid).

## Documentation

| For | Read |
|-----|------|
| Client / product | [docs/client/PROJECT_GUIDE.md](docs/client/PROJECT_GUIDE.md) |
| Install & run (step-by-step) | [docs/client/HOW_TO_RUN.md](docs/client/HOW_TO_RUN.md) |
| Developers / API | [docs/client/TECHNICAL_REFERENCE.md](docs/client/TECHNICAL_REFERENCE.md) |
| Maintainer pipeline index | [docs/WORKFLOW.md](docs/WORKFLOW.md) |
| Quick laptop commands | [docs/LAPTOP_SETUP.md](docs/LAPTOP_SETUP.md) |
| Environment variables | [.env.example](.env.example) |

Thesis assets (`docs/NLP_Final_Report.docx`, `docs/*.pptx`) are separate deliverables.

## Surfaces

| Surface | Command | Notes |
|---------|---------|--------|
| **React UI** | `make web` + `make api` | Default product |
| **AAA API** | `make api` | Auth, sessions, messages, speech, documents (upload API only) |
| **Stateless API** | `uv run python -c "from tutor.api import app"` | `POST /v1/chat` — no session history |
| **CLI** | `make chat` | One-shot, no Postgres |

## Frontend (`web/`)

```bash
cd web && npm install && cp .env.example .env
```

Dev proxy: `/api` → port 8001. See [web/README.md](web/README.md).

## Makefile

| Target | Purpose |
|--------|---------|
| `make sync` | `uv sync --extra app --extra aaa` |
| `make db-up` | Docker Postgres + pgvector (port 5435) |
| `make db-migrate` | Alembic migrations |
| `make db-ingest` | Load `knowledge/` into pgvector |
| `make api` / `make serve-api` | Litestar AAA API |
| `make web` | Vite dev server |
| `make preflight` | Keys, backend, Gemini probe |
| `make chat` | CLI tutor |
| `make test` | pytest |
| `make miit-index` | Hybrid `index.json` from JSONL |
| `make smoke-hybrid` | Live hybrid smoke prompts |
| `make eval` | Eval script |
