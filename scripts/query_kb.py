#!/usr/bin/env python3
"""
Ad-hoc retrieval against the indexed legal knowledge base — a quick way to sanity-check the
vector stores and compare ChromaDB vs Qdrant results for the same query.

Run from repo root:
    python scripts/query_kb.py "Can my landlord keep my security deposit?"
    python scripts/query_kb.py "penalty for breaking a contract" --store chroma --top-k 5
    python scripts/query_kb.py "unfair arbitration clause" --doc-type redflag
"""
from __future__ import annotations

import argparse
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO_ROOT, "backend"))

from rag import settings                        # noqa: E402
from rag.embeddings import Embedder             # noqa: E402
from rag.vector_store import get_store          # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description="Query the legal knowledge base.")
    ap.add_argument("query", help="natural-language query")
    ap.add_argument("--store", choices=["chroma", "qdrant", "both"], default="both")
    ap.add_argument("--top-k", type=int, default=5)
    ap.add_argument("--doc-type", default=None,
                    help="restrict to a doc_type (statute|judgment|glossary|redflag|template)")
    args = ap.parse_args()

    where = {"doc_type": args.doc_type} if args.doc_type else None
    qvec = Embedder.get().embed_query(args.query)
    backends = ["chroma", "qdrant"] if args.store == "both" else [args.store]

    for b in backends:
        store = get_store(b, settings.KB_COLLECTION, settings.EMBEDDING_DIM)
        hits = store.query(qvec, top_k=args.top_k, where=where)
        print(f"\n=== {b}  (collection '{settings.KB_COLLECTION}', {store.count()} vectors) ===")
        for i, h in enumerate(hits, 1):
            m = h.metadata
            tag = m.get("doc_type", "?")
            src = m.get("source", "")
            sec = m.get("section") or ""
            cite = m.get("citation") or ""
            snippet = h.text[:150].replace("\n", " ")
            print(f"{i}. [{h.score:.3f}] ({tag}) {src} {sec} {cite}".rstrip())
            print(f"      {snippet}...")
        store.close()


if __name__ == "__main__":
    main()
