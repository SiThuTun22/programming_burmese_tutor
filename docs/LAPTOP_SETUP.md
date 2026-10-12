# Laptop setup (Mac M2, 8 GB)

The Computer Engineering Tutor is Gemini chat. It does not load a local model. VPN is required for Gemini where Google APIs are blocked.

## What GitHub includes

- Source code, MIIT notes, and tests
- **Not** in git: `.env`, `.venv`, `data/miit/index.json`, demo transcripts in `results/`

## Mac demo

1. Get a free key at [Google AI Studio](https://aistudio.google.com/).
2. `make sync` (installs Gradio + AAA stack: LangGraph, pgvector, async Postgres driver)
3. `cp .env.example .env` and set at least `GEMINI_API_KEYS` (comma-separated). Example:

```
TUTOR_BACKEND=aaa
DATABASE_URL=postgresql+asyncpg://aaa:aaa@localhost:5435/aaa
GEMINI_API_KEYS=your_key,your_second_key
GEMINI_MODEL=gemini-3.1-flash-lite
GEMINI_EMBEDDING_MODEL=gemini-embedding-001
RAG_TOP_K=5
```

4. **AAA (default):** `make db-up` then `make db-migrate && make db-ingest` (Docker; first run only). **Hybrid:** set `TUTOR_BACKEND=hybrid` and `make miit-index`.
5. `make preflight`, then in two terminals: `make api` (port **8001**) and `make web` → **http://localhost:5173**

`make preflight` runs a short Gemini connectivity probe (disable with `GEMINI_PREFLIGHT_PROBE=false`). If you see SSL/connect timeout, turn on VPN first, then retry. Keys should come from Google AI Studio (`AIza…` in `GEMINI_API_KEYS`).

Programming questions use the tutor prompt. MIIT faculty notes use embedding retrieval when similarity is high enough.

Optional: `make smoke-hybrid` (15 prompts; calls the chat API).

Free-tier rate limits apply.
