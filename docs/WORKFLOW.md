# Working flow (developer index)

**Client documentation (start here for handoff):**

- [docs/client/PROJECT_GUIDE.md](client/PROJECT_GUIDE.md) — product, features, workflow, smoke tests  
- [docs/client/HOW_TO_RUN.md](client/HOW_TO_RUN.md) — step-by-step install and operations  
- [docs/client/TECHNICAL_REFERENCE.md](client/TECHNICAL_REFERENCE.md) — architecture, API, configuration  

Quick laptop install: [LAPTOP_SETUP.md](LAPTOP_SETUP.md).

---

The sections below are a **maintainer’s deep dive** (routing, retrieval, prompts). They overlap the client guides; prefer updating `docs/client/*.md` for client-facing changes, then adjust this file only when you need extra implementation detail.

## Surfaces

| Surface | Command | History / chats | Extra |
|---------|---------|-----------------|-------|
| **React UI** | `make web` + `make api` | Yes. Postgres sessions via [`app/`](../app/) | TTS Speak, theme |
| **AAA HTTP API** | `make serve-api` | Yes (auth + session routes) | Same backend as React |
| **Stateless API** | [`tutor/api.py`](../tutor/api.py) | No | `POST /v1/chat` only |
| **CLI** | `make chat` | No | Optional pasted code |

Default backend **`aaa`**: LangGraph + pgvector (`knowledge/`). **`hybrid`**: local `data/miit/index.json`.

**In scope:** MIIT notes + CSE/ECE. Off-topic → `OUT_OF_SCOPE_ANSWER`. Faculty Myanmar/English via [`tutor/faculty_query.py`](../tutor/faculty_query.py). Document upload API only (no React v1 UI).

---

## Pipeline summary

1. **Setup** — `.env.example`, `make db-up`, `db-migrate`, `db-ingest`, `preflight`, `api` + `web`.  
2. **Index** — AAA: `make db-ingest`; hybrid: `make miit-index`.  
3. **Ask** — `POST .../messages` → LangGraph → Gemini; TTS prefetch.  
4. **Route** — `tutor/router.py` (rules → inherit → LLM router).  
5. **Retrieve** — `tutor/knowledge.py` / pgvector (MIIT only).  
6. **Prompts** — `tutor/prompts.py`, `app/ai/prompts.py`.  
7. **Generate** — `tutor/gemini_client.py`, key pool.  
8. **UI** — sidebar, speech/status, session titles in `app/ai/session_title.py`.

For full narrative and diagrams, see [client/PROJECT_GUIDE.md](client/PROJECT_GUIDE.md) and the original detailed sections in git history or extend this file as needed.
