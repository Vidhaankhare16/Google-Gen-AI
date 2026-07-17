#!/bin/bash
# deploy.sh — Deploy Legal EASE to Google Cloud Run
# Run from project root: bash deploy.sh
set -euo pipefail

# ── Configuration ─────────────────────────────────────────────────────────────
SERVICE_NAME="legal-ease"
REPO_NAME="legal-ease"
REGION="${REGION:-us-central1}"
PROJECT_ID="${GOOGLE_CLOUD_PROJECT:-$(gcloud config get-value project 2>/dev/null)}"
IMAGE="$REGION-docker.pkg.dev/$PROJECT_ID/$REPO_NAME/$SERVICE_NAME"

# ── Colours ───────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
log()     { echo -e "${BLUE}[$(date +%H:%M:%S)]${NC} $1"; }
success() { echo -e "${GREEN}✅  $1${NC}"; }
warn()    { echo -e "${YELLOW}⚠️   $1${NC}"; }
die()     { echo -e "${RED}❌  $1${NC}"; exit 1; }

# ── Pre-flight checks ─────────────────────────────────────────────────────────
[[ -z "${PROJECT_ID:-}" ]] && die "Set GOOGLE_CLOUD_PROJECT or run: gcloud config set project YOUR_PROJECT_ID"
command -v gcloud >/dev/null 2>&1 || die "gcloud CLI not found. Install: https://cloud.google.com/sdk/docs/install"

# Load GEMINI_API_KEY from backend/.env if not already in environment
if [[ -z "${GEMINI_API_KEY:-}" ]] && [[ -f "backend/.env" ]]; then
    GEMINI_API_KEY=$(grep '^GEMINI_API_KEY=' backend/.env 2>/dev/null | cut -d'=' -f2- | tr -d '"' || true)
fi
[[ -z "${GEMINI_API_KEY:-}" ]] && die "GEMINI_API_KEY not found. Set it in backend/.env or export it."

echo ""
echo -e "${GREEN}🚀 Deploying Legal EASE to Google Cloud Run${NC}"
echo -e "   Project : ${YELLOW}$PROJECT_ID${NC}"
echo -e "   Region  : ${YELLOW}$REGION${NC}"
echo -e "   Service : ${YELLOW}$SERVICE_NAME${NC}"
echo -e "   Image   : ${YELLOW}$IMAGE${NC}"
echo ""

# ── GCP setup ─────────────────────────────────────────────────────────────────
log "Setting active project..."
gcloud config set project "$PROJECT_ID" --quiet

log "Enabling required APIs (may take a minute on first run)..."
gcloud services enable \
    cloudbuild.googleapis.com \
    run.googleapis.com \
    artifactregistry.googleapis.com \
    secretmanager.googleapis.com \
    --quiet

# ── Artifact Registry ─────────────────────────────────────────────────────────
log "Ensuring Artifact Registry repository exists..."
if ! gcloud artifacts repositories describe "$REPO_NAME" --location="$REGION" --quiet 2>/dev/null; then
    gcloud artifacts repositories create "$REPO_NAME" \
        --repository-format=docker \
        --location="$REGION" \
        --description="Legal EASE Docker images" \
        --quiet
    success "Created Artifact Registry repo: $REPO_NAME"
else
    log "Artifact Registry repo already exists."
fi

# ── Secret Manager ────────────────────────────────────────────────────────────
log "Storing GEMINI_API_KEY in Secret Manager..."
if gcloud secrets describe gemini-api-key --quiet 2>/dev/null; then
    echo -n "$GEMINI_API_KEY" | gcloud secrets versions add gemini-api-key --data-file=- --quiet
    log "Updated existing secret version."
else
    echo -n "$GEMINI_API_KEY" | gcloud secrets create gemini-api-key \
        --data-file=- \
        --replication-policy=automatic \
        --quiet
    success "Created secret: gemini-api-key"
fi

# Grant Cloud Run's default compute SA access to the secret
PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format="value(projectNumber)")
COMPUTE_SA="$PROJECT_NUMBER-compute@developer.gserviceaccount.com"
log "Granting secret access to Cloud Run service account..."
gcloud secrets add-iam-policy-binding gemini-api-key \
    --member="serviceAccount:$COMPUTE_SA" \
    --role="roles/secretmanager.secretAccessor" \
    --quiet

# ── Build with Cloud Build (no local Docker required) ────────────────────────
log "Building image with Cloud Build (this takes ~3-5 minutes)..."
gcloud builds submit \
    --tag "$IMAGE:latest" \
    --machine-type=e2-highcpu-8 \
    --timeout=1200s \
    .
success "Image built and pushed: $IMAGE:latest"

# ── Deploy to Cloud Run ───────────────────────────────────────────────────────
log "Deploying to Cloud Run..."
gcloud run deploy "$SERVICE_NAME" \
    --image "$IMAGE:latest" \
    --region "$REGION" \
    --platform managed \
    --allow-unauthenticated \
    --memory 2Gi \
    --cpu 1 \
    --timeout 300 \
    --concurrency 50 \
    --min-instances 0 \
    --max-instances 10 \
    --set-secrets "GEMINI_API_KEY=gemini-api-key:latest" \
    --set-env-vars "FLASK_ENV=production,MAX_FILE_SIZE=10485760,SESSION_TIMEOUT=3600" \
    --quiet

# ── Done ──────────────────────────────────────────────────────────────────────
SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" --region="$REGION" --format="value(status.url)")
echo ""
success "Deployment complete!"
echo -e "   URL         : ${GREEN}$SERVICE_URL${NC}"
echo -e "   Health check: ${BLUE}$SERVICE_URL/api/health${NC}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "  • Open $SERVICE_URL in your browser"
echo "  • View logs: gcloud run services logs tail $SERVICE_NAME --region=$REGION"
