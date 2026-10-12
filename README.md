# Context-Aware Myanmar Language Tutor for Computer Engineering

Burmese answers for **computer-engineering** (CSE/ECE) subject questions and coding via Gemini, plus MIIT notes (curriculum, admission, faculty, campus) via RAG. Default backend **`aaa`** uses LangGraph + pgvector (`knowledge/`). Set `TUTOR_BACKEND=hybrid` for the legacy local `index.json` path.

## Quick start

```bash
make sync
cp .env.example .env   # GEMINI_API_KEYS, DATABASE_URL, JWT_SECRET, TUTOR_CORS_ORIGINS
make db-up && make db-migrate && make db-ingest   # first run
make preflight
```

Run the stack in **two terminals**:

```bash
make api    # Litestar AAA API → http://127.0.0.1:8001
make web    # React UI → http://127.0.0.1:5173
```

Register an account in the UI, start a chat, and ask questions. Use **Speak** on assistant replies for TTS (pause/resume toggles on the same button). Gemini may need a VPN where Google APIs are blocked.

After you edit `data/miit/*.jsonl`, run `make db-ingest` (aaa) or `make miit-index` (hybrid).

Mac setup: [docs/LAPTOP_SETUP.md](docs/LAPTOP_SETUP.md). Ask path: [docs/WORKFLOW.md](docs/WORKFLOW.md).

## Surfaces

| Surface | Command | Notes |
|---------|---------|--------|
| **React UI** | `make web` + `make api` | Default product UI |
| **AAA API** | `make api` / `make serve-api` | Auth, sessions, messages, speech |
| **Stateless API** | `uv run python -c "from tutor.api import app"` | `POST /v1/chat` only (see tutor/api.py) |
| **CLI** | `make chat` | Interactive, no history |

## Frontend (`web/`)

- Vite + React + TypeScript + Tailwind
- `cd web && npm install && cp .env.example .env`
- Dev proxy forwards `/api` and `/health` to port 8001

Production: `cd web && npm run build` → serve `web/dist` (static hosting or future Litestar static mount).

## Makefile targets

| Target | Purpose |
|--------|---------|
| `make api` / `make serve-api` | AAA Litestar API |
| `make web` | React dev server |
| `make app` | Preflight + API (run `make web` separately) |
| `make chat` | CLI |
| `make test` | Python tests |
| `make miit-index` | Hybrid index from JSONL |
| `make db-ingest` | AAA knowledge ingest |
