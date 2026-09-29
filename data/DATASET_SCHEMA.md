# Dataset Schema

Every sample in `data/processed/*.jsonl` must conform to this schema.

## Record Format (JSONL — one JSON object per line)

```json
{
  "id": "js_0042",
  "task_type": "explain_code",
  "domain": "javascript",
  "instruction": "JavaScript arrow function ကို Myanmar ဘာသာနဲ့ ရှင်းပြပါ။ မြန်မာဘာသာဖြင့်သာ ရှင်းပြပါ",
  "input": "const add = (a, b) => a + b;",
  "output": "arrow function ဆိုတာ ...",
  "source_book": "Ei Maung JavaScript - On Point",
  "source_chapter": "Chapter 5",
  "terms": ["function", "parameter", "return"],
  "split": "train"
}
```

## Field Definitions

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | yes | Unique ID: `{domain_prefix}_{序号}` e.g. `pb_0001` |
| `task_type` | enum | yes | `concept_qa`, `explain_code`, or `debug_explain` |
| `domain` | enum | yes | See domains below |
| `instruction` | string | yes | User question in Myanmar; must include language suffix |
| `input` | string | yes | Code snippet or empty string `""` |
| `output` | string | yes | Gold Myanmar explanation (reviewed/cleaned) |
| `source_book` | string | yes | Full book title |
| `source_chapter` | string | yes | Chapter or section name |
| `terms` | string[] | yes | CS terms used (from TERMINOLOGY.md) |
| `split` | enum | yes | `train`, `val`, or `test` |

## Domains

`programming_basic`, `database`, `javascript`, `php`, `react`, `laravel`, `api`, `bootstrap`, `pwd`

## Task Types

| Type | Target % | Description |
|------|----------|-------------|
| `concept_qa` | 40% | Conceptual question, no code required |
| `explain_code` | 40% | Code snippet + step-by-step Myanmar explanation |
| `debug_explain` | 20% | Wrong code + why wrong + correct fix in Myanmar |

## Chat Format (for training)

After processing, convert to chat format via `scripts/build_chat_format.py`:

```json
{
  "messages": [
    {"role": "user", "content": "{instruction}\n\n{input}"},
    {"role": "assistant", "content": "{output}"}
  ]
}
```

## ID Prefixes

| Domain | Prefix |
|--------|--------|
| programming_basic | `pb_` |
| database | `db_` |
| javascript | `js_` |
| php | `php_` |
| react | `react_` |
| laravel | `laravel_` |
| api | `api_` |
| bootstrap | `bs_` |
| pwd | `pwd_` |
