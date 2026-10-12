# Computer Engineering Tutor — Technical Reference

Audience: **developers and integrators**. Product overview: [PROJECT_GUIDE.md](PROJECT_GUIDE.md). Installation: [HOW_TO_RUN.md](HOW_TO_RUN.md).

---

## 1. Architecture

```mermaid
flowchart LR
  web[web React Vite] -->|JWT REST| api[app Litestar]
  api --> db[(Postgres pgvector)]
  api --> graph[app/agents LangGraph]
  graph --> gemini[Google Gemini]
  graph --> rag[knowledge chunks]
  api --> tts[edge-tts MP3 cache]
```

| Layer | Technology | Location |
|-------|------------|----------|
| UI | React 19, TypeScript, Tailwind, TanStack Query | `web/` |
| API | Litestar, JWT auth, OpenAPI | `app/` |
| Tutor graph | LangGraph, LangChain Google GenAI | `app/agents/`, `app/ai/` |
| Legacy / shared logic | Router, hybrid engine, Gemini pool | `tutor/` |
| Data | Postgres + pgvector (AAA); optional `index.json` (hybrid) | `app/db/`, `data/miit/` |
| Speech | edge-tts, cached under `data/tts-audio/` | `app/ai/tts.py` |

**Default backend:** `TUTOR_BACKEND=aaa` — product path uses LangGraph + DB RAG.  
**Hybrid:** `TUTOR_BACKEND=hybrid` — `tutor/hybrid.py` + local `data/miit/index.json` (CLI / smoke, not the React UI stack).

---

## 2. Repository map

| Path | Role |
|------|------|
| `app/main.py` | Litestar app, CORS, plugins, startup ingest hook |
| `app/routes/` | HTTP handlers (auth, sessions, messages, documents) |
| `app/services/chat/` | Message exchange, session titles |
| `app/agents/` | LangGraph router nodes, state |
| `app/ai/` | Prompts, tutor reply, TTS, session titles, embeddings |
| `app/knowledge/` | pgvector store and ingest |
| `web/src/` | Chat UI, auth, Speak button, sidebar |
| `tutor/router.py` | Route classification (miit / programming / other) |
| `tutor/faculty_query.py` | Faculty name hints, canonical titles, retrieval expansion |
| `tutor/knowledge.py` | Hybrid retrieval (embed + token fallback) |
| `data/miit/*.jsonl` | Source notes |
| `knowledge/` | AAA ingest layout (symlinks to JSONL) |
| `scripts/serve_aaa_api.py` | Uvicorn entry for `make api` |
| `scripts/aaa_bootstrap.py` | `migrate`, `ingest` |
| `.env` | Secrets and config (see `.env.example`) |

---

## 3. Request flow (AAA API)

1. `POST /api/chat-sessions/{id}/messages` with `{ "content": "..." }`.
2. `send_message_exchange` loads history from Postgres.
3. `generate_tutor_reply` runs `run_tutor_graph` (classify → retrieve → generate).
4. Messages persisted; `schedule_message_speech` prefetches TTS.
5. Response: `user_message`, `assistant_message`, updated `session`.

Routing (summary): rules → thread inherit → Gemini JSON router → out-of-scope short-circuit. Details in `tutor/router.py` and `app/agents/router.py`.

**AAA scope:** MIIT route may require retrieved chunks (`tutor/aaa_scope.py`).

---

## 4. HTTP API

Base URL (dev): `http://127.0.0.1:8001`.  
Interactive OpenAPI UI: **http://127.0.0.1:8001/scalar** (when API is running).

All routes below except `/health` expect `Authorization: Bearer <JWT>` after login.

### Health

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Liveness |

### Auth (`/api/auth`)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/auth/register` | Create account |
| POST | `/api/auth/login` | Returns `access_token` |
| GET | `/api/auth/me` | Current user |

### Chat sessions (`/api/chat-sessions`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/chat-sessions/` | List sessions (recent user activity) |
| POST | `/api/chat-sessions/` | Create session |
| GET | `/api/chat-sessions/{session_id}` | Get one session |
| PATCH | `/api/chat-sessions/{session_id}` | Update `tutor_avatar` / tone |
| DELETE | `/api/chat-sessions/{session_id}` | Delete session and uploads |

### Messages (`/api/chat-sessions`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/chat-sessions/{session_id}/messages` | List messages |
| POST | `/api/chat-sessions/{session_id}/messages` | Ask (returns exchange + session) |
| GET | `/api/chat-sessions/{session_id}/messages/{message_id}/speech/status` | `{ ready, pending }` |
| GET | `/api/chat-sessions/{session_id}/messages/{message_id}/speech` | MP3 bytes |

### Documents (`/api/chat-sessions`) — not in React v1

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/chat-sessions/{session_id}/documents` | List documents |
| GET | `/api/chat-sessions/{session_id}/documents/latest` | Latest document |
| GET | `/api/chat-sessions/{session_id}/documents/{document_id}` | Metadata |
| GET | `/api/chat-sessions/{session_id}/documents/{document_id}/file` | Download file |
| POST | `/api/chat-sessions/{session_id}/documents` | Multipart upload + optional question |

### Stateless tutor (legacy)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/v1/chat` | No session history (`tutor/api.py`) |

---

## 5. Database (AAA)

- **Users** — email, password hash, display name.
- **Chat sessions** — title, tutor_avatar, owner.
- **Chat messages** — role, content, tutor_avatar, optional document link.
- **Knowledge chunks** — pgvector embeddings for RAG.
- **Session documents** — file metadata and storage paths.

Migrations: `migrations/` via `make db-migrate`.

---

## 6. Configuration (summary)

Full template: [`.env.example`](../../.env.example) at repo root.

| Variable | Purpose |
|----------|---------|
| `DATABASE_URL` | Async Postgres URL (default port **5435**) |
| `JWT_SECRET` | Sign login tokens (change in production) |
| `GEMINI_API_KEYS` | Comma-separated API key pool |
| `GEMINI_MODEL` | Chat model (default `gemini-3.1-flash-lite`) |
| `GEMINI_EMBEDDING_MODEL` | Embeddings (default `gemini-embedding-001`) |
| `RAG_TOP_K` | Retrieval top-k |
| `TUTOR_BACKEND` | `aaa` (product) or `hybrid` |
| `TUTOR_API_PORT` | API port (default **8001**) |
| `TUTOR_CORS_ORIGINS` | Allowed browser origins (include Vite URL) |
| `TUTOR_TTS_ENABLED` | Enable speech pipeline |
| `TTS_SKIP_GEMINI_HELPERS` | Skip Gemini spell/name maps for TTS |

Frontend optional: `web/.env` → `VITE_API_BASE_URL` (empty = dev proxy to API).

---

## 7. Security notes

- Passwords hashed (Argon2 via pwdlib).
- JWT in `Authorization` header; React stores token in `localStorage`.
- CORS restricted to `TUTOR_CORS_ORIGINS`.
- Sessions and messages are **per-user** (owner_id checks on all chat routes).
- Do not commit `.env` or API keys.

---

## 8. TTS pipeline

1. `schedule_message_speech(message_id, content, avatar)` after assistant message saved.
2. `prepare_message_speech` — markdown strip, lexicon, optional Gemini helpers, `edge-tts` synthesis.
3. Files: `data/tts-audio/{message_id}.mp3`.
4. `message_speech_pending` / `message_speech_ready` back the status endpoint.

---

## 9. Related documents

- [PROJECT_GUIDE.md](PROJECT_GUIDE.md)  
- [HOW_TO_RUN.md](HOW_TO_RUN.md)  
- [../WORKFLOW.md](../WORKFLOW.md) — deeper pipeline notes for maintainers  
