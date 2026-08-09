# ChromaDB vs Qdrant — Comparative Study (Legal EASE), 5-run average

Corpus: **9063 vectors** (law-ai/InLegalBERT, 768-dim, cosine). Both DBs loaded with identical embeddings; each backend benchmarked in an isolated subprocess. **5 independent runs**, 28 queries, 25 timed reps each, top-k=10. Values are **mean ± std** across runs.

## 1. Indexing performance
| Metric | ChromaDB | Qdrant |
|---|---|---|
| Index build time (s) | 9.3 ± 0.2 | 54.9 ± 1.7 |
| Throughput (vectors/s) | 977 ± 20 | 165 ± 5 |
| On-disk index (MB) | 130.7 | 84.0 |

## 2. Query latency — unfiltered (ms)
| Percentile | ChromaDB | Qdrant |
|---|---|---|
| mean | 1.41 ± 0.09 | 32.19 ± 2.22 |
| p50 | 1.39 ± 0.07 | 32.26 ± 2.69 |
| p90 | 1.63 ± 0.13 | 34.77 ± 2.23 |
| p95 | 1.72 ± 0.18 | 36.30 ± 1.63 |
| p99 | 1.99 ± 0.38 | 40.12 ± 3.09 |
| throughput (q/s) | 710 | 31 |

## 3. Query latency — metadata-filtered doc_type=statute (ms)
| Percentile | ChromaDB | Qdrant |
|---|---|---|
| mean | 11.87 ± 0.29 | 93.26 ± 2.54 |
| p95 | 13.14 ± 0.62 | 99.55 ± 2.60 |
| p99 | 14.48 ± 1.09 | 113.57 ± 7.76 |

## 4. Retrieval quality — recall@k vs exact brute-force
| Metric | ChromaDB | Qdrant |
|---|---|---|
| recall@10 | 0.761 ± 0.017 | 1.000 ± 0.000 |

## 5. Cross-DB agreement (same query, both stores)
| Metric | Value |
|---|---|
| top-10 overlap | 0.761 ± 0.017 |
| top-1 agreement | 0.679 |
| mean abs. score difference | 1.82e-07 |

## 6. Resource usage
| Metric | ChromaDB | Qdrant |
|---|---|---|
| Peak process RSS (MB) | 228.2 | 328.4 |
| On-disk (MB) | 130.7 | 84.0 |

## 7. Delete performance (metadata-filtered subset)
| Metric | ChromaDB | Qdrant |
|---|---|---|
| delete time (ms) | 158.3 ± 3.9 | 289.7 ± 4.8 |

*Full per-run data + charts: `docs/benchmark_data.json` and the visual report. Answer-quality comparison: `scripts/compare_answers.py`.*