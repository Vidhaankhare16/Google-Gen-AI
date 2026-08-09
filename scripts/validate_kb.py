#!/usr/bin/env python3
"""
Validate the processed knowledge base (knowledge_base/processed/*.jsonl).

Checks:
  * required metadata present on every record
  * no empty text, no duplicate ids
  * every chunk within the InLegalBERT 512-token hard limit (warns above the 400 target)
  * prints chunk counts per doc_type and per source, plus a few random samples

Exit code is non-zero if any hard check fails, so this doubles as a CI gate.

Run from repo root:
    python scripts/validate_kb.py
"""
from __future__ import annotations

import glob
import json
import os
import random
import sys
from collections import Counter

# Windows consoles default to cp1252 and choke on legal unicode (em dashes, ₹, emoji).
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO_ROOT, "backend"))
from rag.chunker import count_tokens, using_real_tokenizer, HARD_TOKEN_LIMIT, DEFAULT_MAX_TOKENS  # noqa: E402

PROCESSED = os.path.join(REPO_ROOT, "knowledge_base", "processed")
REQUIRED = ("id", "text", "doc_type", "source", "jurisdiction")


def main() -> int:
    files = sorted(glob.glob(os.path.join(PROCESSED, "*.jsonl")))
    if not files:
        print(f"No processed files in {PROCESSED}. Run build_knowledge_base.py first.")
        return 1

    records = []
    for path in files:
        with open(path, encoding="utf-8") as f:
            for ln, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError as e:
                    print(f"  FAIL: {os.path.basename(path)}:{ln} invalid JSON: {e}")
                    return 1

    print(f"Token counter: {'InLegalBERT tokenizer' if using_real_tokenizer() else 'heuristic'}")
    print(f"Loaded {len(records)} records from {len(files)} files\n")

    errors = 0
    warnings = 0
    ids = set()
    by_type = Counter()
    by_source = Counter()
    max_tok = 0

    for i, r in enumerate(records):
        for key in REQUIRED:
            if not r.get(key):
                print(f"  FAIL: record #{i} missing '{key}'")
                errors += 1
        text = r.get("text", "")
        if not text.strip():
            print(f"  FAIL: record #{i} has empty text")
            errors += 1
        rid = r.get("id")
        if rid in ids:
            print(f"  FAIL: duplicate id {rid}")
            errors += 1
        ids.add(rid)

        tok = count_tokens(text)
        max_tok = max(max_tok, tok)
        if tok > HARD_TOKEN_LIMIT:
            print(f"  FAIL: record #{i} ({r.get('source')}) = {tok} tokens > {HARD_TOKEN_LIMIT} limit")
            errors += 1
        elif tok > DEFAULT_MAX_TOKENS:
            warnings += 1

        by_type[r.get("doc_type")] += 1
        by_source[r.get("source")] += 1

    print("Chunks by doc_type:")
    for t, n in by_type.most_common():
        print(f"  {t:10} {n}")
    print("\nChunks by source:")
    for s, n in by_source.most_common():
        print(f"  {n:4}  {s}")

    print(f"\nMax tokens in any chunk: {max_tok} (target {DEFAULT_MAX_TOKENS}, hard limit {HARD_TOKEN_LIMIT})")
    print(f"Chunks over the {DEFAULT_MAX_TOKENS}-token target (still under limit): {warnings}")

    # Sample a few chunks per doc_type for eyeball review.
    print("\n--- random samples ---")
    by_type_records = {}
    for r in records:
        by_type_records.setdefault(r["doc_type"], []).append(r)
    random.seed(7)
    for t, recs in by_type_records.items():
        print(f"\n[{t}]")
        for r in random.sample(recs, min(2, len(recs))):
            snippet = r["text"][:220].replace("\n", " ")
            print(f"  ({r.get('source')} / {r.get('section')}) {snippet}...")

    print("\n" + ("RESULT: PASS" if errors == 0 else f"RESULT: FAIL ({errors} errors)"))
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
