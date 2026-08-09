# ── Stage 1: Build React frontend ──────────────────────────────────────────
FROM node:20-alpine AS frontend-build

WORKDIR /app/frontend

# Cache dependency layer separately from source
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

# Disable source maps to reduce build size and memory usage
ENV GENERATE_SOURCEMAP=false

COPY frontend/src ./src
COPY frontend/public ./public
COPY frontend/tsconfig.json ./

RUN npm run build

# ── Stage 2: Python backend + RAG stack + built frontend ────────────────────
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# System libraries:
#   gcc/g++   – required for some pip packages
#   curl      – health-check & runtime use
#   libmagic1 – required by python-magic (file type detection)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    curl \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies before copying source (better layer caching).
# torch comes from the CPU wheel index so we don't pull ~2GB of CUDA libraries.
COPY backend/requirements.txt backend/requirements-rag.txt ./
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir -r requirements-rag.txt

# Bake the InLegalBERT weights into the image so cold starts never hit HuggingFace.
ENV HF_HOME=/app/hf_cache
ENV TRANSFORMERS_OFFLINE=1
ENV HF_HUB_OFFLINE=1
RUN HF_HUB_OFFLINE=0 TRANSFORMERS_OFFLINE=0 python -c "\
from transformers import AutoTokenizer, AutoModel; \
AutoTokenizer.from_pretrained('law-ai/InLegalBERT'); \
AutoModel.from_pretrained('law-ai/InLegalBERT')"

# Copy backend source
COPY backend/ ./

# Legal knowledge base: the prebuilt Chroma index (~9k vectors of Indian statutes,
# judgments, red-flags and glossary entries). Qdrant/raw/processed are excluded by
# .dockerignore — only the Chroma index is needed at query time.
COPY knowledge_base/vector_store/chroma ./knowledge_base/vector_store/chroma
ENV VECTOR_DB=chroma
ENV CHROMA_PATH=/app/knowledge_base/vector_store/chroma

# Copy React build output from Stage 1
COPY --from=frontend-build /app/frontend/build ./static/

# Run as non-root for security
RUN useradd --create-home --shell /bin/bash appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8080

# One worker only: each worker would load its own copy of InLegalBERT (~450MB) and
# its own Chroma client. Concurrency comes from threads instead, which is the right
# shape here because requests are dominated by waiting on the Gemini API.
CMD ["gunicorn", \
     "--bind", "0.0.0.0:8080", \
     "--workers", "1", \
     "--threads", "8", \
     "--timeout", "300", \
     "--keep-alive", "5", \
     "--access-logfile", "-", \
     "app:app"]
