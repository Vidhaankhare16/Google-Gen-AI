# Presenter's Guide — ChromaDB vs Qdrant (Legal EASE)

> Companion notes for presenting `vector_db_comparison_report_v3_print.html`.
> Read this once and you'll have enough context to narrate every slide and defend every number.

**The 15-second pitch:** *"We built a legal-RAG knowledge base of ~9,000 Indian-law passages, then
ran a rigorous 5-run benchmark to decide which vector database to use — ChromaDB or Qdrant. Answer
quality is a tie, so it came down to performance: Chroma wins in-process query latency, Qdrant's
server wins indexing, deletes, and recall. Recommendation: Chroma now, Qdrant server at scale."*

---

## 1. Project context — why this comparison exists

Legal EASE is a RAG system that analyses Indian legal contracts. When a user uploads a contract, the
app retrieves relevant **Indian statutes, case-law precedents, and risk references** from a knowledge
base and feeds them to Gemini to ground the analysis (so it cites real law instead of hallucinating).

A RAG system's retrieval layer is a **vector database**. We had to pick one for production, so we
benchmarked the two leading open-source options — **ChromaDB** and **Qdrant** — on our own data and
workload rather than trusting generic blog benchmarks.

**Say this:** *"The vector DB is the retrieval engine of our RAG stack. Choosing it is an
infrastructure decision for an institutional legal-AI product, so we made it evidence-based."*

---

## 2. The knowledge base (KB)

### 2.1 What's in it — 9,063 chunks across 5 categories

| Category | Chunks | Source |
|---|---|---|
| **Case law (judgments)** | **7,168** | Kaggle "SC Judgments India (1950–2024)" — 249 curated judgments |
| **Statutes & codes** | **1,791** | Constitution + 12 Acts (India Code, via a HuggingFace mirror) |
| **Legal glossary** | 47 | Plain-English term definitions (authored) |
| **Red-flag clause reference** | 30 | Risky-clause patterns → why risky → statute (authored) |
| **Model contract templates** | 27 | Standard rent/NDA/employment clauses (authored) |
| **Total** | **9,063** | |

The **12 statutes**: Indian Contract Act 1872, **Bharatiya Nyaya Sanhita 2023 (BNS)**, Transfer of
Property Act, Consumer Protection Act 2019, IT Act 2000, Arbitration & Conciliation Act, Specific
Relief Act, Sale of Goods Act, Partnership Act, Registration Act, Negotiable Instruments Act, plus
the Constitution.

### 2.2 How the case-law documents were selected (the interesting part)

The Kaggle dataset is **~26,000+ judgment PDFs** organised in per-year folders. We did **not** ingest
all of them (that would be 100k+ chunks and mostly irrelevant). Instead, our ingester
(`scripts/ingest_kaggle_pdfs.py`) does a **curated, topic-filtered sample**:

1. **Walks the per-year folders** and **shuffles across all years** (fixed seed) → temporal spread
   from 1950 to 2024, not just old cases.
2. **Extracts text fast** with PyMuPDF (~40 ms/PDF).
3. **Harvests metadata for free** — the case name + date come from the **filename**
   (`Abdulla_Ahmed_vs_..._on_14_March_1950.PDF`), and the **`Equivalent citations:`** and **`Bench:`**
   lines come from the judgment's header text. → real neutral citations (AIR/SCR/SCC) and judge names.
4. **Topic-filters** to keep only contract / consumer / tenancy / commercial judgments (keyword
   match: *contract, agreement, lease, tenancy, arbitration, indemnity, damages, breach, employment,
   consumer, liquidated…*). A random criminal case about, say, gold-ornament theft is dropped.
5. **Dedupes by case name** and **caps at 250** to keep the corpus balanced.

**Result: 249 distinct judgments, 222 with real citations** → 7,168 chunks. Because the app analyses
*contracts*, we deliberately biased the corpus toward contract/consumer/tenancy law.

**Say this:** *"We didn't dump 26,000 judgments. We sampled across all years, extracted case names
and citations from the filenames and headers, and kept only the ~250 judgments relevant to contract
and consumer disputes — the law our app actually needs."*

### 2.3 "How is it ~9,000?" — chunks, not tokens

**Important clarification for the room:** the 9,063 figure is **chunks (a.k.a. passages/vectors)**,
not tokens.

- A document is split into **chunks** so each fits the embedding model's context window. Each chunk
  is **≤ ~400 tokens** (the model's hard limit is 512; we target 400 with ~50 tokens of overlap).
- **Chunking strategy is content-aware:** statutes are split **by section**, judgments **by
  paragraph** (packed to ~400 tokens), and glossary/red-flag/template entries are **one chunk each**.
- Every chunk becomes **one 768-dimensional vector** (via InLegalBERT). So "9,063 vectors" = "9,063
  chunks."
- **Why it lands near 9,000:** case law dominates — 249 full judgments average ~29 chunks each
  (~7,200), plus 1,791 statute-section chunks, plus ~100 authored chunks. Total legal text is
  roughly **2–3 million tokens**; the 250-judgment cap is what keeps the vector count ~9k instead of
  100k+.

**If someone says "9,000 tokens":** gently correct — *"9,000 chunks; each chunk is up to ~400 tokens,
so it's ~2–3 million tokens of legal text total."*

### 2.4 The embedding model — InLegalBERT

- Model: **`law-ai/InLegalBERT`** — a BERT trained on **5.4 million Indian court documents**. We chose
  it over general embeddings (OpenAI, BGE) because it understands Indian legal vocabulary.
- Output: **768-dim** vectors, **mean-pooled** (InLegalBERT has no native sentence head), then
  **L2-normalized** so cosine similarity is meaningful.
- Runs **on CPU** locally (no GPU needed) — embedding the full KB once took ~31 minutes; that's a
  one-time cost and is **not** part of the DB benchmark (see methodology).

---

## 3. Methodology — how we measured (say this early; it earns trust)

The golden rule: **only the vector database varies.** Everything else is held constant.

- **Identical vectors.** The 9,063 InLegalBERT embeddings are computed **once** and fed to every
  configuration. Embedding cost never contaminates the DB numbers.
- **Isolated subprocess.** Each database runs in its **own process**; the parent samples memory (RSS)
  for a clean peak. For the Qdrant *server*, memory is measured on the **container**.
- **Exact ground truth for recall.** We compute the *true* top-10 neighbours with a brute-force NumPy
  cosine scan over all 9,063 vectors, then check what each database's fast search returns against it.
- **5 independent runs, reported as mean ± std** — so variance is visible and nobody can say it was a
  lucky single shot.
- **Fixed query set:** 28 realistic Indian-contract-law questions; latency = 25 timed reps × 28
  queries × 5 runs; top-k = 10.

---

## 4. The two databases (30-second primer per slide)

- **ChromaDB** — Python-first "embeddings database" for LLM apps. Runs **in-process** (HNSW via
  hnswlib + SQLite). No server to run: `pip install` and go. Great for single-node / prototyping.
- **Qdrant** — a **Rust** vector-search engine built for production scale: a server with gRPC/REST,
  indexed metadata filtering, quantization, sharding/replication/HA. Also has an embedded Python mode
  for development (which turned out to matter — see §6).

Both are **Apache-2.0** (fully open source, no license risk).

---

## 5. The metrics — what each means, how it was tested, the result

Present these in order; each is one chart/slide.

| Metric | What it means | How we tested it | Headline result |
|---|---|---|---|
| **Indexing time / throughput** | Time to build the index from scratch (insert all 9,063 vectors) | Timed the batched upsert loop into a fresh, empty collection | Qdrant **server** fastest (6.2 s); Chroma 9.3 s; Qdrant local 54.9 s |
| **Query latency** (mean, p50/p90/p95/p99) | How long one similarity search takes; percentiles show tail latency | 28 queries × 25 timed reps × 5 runs, top-k=10 | Chroma ~1.4 ms (in-process); Qdrant server ~15 ms; local ~32 ms |
| **Filtered query latency** | Latency when also filtering by metadata (`doc_type`) | Same, with a `where` filter | Chroma 12 ms; **Qdrant server 27 ms** (vs 93 ms local — payload indexes help) |
| **Recall@10** | Of the *true* 10 nearest vectors, how many the fast search actually returns (accuracy) | Compare each store's top-10 vs the exact brute-force top-10 | Qdrant **1.000**; Chroma **0.76** (default HNSW; tunable) |
| **Cross-DB agreement** | Do the two stores return the same results? (overlap, top-1 match, score diff) | Compare the two stores' top-10 per query | 0.76 overlap; scores identical to 1e-7 (same vectors) |
| **Resource usage** | On-disk index size + peak RAM | Directory size on disk; RSS polled per process/container | Qdrant −35% disk; Chroma lowest RAM (228 MB) |
| **Delete performance** | Time to delete a metadata-filtered subset (matters for our doc-expiry eviction) | Timed a filtered delete of the 47 glossary vectors | Qdrant **server 37 ms**; Chroma 158 ms; local 290 ms |
| **Answer quality** | Do the *generated answers* differ between backends? (the thing users actually see) | Same 3 questions → each backend → Gemini → cosine-compare the two answers | **0.98 similarity — effectively identical** |

**The two things to emphasise verbally:**
1. **Recall vs latency is a trade-off, not a defect.** Chroma is fast because its default HNSW
   explores fewer candidates; that's tunable. Qdrant is accurate out of the box.
2. **Answer quality is a tie because retrieval agrees where it counts.** Even though top-10 overlap
   is only 0.76, the *decisive* high-signal chunks (the right statute, the right red-flag) are
   retrieved by **both** — so the LLM produces the same grounded answer. In our example questions,
   both backends retrieved the **identical top-9 sources with identical scores**.

---

## 6. The Qdrant server — how it actually works (they *will* ask)

This is the part most likely to draw technical questions, so here's the full picture.

### It's a Rust server, delivered as a Docker container — both, not either/or
- Qdrant **is written in Rust**. The "server" is that compiled Rust binary.
- We ran it via **Docker**: `docker run -p 6333:6333 -p 6334:6334 qdrant/qdrant` (image v1.18.3).
  Docker just **packages** the Rust binary + its runtime so it starts with one command. The container
  *is* the Rust server.
- (Qdrant can also run as a bare native binary or on Qdrant Cloud — Docker is simply the standard,
  reproducible way to run it locally, and what we used.)

### How a query flows in server mode
1. The Rust process listens on **port 6333 (REST/HTTP)** and **6334 (gRPC)**, storing vectors +
   metadata in `/qdrant/storage` inside the container (on a persistent volume).
2. Our Python app (`qdrant-client`) connects **over the network** to `localhost:6333`.
3. For each query: the client **serializes** the 768-dim query vector → sends it over gRPC → the Rust
   engine runs the **HNSW** nearest-neighbour search (with SIMD-accelerated distance math and
   **payload indexes** for the metadata filter) → returns the matches → the client **deserializes**.
4. That **network round-trip + (de)serialization is ~10–15 ms** on localhost. It's why the server's
   single-query latency (~15 ms) is higher than in-process Chroma (~1.4 ms) — **the search itself is
   fast; the transport is the overhead.**

### Why this matters (the key insight of the whole study)
- **In-process (Chroma)** = a function call, zero network cost → wins a single synchronous query.
- **Client-server (Qdrant)** = pays transport per request, **but** wins on concurrency, horizontal
  scale, isolation, HA, and many clients sharing one store — exactly what production needs. Under
  concurrent load, the server's throughput advantage reasserts itself.

### Contrast: Qdrant "local mode" (the earlier, slower numbers)
- Qdrant's embedded local mode (`QdrantClient(path=…)`) is a **pure-Python reimplementation** of
  search — no Rust engine, no server. It's a **dev convenience**, not the performance path. That's why
  local mode was **9× slower at indexing**. Running the real Rust server fixed that (index 55 s → 6 s,
  delete 290 ms → 37 ms). **This is why the report shows both modes** — to be honest that the first
  numbers weren't Qdrant's true capability.

**Say this:** *"Qdrant is a Rust engine; we ran it as a Docker container. Every query is a gRPC
round-trip to that engine, so single-query latency includes ~10–15 ms of transport that in-process
Chroma doesn't pay. The search itself is fast — indexing and deletes actually beat Chroma."*

---

## 7. The verdict (closing slide)

- **Answer quality: tie (0.98).** The DB choice does **not** change what the user reads.
- **ChromaDB** wins single-query latency and simplicity → **best for Legal EASE today** (single node,
  latency-sensitive, no ops).
- **Qdrant server** wins indexing, deletes, recall, and scales horizontally → **best at institutional
  scale**.
- **We're not locked in:** the app uses a pluggable `VectorStore` abstraction, so switching is a
  one-line `VECTOR_DB=qdrant` change — no rewrite.

---

## 8. Suggested presentation flow (map to the report)

1. **Hook** — "Which vector DB should power a legal-AI RAG system? We measured it." (masthead + verdict tiles)
2. **The knowledge base** — what's in it, how case law was curated (§2 here).
3. **Methodology** — identical vectors, exact ground truth, 5 runs (builds credibility).
4. **The master table** — the one-slide side-by-side; let it breathe.
5. **Walk the metrics** — indexing → latency → recall → answer quality (the tie is the "aha").
6. **Local vs server** — the honesty slide; the story flips; explain transport cost.
7. **Verdict + recommendation** — Chroma now, Qdrant server at scale, one-line switch.
8. **FAQ / discussion.**

Pacing: spend the most time on **the master table**, **answer-quality tie**, and **local-vs-server**.
Those are the memorable, defensible points.

---

## 9. FAQ — likely questions from GenAI/ML engineers

**Q: Why InLegalBERT instead of OpenAI / a general embedding model?**
A: It's trained on 5.4M Indian court documents, so it captures Indian legal vocabulary (statute
names, doctrines, latin terms) far better than a general model. It's also free, local, and CPU-only
— no per-call API cost or data leaving the machine, which matters for legal confidentiality.

**Q: Chroma's recall is only 0.76 — isn't that bad for a legal product?**
A: It's the **out-of-the-box** number with default HNSW parameters that favour speed. Recall is
**tunable** — raising the search breadth (`ef_search`) trades some of Chroma's large latency surplus
for recall. And critically, it didn't hurt answer quality (next question). We'd tune it before
shipping if we stay on Chroma.

**Q: If recall differs (0.76 vs 1.0), how can answer quality be identical (0.98)?**
A: Because the recall gap is in the **low-ranked tail**. The top few chunks — the ones that actually
decide the answer (the relevant statute, the matching red-flag) — are retrieved by **both** stores.
In our examples, both retrieved the identical top-9 sources with identical scores; the LLM saw the
same context, so the answers matched. The misses were low-similarity chunks the LLM wouldn't have
used anyway.

**Q: Does the choice of vector DB affect hallucination?**
A: No. Grounding quality depends on *what context reaches the LLM*, and both DBs deliver the same
high-signal context. Hallucination control comes from the retrieval + prompt design, not the store.

**Q: Why only ~250 judgments? Why not the full 26,000?**
A: Balance and relevance. 26k judgments would be ~150k+ chunks, dominated by criminal/unrelated law,
drowning the contract-relevant signal and making retrieval noisier. We sampled across all years and
kept the contract/consumer/tenancy cases our app needs. The pipeline can scale up trivially if we
want more.

**Q: Isn't Qdrant supposed to be faster? Why does Chroma beat it on latency?**
A: For a **single query**, in-process always beats client-server because Chroma is a function call
while Qdrant pays a network round-trip (~10–15 ms) even on localhost. Qdrant's engine is fast — it
actually beats Chroma on **indexing and deletes**. Qdrant's latency advantage shows up under
**concurrency and scale**, which a micro-benchmark of sequential single queries doesn't capture.

**Q: Was the first comparison (Qdrant local) unfair?**
A: We were upfront about it. Local/embedded mode is a Python dev shim, not Qdrant's engine — so we
**re-ran everything against the real Rust server** and reported both. That's the local-vs-server
slide.

**Q: How do you know the "true" top-10 for recall?**
A: Brute force. With only 9,063 vectors, we compute exact cosine similarity of every query against
every vector in NumPy — that's the mathematically exact answer, and we measure each DB's approximate
search against it.

**Q: Why cosine similarity and HNSW?**
A: Cosine because our embeddings are L2-normalized, so cosine = dot product = the natural similarity
for text embeddings. HNSW (Hierarchical Navigable Small World) is the standard approximate-nearest-
neighbour graph index both DBs use — it's fast and accurate; the recall difference is just parameter
tuning.

**Q: Why 5 runs — is that statistically meaningful?**
A: It's enough to expose run-to-run variance (HNSW graph construction is randomised, so Chroma's
recall drifts 0.73–0.78 across runs; Qdrant is deterministic at 1.000). We report mean ± std so the
spread is visible. For a go/no-go infra decision, 5 runs with tight std is sufficient.

**Q: What about managed/cloud vector DBs (Pinecone, Weaviate, pgvector)?**
A: Out of scope for this decision — we compared the two open-source engines we'd self-host for data
control and cost. Both have managed clouds (Chroma Cloud, Qdrant Cloud) if we later want managed ops.

**Q: Does this hold at millions of vectors?**
A: This benchmark is 9k on one CPU machine, so it doesn't extrapolate to billion-scale directly. But
it points the right way: at large scale you need Qdrant's server (sharding, quantization, HA), and
its indexing/recall advantages compound — which is exactly our "at scale → Qdrant" recommendation.

**Q: How does the hybrid retrieval actually work in the app?**
A: For a query we retrieve **per document type** — a few statutes + a few red-flags + a few
precedents + glossary — and merge them, rather than a flat top-k. That prevents the 7k judgment
chunks from drowning out the concise, high-value statute/red-flag chunks. It also retrieves from the
**uploaded document** itself, so answers combine "what your contract says" with "what Indian law says."

**Q: Where does the embedding run — is it a bottleneck?**
A: InLegalBERT runs on CPU. Embedding the whole KB was a ~31-min one-time job; per-query embedding is
milliseconds. It's not in the DB benchmark (we pre-computed vectors) precisely so it doesn't confound
the comparison. A GPU or a hosted embedding endpoint would make it near-instant in production.

**Q: Any cost implications between the two?**
A: Both are free/open-source. The real cost difference is **operational**: Chroma = no server to run
(cheaper to operate at small scale); Qdrant server = you run a container/cluster (more ops, but
necessary at scale). Neither adds LLM/API cost — that's Gemini, unchanged.
