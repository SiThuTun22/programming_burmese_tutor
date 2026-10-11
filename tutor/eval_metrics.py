"""Published NLP metrics: classification Accuracy/F1, IR Recall@k/MRR, QA EM/token F1.

Citations (same families as intent classification, DPR retrieval, and RAG QA):
- Sokolova & Lapalme (2009), IP&M. https://doi.org/10.1016/j.ipm.2009.03.002
- Karpukhin et al. (2020), DPR, EMNLP. https://aclanthology.org/2020.emnlp-main.550/
- Manning, Raghavan & Schütze (2008), IIR. https://nlp.stanford.edu/IR-book/
- Lewis et al. (2020), RAG, NeurIPS. https://arxiv.org/abs/2005.11401
"""

from __future__ import annotations

import re
from collections import Counter

LABELS = ("miit", "programming", "other")
_TOKEN_RE = re.compile(r"[A-Za-z0-9]+|[\u1000-\u109F]+")


def accuracy(gold: list[str], pred: list[str]) -> float:
    """Classification accuracy (Sokolova & Lapalme, 2009)."""
    if not gold:
        return 0.0
    return sum(g == p for g, p in zip(gold, pred, strict=True)) / len(gold)


def _f1(tp: int, fp: int, fn: int) -> float:
    if tp == 0:
        return 0.0
    prec = tp / (tp + fp)
    rec = tp / (tp + fn)
    return 2 * prec * rec / (prec + rec)


def macro_f1(gold: list[str], pred: list[str], labels: tuple[str, ...] = LABELS) -> float:
    """Macro-averaged F1 over labels (Sokolova & Lapalme, 2009)."""
    scores: list[float] = []
    for label in labels:
        tp = sum(g == label and p == label for g, p in zip(gold, pred, strict=True))
        fp = sum(g != label and p == label for g, p in zip(gold, pred, strict=True))
        fn = sum(g == label and p != label for g, p in zip(gold, pred, strict=True))
        scores.append(_f1(tp, fp, fn))
    return sum(scores) / max(len(scores), 1)


def confusion(gold: list[str], pred: list[str], labels: tuple[str, ...] = LABELS) -> list[list[int]]:
    index = {name: i for i, name in enumerate(labels)}
    matrix = [[0] * len(labels) for _ in labels]
    for g, p in zip(gold, pred, strict=True):
        if g in index and p in index:
            matrix[index[g]][index[p]] += 1
    return matrix


def recall_at_k(gold_ids: list[str], ranked_ids: list[str], k: int = 3) -> float:
    """Recall@k: 1 if any gold id is in the top-k ranked list (Karpukhin et al., 2020)."""
    if not gold_ids:
        return 0.0
    top = set(ranked_ids[:k])
    return 1.0 if any(gid in top for gid in gold_ids) else 0.0


def mrr(gold_ids: list[str], ranked_ids: list[str]) -> float:
    """Mean Reciprocal Rank for one query (Manning et al., 2008). 0 if no gold in list."""
    gold = set(gold_ids)
    for i, cid in enumerate(ranked_ids, start=1):
        if cid in gold:
            return 1.0 / i
    return 0.0


def tokenize_eval(text: str) -> list[str]:
    return [tok.lower() for tok in _TOKEN_RE.findall(text or "")]


def exact_match(answer: str, gold_spans: list[str]) -> float:
    """1 if every gold span occurs in the answer (Lewis et al., 2020-style EM on facts)."""
    if not gold_spans:
        return 0.0
    lowered = (answer or "").lower()
    return 1.0 if all(span.lower() in lowered for span in gold_spans) else 0.0


def token_f1(answer: str, gold_spans: list[str]) -> float:
    """Token F1 between the answer and concatenated gold spans (Lewis et al., 2020)."""
    pred = tokenize_eval(answer)
    gold = tokenize_eval(" ".join(gold_spans))
    if not pred or not gold:
        return 0.0
    overlap = sum((Counter(pred) & Counter(gold)).values())
    prec = overlap / len(pred)
    rec = overlap / len(gold)
    if prec + rec == 0:
        return 0.0
    return 2 * prec * rec / (prec + rec)
