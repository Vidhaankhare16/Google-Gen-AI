# Legal EASE — Deployment Guide

Deploy the Legal EASE AI legal document analysis platform to Google Cloud Run.

## Architecture

- **Frontend**: React 18 + TypeScript, built into Flask's `static/` folder
- **Backend**: Flask 3 + Gunicorn, served on port 8080
- **AI**: Gemini `gemini-2.0-flash` via Google AI REST API
- **Infrastructure**: Cloud Run (serverless), Artifact Registry, Secret Manager, Cloud Build

---

## Prerequisites

| Tool | Purpose | Required |
|---|---|---|
| `gcloud` CLI | Deploy and manage GCP resources | Yes |
| Google Cloud account | Billing-enabled GCP project | Yes |
| Gemini API key | AI analysis ([get one here](https://aistudio.google.com/app/apikey)) | Yes |
| Docker Desktop | Local testing only | No (Cloud Build handles CI/CD) |
| Node.js 20+ / Python 3.11+ | Local development only | No |

> **Windows users**: Run `.sh` scripts in Git Bash, WSL, or Google Cloud Shell. PowerShell is not supported for these scripts.

---

## Quick Deploy (5 minutes)

### Step 1 — One-time GCP setup

```bash
export GOOGLE_CLOUD_PROJECT="your-project-id"
bash setup-gcp.sh
```

This script:
- Enables required APIs (Cloud Build, Cloud Run, Artifact Registry, Secret Manager)
- Creates an Artifact Registry Docker repository named `legal-ease`
- Prompts for your Gemini API key and stores it in Secret Manager
- Grants the Cloud Run service account access to the secret

### Step 2 — Configure local environment

```bash
cp backend/.env.example backend/.env
```

Edit `backend/.env` — only one variable is required:

```bash
GEMINI_API_KEY=your-gemini-api-key
```

Optional variables (defaults shown):

```bash
FLASK_ENV=production
PORT=8080
MAX_FILE_SIZE=10485760   # 10 MB
SESSION_TIMEOUT=3600     # 1 hour
```

### Step 3 — Deploy

```bash
export GOOGLE_CLOUD_PROJECT="your-project-id"
bash deploy.sh
```

The deploy script:
1. Enables all required GCP APIs
2. Creates the Artifact Registry repo if it doesn't exist
3. Reads `GEMINI_API_KEY` from `backend/.env` and stores it in Secret Manager
4. Submits a remote Docker build via **Cloud Build** (no local Docker required)
5. Deploys to Cloud Run and injects the API key from Secret Manager at runtime
6. Prints the live service URL on success

### Step 4 — Verify

```bash
# Get the service URL
gcloud run services describe legal-ease --region=us-central1 --format="value(status.url)"

# Test the health endpoint
curl https://YOUR_SERVICE_URL/api/health
```

---

## CI/CD with Cloud Build

`cloudbuild.yaml` defines an automated pipeline triggered on every push to `main`.

**To connect:**
1. Go to Cloud Build → Triggers → Connect Repository
2. Select your GitHub repo
3. Set trigger: push to `main` branch, config file `cloudbuild.yaml`
4. Set substitutions if needed:
   - `_REGION`: e.g. `us-central1` (default)
   - `_SERVICE_NAME`: `legal-ease` (default)

The pipeline builds a versioned image (`$BUILD_ID` tag) plus `latest`, pushes both to Artifact Registry, and deploys to Cloud Run.

---

## Manual Cloud Run service definition

To apply `cloud-run-service.yaml` directly (useful for fine-grained config changes without a full rebuild):

```bash
# Replace placeholders first
sed -i "s/PROJECT_ID/your-project-id/g; s/REGION/us-central1/g" cloud-run-service.yaml

gcloud run services replace cloud-run-service.yaml --region=us-central1
```

---

## Local Development

### Option A — Docker Compose (closest to production)

```bash
# Requires backend/.env with GEMINI_API_KEY set
docker-compose up --build
```

Open: http://localhost:8080

### Option B — Run services separately

**Terminal 1 — Backend**
```bash
cd backend
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Backend runs on http://localhost:8080

**Terminal 2 — Frontend dev server**
```bash
cd frontend
npm install
npm start
```

Frontend runs on http://localhost:3000 and proxies API calls to port 8080.

---

## Cloud Run configuration

| Setting | Value |
|---|---|
| Region | us-central1 |
| CPU | 1 vCPU |
| Memory | 2 GB |
| Concurrency | 50 req/instance |
| Min instances | 0 (scales to zero) |
| Max instances | 10 |
| Request timeout | 300 s |
| Execution environment | gen2 (faster cold start) |

To change these, edit the `gcloud run deploy` flags in `deploy.sh` or the container spec in `cloud-run-service.yaml`.

---

## Rate limits

| Endpoint | Limit |
|---|---|
| `POST /api/analyze` | 5 requests per 5 minutes |
| `POST /api/question` | 20 requests per 5 minutes |

---

## Monitoring & Logs

```bash
# Tail live logs
gcloud run services logs tail legal-ease --region=us-central1

# Read recent logs
gcloud logging read 'resource.type="cloud_run_revision" resource.labels.service_name="legal-ease"' \
  --limit=50 --format="table(timestamp, textPayload)"
```

Health check endpoint: `GET /api/health` — returns `{"status":"healthy",...}` with HTTP 200.

---

## Troubleshooting

### 404 from Gemini API
The model name is incorrect or not available in your region. Current model: `gemini-2.0-flash`. Check [Google AI Studio](https://aistudio.google.com/) for available models.

### `GEMINI_API_KEY` not found in Cloud Run
Verify the secret exists and the service account has access:
```bash
gcloud secrets describe gemini-api-key
PROJECT_NUMBER=$(gcloud projects describe $GOOGLE_CLOUD_PROJECT --format="value(projectNumber)")
gcloud secrets get-iam-policy gemini-api-key
```

### Build fails — `libmagic` not found
This is installed in the Dockerfile via `apt-get install -y libmagic1`. If you see this error locally (not in Cloud Build), ensure your local Docker image is rebuilt:
```bash
docker-compose build --no-cache
```

### App crashes on startup — missing `GEMINI_API_KEY`
Only `GEMINI_API_KEY` is required. Verify `backend/.env` contains it and is not the placeholder value.

### Frontend changes not reflected
The React app is built into `backend/static/` during the Docker build. If you changed frontend code, rebuild the image:
```bash
bash deploy.sh
```

---

## Cost estimate (moderate usage)

| Service | Estimated cost |
|---|---|
| Cloud Run | $0–10/month (scales to zero) |
| Cloud Build | ~$0.003/build-minute, first 120 min/day free |
| Artifact Registry | ~$0.10/GB stored |
| Secret Manager | ~$0.06/10k API operations |
| Gemini API | Pay-per-use (free tier available) |
| **Total** | **~$5–20/month** |

---

## Security

- GEMINI_API_KEY stored in **Secret Manager**, never in environment variables at build time
- HTTPS enforced in production via `require_https()` decorator
- Rate limiting on all write endpoints
- All file uploads validated (PDF-only, 10 MB max, magic-byte check)
- Container runs as non-root user (UID 1000)
- All Linux capabilities dropped
- Security headers added to every response (CSP, X-Frame-Options, etc.)
- `.env` files are in `.gitignore` and `.dockerignore`
