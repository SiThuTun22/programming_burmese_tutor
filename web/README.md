# Web UI (`web/`)

React + TypeScript + Vite + Tailwind chat client for the **Computer Engineering Tutor** AAA API.

## Setup

```bash
cd web
npm install
cp .env.example .env   # optional; empty VITE_API_BASE_URL uses the dev proxy
```

From the **repo root** (separate terminal):

```bash
make api   # Litestar on port 8001
```

## Dev

```bash
npm run dev
```

Open http://localhost:5173 — register/login, sidebar chats, Ask, **Speak** (TTS with prefetch spinner), light/dark theme.

`vite.config.ts` proxies `/api` and `/health` to `http://localhost:8001`.

## Production build

```bash
npm run build
```

Serve `web/dist` behind your host; set `VITE_API_BASE_URL` to the public API origin at build time if the API is not same-origin.

## Root configuration

Gemini keys, Postgres, JWT, and CORS live in the repo root `.env` (see `../.env.example`). `TUTOR_CORS_ORIGINS` must include your web origin.
