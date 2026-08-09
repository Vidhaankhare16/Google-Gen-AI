#!/usr/bin/env python3
"""
Fetch full-text Indian central bare acts from the public HuggingFace dataset
``geekyrakshit/indian-legal-acts`` (India Code source, no login required) and save cleaned
plain text to ``knowledge_base/raw/statutes/<slug>.txt`` plus a metadata manifest.

These files are then chunked by ``build_knowledge_base.py`` (the ``bare_act`` adapter chunks by
Section header, deduping TOC stubs against enacted bodies).

Run from repo root:
    python scripts/fetch_statutes.py
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(REPO_ROOT, "knowledge_base", "raw", "statutes")
DATASET = "geekyrakshit/indian-legal-acts"
SEARCH_URL = "https://datasets-server.huggingface.co/search"

# Target acts most relevant to analysing contracts/agreements. (query, canonical title, slug)
TARGETS = [
    ("The Indian Contract Act, 1872",            "indian_contract_act_1872"),
    ("The Transfer of Property Act, 1882",       "transfer_of_property_act_1882"),
    ("The Consumer Protection Act, 2019",        "consumer_protection_act_2019"),
    ("The Information Technology Act, 2000",      "information_technology_act_2000"),
    ("The Arbitration and Conciliation Act, 1996","arbitration_and_conciliation_act_1996"),
    ("The Specific Relief Act, 1963",            "specific_relief_act_1963"),
    ("The Sale of Goods Act, 1930",              "sale_of_goods_act_1930"),
    ("The Indian Partnership Act, 1932",         "indian_partnership_act_1932"),
    ("The Registration Act, 1908",               "registration_act_1908"),
    ("The Negotiable Instruments Act, 1881",     "negotiable_instruments_act_1881"),
    ("The Bharatiya Nyaya Sanhita, 2023",        "bharatiya_nyaya_sanhita_2023"),
]


def clean_markdown(md: str) -> str:
    """Strip markdown/formatting artifacts so the text chunks cleanly by section header."""
    md = md.encode("utf-8", "ignore").decode("utf-8")           # drop lone surrogates
    md = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", md)            # [text](url) -> text
    md = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", md)                # images
    md = re.sub(r"(?m)^#{1,6}\s*", "", md)                      # heading markers
    md = re.sub(r"(?m)^\s*_{2,}\s*$", "", md)                   # ____ horizontal rules
    md = re.sub(r"\*{1,3}([^*]+)\*{1,3}", r"\1", md)            # bold/italic
    md = re.sub(r"_([^_\n]+)_", r"\1", md)                      # _emphasis_
    md = re.sub(r"[ \t]+", " ", md)                             # collapse spaces
    md = re.sub(r"\n{3,}", "\n\n", md)                          # collapse blank lines
    return md.strip()


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def fetch_act(query: str):
    """Return the best-matching dataset row dict for an act title, or None."""
    url = (f"{SEARCH_URL}?dataset={urllib.parse.quote(DATASET)}"
           f"&config=default&split=central&query={urllib.parse.quote(query)}")
    req = urllib.request.Request(url, headers={"User-Agent": "LegalEaseKB/1.0"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.load(resp)
    rows = [r["row"] for r in data.get("rows", [])]
    if not rows:
        return None
    target = _norm(query)
    # Prefer an exact normalized Short Title match; else the longest-text row containing the query.
    exact = [r for r in rows if _norm(r.get("Short Title", "")) == target]
    if exact:
        return exact[0]
    contains = [r for r in rows if target[:20] in _norm(r.get("Short Title", ""))]
    pool = contains or rows
    return max(pool, key=lambda r: len(r.get("Markdown") or ""))


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    manifest_path = os.path.join(OUT_DIR, "manifest.json")
    manifest = {}
    if os.path.exists(manifest_path):
        manifest = json.load(open(manifest_path, encoding="utf-8"))

    for query, slug in TARGETS:
        try:
            row = fetch_act(query)
        except Exception as e:
            print(f"  ! {query}: fetch error {e}")
            continue
        if not row:
            print(f"  ! {query}: no match")
            continue
        text = clean_markdown(row.get("Markdown") or "")
        if len(text) < 500:
            print(f"  ! {query}: text too short ({len(text)} chars), skipping")
            continue
        out = os.path.join(OUT_DIR, f"{slug}.txt")
        with open(out, "w", encoding="utf-8") as f:
            f.write(text)
        manifest[slug] = {
            "source": row.get("Short Title", query).strip(),
            "act_number": str(row.get("Act Number", "")).strip(),
            "enactment_date": row.get("Enactment Date", ""),
            "url": row.get("View", ""),
        }
        print(f"  ok  {row.get('Short Title'):45} {len(text):>7} chars -> {slug}.txt")
        time.sleep(0.5)  # be polite to the API

    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    print(f"\nWrote {len(manifest)} acts + manifest.json to {OUT_DIR}")


if __name__ == "__main__":
    main()
