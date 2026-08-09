#!/usr/bin/env python3
"""
Answer-quality comparison: ChromaDB vs Qdrant on the SAME questions (end-to-end RAG).

For each question about a test contract, this runs the full Legal EASE answer pipeline once with
ChromaDB and once with Qdrant, then compares the two generated answers (full text + an embedding
cosine similarity). Because both stores hold identical vectors, answers should be near-identical
where retrieval agrees, and may diverge where ANN recall differs.

Dumps docs/answer_comparison.json (full answers) for the visual report.

Gemini free tier allows ~5 requests/min, so calls are spaced by --delay seconds.

Run from repo root (KB indexed into BOTH stores + working GEMINI_API_KEY):
    GEMINI_MODEL=gemini-2.5-flash python scripts/compare_answers.py --delay 14
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import uuid

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO_ROOT, "backend"))

import numpy as np  # noqa: E402
from rag.embeddings import Embedder  # noqa: E402
from rag.retriever import Retriever  # noqa: E402
import services.rag_service as rag_service  # noqa: E402
from services.ai_analyzer import ai_analyzer  # noqa: E402

DOC = os.path.join(REPO_ROOT, "knowledge_base", "test_documents", "rent_deed.txt")
QUESTIONS = [
    "Is the non-refundable security deposit in this agreement legally enforceable in India?",
    "Is the penalty of paying the entire balance rent for early termination valid under Indian law?",
    "Can the landlord increase the rent at his sole discretion as clause 2 of this deed says?",
]


def cosine(a, b):
    va, vb = np.array(a), np.array(b)
    return float(va @ vb / (np.linalg.norm(va) * np.linalg.norm(vb) + 1e-9))


def answers_for(backend, text, delay):
    Retriever._instance = None
    rag_service._retriever = Retriever(backend)
    rag_service._init_failed = False
    doc_id = str(uuid.uuid4())
    rag_service.index_document(doc_id, text)
    out = []
    for q in QUESTIONS:
        res = ai_analyzer.answer_question(text, q, doc_id)
        out.append({"answer": res.get("answer", ""), "confidence": res.get("confidence"),
                    "sources": res.get("sources", [])})
        print(f"  [{backend}] answered: {q[:55]}...", flush=True)
        time.sleep(delay)   # respect the free-tier rate limit
    rag_service.delete_document(doc_id)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--delay", type=float, default=14.0, help="seconds between Gemini calls")
    args = ap.parse_args()

    text = open(DOC, encoding="utf-8").read()
    model = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
    print(f"Model: {model} | delay {args.delay}s between calls\n")

    chroma = answers_for("chroma", text, args.delay)
    qdrant = answers_for("qdrant", text, args.delay)

    emb = Embedder.get()
    rows = []
    for i, q in enumerate(QUESTIONS):
        ca, qa = chroma[i]["answer"], qdrant[i]["answer"]
        ok = not (ca.startswith("Error") or qa.startswith("Error"))
        sim = cosine(*emb.embed([ca, qa])) if ok else None
        rows.append({"question": q, "similarity": sim,
                     "chroma": chroma[i], "qdrant": qdrant[i]})
        print(f"\nQ{i+1}: {q}")
        print(f"   similarity: {sim if sim is None else round(sim,4)}")
        print(f"   [chroma] {ca[:200].strip()}")
        print(f"   [qdrant] {qa[:200].strip()}")

    sims = [r["similarity"] for r in rows if r["similarity"] is not None]
    summary = {"model": model, "document": "rent_deed.txt",
               "mean_similarity": float(np.mean(sims)) if sims else None,
               "n_compared": len(sims), "rows": rows}
    json.dump(summary, open(os.path.join(REPO_ROOT, "docs", "answer_comparison.json"), "w"), indent=2)
    if sims:
        print(f"\nMean answer similarity: {np.mean(sims):.4f}  (1.0 = effectively identical)")
    print("Wrote docs/answer_comparison.json")


if __name__ == "__main__":
    main()
