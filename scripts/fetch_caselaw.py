#!/usr/bin/env python3
"""
Fetch a curated subset of Indian court judgments from the public HuggingFace dataset
``ninadn/indian-legal`` (columns: Text, Summary; ~7k Supreme Court judgments) and save the ones
relevant to contract / consumer / tenancy / commercial disputes to
``knowledge_base/raw/caselaw/curated_judgments.json``.

The ``caselaw`` adapter in build_knowledge_base.py then chunks these by paragraph.

Why a curated subset: full judgments are long (tens of chunks each). Filtering to relevant topics
and capping the count keeps the corpus balanced and the later Chroma-vs-Qdrant comparison tractable.

Run from repo root:
    python scripts/fetch_caselaw.py
"""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.parse
import urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(REPO_ROOT, "knowledge_base", "raw", "caselaw")
DATASET = "ninadn/indian-legal"
ROWS_URL = "https://datasets-server.huggingface.co/rows"

# A judgment is kept if its text matches enough of these topic cues.
KEYWORDS = ("contract", "agreement", "lease", "tenan", " rent", "consumer", "arbitration",
            "indemnit", "damages", "breach of", "employment", "unfair", "clause",
            "specific performance", "landlord", "sale of goods", "negotiable instrument",
            "partnership", "liquidated")

MAX_CASES = 120        # cap curated judgments to keep the corpus balanced
MAX_PAGES = 40         # scan up to 40*100 = 4000 source rows
PAGE = 100


def _title_from(text: str) -> str:
    """Derive a short readable title from the first meaningful line of the judgment."""
    for line in text.splitlines():
        line = line.strip()
        if len(line) > 12:
            return "Indian judgment: " + re.sub(r"\s+", " ", line)[:90]
    return "Indian judgment"


def fetch_page(offset: int):
    url = (f"{ROWS_URL}?dataset={urllib.parse.quote(DATASET)}"
           f"&config=default&split=train&offset={offset}&length={PAGE}")
    req = urllib.request.Request(url, headers={"User-Agent": "LegalEaseKB/1.0"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.load(resp).get("rows", [])


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    kept = []
    scanned = 0
    for page in range(MAX_PAGES):
        try:
            rows = fetch_page(page * PAGE)
        except Exception as e:
            print(f"  ! page {page} error: {e}")
            continue
        if not rows:
            break
        for r in rows:
            scanned += 1
            row = r["row"]
            text = (row.get("Text") or "").strip()
            if len(text) < 400:
                continue
            low = text.lower()
            hits = sum(1 for k in KEYWORDS if k in low)
            if hits < 2:            # require at least two topic cues to reduce noise
                continue
            kept.append({
                "title": _title_from(text),
                "text": text,
                "summary": (row.get("Summary") or "").strip(),
                "source_dataset": DATASET,
                "url": "https://huggingface.co/datasets/ninadn/indian-legal",
            })
            if len(kept) >= MAX_CASES:
                break
        print(f"  page {page:2d}: scanned={scanned} kept={len(kept)}")
        if len(kept) >= MAX_CASES:
            break

    out = os.path.join(OUT_DIR, "curated_judgments.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(kept, f, ensure_ascii=False)
    print(f"\nSaved {len(kept)} curated judgments (scanned {scanned}) -> {out}")


if __name__ == "__main__":
    main()
