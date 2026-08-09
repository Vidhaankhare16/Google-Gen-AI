#!/usr/bin/env python3
"""
Build the Legal EASE knowledge base: acquire (where automatable) -> parse -> chunk -> write JSONL.

Reads raw sources from ``knowledge_base/raw/<category>/`` and writes normalized, chunked records
to ``knowledge_base/processed/<category>.jsonl``. This stage is **vector-DB agnostic**: no
embeddings are computed here, so the corpus can be reused across ChromaDB and Qdrant (and across
embedding-model experiments) later.

Normalized record schema (one JSON object per line):
    id, text, doc_type, source, section, citation, jurisdiction, url, extra{...}

Run from the repo root:
    python scripts/build_knowledge_base.py
Sources needing manual/Kaggle download (BNS, other statutes, case law) are picked up automatically
once their files are placed under raw/ as documented in knowledge_base/sources.md.
"""
from __future__ import annotations

import json
import os
import sys
import uuid
import glob
from typing import Dict, List, Optional

# Windows consoles default to cp1252 and choke on legal unicode; force UTF-8 output.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# --- make backend/ importable so we can reuse the RAG chunker --------------- #
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO_ROOT, "backend"))

from rag.chunker import (  # noqa: E402
    chunk_statute,
    chunk_judgment,
    chunk_entry,
    count_tokens,
    using_real_tokenizer,
)

RAW = os.path.join(REPO_ROOT, "knowledge_base", "raw")
PROCESSED = os.path.join(REPO_ROOT, "knowledge_base", "processed")

JURISDICTION = "India"


def _record(text: str, doc_type: str, source: str, *, section: Optional[str] = None,
            citation: Optional[str] = None, url: Optional[str] = None,
            extra: Optional[Dict] = None) -> Dict:
    """Build one normalized chunk record."""
    return {
        "id": str(uuid.uuid4()),
        "text": text.strip(),
        "doc_type": doc_type,
        "source": source,
        "section": section,
        "citation": citation,
        "jurisdiction": JURISDICTION,
        "url": url,
        "extra": extra or {},
    }


# --------------------------------------------------------------------------- #
# Adapters (one per source type). Each returns a list of records.             #
# --------------------------------------------------------------------------- #
def adapt_constitution() -> List[Dict]:
    """Constitution of India from the structured COI.json (chunked by Article)."""
    path = os.path.join(RAW, "constitution", "COI.json")
    if not os.path.exists(path):
        return []
    data = json.load(open(path, encoding="utf-8"))
    articles = data[0] if isinstance(data, list) else data
    url = "https://github.com/Yash-Handa/The_Constitution_Of_India"
    records: List[Dict] = []
    for art in articles:
        art_no = str(art.get("ArtNo", "")).strip()
        name = (art.get("Name") or "").strip()
        parts = [f"Article {art_no}. {name}".strip()]
        if art.get("ArtDesc"):
            parts.append(art["ArtDesc"].strip())
        for cl in art.get("Clauses", []) or []:
            cno = str(cl.get("ClauseNo", "")).strip()
            desc = (cl.get("ClauseDesc") or "").strip()
            parts.append(f"({cno}) {desc}" if cno else desc)
        body = "\n".join(p for p in parts if p)
        label = f"Article {art_no}" if art_no else "Preamble"
        for piece in chunk_entry(body):
            records.append(_record(piece, "statute", "Constitution of India",
                                   section=label, url=url,
                                   extra={"act": "Constitution of India"}))
    return records


# Map a bare-act filename stem -> (nice source name, citation, url).
_BARE_ACT_META = {
    "indian_contract_act_1872": ("The Indian Contract Act, 1872", "Act No. 9 of 1872",
                                 "https://www.indiacode.nic.in/handle/123456789/2187"),
    "transfer_of_property_act_1882": ("The Transfer of Property Act, 1882", "Act No. 4 of 1882",
                                      "https://www.indiacode.nic.in/handle/123456789/2338"),
    "consumer_protection_act_2019": ("The Consumer Protection Act, 2019", "Act No. 35 of 2019",
                                     "https://www.indiacode.nic.in/handle/123456789/12563"),
    "information_technology_act_2000": ("The Information Technology Act, 2000", "Act No. 21 of 2000",
                                        "https://www.indiacode.nic.in/handle/123456789/1999"),
    "arbitration_and_conciliation_act_1996": ("The Arbitration and Conciliation Act, 1996",
                                              "Act No. 26 of 1996",
                                              "https://www.indiacode.nic.in/handle/123456789/1978"),
}


def adapt_bare_acts() -> List[Dict]:
    """Any plain-text bare act in raw/statutes/*.txt, chunked by Section header.

    Metadata (title, act number, source URL) comes from raw/statutes/manifest.json when present
    (written by fetch_statutes.py), otherwise falls back to _BARE_ACT_META or the filename.
    """
    stat_dir = os.path.join(RAW, "statutes")
    manifest: Dict = {}
    mpath = os.path.join(stat_dir, "manifest.json")
    if os.path.exists(mpath):
        manifest = json.load(open(mpath, encoding="utf-8"))

    records: List[Dict] = []
    for path in sorted(glob.glob(os.path.join(stat_dir, "*.txt"))):
        stem = os.path.splitext(os.path.basename(path))[0].lower()
        meta = manifest.get(stem)
        if meta:
            source = meta.get("source") or stem
            citation = f"Act No. {meta['act_number']}" if meta.get("act_number") else None
            url = meta.get("url") or None
        else:
            source, citation, url = _BARE_ACT_META.get(
                stem, (stem.replace("_", " ").title(), None, None))
        text = open(path, encoding="utf-8", errors="ignore").read()
        for ch in chunk_statute(text):
            records.append(_record(ch.text, "statute", source, section=ch.section,
                                   citation=citation, url=url, extra={"act": source}))
    return records


def adapt_bns() -> List[Dict]:
    """Bharatiya Nyaya Sanhita, 2023 from a Kaggle CSV (columns vary; best-effort)."""
    import csv
    records: List[Dict] = []
    for path in glob.glob(os.path.join(RAW, "statutes", "bns*.csv")):
        with open(path, encoding="utf-8", errors="ignore") as f:
            for row in csv.DictReader(f):
                # tolerate different column namings
                sec = row.get("Section") or row.get("section") or row.get("section_number") or ""
                title = row.get("Title") or row.get("title") or row.get("section_title") or ""
                desc = (row.get("Description") or row.get("description")
                        or row.get("section_desc") or row.get("Text") or "")
                body = f"Section {sec}. {title}\n{desc}".strip()
                if not body:
                    continue
                for piece in chunk_entry(body):
                    records.append(_record(piece, "statute", "Bharatiya Nyaya Sanhita, 2023",
                                           section=f"Section {sec}".strip(),
                                           citation="Act No. 45 of 2023",
                                           url="https://www.indiacode.nic.in/handle/123456789/20062",
                                           extra={"act": "BNS 2023"}))
    return records


def adapt_glossary() -> List[Dict]:
    path = os.path.join(RAW, "glossary", "glossary.json")
    if not os.path.exists(path):
        return []
    data = json.load(open(path, encoding="utf-8"))
    records: List[Dict] = []
    for t in data.get("terms", []):
        term, definition = t.get("term", ""), t.get("definition", "")
        statute = t.get("statute")
        text = f"{term}: {definition}"
        if statute:
            text += f" (Relevant law: {statute}.)"
        for piece in chunk_entry(text):
            records.append(_record(piece, "glossary", "Legal glossary (Legal EASE)",
                                   section=term, citation=statute,
                                   extra={"category": t.get("category")}))
    return records


def adapt_redflags() -> List[Dict]:
    path = os.path.join(RAW, "redflags", "redflags.json")
    if not os.path.exists(path):
        return []
    data = json.load(open(path, encoding="utf-8"))
    records: List[Dict] = []
    for rf in data.get("red_flags", []):
        pattern = rf.get("pattern", "")
        text = (f"Red-flag clause: {pattern}. "
                f"Why it is risky: {rf.get('why_risky','')} "
                f"Severity: {rf.get('severity','')}.")
        if rf.get("statute"):
            text += f" Relevant law: {rf['statute']}."
        for piece in chunk_entry(text):
            records.append(_record(piece, "redflag", "Red-flag reference (Legal EASE)",
                                   section=pattern, citation=rf.get("statute"),
                                   extra={"severity": rf.get("severity"),
                                          "category": rf.get("category")}))
    return records


def adapt_templates() -> List[Dict]:
    path = os.path.join(RAW, "templates", "templates.json")
    if not os.path.exists(path):
        return []
    data = json.load(open(path, encoding="utf-8"))
    records: List[Dict] = []
    for tpl in data.get("templates", []):
        name = tpl.get("name", "")
        ctype = tpl.get("contract_type")
        for cl in tpl.get("clauses", []):
            text = f"{name} — standard '{cl.get('clause','')}' clause: {cl.get('standard','')}"
            for piece in chunk_entry(text):
                records.append(_record(piece, "template", f"Model contract: {name}",
                                       section=cl.get("clause"),
                                       extra={"contract_type": ctype}))
    return records


def adapt_caselaw() -> List[Dict]:
    """
    Curated case-law from raw/caselaw/*.json (list of {title, court, year, citation, text, url}).
    Filters to contract/consumer/tenancy topics. Ready for Kaggle/ILDC drops; no-op if empty.
    """
    KEYWORDS = ("contract", "agreement", "lease", "tenan", "rent", "consumer", "arbitration",
                "indemnit", "damages", "breach", "employment", "unfair", "clause")
    records: List[Dict] = []
    for path in glob.glob(os.path.join(RAW, "caselaw", "*.json")):
        try:
            data = json.load(open(path, encoding="utf-8"))
        except Exception:
            continue
        for case in (data if isinstance(data, list) else data.get("cases", [])):
            text = case.get("text") or case.get("judgment") or ""
            if not text:
                continue
            # Safety filter over the FULL text (not just the head): topic keywords in a judgment
            # often appear well after the procedural header. Ingesters already pre-curate, so this
            # only guards against an unfiltered raw drop.
            blob = (case.get("title", "") + " " + text).lower()
            if not any(k in blob for k in KEYWORDS):
                continue
            try:
                judgment_chunks = chunk_judgment(text)
            except Exception as e:  # one malformed judgment shouldn't drop the whole category
                print(f"  ! skipping a judgment in {os.path.basename(path)}: {e}")
                continue
            for ch in judgment_chunks:
                records.append(_record(
                    ch.text, "judgment", case.get("title", "Judgment"),
                    citation=case.get("citation"), url=case.get("url"),
                    extra={"court": case.get("court"), "year": case.get("year"),
                           "judges": case.get("extra_judges"),
                           "summary": (case.get("summary") or "")[:500],
                           "source_dataset": case.get("source_dataset")}))
    return records


# --------------------------------------------------------------------------- #
# Orchestration                                                               #
# --------------------------------------------------------------------------- #
# category name -> (output filename, list of adapter callables)
PIPELINE = {
    "statutes": ("statutes.jsonl", [adapt_constitution, adapt_bare_acts, adapt_bns]),
    "caselaw": ("caselaw.jsonl", [adapt_caselaw]),
    "glossary": ("glossary.jsonl", [adapt_glossary]),
    "templates": ("templates.jsonl", [adapt_templates]),
    "redflags": ("redflags.jsonl", [adapt_redflags]),
}


def _write_jsonl(path: str, records: List[Dict]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def main() -> None:
    os.makedirs(PROCESSED, exist_ok=True)
    print(f"Token counter: {'InLegalBERT tokenizer' if using_real_tokenizer() else 'heuristic (transformers not installed)'}")
    grand_total = 0
    for category, (fname, adapters) in PIPELINE.items():
        records: List[Dict] = []
        for adapter in adapters:
            try:
                records.extend(adapter())
            except Exception as e:  # one bad source shouldn't kill the build
                print(f"  ! {category}/{adapter.__name__} failed: {e}")
        out = os.path.join(PROCESSED, fname)
        _write_jsonl(out, records)
        toks = [count_tokens(r["text"]) for r in records] or [0]
        print(f"[{category:9}] {len(records):5d} chunks  "
              f"(max {max(toks)} tok, avg {sum(toks)//max(len(toks),1)} tok) -> {fname}")
        grand_total += len(records)
    print(f"\nTotal: {grand_total} chunks written to {PROCESSED}")


if __name__ == "__main__":
    main()
