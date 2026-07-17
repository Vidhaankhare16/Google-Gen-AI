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

# ── Stage 2: Python backend + built frontend ────────────────────────────────
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

# Install Python dependencies before copying source (better layer caching)
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source
COPY backend/ ./

# Copy React build output from Stage 1
COPY --from=frontend-build /app/frontend/build ./static/

# Run as non-root for security
RUN useradd --create-home --shell /bin/bash appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8080

# gunicorn: 2 workers is appropriate for Cloud Run (CPU-bound AI calls)
CMD ["gunicorn", \
     "--bind", "0.0.0.0:8080", \
     "--workers", "2", \
     "--timeout", "300", \
     "--keep-alive", "5", \
     "--access-logfile", "-", \
     "app:app"]
