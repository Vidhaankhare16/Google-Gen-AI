"""
Vector-store abstraction for Legal EASE.

A single interface (`VectorStore`) with two interchangeable backends — ChromaDB and Qdrant — so the
same embeddings and the same corpus can be indexed and queried against either, which is what makes
the Chroma-vs-Qdrant comparative study fair. The app and the retriever depend only on this
interface; swapping backends is a one-line factory call.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class SearchHit:
    """One retrieved chunk."""
    id: str
    score: float                 # similarity in [0, 1] (cosine), higher = closer
    text: str
    metadata: Dict = field(default_factory=dict)


class VectorStore(ABC):
    """Backend-agnostic vector collection bound to one collection name + embedding dim."""

    @abstractmethod
    def upsert(self, ids: List[str], embeddings: List[List[float]],
               documents: List[str], metadatas: List[Dict]) -> None:
        """Insert/replace vectors with their source text and metadata."""

    @abstractmethod
    def query(self, embedding: List[float], top_k: int = 5,
              where: Optional[Dict] = None) -> List[SearchHit]:
        """Return the top_k nearest chunks, optionally filtered by exact metadata match (`where`)."""

    @abstractmethod
    def delete(self, where: Dict) -> None:
        """Delete all vectors matching an exact-match metadata filter (e.g. one document_id)."""

    @abstractmethod
    def count(self) -> int:
        """Number of vectors currently in the collection."""

    @abstractmethod
    def delete_collection(self) -> None:
        """Drop the whole collection (used for per-document cleanup and re-indexing)."""

    @abstractmethod
    def _create_collection(self) -> None:
        """(Re)create the empty collection on the current client."""

    def reset(self) -> None:
        """Drop and recreate the collection on the SAME client (no second client/lock)."""
        try:
            self.delete_collection()
        except Exception:
            pass
        self._create_collection()

    def close(self) -> None:
        """Release backend resources (e.g. Qdrant local file lock). Default: no-op."""

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


def clean_metadata(meta: Dict) -> Dict:
    """
    Normalize metadata to primitive scalars (str/int/float/bool), dropping None and empties.

    ChromaDB rejects None and non-scalar metadata values; Qdrant is more permissive but we keep a
    single normalized shape across both backends for parity.
    """
    out: Dict = {}
    for k, v in (meta or {}).items():
        if v is None or v == "":
            continue
        if isinstance(v, (str, int, float, bool)):
            out[k] = v
        else:
            out[k] = str(v)
    return out


def get_store(backend: str, collection: str, dim: int) -> VectorStore:
    """Factory: return a VectorStore for 'chroma' or 'qdrant'."""
    backend = (backend or "").lower()
    if backend == "chroma":
        from rag.chroma_store import ChromaStore
        return ChromaStore(collection=collection, dim=dim)
    if backend == "qdrant":
        from rag.qdrant_store import QdrantStore
        return QdrantStore(collection=collection, dim=dim)
    raise ValueError(f"Unknown vector backend: {backend!r} (expected 'chroma' or 'qdrant')")
