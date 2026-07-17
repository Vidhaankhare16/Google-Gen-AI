#!/bin/bash
# setup-gcp.sh — One-time GCP project setup for Legal EASE
# Run once before your first deploy: bash setup-gcp.sh
set -euo pipefail

PROJECT_ID="${GOOGLE_CLOUD_PROJECT:-$(gcloud config get-value project 2>/dev/null)}"
REGION="${REGION:-us-central1}"
REPO_NAME="legal-ease"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
log()     { echo -e "${BLUE}[setup]${NC} $1"; }
success() { echo -e "${GREEN}✅  $1${NC}"; }
die()     { echo -e "${RED}❌  $1${NC}"; exit 1; }

[[ -z "${PROJECT_ID:-}" ]] && die "Set GOOGLE_CLOUD_PROJECT or run: gcloud config set project YOUR_PROJECT_ID"
command -v gcloud >/dev/null 2>&1 || die "gcloud CLI not found: https://cloud.google.com/sdk/docs/install"

echo ""
echo -e "${GREEN}🔧 Setting up GCP for Legal EASE${NC}"
echo -e "   Project: ${YELLOW}$PROJECT_ID${NC}  Region: ${YELLOW}$REGION${NC}"
echo ""

gcloud config set project "$PROJECT_ID" --quiet

# Enable APIs
log "Enabling APIs..."
gcloud services enable \
    cloudbuild.googleapis.com \
    run.googleapis.com \
    artifactregistry.googleapis.com \
    secretmanager.googleapis.com \
    --quiet
success "APIs enabled"

# Create Artifact Registry repository
log "Creating Artifact Registry repository..."
if ! gcloud artifacts repositories describe "$REPO_NAME" --location="$REGION" --quiet 2>/dev/null; then
    gcloud artifacts repositories create "$REPO_NAME" \
        --repository-format=docker \
        --location="$REGION" \
        --description="Legal EASE Docker images" \
        --quiet
    success "Created repository: $REPO_NAME"
else
    log "Repository already exists."
fi

# Store GEMINI_API_KEY in Secret Manager
echo ""
echo -e "${YELLOW}Enter your Gemini API key (input hidden):${NC}"
read -rs GEMINI_KEY
echo ""

if [[ -n "$GEMINI_KEY" ]]; then
    if gcloud secrets describe gemini-api-key --quiet 2>/dev/null; then
        echo -n "$GEMINI_KEY" | gcloud secrets versions add gemini-api-key --data-file=- --quiet
        success "Updated gemini-api-key secret"
    else
        echo -n "$GEMINI_KEY" | gcloud secrets create gemini-api-key \
            --data-file=- --replication-policy=automatic --quiet
        success "Created gemini-api-key secret"
    fi
else
    log "Skipping API key setup. Run again or create manually."
fi

# Grant Cloud Run SA access to secret
PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format="value(projectNumber)")
COMPUTE_SA="$PROJECT_NUMBER-compute@developer.gserviceaccount.com"
log "Granting secret access to Cloud Run service account ($COMPUTE_SA)..."
gcloud secrets add-iam-policy-binding gemini-api-key \
    --member="serviceAccount:$COMPUTE_SA" \
    --role="roles/secretmanager.secretAccessor" \
    --quiet 2>/dev/null || log "IAM binding already exists or secret not created — skipping."
success "Setup complete!"

echo ""
echo -e "${YELLOW}Next step: run  bash deploy.sh  to build and deploy.${NC}"
