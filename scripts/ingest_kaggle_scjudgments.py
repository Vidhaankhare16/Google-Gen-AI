#!/usr/bin/env python3
"""
Normalize the Kaggle "SC Judgments India (1950-2024)" dataset into the case-law JSON that the
knowledge-base pipeline already consumes.

    Kaggle:  adarshsingh0903/legal-dataset-sc-judgments-india-19502024

This dataset (unlike the HF ninadn set already ingested) ships real case names, citations, and
dates. This script is **schema-tolerant**: it auto-detects the relevant columns whatever they are
named, filters to contract/consumer/tenancy/commercial judgments, caps the count, and writes
``knowledge_base/raw/caselaw/kaggle_sc_curated.json`` in the
``{title, court, year, citation, text, url}`` shape that ``build_knowledge_base.py``'s
``caselaw`` adapter reads. After running it, just rebuild the KB.

Usage (from repo root):
    # 1) download the Kaggle files into raw/caselaw/kaggle_sc/ (see linking steps below), then:
    python scripts/ingest_kaggle_scjudgments.py --dry-run     # inspect detected columns first
    python scripts/ingest_kaggle_scjudgments.py               # write the normalized JSON
    python scripts/build_knowledge_base.py && python scripts/validate_kb.py

Column overrides (if auto-detect picks wrong): --text-col, --title-col, --citation-col,
--date-col, --court-col, --url-col. See --help.
"""
from __future__ import annotations

import argparse
import csv
import glob
import json
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# Judgment text can be huge; raise the CSV field size limit (guard against Windows OverflowError).
try:
    csv.field_size_limit(sys.maxsize)
except OverflowError:
    csv.field_size_limit(2**31 - 1)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_INPUT = os.path.join(REPO_ROOT, "knowledge_base", "raw", "caselaw", "kaggle_sc")
DEFAULT_OUT = os.path.join(REPO_ROOT, "knowledge_base", "raw", "caselaw", "kaggle_sc_curated.json")

# Candidate column names (normalized: lowercased, alnum only) for each logical field.
CANDIDATES = {
    "text":     ["text", "judgment", "judgmenttext", "fulltext", "casetext", "content",
                 "body", "rawtext", "judgement", "judgementtext", "case"],
    "title":    ["title", "casetitle", "casename", "name", "petitionervsrespondent",
                 "caseno", "diaryno", "matter"],
    "citation": ["citation", "cite", "neutralcitation", "equivalentcitation", "citations"],
    "date":     ["date", "judgmentdate", "decisiondate", "dateofjudgment", "judgementdate", "year"],
    "court":    ["court", "courtname", "bench"],
    "url":      ["url", "sourceurl", "link", "kanoonurl", "source", "docurl"],
}

KEYWORDS = ("contract", "agreement", "lease", "tenan", " rent", "consumer", "arbitration",
            "indemnit", "damages", "breach of", "employment", "unfair", "clause",
            "specific performance", "landlord", "sale of goods", "negotiable instrument",
            "partnership", "liquidated")


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def detect_columns(headers):
    """Map each logical field -> actual header, by exact then substring match on normalized names."""
    norm_map = {_norm(h): h for h in headers}
    result = {}
    for field, cands in CANDIDATES.items():
        found = None
        for c in cands:                       # exact normalized match first
            if c in norm_map:
                found = norm_map[c]
                break
        if not found:                         # then substring match
            for nh, h in norm_map.items():
                if any(c in nh for c in cands):
                    found = h
                    break
        result[field] = found
    return result


def iter_rows(input_dir):
    """Yield dict rows from every .csv/.json/.jsonl/.parquet under input_dir."""
    files = []
    for ext in ("*.csv", "*.json", "*.jsonl", "*.parquet"):
        files += glob.glob(os.path.join(input_dir, "**", ext), recursive=True)
    if not files:
        return
    for path in sorted(files):
        low = path.lower()
        if low.endswith(".csv"):
            with open(path, encoding="utf-8", errors="ignore", newline="") as f:
                for row in csv.DictReader(f):
                    yield row
        elif low.endswith(".jsonl"):
            with open(path, encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            yield json.loads(line)
                        except Exception:
                            pass
        elif low.endswith(".json"):
            try:
                data = json.load(open(path, encoding="utf-8", errors="ignore"))
            except Exception:
                continue
            for row in (data if isinstance(data, list) else data.get("data", [])):
                if isinstance(row, dict):
                    yield row
        elif low.endswith(".parquet"):
            try:
                import pandas as pd  # optional
            except ImportError:
                print(f"  ! {os.path.basename(path)} is parquet; install pandas+pyarrow to read it, "
                      f"or export it to CSV.")
                continue
            for row in pd.read_parquet(path).to_dict("records"):
                yield row


def _year(val: str):
    m = re.search(r"(1[89]\d\d|20\d\d)", str(val or ""))
    return int(m.group(1)) if m else None


def main() -> None:
    ap = argparse.ArgumentParser(description="Normalize Kaggle SC judgments into the KB case-law format.")
    ap.add_argument("--input", default=DEFAULT_INPUT, help="dir with the downloaded Kaggle files")
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--max", type=int, default=300, help="max judgments to keep")
    ap.add_argument("--min-hits", type=int, default=2, help="min topic-keyword hits to keep a case")
    ap.add_argument("--no-filter", action="store_true", help="keep all judgments (skip topic filter)")
    ap.add_argument("--dry-run", action="store_true", help="report detected columns + counts, write nothing")
    for f in CANDIDATES:
        ap.add_argument(f"--{f}-col", default=None, help=f"override the '{f}' column name")
    args = ap.parse_args()

    if not os.path.isdir(args.input):
        print(f"Input dir not found: {args.input}\n"
              f"Download the Kaggle dataset into it first (see the script header / linking steps).")
        sys.exit(1)

    # Peek at the first row to detect columns.
    rows_iter = iter_rows(args.input)
    try:
        first = next(rows_iter)
    except StopIteration:
        print(f"No .csv/.json/.jsonl/.parquet files found under {args.input}")
        sys.exit(1)

    cols = detect_columns(list(first.keys()))
    for f in CANDIDATES:                      # apply user overrides
        override = getattr(args, f"{f}_col")
        if override:
            cols[f] = override

    print("Detected columns:")
    for f, c in cols.items():
        print(f"  {f:9}-> {c}")
    print(f"All headers: {list(first.keys())}")

    if not cols["text"]:
        print("\n! Could not find a judgment-text column. Re-run with --text-col <name>.")
        sys.exit(1)

    kept, scanned = [], 0
    # re-chain the first row we already consumed
    import itertools
    for row in itertools.chain([first], rows_iter):
        scanned += 1
        text = str(row.get(cols["text"]) or "").strip()
        if len(text) < 400:
            continue
        if not args.no_filter:
            low = text.lower()
            if sum(1 for k in KEYWORDS if k in low) < args.min_hits:
                continue
        title = str(row.get(cols["title"]) or "").strip() if cols["title"] else ""
        kept.append({
            "title": title or "Supreme Court of India judgment",
            "court": (str(row.get(cols["court"])).strip() if cols["court"] else "Supreme Court of India"),
            "year": _year(row.get(cols["date"])) if cols["date"] else None,
            "citation": (str(row.get(cols["citation"])).strip() if cols["citation"] else None),
            "text": text,
            "url": (str(row.get(cols["url"])).strip() if cols["url"] else None),
            "source_dataset": "kaggle:adarshsingh0903/legal-dataset-sc-judgments-india-19502024",
        })
        if len(kept) >= args.max:
            break

    print(f"\nScanned {scanned} rows, kept {len(kept)} judgments"
          f"{'' if args.no_filter else ' (topic-filtered)'}.")
    if args.dry_run:
        print("Dry run: nothing written. Sample titles:")
        for c in kept[:5]:
            print(f"  - {c['title'][:80]}  [{c.get('citation') or 'no citation'}]")
        return

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(kept, f, ensure_ascii=False)
    print(f"Wrote {len(kept)} judgments -> {args.out}")
    print("Next: python scripts/build_knowledge_base.py && python scripts/validate_kb.py")


if __name__ == "__main__":
    main()
