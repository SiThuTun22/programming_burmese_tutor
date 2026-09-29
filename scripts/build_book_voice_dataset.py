#!/usr/bin/env python3
"""Rebuild gold answers v0.5: catalog gold is the spine; book sentences are optional garnish.

Keeps catalog questions, code, debug fixes, ids, and splits.
At most one on-topic book sentence may be prepended. Book text never replaces gold.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from build_gold_dataset import QUOTAS, build_domain  # noqa: E402

MYANMAR_RE = re.compile(r"[\u1000-\u109F]")
LEFTOVER_RE = re.compile(
    r"(flowchart|flow chart|flow chat|အထက်ပါ|အောက်မှာ ဖော်ပြ|"
    r"discord|telegram|လေ့ကျင့်ခန်း|A\.\s|B\.\s|"
    r"https://discord|https://t\.me|ဒီစာအုပ်|မာတိကာ|"
    r"github issues|နိဂုံးချုပ်)",
    re.IGNORECASE,
)
CODE_TOKEN_RE = re.compile(r"[A-Za-z_]{3,}")
DEBUG_RE = re.compile(r"မှန်ကန်သော code:\s*(.*)$", re.DOTALL)

STOP_EN = {
    "the",
    "and",
    "for",
    "this",
    "that",
    "with",
    "from",
    "what",
    "how",
    "code",
    "hello",
    "world",
}

GARBAGE_RE = re.compile(
    r"(ရှင်းပြပါ|ရေးပြပါ|ဒီစာအုပ်|telegram|github|"
    r"localhost|to Path|info\.php|checkbox|XAMPP|"
    r"အကြောင်း Myanmar|World Wide|http://|https://|"
    r"မာတိကာ|နိဂုံးချုပ်|လို - တို|အခန်း \(|"
    r"မှန်ကန်သော code|ဘာမှားနေလဲ|နောက်လာမယ့် အခန်း|"
    r"Myanmar ဘာသာနဲ့|ClassName|HELLO\s*Python|အတွက)",
    re.IGNORECASE,
)

ROBOT_FIXES = [
    ("ဒြပ်စင်များ ခြုံခြင်း", "tag တွေကို ခြုံပေးတာ"),
    ("ဒြပ်စင်များ", "element တွေ"),
    ("ဒြပ်စင်", "element"),
    ("ဖြစ်ခြင်း ဖြစ်ပါတယ်", "ဖြစ်ပါတယ်"),
    ("ရေးခြင်း ဖြစ်ပါတယ်", "ရေးတာ ဖြစ်ပါတယ်"),
    ("ပိုင်ခြင်း ဖြစ်ပါတယ်", "ပိုင်တာ ဖြစ်ပါတယ်"),
    ("လုပ်ခြင်း ဖြစ်ပါတယ်", "လုပ်တာ ဖြစ်ပါတယ်"),
    ("ခိုင်းစေခြင်း ဖြစ်ပါတယ်", "ခိုင်းစေတာ ဖြစ်ပါတယ်"),
    ("ဝေမျှခြင်း ဖြစ်ပါတယ်", "ဝေမျှတာ ဖြစ်ပါတယ်"),
]


def myanmar_ratio(text: str) -> float:
    if not text:
        return 0.0
    compact = text.replace(" ", "")
    return len(MYANMAR_RE.findall(text)) / max(len(compact), 1)


def repair_book_text(text: str) -> str:
    text = text.replace("\x00", "")
    text = text.replace("\u00ad", "")
    text = re.sub(r"-\n", "", text)
    text = re.sub(r"([\u1000-\u109F])\n+([\u1000-\u109F])", r"\1\2", text)
    text = re.sub(r"([A-Za-z0-9])\n+([A-Za-z0-9])", r"\1\2", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def apply_robot_fixes(text: str) -> str:
    for old, new in ROBOT_FIXES:
        text = text.replace(old, new)
    return text


def split_sentences(text: str) -> list[str]:
    parts = []
    for chunk in re.split(r"(?<=။)", repair_book_text(text)):
        sent = chunk.strip()
        sent = re.sub(r"\s+", " ", sent)
        if sent:
            parts.append(sent)
    return parts


def is_usable_sentence(sent: str) -> bool:
    if not sent.endswith("။"):
        return False
    if len(sent) < 55 or len(sent) > 360:
        return False
    if myanmar_ratio(sent) < 0.30:
        return False
    if LEFTOVER_RE.search(sent) or GARBAGE_RE.search(sent):
        return False
    if re.search(r"^\d+\s", sent):
        return False
    if sent.count("–") >= 2:
        return False
    if sent.count("(") != sent.count(")"):
        return False
    if "စသည်ဖြင့်" in sent and len(sent) < 90:
        return False
    if "သင်ကြားတာ မဟုတ်" in sent:
        return False
    if "Add Python" in sent or "run time" in sent or "HELLO" in sent:
        return False
    if "အတွက" in sent:
        return False
    if "<?" in sent or sent.count(";") >= 2:
        return False
    if re.search(r"နံပါတ်\s*\(", sent) or "ပြထားတဲ့နေရာ" in sent:
        return False
    if sent.count("{") + sent.count("}") > 0:
        return False
    if len(re.findall(r"[;{}=<>]", sent)) > 6:
        return False
    if re.search(r"ResponseHeader|Request Header|Developer Tool", sent, re.I):
        return False
    if re.search(r"စာအုပ်မှာ|ရေးသားခဲ့", sent):
        return False
    return True


def load_book_sentences() -> dict[str, list[str]]:
    by_domain: dict[str, list[str]] = {}
    raw_dir = ROOT / "data" / "raw"
    for path in sorted(raw_dir.glob("*_candidates.jsonl")):
        with open(path, encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                row = json.loads(line)
                domain = row.get("domain", "")
                blob = " ".join(
                    [
                        row.get("output", ""),
                        row.get("instruction", ""),
                    ]
                )
                for sent in split_sentences(blob):
                    if not is_usable_sentence(sent):
                        continue
                    by_domain.setdefault(domain, []).append(sent)
    deduped: dict[str, list[str]] = {}
    for domain, sents in by_domain.items():
        seen: set[str] = set()
        keep = []
        for sent in sents:
            key = re.sub(r"\s+", "", sent)
            if key in seen:
                continue
            seen.add(key)
            keep.append(sent)
        deduped[domain] = keep
    return deduped


def topic_keys(instruction: str) -> list[str]:
    text = instruction.replace("မြန်မာဘာသာဖြင့်သာ ရှင်းပြပါ", "")
    tokens = []
    for tok in re.findall(r"[A-Za-z][A-Za-z0-9_+#.-]{1,}", text):
        if tok.lower() in STOP_EN:
            continue
        if len(tok) < 3:
            continue
        tokens.append(tok)
    if not tokens:
        for tok in re.findall(r"[\u1000-\u109F]{3,}", text):
            if tok in {"ဘာလဲ", "ဘယ်လို", "ရှင်းပြပါ", "ဒီကုဒ်", "အကြောင်း"}:
                continue
            tokens.append(tok)
    return tokens


def token_in_text(token: str, text: str) -> bool:
    if re.match(r"[A-Za-z]", token):
        return (
            re.search(
                rf"(?<![A-Za-z0-9_]){re.escape(token)}(?![A-Za-z0-9_])",
                text,
                re.IGNORECASE,
            )
            is not None
        )
    return token.lower() in text.lower()


def score_sentence(sent: str, keys: list[str]) -> int:
    score = 0
    for key in keys:
        if token_in_text(key, sent):
            score += 3 if re.match(r"[A-Za-z]", key) else 2
    return score


def pick_book_sentences(row: dict, pool: list[str], limit: int = 1) -> list[str]:
    keys = topic_keys(row["instruction"])
    code_keys: list[str] = []
    if row["task_type"] in {"explain_code", "debug_explain"}:
        for token in CODE_TOKEN_RE.findall(row.get("input") or ""):
            if len(token) >= 3 and token.lower() not in STOP_EN:
                code_keys.append(token)
    if row["task_type"] in {"explain_code", "debug_explain"} and code_keys:
        must = code_keys[0]
        match_keys = list(dict.fromkeys(code_keys + keys))
    elif keys:
        must = keys[0]
        match_keys = keys
    else:
        return []
    min_points = 4 if row["task_type"] in {"explain_code", "debug_explain"} else 3
    ranked = []
    for sent in pool:
        if not any(token_in_text(k, sent) for k in match_keys):
            continue
        if row["task_type"] == "concept_qa":
            topic_def = re.search(
                rf"{re.escape(must)}\s*(ဆိုတာ|ကတော့|ဟာ)",
                sent,
                re.IGNORECASE,
            )
            if not topic_def:
                continue
        points = score_sentence(sent, keys)
        if re.search(rf"{re.escape(must)}\s*ဆိုတာ", sent, re.IGNORECASE):
            points += 6
        if code_keys:
            code_hits = sum(1 for token in code_keys if token_in_text(token, sent))
            if code_hits == 0:
                continue
            if len(set(k.lower() for k in code_keys)) >= 3 and code_hits < 2:
                continue
            points += code_hits
        if points < min_points:
            continue
        ranked.append((points, len(sent), sent))
    ranked.sort(key=lambda item: (item[0], item[1]), reverse=True)
    picked = []
    seen = set()
    for _, __, sent in ranked:
        key = sent[:48]
        if key in seen:
            continue
        seen.add(key)
        picked.append(sent)
        if len(picked) >= limit:
            break
    return picked


def gold_sentences(output: str) -> tuple[list[str], str]:
    debug = ""
    match = DEBUG_RE.search(output)
    body = output
    if match:
        debug = "မှန်ကန်သော code:\n" + match.group(1).strip()
        body = output[: match.start()].strip()
    body = apply_robot_fixes(body)
    sents = []
    for part in re.split(r"။", body):
        part = re.sub(r"\s+", " ", part).strip()
        if not part or part.startswith("မှန်ကန်သော"):
            continue
        sents.append(part + "။")
    return sents, debug


def ensure_code_overlap(output: str, code: str) -> str:
    tokens = []
    seen = set()
    for token in CODE_TOKEN_RE.findall(code):
        key = token.lower()
        if key not in seen:
            seen.add(key)
            tokens.append(token)
    if not tokens:
        return output
    hits = sum(1 for token in tokens if token.lower() in output.lower())
    if hits > 0:
        return output
    shown = ", ".join(tokens[:6])
    return output.rstrip() + f"\n\nဒီ code မှာ {shown} ကို သုံးထားပါတယ်။"


def compose_output(row: dict, book_sents: list[str]) -> tuple[str, str]:
    """Return (output text, composition mode: gold_only | gold_plus_book)."""
    gold_sents, debug = gold_sentences(row["output"])
    paras = list(gold_sents)
    mode = "gold_only"
    garnish = ""
    for sent in book_sents[:1]:
        if not sent or sent in paras:
            continue
        if GARBAGE_RE.search(sent) or LEFTOVER_RE.search(sent):
            continue
        if any(sent[:24] in gold or gold[:24] in sent for gold in paras):
            continue
        if any(sent[:40] in gold or gold[:40] in sent for gold in paras):
            continue
        garnish = sent
        break
    routing_q = bool(
        re.search(
            r"(route|routing|router|/posts|/hello|web\.php)",
            row.get("instruction", ""),
            re.I,
        )
    )
    if garnish and "လမ်းကြောင်း" in garnish and not routing_q:
        garnish = ""
    if garnish and is_usable_sentence(garnish):
        paras = [garnish] + paras
        mode = "gold_plus_book"

    text = "\n\n".join(paras).strip()
    if row["task_type"] == "explain_code":
        text = ensure_code_overlap(text, row.get("input", ""))
    if debug:
        text = text.rstrip() + "\n\n" + debug
        if not text.endswith("။"):
            text = text + "\n\nဒီလို ပြင်ရင် အမှား ပျောက်ပါတယ်။"
    elif row["task_type"] == "debug_explain" and not text.endswith("။"):
        if "ဒီလို ပြင်ရင်" not in text:
            text = text + "\n\nဒီလို ပြင်ရင် အမှား ပျောက်ပါတယ်။"
    return apply_robot_fixes(text).strip(), mode


def merge_pools(pool: dict[str, list[str]]) -> list[str]:
    merged: list[str] = []
    seen: set[str] = set()
    for sents in pool.values():
        for sent in sents:
            key = re.sub(r"\s+", "", sent)
            if key in seen:
                continue
            seen.add(key)
            merged.append(sent)
    return merged


def pick_for_row(row: dict, domain_sents: list[str], global_sents: list[str]) -> list[str]:
    picked = pick_book_sentences(row, domain_sents, limit=1)
    if picked:
        return picked
    if global_sents is domain_sents:
        return picked
    extra = pick_book_sentences(row, global_sents, limit=1)
    for sent in extra:
        if sent in picked:
            continue
        picked.append(sent)
        if len(picked) >= 1:
            break
    return picked


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> None:
    pool = load_book_sentences()
    global_sents = merge_pools(pool)
    all_rows: list[dict] = []
    book_used = 0
    mode_counts: dict[str, int] = {}
    for domain in QUOTAS:
        rows = build_domain(domain)
        sentences = pool.get(domain, [])
        for row in rows:
            picked = pick_for_row(row, sentences, global_sents)
            if picked:
                book_used += 1
            text, mode = compose_output(row, picked)
            mode_counts[mode] = mode_counts.get(mode, 0) + 1
            row["output"] = text
        all_rows.extend(rows)

    train = [row for row in all_rows if row["split"] == "train"]
    val = [row for row in all_rows if row["split"] == "val"]
    test = [row for row in all_rows if row["split"] == "test"]

    gold_dir = ROOT / "data" / "gold"
    proc_dir = ROOT / "data" / "processed"
    write_jsonl(gold_dir / "all.jsonl", all_rows)
    write_jsonl(gold_dir / "train.jsonl", train)
    write_jsonl(gold_dir / "val.jsonl", val)
    write_jsonl(gold_dir / "test.jsonl", test)
    write_jsonl(proc_dir / "all.jsonl", all_rows)
    write_jsonl(proc_dir / "train.jsonl", train)
    write_jsonl(proc_dir / "val.jsonl", val)
    write_jsonl(proc_dir / "test.jsonl", test)

    by_task: dict[str, int] = {}
    for row in all_rows:
        by_task[row["task_type"]] = by_task.get(row["task_type"], 0) + 1

    print(
        f"Book-voice v0.5: train={len(train)} val={len(val)} "
        f"test={len(test)} total={len(all_rows)}"
    )
    print(f"rows with matched book sentences: {book_used}/{len(all_rows)}")
    print("compose modes:", mode_counts)
    print("tasks:", by_task)
    lengths = [len(row["output"]) for row in all_rows]
    print(f"avg output chars: {sum(lengths) / len(lengths):.0f}")


if __name__ == "__main__":
    main()
