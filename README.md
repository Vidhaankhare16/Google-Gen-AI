# Legal EASE — read the margin, not just the contract

Legal EASE reads a contract you were handed, marks the clauses that work against you, and
puts the Indian statute or judgment that says so right beside each finding. Answers are
retrieved from a real corpus of Indian law rather than recalled by the model.

## What it does

- **Reads a PDF contract**, including scanned pages (Gemini Vision OCR fallback).
- **Scores the risk 0–10** and lists what to push back on, worst first, with severities.
- **Cites Indian law** — every finding and every chat answer is grounded in retrieved
  statutes, Supreme Court judgments, red-flag clause patterns and definitions.
- **Answers questions about your document** from the retrieved clauses, not the whole file.
- **WhatsApp intake** (optional, via Twilio).

## How the RAG works

Two retrieval sources are combined per query:

1. **Your uploaded document** — chunked, embedded and indexed into a `user_docs` collection
   at upload time, tagged with a `document_id`. Answers *"what does my contract say?"*
2. **The legal knowledge base** (`legal_kb`, 9,063 vectors) — answers *"is this fair or
   enforceable under Indian law?"* and supplies the citations.

| Corpus | Chunks | Source |
| --- | ---: | --- |
| Statute sections | 1,791 | 11 bare Acts + the Constitution of India |
| Judgment passages | 7,168 | Supreme Court of India |
| Red-flag clauses | 30 | curated one-sided-clause patterns |
| Glossary | 47 | plain-English definitions |
| Model clauses | 27 | fair-alternative templates |

Everything is embedded with **InLegalBERT** (`law-ai/InLegalBERT`, 768-dim, mean-pooled and
L2-normalised) and stored in **ChromaDB**, with a **Qdrant** mirror of the same vectors for
the comparative study in [`docs/`](docs/).

Two details worth knowing:

- KB retrieval runs **per `doc_type`** with a budget each, so the 7k judgment chunks can't
  drown out the concise statute and red-flag chunks.
- Whole-document analysis probes with **chunks spread across the document**, not the first
  few thousand characters — probing the preamble only returns registration and stamp-duty
  provisions instead of the law governing the risky clauses.

## Stack

- **Frontend** — React 18, TypeScript, MUI v5
- **Backend** — Flask, Gunicorn
- **Model** — Gemini 2.5 Flash, via **Vertex AI** (OAuth) or the AI Studio API (key)
- **Retrieval** — InLegalBERT + ChromaDB (Qdrant interchangeable)
- **Deployment** — Docker on Google Cloud Run

## Setup

### Prerequisites

Python 3.11+, Node 18+, and either a GCP project with Vertex AI enabled or a Gemini API key.

### Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Windows;  source venv/bin/activate elsewhere

pip install -r requirements.txt
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements-rag.txt
```

`torch` comes from the CPU wheel index deliberately — the default index pulls ~2 GB of CUDA
libraries that are never used.

### Configuration

Copy `backend/.env.example` to `backend/.env`. To call Gemini through **Vertex AI** (billed
to your GCP project, no API key):

```env
AI_BACKEND=vertex
GOOGLE_CLOUD_PROJECT=your-project-id
VERTEX_AI_LOCATION=global
GEMINI_MODEL=gemini-2.5-flash
```

then authenticate locally with `gcloud auth application-default login`. On Cloud Run the
attached service account is used instead and no credentials are stored anywhere.

To use an **AI Studio key** instead, set `AI_BACKEND=studio` and `GEMINI_API_KEY=...`.

> `VERTEX_AI_LOCATION=global` is the safe choice — regional endpoints do not serve every
> model in every region.

### Knowledge base

The built index lives in `knowledge_base/vector_store/` and is gitignored (~230 MB). To
rebuild it from the corpus:

```bash
python scripts/build_knowledge_base.py         # raw sources -> processed JSONL
python scripts/index_knowledge_base.py --store both --recreate
python scripts/query_kb.py "can my landlord forfeit my deposit?"   # sanity check
```

### Frontend

```bash
cd frontend
npm install
npm start          # proxies /api to the backend on :8080
```

## Running locally

```bash
# Backend — note: not `python app.py`.
# Flask's debug reloader segfaults with torch loaded in-process.
cd backend
python -c "from app import app; app.run(host='127.0.0.1', port=8080, threaded=True)"

# Frontend
cd frontend && npm start
```

The first request loads InLegalBERT (~450 MB) and opens the Chroma index, so expect a slow
first analysis and fast ones after.

## Deploying to Cloud Run

```bash
gcloud builds submit --tag gcr.io/PROJECT_ID/legal-ease:v1 \
  --timeout=3600s --machine-type=e2-highcpu-8

gcloud run deploy legal-ease \
  --image gcr.io/PROJECT_ID/legal-ease:v1 \
  --region us-central1 --allow-unauthenticated \
  --memory 4Gi --cpu 2 --timeout 300 --concurrency 8 \
  --set-env-vars "AI_BACKEND=vertex,GOOGLE_CLOUD_PROJECT=PROJECT_ID,VERTEX_AI_LOCATION=global,FLASK_ENV=production"
```

The runtime service account needs `roles/aiplatform.user`.

Two deployment details that matter:

- **`.gcloudignore` must exist.** Without it gcloud falls back to `.gitignore`, which
  excludes `knowledge_base/vector_store` — the index the image has to contain.
- **One Gunicorn worker, several threads.** Each worker would load its own copy of
  InLegalBERT and its own Chroma client; concurrency comes from threads instead, which
  suits requests dominated by waiting on Gemini.

## API

```bash
POST /api/analyze                       # multipart PDF -> analysis + sources
POST /api/question                      # {document_id, question} -> answer + sources
DELETE /api/document/delete/<id>        # erase a document immediately
GET  /api/health
POST /whatsapp/webhook                  # Twilio inbound
```

Both analysis and answers include a `sources[]` array of `{type, source, section, citation,
score}` — deduplicated by authority, so a long judgment matching on several chunks is
listed once.

## Security

Rate limiting, PDF validation, security headers with a CSP, in-memory document storage with
session expiry, and vector-store eviction wired to document deletion so chunks never
outlive the document.

## License

MIT — see [LICENSE](LICENSE).

---

**Legal EASE explains documents. It is not a substitute for a lawyer, and nothing it
produces is legal advice.**
