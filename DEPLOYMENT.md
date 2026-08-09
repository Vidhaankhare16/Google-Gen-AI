# Deploying Legal EASE to Cloud Run

The service is one container: Gunicorn serving the Flask API and the built React app, with
the InLegalBERT weights and the prebuilt Chroma index baked into the image. Gemini is
called through Vertex AI using the runtime service account, so no API key is stored
anywhere.

## One-time project setup

```bash
PROJECT=your-project-id
gcloud projects create $PROJECT --name="Legal EASE"
gcloud billing projects link $PROJECT --billing-account=YOUR-BILLING-ID
gcloud config set project $PROJECT

gcloud services enable \
  run.googleapis.com cloudbuild.googleapis.com \
  artifactregistry.googleapis.com aiplatform.googleapis.com

# The runtime service account must be allowed to call Gemini.
NUM=$(gcloud projects describe $PROJECT --format='value(projectNumber)')
gcloud projects add-iam-policy-binding $PROJECT \
  --member="serviceAccount:$NUM-compute@developer.gserviceaccount.com" \
  --role="roles/aiplatform.user" --condition=None
```

## Build and deploy

```bash
cd frontend && npm run build && cd ..     # the image copies frontend/build

gcloud builds submit \
  --tag=gcr.io/$PROJECT/legal-ease:v1 \
  --timeout=3600s --machine-type=e2-highcpu-8

gcloud run deploy legal-ease \
  --image=gcr.io/$PROJECT/legal-ease:v1 \
  --region=us-central1 --allow-unauthenticated \
  --memory=4Gi --cpu=2 --timeout=300 --concurrency=8 --max-instances=3 \
  --set-env-vars="AI_BACKEND=vertex,GOOGLE_CLOUD_PROJECT=$PROJECT,VERTEX_AI_LOCATION=global,GEMINI_MODEL=gemini-2.5-flash,GEMINI_VISION_MODEL=gemini-2.5-flash,FLASK_ENV=production,VECTOR_DB=chroma,CHROMA_PATH=/app/knowledge_base/vector_store/chroma"
```

The build takes 10–20 minutes and the image is ~3 GB: torch (CPU wheels), the InLegalBERT
weights and the ~100 MB Chroma index. `--machine-type=e2-highcpu-8` and the long timeout
are both needed; the defaults time out.

## Things that will bite you

**`.gcloudignore` must exist.** Without it gcloud falls back to `.gitignore`, which excludes
`knowledge_base/vector_store` — so the image builds successfully and then has no knowledge
base, and every answer silently loses its citations.

**Pin numpy loosely.** `numpy>=2.0,<3`. The exact pin from a Python 3.13 dev machine
(`numpy==2.5.1`) requires Python ≥3.12 and fails against the 3.11 base image.

**`VERTEX_AI_LOCATION=global`.** Regional endpoints do not serve every model in every
region; `us-central1` did not serve `gemini-2.5-flash` here.

**Vertex requires `"role": "user"`** on each `contents` entry. The AI Studio API defaults it;
Vertex returns `400 Please use a valid role`.

**One worker, several threads.** Each Gunicorn worker loads its own copy of InLegalBERT
(~450 MB) and its own Chroma client, so `--workers 1 --threads 8` is deliberate. Memory
below 4 GiB will OOM during model load.

**Cold starts are slow.** The container starts listening immediately and warms the
retriever on a background thread (`RAG_WARMUP=0` disables it), but a request arriving
during warm-up still waits for the model. The frontend allows 180 s. Set
`--min-instances=1` if you want that gone, at the cost of an always-billed instance.

## Verifying a deployment

```bash
URL=$(gcloud run services describe legal-ease --region=us-central1 --format='value(status.url)')

curl -s $URL/api/health
curl -s -X POST -F "file=@knowledge_base/test_documents/rent_deed.pdf" $URL/api/analyze | jq '.analysis | {risk_score, document_type, sources: (.sources|length)}'
```

A healthy response has a non-empty `sources[]`. If `sources` is empty the knowledge base
did not make it into the image — check `.gcloudignore` first.

## Configuration reference

| Variable | Purpose |
| --- | --- |
| `AI_BACKEND` | `vertex` (OAuth) or `studio` (API key) |
| `GOOGLE_CLOUD_PROJECT` | Project billed for Vertex AI calls |
| `VERTEX_AI_LOCATION` | `global` recommended |
| `GEMINI_API_KEY` | Only for `AI_BACKEND=studio` |
| `GEMINI_MODEL` / `GEMINI_VISION_MODEL` | Text and OCR models |
| `VECTOR_DB` | `chroma` or `qdrant` |
| `CHROMA_PATH` | Index location inside the image |
| `RAG_WARMUP` | `0` to skip background warm-up |
| `SESSION_TIMEOUT` | Seconds a document is retained |

## Rolling back

```bash
gcloud run revisions list --service=legal-ease --region=us-central1
gcloud run services update-traffic legal-ease --region=us-central1 --to-revisions=REVISION=100
```
