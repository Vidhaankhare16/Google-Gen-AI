# ChromaDB vs Qdrant — Comparative Study (Legal EASE), 5-run average

Corpus: **9063 vectors** (law-ai/InLegalBERT, 768-dim, cosine). Both DBs loaded with identical embeddings; each backend benchmarked in an isolated subprocess. **5 independent runs**, 28 queries, 25 timed reps each, top-k=10. Values are **mean ± std** across runs.

## 1. Indexing performance
| Metric | ChromaDB | Qdrant |
|---|---|---|
| Index build time (s) | 9.3 ± 0.2 | 6.2 ± 0.3 |
| Throughput (vectors/s) | 980 ± 23 | 1476 ± 77 |
| On-disk index (MB) | 130.7 | 0.0 |

## 2. Query latency — unfiltered (ms)
| Percentile | ChromaDB | Qdrant |
|---|---|---|
| mean | 1.42 ± 0.08 | 14.71 ± 0.37 |
| p50 | 1.40 ± 0.08 | 15.37 ± 0.05 |
| p90 | 1.68 ± 0.13 | 24.79 ± 1.53 |
| p95 | 1.78 ± 0.15 | 26.48 ± 0.27 |
| p99 | 2.04 ± 0.20 | 29.96 ± 0.33 |
| throughput (q/s) | 705 | 68 |

## 3. Query latency — metadata-filtered doc_type=statute (ms)
| Percentile | ChromaDB | Qdrant |
|---|---|---|
| mean | 11.65 ± 0.29 | 26.97 ± 1.37 |
| p95 | 13.09 ± 0.44 | 32.68 ± 0.16 |
| p99 | 14.49 ± 0.57 | 34.65 ± 0.13 |

## 4. Retrieval quality — recall@k vs exact brute-force
| Metric | ChromaDB | Qdrant |
|---|---|---|
| recall@10 | 0.772 ± 0.024 | 1.000 ± 0.000 |

## 5. Cross-DB agreement (same query, both stores)
| Metric | Value |
|---|---|
| top-10 overlap | 0.772 ± 0.024 |
| top-1 agreement | 0.671 |
| mean abs. score difference | 1.67e-07 |

## 6. Resource usage
| Metric | ChromaDB | Qdrant |
|---|---|---|
| Peak process RSS (MB) | 229.1 | 199.4 |
| On-disk (MB) | 130.7 | 0.0 |

## 7. Delete performance (metadata-filtered subset)
| Metric | ChromaDB | Qdrant |
|---|---|---|
| delete time (ms) | 164.4 ± 9.3 | 37.0 ± 5.6 |

*Full per-run data + charts: `docs/benchmark_data.json` and the visual report. Answer-quality comparison: `scripts/compare_answers.py`.*