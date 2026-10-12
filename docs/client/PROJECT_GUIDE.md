# Computer Engineering Tutor — Project Guide

Audience: **client / product owner**. For installation see [HOW_TO_RUN.md](HOW_TO_RUN.md). For API and code layout see [TECHNICAL_REFERENCE.md](TECHNICAL_REFERENCE.md).

---

## 1. What this product is

The **Computer Engineering Tutor** is a web application for MIIT students. It answers questions in **Burmese** about:

- **Computer engineering** (CSE/ECE): programming, circuits, OS, networks, and related subjects.
- **MIIT institute knowledge**: campus, admission, curriculum, and faculty profiles (from curated notes, not the open web).

There is **no local AI model** on the laptop. Answers use **Google Gemini** in the cloud. MIIT-specific facts use **retrieval** over embedded notes (RAG), so the tutor is steered toward your JSONL knowledge base rather than inventing faculty names or elective codes.

**Default delivery:** React UI + Litestar API + Postgres (`TUTOR_BACKEND=aaa`).

---

## 2. What is in scope vs out of scope

| In scope | Out of scope |
|----------|----------------|
| CE/CSE/ECE study help (e.g. `Python for loop ရှင်းပြပါ`) | Weather, sports, general chit-chat |
| MIIT overview (e.g. `MIIT ဆိုတာ ဘာလဲ`) | Biology, unrelated domains |
| Faculty / papers when notes exist (Myanmar or English, e.g. `ဒေါက်တာစင်သီယာမြင့်က ဘယ်သူလဲ`) | Answers without supporting notes (AAA may refuse MIIT asks with no retrieval hit) |
| Follow-up questions in the **same chat** (e.g. `အသေးစိတ်`, `more`) | Off-topic even if Gemini could answer |

Off-topic questions receive a **fixed Burmese refusal** without calling the main tutor model.

---

## 3. How users interact (React UI)

### 3.1 Login and sessions

1. User **registers** or **logs in** (JWT stored in the browser).
2. **Sidebar** lists chat sessions (newest activity first).
3. **New chat** creates a session immediately (label **New chat** until the first question sets a title).
4. **Delete** removes a session; deleting the open chat starts a **new empty** chat.

### 3.2 Asking a question

1. Type in the composer (Myanmar, English, or mixed).
2. Choose **female / male** voice icon before **Ask** (affects TTS for that turn).
3. Click **Ask** — the UI shows loading until the assistant reply appears.
4. Replies support **Markdown** (tables, lists, code).

Example screenshot (UI may vary slightly by version):  
`docs/figures/figure_4_1_ask.png`

### 3.3 Speak (text-to-speech)

- Each assistant message has a **Speak** button.
- While audio is **prefetching**, the button shows a **spinner** (not the speaker icon).
- When ready, **Speak** plays MP3 (Burmese **edge-tts**; female `my-MM-NilarNeural`, male `my-MM-ThihaNeural`).
- Click again to **pause**; playback uses one shared player per page.

Speech needs **outbound internet** (Microsoft edge-tts), in addition to Gemini.

### 3.4 Theme

Header **Light / Dark** toggle; preference saved in the browser.

### 3.5 Session titles

The **first user message** in a chat can set the sidebar title (often a short English phrase). Faculty “who is” questions use **canonical names** from the knowledge base (e.g. Cynthia **Myint**, not a hallucinated surname).

---

## 4. End-to-end workflow (one question)

High-level path from the student’s perspective to the answer:

```mermaid
flowchart TD
  user[Student types question] --> api[API saves user message]
  api --> graph[LangGraph tutor]
  graph --> route[Route MIIT or programming or refuse]
  route -->|programming| progPrompt[CE tutor prompt]
  route -->|miit| rag[Retrieve note chunks]
  rag --> miitPrompt[MIIT prompt with passages]
  progPrompt --> gemini[Gemini generates Burmese answer]
  miitPrompt --> gemini
  gemini --> save[Save assistant message]
  save --> tts[Background TTS prefetch]
```

**Step-by-step (product view):**

1. **Route** — Rules and a small Gemini router decide: MIIT notes, programming tutor, or out-of-scope.
2. **Retrieve** (MIIT only) — Embed the question (+ recent history) and pull top matching chunks from pgvector (faculty names in Myanmar text are normalized for search).
3. **Generate** — Gemini writes the answer using the right system prompt (strict notes for MIIT; beginner-friendly CE style for programming).
4. **Persist** — User and assistant messages stored in **Postgres**; session list updates.
5. **Speech** — Server prepares MP3 in the background; UI polls until ready.

Follow-ups like `သူမရဲ့ စာတမ်းတွေ` stay on the MIIT thread when the prior turn was about faculty.

---

## 5. Knowledge content (what the tutor can cite)

Notes live as `data/miit/*.jsonl` (linked into `knowledge/` for AAA). Shipped topics include:

| File | Topic |
|------|--------|
| `institute.jsonl` | Campus, governance, programs |
| `bachelor_admission.jsonl` | B.E. (Hons) CSE/ECE admission |
| `cse_be_hons.jsonl` / `ece_be_hons.jsonl` | Curriculum by year |
| Faculty JSONL files | Profiles and research (e.g. Cynthia Myint, Aye Aye Thant, …) |

After editors change JSONL, operators must **re-ingest** (see [HOW_TO_RUN.md](HOW_TO_RUN.md)).

---

## 6. Other ways to use the engine (not the main UI)

| Surface | History | Typical use |
|---------|---------|-------------|
| React + API | Yes | **Product** |
| `make chat` (CLI) | No | Quick terminal test |
| `POST /v1/chat` (stateless) | No | Integrations without login |

---

## 7. Limitations (v1)

- **Document upload** exists on the API but is **not** in the React UI.
- **Gemini quotas** — use multiple keys in `GEMINI_API_KEYS`; VPN may be required where Google is blocked.
- **TTS** quality depends on edge-tts and pronunciation maps; polite particles are normalized for speech (e.g. `…။ ရှင်။` merged into one sentence).
- Session titles already saved in the database are **not** auto-renamed when title logic improves; new chats get the new behavior.

---

## 8. Acceptance smoke checklist

Run after [HOW_TO_RUN.md](HOW_TO_RUN.md) setup:

1. Open http://localhost:5173 and register.
2. Ask: `What's the weather?` → Burmese refusal (out of scope).
3. Ask: `Python for loop ရှင်းပြပါ` → programming answer in Burmese.
4. Ask: `MIIT ဆိုတာ ဘာလဲ` → institute overview from notes.
5. Ask: `ဒေါက်တာစင်သီယာမြင့်က ဘယ်သူလဲ` → faculty answer; sidebar title should include **Myint** (not a wrong surname).
6. Click **Speak** on the last reply → spinner then audible Burmese speech.

---

## 9. Related documents

- [HOW_TO_RUN.md](HOW_TO_RUN.md) — install and operate step by step  
- [TECHNICAL_REFERENCE.md](TECHNICAL_REFERENCE.md) — architecture, API, configuration  
- [../WORKFLOW.md](../WORKFLOW.md) — developer index into the pipeline  
