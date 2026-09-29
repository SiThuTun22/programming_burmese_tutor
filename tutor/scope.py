"""Refuse questions outside Saturngod / Ei Maung book stacks."""

from __future__ import annotations

import re

SCOPE_LANGUAGES = "Python, JavaScript, PHP, HTML, CSS, SQL"
SCOPE_TOPICS = "React, Laravel, Bootstrap, API, programming အခြေခံ, database အခြေခံ, data structures & algorithms"

SCOPE_BANNER_MD = (
    "> **သတိ။** ဒီ tutor က စာအုပ်ထဲက ဘာသာစကားတွေပဲ သင်ပေးပါတယ်။ "
    f"ဘာသာစကား: **{SCOPE_LANGUAGES}**။ "
    f"Framework / ခေါင်းစဉ်: **{SCOPE_TOPICS}**။ "
    "ဖြေချက်က မြန်မာလိုသာ။ စာအုပ်မှာ မပါတဲ့ ခေါင်းစဉ် (ဥပမာ Svelte, Vue, Rust) ကို နယ်ပယ်ပြင်ပ လို့ ပြောပါမယ်။"
)

OUT_OF_SCOPE_MESSAGE = (
    "ဒီမေးခွန်းက **နယ်ပယ်ပြင်ပ** ဖြစ်ပါတယ်။ "
    f"ကျွန်တော် သင်ပေးနိုင်တာက {SCOPE_LANGUAGES} နဲ့ {SCOPE_TOPICS} ပါ။ "
    "စာအုပ်မှာ မပါတဲ့ ဘာသာစကား/framework ကို ခန့်မှန်းပြီး မဖြေပါ။ "
    "အထက်က စာရင်းထဲက ခေါင်းစဉ်နဲ့ ပြန်မေးပါ။"
)

_LATIN_TOKEN = re.compile(r"[A-Za-z][A-Za-z0-9_+#.-]{1,}")
_WHAT_IS = re.compile(
    r"([A-Za-z][A-Za-z0-9_+#.-]{1,})\s*ဆိုတာ\s*ဘာလဲ",
    re.IGNORECASE,
)
_OOB_EXT = re.compile(
    r"\.(svelte|vue|rs|kt|swift|java|go|rb|ts|tsx|dart)\b",
    re.IGNORECASE,
)

# Named stacks that are not in the source books.
OUT_OF_SCOPE_STACKS = frozenset(
    {
        "svelte",
        "vue",
        "angular",
        "next",
        "nextjs",
        "nuxt",
        "django",
        "flask",
        "fastapi",
        "spring",
        "rust",
        "kotlin",
        "swift",
        "ruby",
        "rails",
        "java",
        "golang",
        "csharp",
        "typescript",
        "flutter",
        "dart",
        "solid",
        "qwik",
        "astro",
        "remix",
        "deno",
        "haskell",
        "scala",
        "elixir",
        "c++",
        "cpp",
    }
)

IN_SCOPE_TOKENS = frozenset(
    {
        "python",
        "javascript",
        "js",
        "php",
        "html",
        "css",
        "sql",
        "mysql",
        "sqlite",
        "react",
        "laravel",
        "bootstrap",
        "artisan",
        "blade",
        "eloquent",
        "json",
        "dom",
        "api",
        "http",
        "rest",
        "jsx",
        "hook",
        "usestate",
        "useeffect",
        "props",
        "state",
        "component",
        "variable",
        "function",
        "parameter",
        "loop",
        "array",
        "class",
        "object",
        "oop",
        "string",
        "boolean",
        "list",
        "dict",
        "print",
        "input",
        "return",
        "route",
        "routing",
        "middleware",
        "csrf",
        "migration",
        "form",
        "get",
        "post",
        "put",
        "delete",
        "select",
        "insert",
        "update",
        "where",
        "join",
        "table",
        "index",
        "debug",
        "error",
        "exception",
        "promise",
        "async",
        "await",
        "const",
        "let",
        "var",
        "map",
        "filter",
        "event",
        "listener",
        "query",
        "selector",
        "code",
        "program",
        "programming",
        "language",
        "web",
        "css",
        "mvc",
        "orm",
        "token",
        "header",
        "request",
        "response",
        "server",
        "client",
        "frontend",
        "backend",
        "database",
        "db",
        "true",
        "false",
        "null",
        "none",
        "if",
        "else",
        "elif",
        "for",
        "while",
        "def",
        "try",
        "catch",
        "fragment",
        "spa",
        "router",
        "controller",
        "model",
        "view",
        "npm",
        "node",
        "binary_search",
        "stack",
        "queue",
        "heap",
        "sort",
        "sorting",
        "tree",
        "hash",
        "hashing",
        "greedy",
        "peek",
        "enqueue",
        "dequeue",
        "linkedlist",
        "bigo",
        "avl",
        "collision",
        "chaining",
        "recursion",
        "search",
        "target",
        "mid",
    }
)

_STOP = frozenset(
    {
        "the",
        "and",
        "for",
        "this",
        "that",
        "with",
        "from",
        "what",
        "how",
        "hello",
        "world",
        "name",
        "user",
        "your",
        "my",
        "is",
        "are",
        "to",
        "of",
        "in",
        "on",
        "a",
        "an",
    }
)


def _tokens(text: str) -> list[str]:
    found = []
    for raw in _LATIN_TOKEN.findall(text or ""):
        key = raw.lower().strip("._-")
        key = key.replace("++", "++")
        if key.endswith("js") and len(key) > 2 and key not in {"js"}:
            # nextjs / vuejs
            pass
        if len(key) < 2 or key in _STOP:
            continue
        found.append(key)
    return found


def is_out_of_scope(question: str, code: str = "") -> bool:
    blob = f"{question}\n{code}"
    if _OOB_EXT.search(blob):
        return True
    tokens = _tokens(blob)
    for tok in tokens:
        compact = tok.replace(".", "").replace("-", "")
        if tok in OUT_OF_SCOPE_STACKS or compact in OUT_OF_SCOPE_STACKS:
            return True
        if tok in {"go"} and re.search(r"\bgo\b", blob, re.I) and re.search(
            r"golang|\.go\b|go language", blob, re.I
        ):
            return True
    for match in _WHAT_IS.finditer(question or ""):
        name = match.group(1).lower().strip("._-")
        compact = name.replace(".", "").replace("-", "")
        if name in IN_SCOPE_TOKENS or compact in IN_SCOPE_TOKENS:
            continue
        if name in _STOP:
            continue
        return True
    return False


def out_of_scope_message() -> str:
    return OUT_OF_SCOPE_MESSAGE
