# Knowledge Base — Sources & Provenance

This file records **every source** used to build the Legal EASE RAG knowledge base, with its
URL, license, and how it is acquired/processed. Update it whenever a source is added.

> Legal principle: Indian statutes and court judgments are government works and are broadly
> reproducible, but each *host/dataset* may attach its own terms. Record them here before use.

## Layout
- `raw/` — original downloaded/authored source files (git-ignored; large or license-restricted).
- `processed/` — normalized, chunked JSONL (one file per category) produced by
  `scripts/build_knowledge_base.py`. This is what gets embedded/indexed later.

## Normalized chunk schema (in `processed/*.jsonl`)
```
id, text, doc_type, source, section, citation, jurisdiction, url, extra{...}
```
`doc_type ∈ {statute, judgment, glossary, template, redflag}`

---

## Category 1 — Statutes & codes

Acquired programmatically via `scripts/fetch_statutes.py` from the public HuggingFace dataset
**`geekyrakshit/indian-legal-acts`** (883 central acts, full text in Markdown, sourced from
India Code — no login required). The fetcher cleans the Markdown and writes `raw/statutes/<slug>.txt`
plus `raw/statutes/manifest.json` (act title, act number, enactment date, India Code URL).

| Source | URL | License | Status |
|---|---|---|---|
| Constitution of India (structured JSON) | https://github.com/Yash-Handa/The_Constitution_Of_India (`COI.json`) | Public data / MIT repo | ✅ ingested (**43-article subset**; replace `COI.json` with a full-articles source to enrich) |
| The Indian Contract Act, 1872 | HF `geekyrakshit/indian-legal-acts` → India Code a1872-9 | Public domain (Indian statute) | ✅ ingested (255 chunks) |
| The Transfer of Property Act, 1882 | HF `geekyrakshit/indian-legal-acts` | Public domain | ✅ ingested |
| The Consumer Protection Act, 2019 | HF `geekyrakshit/indian-legal-acts` | Govt work | ✅ ingested |
| The Information Technology Act, 2000 | HF `geekyrakshit/indian-legal-acts` | Govt work | ✅ ingested |
| The Arbitration & Conciliation Act, 1996 | HF `geekyrakshit/indian-legal-acts` | Govt work | ✅ ingested |
| Specific Relief / Sale of Goods / Partnership / Registration / Negotiable Instruments Acts | HF `geekyrakshit/indian-legal-acts` | Govt work | ✅ ingested (bonus contract-relevant acts) |
| The Bharatiya Nyaya Sanhita, 2023 (BNS) | HF `geekyrakshit/indian-legal-acts` → India Code | Govt work | ✅ ingested (442 chunks). The related BNSS (procedure) and BSA (evidence) 2023 codes are also in the dataset — add to `TARGETS` if wanted. |

**Bare-act adapter contract:** any plain-text statute in `raw/statutes/*.txt` whose sections start
with a line like `1.`, `2.`, `Section 3.`, `73.` is chunked by section automatically (TOC stubs
are deduped against enacted bodies). To add more acts, extend `TARGETS` in `fetch_statutes.py`
(the dataset has 883 central acts) or drop your own `.txt` files in `raw/statutes/`.

## Category 2 — Case law & verdicts

Acquired via `scripts/ingest_kaggle_pdfs.py` from the **Kaggle "SC Judgments India (1950–2024)"**
dataset, which ships as ~26k judgment PDFs in per-year folders under
`raw/caselaw/supreme_court_judgments/<year>/`. The ingester samples across all years, extracts text
with PyMuPDF, reads case name + date from the filename and the `Equivalent citations:` / `Bench:`
lines from each judgment header, topic-filters (contract/consumer/tenancy/commercial), dedupes by
case name, caps the count, and writes `raw/caselaw/kaggle_sc_curated.json`.

| Source | URL | License | Status |
|---|---|---|---|
| SC Judgments India 1950–2024 (curated subset) | https://www.kaggle.com/datasets/adarshsingh0903/legal-dataset-sc-judgments-india-19502024 | Kaggle terms (research) | ✅ ingested (**249 judgments, 222 with citations** → ~7.2k chunks) |
| Indian SC judgments (HF, no citations) | https://huggingface.co/datasets/ninadn/indian-legal | Research use | ⏸ retired stopgap — `fetch_caselaw.py` still available; superseded by the Kaggle set above (`curated_judgments.json.bak`). |
| ILDC (Indian Legal Documents Corpus) | https://github.com/Exploration-Lab/CJPE | Research / by-request | ⏳ optional |

### Re-linking / expanding the Kaggle "SC Judgments 1950–2024" dataset
The dataset ships as **PDFs in year folders** (not CSV), so it is ingested by
`scripts/ingest_kaggle_pdfs.py` (not the CSV converter `ingest_kaggle_scjudgments.py`, which is
kept for tabular datasets). To (re)build or grow the case-law set:
1. Ensure the PDFs are extracted under `knowledge_base/raw/caselaw/supreme_court_judgments/<year>/`.
2. `python scripts/ingest_kaggle_pdfs.py`  — defaults: keep 250, scan ≤3000, ≥2 topic keywords,
   ≤40 pages/PDF. Grow with `--max 400 --max-scan 6000`, or `--no-filter` to skip topic filtering.
3. `python scripts/build_knowledge_base.py && python scripts/validate_kb.py`.

> Housekeeping: the 6.8 GB `raw/caselaw/archive.zip` can be deleted once extraction is confirmed
> (it is git-ignored either way).

## Category 3 — Legal glossary

| Source | License | Acquisition | Status |
|---|---|---|---|
| Curated plain-English legal glossary (authored for this project) | Ours (CC0) | `raw/glossary/glossary.json` → `glossary` adapter | ✅ authored |

## Category 4 — Templates & red-flags

| Source | License | Acquisition | Status |
|---|---|---|---|
| Model contract clause templates (authored, standard forms) | Ours (CC0) | `raw/templates/templates.json` → `template` adapter | ✅ authored |
| Red-flag clause reference (authored: pattern → why risky → statute) | Ours (CC0) | `raw/redflags/redflags.json` → `redflag` adapter | ✅ authored |

---

## Reproduce
```bash
# from repo root
python scripts/build_knowledge_base.py      # acquire (where automatable) + parse + chunk → processed/*.jsonl
python scripts/validate_kb.py               # verify counts, metadata, token limits
```
Statutes/case-law that need manual/Kaggle download: place the files under `raw/<category>/`
as noted above, then re-run `build_knowledge_base.py`.
