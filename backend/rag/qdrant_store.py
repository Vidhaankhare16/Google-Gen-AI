"""Qdrant implementation of the VectorStore interface (local on-disk or server, cosine).

Qdrant *local mode* permits only one client per storage folder per process, but the retriever
needs several collections (legal_kb + user_docs) at once. So clients are cached per location and
shared across QdrantStore instances.
"""
from __future__ import annotations

from typing import Dict, List, Optional

from rag import settings
from rag.vector_store import VectorStore, SearchHit, clean_metadata

_TEXT_KEY = "_text"           # payload key under which we stash the chunk text
_CLIENTS: Dict[str, object] = {}   # location -> shared QdrantClient


def _get_client(path: str, url: str):
    """Return a process-wide shared client for this location (local path or server url)."""
    key = url or path
    if key not in _CLIENTS:
        from qdrant_client import QdrantClient  # lazy
        _CLIENTS[key] = QdrantClient(url=url) if url else QdrantClient(path=path)
    return _CLIENTS[key]


def close_all() -> None:
    """Close every cached client (release local-mode file locks). For scripts/tests."""
    for key, client in list(_CLIENTS.items()):
        try:
            client.close()
        except Exception:
            pass
        _CLIENTS.pop(key, None)


class QdrantStore(VectorStore):
    def __init__(self, collection: str, dim: int = settings.EMBEDDING_DIM,
                 path: str = settings.QDRANT_PATH, url: str = settings.QDRANT_URL):
        self.collection_name = collection
        self.dim = dim
        self._key = url or path
        self._client = _get_client(path, url)
        self._create_collection()

    def _create_collection(self) -> None:
        from qdrant_client.models import Distance, VectorParams
        if not self._client.collection_exists(self.collection_name):
            self._client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=self.dim, distance=Distance.COSINE),
            )

    def upsert(self, ids: List[str], embeddings: List[List[float]],
               documents: List[str], metadatas: List[Dict]) -> None:
        from qdrant_client.models import PointStruct
        points = []
        for _id, vec, doc, meta in zip(ids, embeddings, documents, metadatas):
            payload = clean_metadata(meta)
            payload[_TEXT_KEY] = doc
            # Qdrant point ids must be UUIDs or ints; our chunk ids are uuid4 strings (valid).
            points.append(PointStruct(id=_id, vector=vec, payload=payload))
        self._client.upsert(collection_name=self.collection_name, points=points)

    def query(self, embedding: List[float], top_k: int = 5,
              where: Optional[Dict] = None) -> List[SearchHit]:
        res = self._client.query_points(
            collection_name=self.collection_name,
            query=embedding,
            limit=top_k,
            query_filter=self._build_filter(where),
            with_payload=True,
        ).points
        hits: List[SearchHit] = []
        for p in res:
            payload = dict(p.payload or {})
            text = payload.pop(_TEXT_KEY, "")
            hits.append(SearchHit(id=str(p.id), score=float(p.score), text=text, metadata=payload))
        return hits

    def _build_filter(self, where: Optional[Dict]):
        if not where:
            return None
        from qdrant_client.models import Filter, FieldCondition, MatchValue
        return Filter(must=[FieldCondition(key=k, match=MatchValue(value=v))
                            for k, v in where.items()])

    def delete(self, where: Dict) -> None:
        """Delete all points matching an exact-match metadata filter (e.g. one document_id)."""
        from qdrant_client.models import FilterSelector
        flt = self._build_filter(where)
        if flt is not None:
            self._client.delete(collection_name=self.collection_name,
                                points_selector=FilterSelector(filter=flt))

    def count(self) -> int:
        return self._client.count(collection_name=self.collection_name).count

    def delete_collection(self) -> None:
        self._client.delete_collection(collection_name=self.collection_name)

    def close(self) -> None:
        # Close + drop the shared client so the on-disk lock is released. Safe to call once at end
        # of a script; the app keeps the client for the process lifetime (no close needed).
        client = _CLIENTS.pop(self._key, None)
        if client is not None:
            try:
                client.close()
            except Exception:
                pass
