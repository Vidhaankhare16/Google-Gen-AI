"""
Central settings for the Legal EASE RAG stack (embeddings + vector stores).

Kept separate from the Flask `config.py` so the offline indexing/benchmark scripts don't need to
import the web app. Values are overridable via environment variables.
"""
from __future__ import annotations

import os

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# --- Embeddings ------------------------------------------------------------ #
# InLegalBERT: BERT-base trained on 5.4M Indian legal docs. 768-dim, 512-token limit.
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "law-ai/InLegalBERT")
EMBEDDING_DIM = int(os.getenv("EMBEDDING_DIM", "768"))
EMBEDDING_BATCH_SIZE = int(os.getenv("EMBEDDING_BATCH_SIZE", "32"))
MAX_SEQ_LENGTH = int(os.getenv("MAX_SEQ_LENGTH", "512"))

# --- Vector stores --------------------------------------------------------- #
# The persistent legal knowledge base collection (shared across users).
KB_COLLECTION = os.getenv("KB_COLLECTION", "legal_kb")
# Ephemeral per-upload chunks live here, tagged with `document_id` metadata.
USER_DOCS_COLLECTION = os.getenv("USER_DOCS_COLLECTION", "user_docs")

# Which backend the app uses at query time: "chroma" | "qdrant".
VECTOR_DB = os.getenv("VECTOR_DB", "chroma")

# On-disk locations for the two local vector stores (kept out of git via .gitignore).
_VS_ROOT = os.getenv("VECTOR_STORE_ROOT", os.path.join(_REPO_ROOT, "knowledge_base", "vector_store"))
CHROMA_PATH = os.getenv("CHROMA_PATH", os.path.join(_VS_ROOT, "chroma"))
QDRANT_PATH = os.getenv("QDRANT_PATH", os.path.join(_VS_ROOT, "qdrant"))
# Optional Qdrant server URL (e.g. http://localhost:6333). If set, used instead of QDRANT_PATH.
QDRANT_URL = os.getenv("QDRANT_URL", "")

# Cosine similarity for both stores (InLegalBERT embeddings are L2-normalized).
DISTANCE = "cosine"

# --- Retrieval defaults ---------------------------------------------------- #
TOP_K_DOC = int(os.getenv("TOP_K_DOC", "5"))   # uploaded-document hits per query

# Per-doc-type budget when retrieving from the legal KB. Retrieving separately per type prevents
# the 7k judgment chunks from drowning out the concise, high-value statute/red-flag chunks.
KB_TOPK_BY_TYPE = {
    "redflag": int(os.getenv("TOP_K_REDFLAG", "3")),
    "statute": int(os.getenv("TOP_K_STATUTE", "3")),
    "judgment": int(os.getenv("TOP_K_JUDGMENT", "2")),
    "glossary": int(os.getenv("TOP_K_GLOSSARY", "1")),
}
