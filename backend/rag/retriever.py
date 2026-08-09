"""
Hybrid retriever for Legal EASE.

Two retrieval sources, combined per query:
  1. **The uploaded document** — chunked + embedded into the `user_docs` collection at upload time,
     tagged with `document_id`. Answers "what does MY contract say?".
  2. **The legal knowledge base** (`legal_kb`) — statutes, red-flags, precedents, glossary.
     Answers "is this fair / legal / risky under Indian law?" and provides citations.

KB retrieval is done **per doc_type** (a few statutes + red-flags + precedents + glossary) so the
7k judgment chunks don't drown out the concise high-value chunks — the issue observed in Phase 1.

Both sources go through the same `VectorStore` interface, so the whole thing runs on either
ChromaDB or Qdrant (selected by `settings.VECTOR_DB`) — keeping the comparative study intact.
"""
from __future__ import annotations

import logging
import threading
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from rag import settings
from rag.chunker import chunk_generic
from rag.embeddings import Embedder
from rag.vector_store import VectorStore, SearchHit, get_store

logger = logging.getLogger(__name__)


@dataclass
class RetrievalResult:
    """Retrieved context for one query: chunks from the uploaded doc and from the legal KB."""
    doc_hits: List[SearchHit] = field(default_factory=list)
    kb_hits: List[SearchHit] = field(default_factory=list)

    def format_context(self, max_doc: int = 6, max_kb: int = 9) -> str:
        """Render a labelled context block for the LLM prompt, with bracketed source tags."""
        lines: List[str] = []
        if self.doc_hits:
            lines.append("=== EXCERPTS FROM THE UPLOADED DOCUMENT ===")
            for i, h in enumerate(self.doc_hits[:max_doc], 1):
                sec = h.metadata.get("section")
                tag = f"D{i}" + (f", {sec}" if sec else "")
                lines.append(f"[{tag}] {h.text.strip()}")
        if self.kb_hits:
            lines.append("\n=== RELEVANT INDIAN LAW & PRECEDENT (for grounding & citations) ===")
            lines.append(self.format_kb(max_kb))
        return "\n".join(lines)

    def format_kb(self, max_kb: int = 9) -> str:
        """Just the legal-KB context lines (each tagged with a human-readable citation)."""
        return "\n".join(f"[{_source_tag(h)}] {h.text.strip()}" for h in self.kb_hits[:max_kb])

    def citations(self) -> List[Dict]:
        """
        Structured sources for the API response / UI.

        Deduplicated by the authority itself, not by chunk: a long judgment or a long
        statutory section is several chunks in the store, and several of them can match
        the same query, which would otherwise list the same citation two or three times.
        The best-scoring chunk's score is kept, and the original ordering is preserved.
        """
        out: List[Dict] = []
        seen: Dict[tuple, int] = {}
        for h in self.kb_hits:
            m = h.metadata
            entry = {
                "type": m.get("doc_type"),
                "source": m.get("source"),
                "section": m.get("section"),
                "citation": m.get("citation"),
                "score": round(h.score, 3),
            }
            key = (entry["type"], entry["source"], entry["section"], entry["citation"])
            if key in seen:
                i = seen[key]
                out[i]["score"] = max(out[i]["score"], entry["score"])
            else:
                seen[key] = len(out)
                out.append(entry)
        return out


def _source_tag(h: SearchHit) -> str:
    """Human-readable citation tag for a KB hit, e.g. 'Statute: Indian Contract Act, Section 74'."""
    m = h.metadata
    dt = m.get("doc_type", "")
    src = m.get("source", "")
    sec = m.get("section")
    cite = m.get("citation")
    if dt == "statute":
        return f"Statute: {src}" + (f", {sec}" if sec else "")
    if dt == "judgment":
        return f"Precedent: {src}" + (f" [{cite}]" if cite else "")
    if dt == "redflag":
        return f"Red flag: {sec}" if sec else "Red flag"
    if dt == "glossary":
        return f"Definition: {sec}" if sec else "Definition"
    if dt == "template":
        return f"Model clause: {src}"
    return src or dt or "Source"


class Retriever:
    """Process-wide hybrid retriever over the legal KB + per-document collections."""

    _instance: Optional["Retriever"] = None
    _lock = threading.Lock()

    def __init__(self, backend: str = settings.VECTOR_DB):
        self.backend = backend
        self._embedder = Embedder.get()
        self._kb: VectorStore = get_store(backend, settings.KB_COLLECTION, settings.EMBEDDING_DIM)
        self._docs: VectorStore = get_store(backend, settings.USER_DOCS_COLLECTION,
                                            settings.EMBEDDING_DIM)

    @classmethod
    def get(cls) -> "Retriever":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # -- indexing the uploaded document ------------------------------------- #
    def index_document(self, document_id: str, text: str) -> int:
        """Chunk + embed an uploaded document into `user_docs`. Returns the chunk count."""
        chunks = chunk_generic(text)
        if not chunks:
            return 0
        embs = self._embedder.embed(chunks)
        # Point ids must be valid UUIDs for Qdrant; keep document_id in metadata for filter/delete.
        ids = [str(uuid.uuid4()) for _ in chunks]
        metas = [{"document_id": document_id, "chunk_index": i, "doc_type": "user_doc"}
                 for i in range(len(chunks))]
        self._docs.upsert(ids, embs, chunks, metas)
        logger.info(f"Indexed uploaded document {document_id}: {len(chunks)} chunks")
        return len(chunks)

    def delete_document(self, document_id: str) -> None:
        try:
            self._docs.delete(where={"document_id": document_id})
        except Exception as e:
            logger.warning(f"Failed to delete doc {document_id} from vector store: {e}")

    # -- retrieval ----------------------------------------------------------- #
    def retrieve(self, query: str, document_id: Optional[str] = None,
                 include_doc: bool = True, include_kb: bool = True) -> RetrievalResult:
        qvec = self._embedder.embed_query(query)
        result = RetrievalResult()

        if include_doc and document_id:
            try:
                result.doc_hits = self._docs.query(
                    qvec, top_k=settings.TOP_K_DOC, where={"document_id": document_id})
            except Exception as e:
                logger.warning(f"user_docs query failed: {e}")

        if include_kb:
            kb_hits: List[SearchHit] = []
            for doc_type, k in settings.KB_TOPK_BY_TYPE.items():
                try:
                    kb_hits.extend(self._kb.query(qvec, top_k=k, where={"doc_type": doc_type}))
                except Exception as e:
                    logger.warning(f"legal_kb query ({doc_type}) failed: {e}")
            kb_hits.sort(key=lambda h: h.score, reverse=True)
            result.kb_hits = kb_hits

        return result

    def retrieve_for_document(self, text: str, max_probes: int = 5,
                              max_hits: int = 12) -> RetrievalResult:
        """
        Retrieve the legal context for a whole-document analysis.

        Probing with the opening few thousand characters grounds the analysis on the
        deed's preamble — parties, place of execution, registration formalities — so the
        top hits come back as stamp-duty and registration provisions rather than the law
        that actually governs the risky clauses further down. Instead we probe with chunks
        spread across the whole document and keep each KB chunk's best score, which
        surfaces the substantive provisions the warnings need to cite.
        """
        chunks = chunk_generic(text)
        if not chunks:
            return RetrievalResult()

        step = max(1, len(chunks) // max_probes)
        probes = chunks[::step][:max_probes]

        best: Dict[str, SearchHit] = {}
        for probe in probes:
            for hit in self.retrieve(probe, include_doc=False, include_kb=True).kb_hits:
                if hit.id not in best or hit.score > best[hit.id].score:
                    best[hit.id] = hit

        hits = sorted(best.values(), key=lambda h: h.score, reverse=True)[:max_hits]
        logger.info(f"Document grounding: {len(probes)} probes -> {len(hits)} legal sources")
        return RetrievalResult(kb_hits=hits)
