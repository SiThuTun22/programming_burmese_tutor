# Laptop setup (quick)

**Full step-by-step:** [docs/client/HOW_TO_RUN.md](client/HOW_TO_RUN.md)  
**Product overview:** [docs/client/PROJECT_GUIDE.md](client/PROJECT_GUIDE.md)

```bash
make sync
cp .env.example .env    # GEMINI_API_KEYS, JWT_SECRET
make db-up && make db-migrate && make db-ingest
make preflight
make api    # terminal 1 → :8001
make web    # terminal 2 → http://localhost:5173
```

VPN if Gemini preflight fails. Hybrid CLI: set `TUTOR_BACKEND=hybrid`, `make miit-index`, `make chat`.
