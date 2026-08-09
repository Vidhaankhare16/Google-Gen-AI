"""
InLegalBERT embedding wrapper for Legal EASE.

InLegalBERT (`law-ai/InLegalBERT`) is a BERT-base model (no native sentence-embedding head), so we
wrap it with sentence-transformers as a Transformer + **mean-pooling** layer and L2-normalize the
output. This yields fixed 768-dim vectors suitable for cosine-similarity retrieval, and it is the
*same* embedder for both ChromaDB and Qdrant so the comparative study stays fair.

Heavy imports (torch / sentence-transformers) are lazy so this module can be imported before the
RAG stack is installed. The model is a process-wide singleton (loaded once, reused).
"""
from __future__ import annotations

import logging
import threading
from typing import List, Optional

from rag import settings

logger = logging.getLogger(__name__)


class Embedder:
    """Loads InLegalBERT once and produces L2-normalized mean-pooled embeddings."""

    _instance: Optional["Embedder"] = None
    _lock = threading.Lock()

    def __init__(self, model_name: str = settings.EMBEDDING_MODEL,
                 max_seq_length: int = settings.MAX_SEQ_LENGTH):
        self.model_name = model_name
        self.max_seq_length = max_seq_length
        self._model = None  # lazy

    # -- singleton accessor -------------------------------------------------- #
    @classmethod
    def get(cls) -> "Embedder":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # -- model loading ------------------------------------------------------- #
    def _load(self):
        if self._model is not None:
            return self._model
        from sentence_transformers import SentenceTransformer, models  # lazy

        logger.info(f"Loading embedding model '{self.model_name}' (mean-pooling)...")
        transformer = models.Transformer(self.model_name, max_seq_length=self.max_seq_length)
        pooling = models.Pooling(
            transformer.get_word_embedding_dimension(),
            pooling_mode="mean",  # InLegalBERT has no [CLS] sentence head -> mean-pool tokens
        )
        self._model = SentenceTransformer(modules=[transformer, pooling])
        dim = self._model.get_sentence_embedding_dimension()
        logger.info(f"Embedding model ready: dim={dim}, device={self._model.device}")
        return self._model

    @property
    def dim(self) -> int:
        return self._load().get_sentence_embedding_dimension()

    # -- encoding ------------------------------------------------------------ #
    def embed(self, texts: List[str], batch_size: int = settings.EMBEDDING_BATCH_SIZE,
              show_progress: bool = False) -> "list":
        """Embed a list of texts -> list of L2-normalized float vectors (as plain lists)."""
        if not texts:
            return []
        model = self._load()
        vecs = model.encode(
            texts,
            batch_size=batch_size,
            normalize_embeddings=True,        # cosine-ready
            convert_to_numpy=True,
            show_progress_bar=show_progress,
        )
        return vecs.tolist()

    def embed_query(self, text: str) -> "list":
        """Embed a single query string -> one L2-normalized vector (plain list)."""
        return self.embed([text])[0]
