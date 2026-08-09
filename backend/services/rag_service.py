"""
RAG service facade for Legal EASE.

A thin, fault-tolerant wrapper around the hybrid retriever so the rest of the app (routes,
ai_analyzer, document_storage) can use RAG without worrying about it being unavailable. If the
vector stores aren't built yet, the embedding stack isn't installed, or anything else fails, every
call degrades to a safe no-op / None and the app continues in its pre-RAG mode.

The heavy retriever (InLegalBERT + vector stores) is loaded lazily on first use.
"""
from __future__ import annotations

import logging
import threading
from typing import Optional

logger = logging.getLogger(__name__)

_retriever = None
_init_failed = False
# Serialises first-use construction. The background warm-up thread and an early request
# otherwise build the retriever — and its vector-store clients — at the same time.
_init_lock = threading.Lock()


def _get():
    """Lazily construct the process-wide Retriever; remember failure so we don't retry every call."""
    global _retriever, _init_failed
    if _retriever is not None or _init_failed:
        return _retriever

    with _init_lock:
        if _retriever is None and not _init_failed:
            try:
                from rag.retriever import Retriever
                _retriever = Retriever.get()
                logger.info("✅ RAG retriever initialized (hybrid: uploaded doc + legal KB)")
            except Exception as e:
                _init_failed = True
                logger.warning(f"⚠️ RAG unavailable, falling back to non-RAG mode: {e}")
    return _retriever


def available() -> bool:
    return _get() is not None


def index_document(document_id: str, text: str) -> int:
    """Chunk+embed an uploaded document into the vector store. Returns chunk count (0 if unavailable)."""
    r = _get()
    if not r:
        return 0
    try:
        return r.index_document(document_id, text)
    except Exception as e:
        logger.warning(f"index_document failed for {document_id}: {e}")
        return 0


def delete_document(document_id: str) -> None:
    r = _get()
    if not r:
        return
    try:
        r.delete_document(document_id)
    except Exception as e:
        logger.warning(f"delete_document failed for {document_id}: {e}")


def retrieve(query: str, document_id: Optional[str] = None,
             include_doc: bool = True, include_kb: bool = True):
    """Return a RetrievalResult, or None if RAG is unavailable."""
    r = _get()
    if not r:
        return None
    try:
        return r.retrieve(query, document_id=document_id,
                          include_doc=include_doc, include_kb=include_kb)
    except Exception as e:
        logger.warning(f"retrieve failed: {e}")
        return None


def retrieve_for_document(text: str):
    """Legal context for a whole-document analysis, or None if RAG is unavailable."""
    r = _get()
    if not r:
        return None
    try:
        return r.retrieve_for_document(text)
    except Exception as e:
        logger.warning(f"retrieve_for_document failed: {e}")
        return None
