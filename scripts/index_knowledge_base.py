#!/usr/bin/env python3
"""
Embed the processed knowledge base (knowledge_base/processed/*.jsonl) with InLegalBERT and index it
into the persistent ``legal_kb`` collection of ChromaDB and/or Qdrant.

Each chunk is embedded **once** and written to both stores in the same pass, so Chroma and Qdrant
hold identical vectors — essential for a fair comparative study.

Run from repo root (after installing requirements-rag.txt):
    python scripts/index_knowledge_base.py --store both            # index into both
    python scripts/index_knowledge_base.py --store chroma --limit 200   # quick smoke test
    python scripts/index_knowledge_base.py --store both --recreate      # wipe + re-index
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys
import time

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO_ROOT, "backend"))

from rag import settings                        # noqa: E402
from rag.embeddings import Embedder             # noqa: E402
from rag.vector_store import get_store          # noqa: E402

PROCESSED = os.path.join(REPO_ROOT, "knowledge_base", "processed")

# Metadata fields copied from each record (plus flattened `extra`).
META_FIELDS = ("doc_type", "source", "section", "citation", "jurisdiction", "url")


def load_records(limit: int = 0):
    records = []
    for path in sorted(glob.glob(os.path.join(PROCESSED, "*.jsonl"))):
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
                    if limit and len(records) >= limit:
                        return records
    return records


def to_metadata(rec: dict) -> dict:
    meta = {k: rec.get(k) for k in META_FIELDS}
    for k, v in (rec.get("extra") or {}).items():   # flatten extra.*
        meta[k] = v
    return meta


def main() -> None:
    ap = argparse.ArgumentParser(description="Embed + index the KB into Chroma and/or Qdrant.")
    ap.add_argument("--store", choices=["chroma", "qdrant", "both"], default="both")
    ap.add_argument("--limit", type=int, default=0, help="index only the first N chunks (smoke test)")
    ap.add_argument("--batch", type=int, default=256, help="embed+upsert batch size")
    ap.add_argument("--recreate", action="store_true", help="drop existing collection(s) first")
    args = ap.parse_args()

    records = load_records(args.limit)
    if not records:
        print("No processed records found. Run build_knowledge_base.py first.")
        sys.exit(1)
    print(f"Loaded {len(records)} chunks from {PROCESSED}")

    backends = ["chroma", "qdrant"] if args.store == "both" else [args.store]
    stores = {}
    for b in backends:
        store = get_store(b, settings.KB_COLLECTION, settings.EMBEDDING_DIM)
        if args.recreate:
            store.reset()   # drop + recreate on the same client (no second lock)
        stores[b] = store
    print(f"Target stores: {', '.join(backends)} (collection '{settings.KB_COLLECTION}')")

    embedder = Embedder.get()
    print(f"Embedding with {settings.EMBEDDING_MODEL} (dim {embedder.dim})...")

    t0 = time.time()
    embed_time = {"secs": 0.0}
    upsert_time = {b: 0.0 for b in backends}
    n = len(records)
    for start in range(0, n, args.batch):
        batch = records[start:start + args.batch]
        ids = [r["id"] for r in batch]
        docs = [r["text"] for r in batch]
        metas = [to_metadata(r) for r in batch]

        te = time.time()
        embs = embedder.embed(docs, batch_size=settings.EMBEDDING_BATCH_SIZE)
        embed_time["secs"] += time.time() - te

        for b, store in stores.items():
            tu = time.time()
            store.upsert(ids, embs, docs, metas)
            upsert_time[b] += time.time() - tu

        done = min(start + args.batch, n)
        print(f"  {done}/{n}  (embed {embed_time['secs']:.0f}s, "
              f"{', '.join(f'{b} {upsert_time[b]:.0f}s' for b in backends)})", flush=True)

    print(f"\nDone in {time.time()-t0:.0f}s. Collection counts:")
    for b, store in stores.items():
        print(f"  {b:7} {store.count()} vectors")

    for store in stores.values():   # release Qdrant local lock / backend resources
        store.close()


if __name__ == "__main__":
    main()
