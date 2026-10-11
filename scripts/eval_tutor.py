#!/usr/bin/env python3
"""Official eval: route Accuracy/F1, retrieval Recall@3/MRR, span EM/token F1."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tutor.env_bootstrap import load_project_env

load_project_env()

from tutor.eval_metrics import (
    accuracy,
    confusion,
    exact_match,
    macro_f1,
    mrr,
    recall_at_k,
    token_f1,
)
from tutor.hybrid import create_engine
from tutor.knowledge import retrieve_miit
from tutor.router import classify_route, inherit_thread_route

ITEMS_PATH = ROOT / "eval" / "items.jsonl"
OUT_PATH = ROOT / "results" / "eval_report.json"
K = 3
CITATIONS = {
    "route": {
        "metric": "Accuracy and macro-F1",
        "paper": "Sokolova & Lapalme (2009). A systematic analysis of performance measures for classification tasks. Information Processing & Management.",
        "url": "https://doi.org/10.1016/j.ipm.2009.03.002",
    },
    "retrieval": {
        "metric": "Recall@3 and MRR",
        "paper": "Karpukhin et al. (2020). Dense Passage Retrieval for Open-Domain Question Answering. EMNLP.",
        "url": "https://aclanthology.org/2020.emnlp-main.550/",
        "ir_book": "https://nlp.stanford.edu/IR-book/",
    },
    "generation": {
        "metric": "Exact Match and token F1 on gold fact spans",
        "paper": "Lewis et al. (2020). Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks. NeurIPS.",
        "url": "https://arxiv.org/abs/2005.11401",
    },
}


def load_items(path: Path) -> list[dict]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def predict_route(
    question: str,
    code: str = "",
    history: list | None = None,
) -> str:
    """Same routing decision as HybridEngine.answer, without generation."""
    classified = classify_route(question, code, history)
    if classified == "other":
        classified = inherit_thread_route(question, history)
        if classified is None:
            return "other"
    if classified == "programming":
        return "programming"
    result = retrieve_miit(question, history=history)
    if classified == "miit" or result.chunks:
        return "miit"
    return "programming"


def main() -> int:
    items = load_items(ITEMS_PATH)
    gold_routes: list[str] = []
    pred_routes: list[str] = []
    recalls: list[float] = []
    mrrs: list[float] = []
    route_rows: list[dict] = []
    retrieval_rows: list[dict] = []

    for item in items:
        question = item["question"]
        code = item.get("code") or ""
        history = item.get("history") or []
        gold = item["gold_route"]
        pred = predict_route(question, code, history)
        gold_routes.append(gold)
        pred_routes.append(pred)
        route_rows.append({"id": item["id"], "gold": gold, "pred": pred})

        gold_ids = list(item.get("gold_chunk_ids") or [])
        if gold_ids:
            ranked = [chunk.id for chunk in retrieve_miit(question, history=history).chunks]
            rec = recall_at_k(gold_ids, ranked, k=K)
            rank_score = mrr(gold_ids, ranked)
            recalls.append(rec)
            mrrs.append(rank_score)
            retrieval_rows.append(
                {
                    "id": item["id"],
                    "gold_chunk_ids": gold_ids,
                    "ranked_ids": ranked[:K],
                    "recall_at_3": rec,
                    "mrr": rank_score,
                }
            )

    gen_items = [item for item in items if item.get("gold_spans")]
    gen_rows: list[dict] = []
    em_scores: list[float] = []
    f1_scores: list[float] = []
    if gen_items:
        engine = create_engine()
        try:
            for item in gen_items:
                answer = engine.answer(
                    item["question"],
                    item.get("code") or "",
                    history=item.get("history") or [],
                )
                spans = list(item["gold_spans"])
                em = exact_match(answer, spans)
                f1 = token_f1(answer, spans)
                em_scores.append(em)
                f1_scores.append(f1)
                gen_rows.append(
                    {
                        "id": item["id"],
                        "gold_spans": spans,
                        "em": em,
                        "token_f1": round(f1, 4),
                        "answer_preview": answer.replace("\n", " ")[:240],
                    }
                )
        finally:
            engine.unload()

    report = {
        "n_items": len(items),
        "citations": CITATIONS,
        "route": {
            "n": len(gold_routes),
            "accuracy": round(accuracy(gold_routes, pred_routes), 4),
            "macro_f1": round(macro_f1(gold_routes, pred_routes), 4),
            "labels": ["miit", "programming", "other"],
            "confusion": confusion(gold_routes, pred_routes),
            "rows": route_rows,
        },
        "retrieval": {
            "n": len(recalls),
            "k": K,
            "recall_at_3": round(sum(recalls) / max(len(recalls), 1), 4),
            "mrr": round(sum(mrrs) / max(len(mrrs), 1), 4),
            "rows": retrieval_rows,
        },
        "generation": {
            "n": len(em_scores),
            "exact_match": round(sum(em_scores) / max(len(em_scores), 1), 4) if em_scores else None,
            "token_f1": round(sum(f1_scores) / max(len(f1_scores), 1), 4) if f1_scores else None,
            "rows": gen_rows,
        },
    }
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        f"route accuracy={report['route']['accuracy']:.3f} "
        f"macro-F1={report['route']['macro_f1']:.3f} n={report['route']['n']}"
    )
    print(
        f"retrieval Recall@{K}={report['retrieval']['recall_at_3']:.3f} "
        f"MRR={report['retrieval']['mrr']:.3f} n={report['retrieval']['n']}"
    )
    gen = report["generation"]
    if gen["n"]:
        print(f"generation EM={gen['exact_match']:.3f} token-F1={gen['token_f1']:.3f} n={gen['n']}")
    else:
        print("generation skipped (no gold_spans)")
    print(f"Wrote {OUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
