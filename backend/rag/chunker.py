"""
Token-aware, type-specific text chunking for the Legal EASE knowledge base.

Design goals
------------
* Respect the embedding model's context limit. The chosen model is **InLegalBERT**
  (`law-ai/InLegalBERT`), a BERT-base with a **512 wordpiece-token** limit, so chunks target
  ~400 tokens with ~50 tokens of overlap, leaving headroom for the [CLS]/[SEP] specials.
* Chunk along **natural legal boundaries**: statutes by section, judgments by paragraph,
  glossary/red-flag/template entries one-per-chunk (sub-split only if oversized).
* Stay dependency-light in Phase 0: token counting uses the real InLegalBERT tokenizer *if*
  `transformers` is installed, otherwise a conservative word-based heuristic. Either way the
  chunk boundaries are stable; only the exact token counts differ.

This module has **no heavy imports at module load** so it is safe to use before the embedding
stack (torch/transformers) is installed.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional

# Chunking defaults (tokens). 512 hard limit → target 400, overlap 50.
DEFAULT_MAX_TOKENS = 400
DEFAULT_OVERLAP_TOKENS = 50
HARD_TOKEN_LIMIT = 512

# --------------------------------------------------------------------------- #
# Token counting                                                              #
# --------------------------------------------------------------------------- #
_HF_TOKENIZER = None
_HF_TRIED = False


def _get_hf_tokenizer():
    """Lazily load the InLegalBERT tokenizer if transformers is available; else None."""
    global _HF_TOKENIZER, _HF_TRIED
    if _HF_TRIED:
        return _HF_TOKENIZER
    _HF_TRIED = True
    try:
        from transformers import AutoTokenizer  # type: ignore

        _HF_TOKENIZER = AutoTokenizer.from_pretrained("law-ai/InLegalBERT")
        # This tokenizer is only ever used to *measure* text, never to feed the model, so
        # the 512-token ceiling doesn't apply — lift it to silence the length warning that
        # fires whenever we count a whole document before splitting it.
        _HF_TOKENIZER.model_max_length = int(1e9)
    except Exception:
        _HF_TOKENIZER = None  # fall back to heuristic
    return _HF_TOKENIZER


def count_tokens(text: str) -> int:
    """
    Count tokens the way InLegalBERT would (incl. special tokens).

    Uses the real wordpiece tokenizer when `transformers` is installed; otherwise a
    conservative heuristic (legal English averages ~1.3 wordpiece tokens per whitespace word).
    """
    tok = _get_hf_tokenizer()
    if tok is not None:
        return len(tok.encode(text, add_special_tokens=True))
    return int(len(text.split()) * 1.3) + 2  # +2 ≈ [CLS]/[SEP]


def using_real_tokenizer() -> bool:
    """True if token counts come from the actual InLegalBERT tokenizer (not the heuristic)."""
    return _get_hf_tokenizer() is not None


# --------------------------------------------------------------------------- #
# Sentence / section splitting                                                #
# --------------------------------------------------------------------------- #
# Abbreviations that must NOT end a sentence when followed by ". "
_ABBREV = {"no", "sec", "art", "cl", "v", "vs", "ors", "anr", "ltd", "pvt", "co", "govt",
           "hon", "mr", "mrs", "ms", "dr", "smt", "sri", "i.e", "e.g", "etc", "para", "pp"}

_SENT_SPLIT = re.compile(r"(?<=[.;:?!])\s+(?=[A-Z0-9(])")

# A statute "section" header at line start, e.g. "73.", "10A.", "Section 23.", "Sec. 4."
_SECTION_HEADER = re.compile(
    r"(?m)^\s*(?:Section|Sec\.?)?\s*(\d+[A-Za-z]?)\.\s+(.+)$"
)


def split_sentences(text: str) -> List[str]:
    """Lightweight sentence splitter tuned to avoid breaking on legal abbreviations."""
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []
    raw = _SENT_SPLIT.split(text)
    out: List[str] = []
    for part in raw:
        part = part.strip()
        if not part:
            continue
        # Merge a fragment back if the previous piece ended in a known abbreviation.
        if out:
            prev_tokens = out[-1].rstrip(".").split()
            prev_last = prev_tokens[-1].lower() if prev_tokens else ""
            if prev_last in _ABBREV:
                out[-1] = out[-1] + " " + part
                continue
        out.append(part)
    return out


# --------------------------------------------------------------------------- #
# Core packing                                                                #
# --------------------------------------------------------------------------- #
@dataclass
class Chunk:
    """A single chunk plus the sub-document label it came from (e.g. section/article)."""
    text: str
    section: Optional[str] = None
    extra: dict = field(default_factory=dict)


def chunk_generic(
    text: str,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    overlap_tokens: int = DEFAULT_OVERLAP_TOKENS,
) -> List[str]:
    """
    Greedily pack whole sentences into windows of <= max_tokens, with token overlap between
    consecutive windows so context isn't lost at boundaries. Never splits mid-sentence unless a
    single sentence alone exceeds the limit (then it is hard-split on words).
    """
    text = (text or "").strip()
    if not text:
        return []
    if count_tokens(text) <= max_tokens:
        return [text]

    sentences = split_sentences(text)
    chunks: List[str] = []
    current: List[str] = []
    current_tok = 0

    for sent in sentences:
        stok = count_tokens(sent)
        # A single monster sentence: hard-split on words.
        if stok > max_tokens:
            if current:
                chunks.append(" ".join(current))
                current, current_tok = [], 0
            chunks.extend(_hard_split_words(sent, max_tokens))
            continue

        if current_tok + stok <= max_tokens:
            current.append(sent)
            current_tok += stok
        else:
            chunks.append(" ".join(current))
            # Start next window with a token-overlap tail of the previous window.
            current = _overlap_tail(current, overlap_tokens)
            current_tok = count_tokens(" ".join(current)) if current else 0
            current.append(sent)
            current_tok += stok

    if current:
        chunks.append(" ".join(current))

    # Safety net: guarantee no chunk exceeds the hard limit, even if the active tokenizer counts
    # more aggressively than the heuristic (e.g. after the real InLegalBERT tokenizer is loaded
    # in Phase 1). Any over-limit chunk is hard-split on words.
    safe: List[str] = []
    ceiling = HARD_TOKEN_LIMIT - 12  # leave room for [CLS]/[SEP] and rounding
    for c in chunks:
        c = c.strip()
        if not c:
            continue
        if count_tokens(c) > ceiling:
            safe.extend(_hard_split_words(c, max_tokens))
        else:
            safe.append(c)
    return safe


def _overlap_tail(sentences: List[str], overlap_tokens: int) -> List[str]:
    """
    Return the trailing sentences whose combined tokens are <= overlap_tokens.

    We deliberately do NOT force-include a trailing sentence that alone exceeds the overlap
    budget: doing so would let the overlap seed plus the next sentence blow past max_tokens.
    An empty tail (no overlap at that boundary) is the safe outcome for a large final sentence.
    """
    tail: List[str] = []
    total = 0
    for sent in reversed(sentences):
        t = count_tokens(sent)
        if total + t > overlap_tokens:
            break
        tail.insert(0, sent)
        total += t
    return tail


def _hard_split_words(text: str, max_tokens: int) -> List[str]:
    """
    Last-resort split of an over-long sentence on word boundaries.

    Packs words against *measured* token counts rather than a fixed words-per-chunk ratio.
    The 1.3 tokens/word assumption holds for ordinary prose but badly under-counts legal
    text — section numbers, citations, ₹ amounts and party names all shatter into several
    wordpieces — so a fixed ratio produced chunks well past the 512-token limit, which the
    encoder then silently truncated. BERT tokenizes whitespace-separated words
    independently, so summing per-word counts gives the exact joint count.
    """
    words = text.split()
    if not words:
        return []

    specials = count_tokens("")            # [CLS]/[SEP] overhead, counted once per chunk
    budget = max(1, max_tokens - specials)
    per_word = [max(1, count_tokens(w) - specials) for w in words]

    chunks: List[str] = []
    current: List[str] = []
    running = 0
    for word, cost in zip(words, per_word):
        if current and running + cost > budget:
            chunks.append(" ".join(current))
            current, running = [], 0
        current.append(word)
        running += cost
    if current:
        chunks.append(" ".join(current))
    return chunks


# --------------------------------------------------------------------------- #
# Type-specific strategies                                                     #
# --------------------------------------------------------------------------- #
def extract_sections(text: str, dedup: bool = True) -> List[tuple]:
    """
    Find statute sections and return ``[(label, body), ...]`` in first-seen order.

    Bare acts (esp. India Code exports) repeat every section number twice: once in the
    'ARRANGEMENT OF SECTIONS' table of contents (a short title stub) and once in the enacted
    body (the full text). With ``dedup=True`` we keep, for each section number, the **longest**
    body seen — which is always the real enacted text, never the TOC stub. This is
    format-independent, so it works across all acts without per-act parsing hacks.
    """
    matches = list(_SECTION_HEADER.finditer(text))
    if not matches:
        return []
    result: List[list] = []      # list of [section_no, body]
    seen: dict = {}              # section_no -> index in result
    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        no = m.group(1)
        body = text[start:end].strip()
        if dedup and no in seen:
            j = seen[no]
            if len(body) > len(result[j][1]):
                result[j][1] = body      # replace TOC stub with the longer enacted body
        else:
            seen[no] = len(result)
            result.append([no, body])
    return [(f"Section {no}", body) for no, body in result]


def chunk_statute(text: str, max_tokens: int = DEFAULT_MAX_TOKENS,
                  min_section_tokens: int = 15) -> List[Chunk]:
    """
    Split a bare-act plain-text body by **section**. Each section becomes one chunk; sections
    longer than max_tokens are sub-split (with overlap) but keep their section label. Sections
    with fewer than ``min_section_tokens`` tokens (leftover TOC scraps, empty headings) are
    dropped. Falls back to generic chunking if no section headers are detected.
    """
    sections = extract_sections(text, dedup=True)
    if not sections:
        return [Chunk(text=c) for c in chunk_generic(text, max_tokens)]

    chunks: List[Chunk] = []
    for label, body in sections:
        if count_tokens(body) < min_section_tokens:
            continue
        if count_tokens(body) <= max_tokens:
            chunks.append(Chunk(text=body, section=label))
        else:
            for piece in chunk_generic(body, max_tokens):
                chunks.append(Chunk(text=piece, section=label))
    return chunks


def chunk_judgment(text: str, max_tokens: int = DEFAULT_MAX_TOKENS,
                   overlap_tokens: int = DEFAULT_OVERLAP_TOKENS) -> List[Chunk]:
    """
    Chunk a court judgment by paragraph, packing paragraphs into token-budgeted windows with
    overlap. Long paragraphs are sentence-packed via chunk_generic.
    """
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    if not paras:
        return []
    chunks: List[Chunk] = []
    current: List[str] = []
    current_tok = 0
    for para in paras:
        ptok = count_tokens(para)
        if ptok > max_tokens:
            if current:
                chunks.append(Chunk(text="\n\n".join(current)))
                current, current_tok = [], 0
            chunks.extend(Chunk(text=c) for c in chunk_generic(para, max_tokens, overlap_tokens))
            continue
        if current_tok + ptok <= max_tokens:
            current.append(para)
            current_tok += ptok
        else:
            chunks.append(Chunk(text="\n\n".join(current)))
            current, current_tok = [para], ptok
    if current:
        chunks.append(Chunk(text="\n\n".join(current)))
    return chunks


def chunk_entry(text: str, max_tokens: int = DEFAULT_MAX_TOKENS) -> List[str]:
    """
    One-entry-per-chunk strategy for glossary/red-flag/template entries. Keeps the entry whole
    unless it exceeds the token budget, in which case it is generically sub-chunked.
    """
    return chunk_generic(text, max_tokens) if count_tokens(text) > max_tokens else [text.strip()]
