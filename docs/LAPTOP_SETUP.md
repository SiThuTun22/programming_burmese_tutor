# Laptop setup (Mac M2, 8 GB)

The Computer Engineering Tutor is Gemini chat. It does not load a local model. VPN is required for Gemini where Google APIs are blocked.

## What GitHub includes

- Source code, MIIT notes, and tests
- **Not** in git: `.env`, `.venv`, `data/miit/index.json`, demo transcripts in `results/`

## Mac demo

1. Get a free key at [Google AI Studio](https://aistudio.google.com/).
2. `uv sync --extra app`
3. `cp .env.example .env` and set:

```
TUTOR_BACKEND=hybrid
HYBRID_CHAT_PROVIDER=gemini
GEMINI_API_KEY=your_key
GEMINI_API_KEY_FALLBACK=your_second_key
GEMINI_MODEL=gemini-3.1-flash-lite
TUTOR_CLOUD_MAX_TOKENS=3072
```

4. `make miit-index` (embeds `data/miit/*.jsonl`; needs the same API key)
5. `make preflight && make app` → **http://localhost:7860**

Programming questions use the tutor prompt. MIIT faculty notes use embedding retrieval when similarity is high enough.

Optional: `make smoke-hybrid` (15 prompts; calls the chat API).

Free-tier rate limits apply.
