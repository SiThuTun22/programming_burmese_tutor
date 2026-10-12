# Computer Engineering Tutor — How to Run

Audience: **operators and lab setup**. What the app does: [PROJECT_GUIDE.md](PROJECT_GUIDE.md). API details: [TECHNICAL_REFERENCE.md](TECHNICAL_REFERENCE.md).

---

## 1. Prerequisites

Install before you start:

| Requirement | Notes |
|-------------|--------|
| **Docker Desktop** | For Postgres + pgvector (`make db-up`) |
| **Python 3.12+** | Managed with **[uv](https://docs.astral.sh/uv/)** |
| **Node.js 20+** and **npm** | For `web/` (`make web`) |
| **Google AI Studio API key(s)** | Usually `AIza…`; comma-separate for quota pool |
| **VPN** (if needed) | Where Google Gemini or edge-tts is blocked |

Git clone of this repository on a machine with ~8 GB RAM is sufficient (no local LLM).

---

## 2. First-time setup (AAA + React) — step by step

### Step 1 — Clone and enter the project

```bash
cd /path/to/programming_burmese_tutor
```

### Step 2 — Install Python dependencies

```bash
make sync
```

This runs `uv sync --extra app --extra aaa`.

### Step 3 — Configure environment

```bash
cp .env.example .env
```

Edit `.env` and set at minimum:

1. **`GEMINI_API_KEYS`** — your key(s), comma-separated.  
2. **`JWT_SECRET`** — long random string before any shared/production deploy.  
3. **`DATABASE_URL`** — leave default unless Postgres runs elsewhere:  
   `postgresql+asyncpg://aaa:aaa@localhost:5435/aaa`  
4. **`TUTOR_CORS_ORIGINS`** — must include the web UI origin, e.g.  
   `http://localhost:5173`

Optional: copy frontend env (usually not required for local dev):

```bash
cd web && cp .env.example .env && cd ..
```

Leave `VITE_API_BASE_URL` empty so Vite proxies `/api` to port 8001.

### Step 4 — Start Postgres

```bash
make db-up
```

- Container name: `programming-tutor-postgres`  
- Host port: **5435** (see `docker-compose.yml`)

Wait until the container is healthy.

### Step 5 — Database schema

```bash
make db-migrate
```

Runs Alembic via `scripts/aaa_bootstrap.py migrate`.

### Step 6 — Load knowledge into pgvector

```bash
make db-ingest
```

Embeds `knowledge/` (JSONL under `data/miit/`) into Postgres.  
Re-run this whenever `data/miit/*.jsonl` changes.

### Step 7 — Preflight check

```bash
make preflight
```

Checks backend, API keys, `knowledge/` layout, and probes Gemini (disable with `GEMINI_PREFLIGHT_PROBE=false` in `.env` if needed).

Fix VPN/firewall if preflight reports SSL/connect errors to Google.

### Step 8 — Start the API (terminal 1)

```bash
make api
```

- Listens on **http://127.0.0.1:8001**  
- OpenAPI: http://127.0.0.1:8001/scalar  
- Health: http://127.0.0.1:8001/health  

### Step 9 — Start the web UI (terminal 2)

```bash
make web
```

Open **http://localhost:5173** in a browser.

### Step 10 — Register and smoke-test

1. **Register** a new account (or login).  
2. Run the checklist in [PROJECT_GUIDE.md §8](PROJECT_GUIDE.md#8-acceptance-smoke-checklist).

---

## 3. Daily development

| Task | Command |
|------|---------|
| API | `make api` |
| UI | `make web` |
| Tests | `make test` |
| After editing JSONL | `make db-ingest` |

---

## 4. Hybrid backend (optional, not the React product path)

For CLI-only experiments:

1. Set `TUTOR_BACKEND=hybrid` in `.env`.  
2. Build local index: `make miit-index` (writes gitignored `data/miit/index.json`).  
3. Run `make chat` or `make smoke-hybrid`.  

No Docker Postgres required for hybrid-only CLI, but the **React app expects `aaa`** with Postgres.

---

## 5. Updating knowledge notes

| Backend | After editing `data/miit/*.jsonl` |
|---------|-----------------------------------|
| **aaa** (default) | `make db-ingest` |
| **hybrid** | `make miit-index` |

Restart API not required for ingest alone; new questions use updated embeddings on next request.

---

## 6. Troubleshooting

| Symptom | Likely cause | Action |
|---------|----------------|--------|
| Preflight SSL / timeout | Google blocked | Enable VPN; verify `AIza` keys |
| `401` on API from browser | Missing/expired JWT | Log in again |
| CORS error in browser console | Wrong origin | Add UI URL to `TUTOR_CORS_ORIGINS` |
| Cannot connect to DB | Postgres down | `make db-up`; check port **5435** |
| Port 8001 in use | Old API process | Stop other process or change `TUTOR_API_PORT` |
| Port 5173 in use | Other Vite app | Stop it or change Vite port in `web/vite.config.ts` |
| Speak never ready | edge-tts blocked | Check outbound network; see API logs |
| Empty MIIT answers (aaa) | Stale/missing ingest | `make db-ingest`; check `knowledge/` |
| Preflight warns JWT | Default secret | Set strong `JWT_SECRET` for production |

---

## 7. Production (brief)

This repo targets **local / lab** dev. For a server deployment:

1. Build frontend: `cd web && npm run build` → serve `web/dist` behind HTTPS.  
2. Set `VITE_API_BASE_URL` at **build time** to the public API URL if not same-origin.  
3. Run API with a process manager (uvicorn/gunicorn) on `TUTOR_API_HOST` / `TUTOR_API_PORT`.  
4. Use managed Postgres; set `DATABASE_URL`.  
5. Set strong `JWT_SECRET` and production `TUTOR_CORS_ORIGINS`.  
6. Restrict network access; never expose Gemini keys to the client.

---

## 8. Related documents

- [PROJECT_GUIDE.md](PROJECT_GUIDE.md)  
- [TECHNICAL_REFERENCE.md](TECHNICAL_REFERENCE.md)  
- [../LAPTOP_SETUP.md](../LAPTOP_SETUP.md) — one-page dev shortcut  
