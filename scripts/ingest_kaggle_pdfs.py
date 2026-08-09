#!/usr/bin/env python3
"""
Ingest the Kaggle "SC Judgments India (1950-2024)" dataset, which ships as ~26k PDFs organised in
per-year folders:  raw/caselaw/supreme_court_judgments/<year>/<Case_Name>_on_<date>_<n>.PDF

This is far too many to ingest wholesale, so this script:
  * samples across all years (shuffled with a fixed seed for reproducibility),
  * extracts text quickly with PyMuPDF (fitz),
  * pulls rich metadata for free: case name + date from the filename, and the
    "Equivalent citations:" and "Bench:" lines from the judgment header,
  * keeps only contract/consumer/tenancy/commercial judgments (topic filter),
  * caps the count and dedupes by case name,
  * writes raw/caselaw/kaggle_sc_curated.json in the standard case-law shape that
    build_knowledge_base.py's `caselaw` adapter already consumes.

Run from repo root:
    python scripts/ingest_kaggle_pdfs.py                 # sensible defaults
    python scripts/ingest_kaggle_pdfs.py --max 400 --max-scan 6000
    python scripts/build_knowledge_base.py && python scripts/validate_kb.py
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import random
import re
import sys
import time

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import fitz  # PyMuPDF

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_INPUT = os.path.join(REPO_ROOT, "knowledge_base", "raw", "caselaw",
                             "supreme_court_judgments")
DEFAULT_OUT = os.path.join(REPO_ROOT, "knowledge_base", "raw", "caselaw",
                           "kaggle_sc_curated.json")

KEYWORDS = ("contract", "agreement", "lease", "tenan", " rent", "consumer", "arbitration",
            "indemnit", "damages", "breach of", "employment", "unfair", "clause",
            "specific performance", "landlord", "sale of goods", "negotiable instrument",
            "partnership", "liquidated", "insurance", "guarantee")

FNAME_RE = re.compile(r"^(?P<name>.+?)_on_(?P<date>\d{1,2}_[A-Za-z]+_\d{4})(?:_(?P<idx>\d+))?$")
CIT_RE = re.compile(r"Equivalent citations?\s*:?\s*(.+)", re.I)
BENCH_RE = re.compile(r"Bench\s*:?\s*(.+)", re.I)


def list_pdfs(input_dir):
    """All PDF paths under numeric year folders only (ignores stray files like script.py)."""
    paths = []
    for entry in sorted(os.listdir(input_dir)):
        ydir = os.path.join(input_dir, entry)
        if os.path.isdir(ydir) and re.fullmatch(r"\d{4}", entry):
            paths += glob.glob(os.path.join(ydir, "*.PDF"))
            paths += glob.glob(os.path.join(ydir, "*.pdf"))
    return paths


def extract(path, max_pages):
    try:
        doc = fitz.open(path)
    except Exception:
        return ""
    parts = []
    for i, page in enumerate(doc):
        if i >= max_pages:
            break
        parts.append(page.get_text())
    doc.close()
    text = "\n".join(parts)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def meta_from(path, text):
    stem = os.path.splitext(os.path.basename(path))[0]
    year = os.path.basename(os.path.dirname(path))
    m = FNAME_RE.match(stem)
    name = m.group("name").replace("_", " ").strip() if m else stem.replace("_", " ")
    head = text[:600]
    cit = CIT_RE.search(head)
    bench = BENCH_RE.search(head)
    citation = cit.group(1).splitlines()[0].strip() if cit else None
    judges = bench.group(1).splitlines()[0].strip() if bench else None
    return name, int(year) if year.isdigit() else None, citation, judges


def main() -> None:
    ap = argparse.ArgumentParser(description="Ingest Kaggle SC judgment PDFs into the KB.")
    ap.add_argument("--input", default=DEFAULT_INPUT)
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--max", type=int, default=250, help="max judgments to keep")
    ap.add_argument("--max-scan", type=int, default=3000, help="max PDFs to open")
    ap.add_argument("--min-hits", type=int, default=2, help="min topic-keyword hits to keep")
    ap.add_argument("--max-pages", type=int, default=40, help="pages to read per PDF")
    ap.add_argument("--no-filter", action="store_true", help="keep all (skip topic filter)")
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()

    if not os.path.isdir(args.input):
        print(f"Input dir not found: {args.input}")
        sys.exit(1)

    paths = list_pdfs(args.input)
    print(f"Found {len(paths)} PDFs across year folders. Sampling (seed={args.seed})...")
    random.seed(args.seed)
    random.shuffle(paths)

    kept, seen, opened = [], set(), 0
    t0 = time.time()
    for path in paths:
        if opened >= args.max_scan or len(kept) >= args.max:
            break
        opened += 1
        text = extract(path, args.max_pages)
        if len(text) < 400:
            continue
        if not args.no_filter:
            low = text.lower()
            if sum(1 for k in KEYWORDS if k in low) < args.min_hits:
                continue
        name, year, citation, judges = meta_from(path, text)
        key = re.sub(r"[^a-z0-9]", "", name.lower())
        if key in seen:                      # dedupe multi-part / repeated cases
            continue
        seen.add(key)
        kept.append({
            "title": name or "Supreme Court of India judgment",
            "court": "Supreme Court of India",
            "year": year,
            "citation": citation,
            "text": text,
            "url": None,
            "extra_judges": judges,
            "source_dataset": "kaggle:adarshsingh0903/legal-dataset-sc-judgments-india-19502024",
        })
        if opened % 250 == 0:
            print(f"  opened={opened} kept={len(kept)} ({time.time()-t0:.0f}s)")

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(kept, f, ensure_ascii=False)
    print(f"\nOpened {opened} PDFs, kept {len(kept)} judgments in {time.time()-t0:.0f}s -> {args.out}")
    if kept:
        print("Sample:")
        for c in kept[:5]:
            print(f"  - {c['title'][:60]} [{c.get('citation') or 'no citation'}] ({c.get('year')})")


if __name__ == "__main__":
    main()
