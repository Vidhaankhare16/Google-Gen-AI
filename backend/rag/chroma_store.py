"""ChromaDB implementation of the VectorStore interface (persistent, local, cosine).

Clients are cached per path and shared across collections (parity with the Qdrant backend).
"""
from __future__ import annotations

import os
import threading
from typing import Dict, List, Optional

from rag import settings
from rag.vector_store import VectorStore, SearchHit, clean_metadata

_CLIENTS: Dict[str, object] = {}   # path -> shared PersistentClient
_CLIENTS_LOCK = threading.Lock()


def _get_client(path: str):
    """
    Return the process-wide PersistentClient for `path`, creating it at most once.

    The lock matters: the server runs Gunicorn with several threads and warms the
    retriever on a background thread, so two threads can reach this concurrently on the
    first request. Without it both build a PersistentClient over the same directory, and
    the losing client is left with a collection handle that answers queries with nothing —
    the knowledge base appears empty even though it is fully populated on disk.
    """
    client = _CLIENTS.get(path)
    if client is not None:
        return client

    with _CLIENTS_LOCK:
        if path not in _CLIENTS:
            import chromadb  # lazy
            os.makedirs(path, exist_ok=True)
            _CLIENTS[path] = chromadb.PersistentClient(path=path)
        return _CLIENTS[path]


def close_all() -> None:
    """Drop cached clients (Chroma has no explicit close; this just clears the cache)."""
    _CLIENTS.clear()


class ChromaStore(VectorStore):
    def __init__(self, collection: str, dim: int = settings.EMBEDDING_DIM,
                 path: str = settings.CHROMA_PATH):
        self.collection_name = collection
        self.dim = dim
        self._path = path
        self._client = _get_client(path)
        self._create_collection()

    def _create_collection(self) -> None:
        self._col = self._client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": settings.DISTANCE},  # cosine
        )

    def upsert(self, ids: List[str], embeddings: List[List[float]],
               documents: List[str], metadatas: List[Dict]) -> None:
        self._col.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=[clean_metadata(m) for m in metadatas],
        )

    def query(self, embedding: List[float], top_k: int = 5,
              where: Optional[Dict] = None) -> List[SearchHit]:
        res = self._col.query(
            query_embeddings=[embedding],
            n_results=top_k,
            where=where or None,
            include=["documents", "metadatas", "distances"],
        )
        hits: List[SearchHit] = []
        ids = (res.get("ids") or [[]])[0]
        docs = (res.get("documents") or [[]])[0]
        metas = (res.get("metadatas") or [[]])[0]
        dists = (res.get("distances") or [[]])[0]
        for i, _id in enumerate(ids):
            dist = dists[i] if i < len(dists) else 1.0   # cosine distance -> similarity
            hits.append(SearchHit(
                id=_id,
                score=1.0 - float(dist),
                text=docs[i] if i < len(docs) else "",
                metadata=metas[i] if i < len(metas) else {},
            ))
        return hits

    def delete(self, where: Dict) -> None:
        """Delete all points matching an exact-match metadata filter (e.g. one document_id)."""
        if where:
            self._col.delete(where=where)

    def count(self) -> int:
        return self._col.count()

    def delete_collection(self) -> None:
        self._client.delete_collection(self.collection_name)

    def close(self) -> None:
        _CLIENTS.pop(self._path, None)
