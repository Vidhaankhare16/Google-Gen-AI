#!/usr/bin/env python3
"""
ChromaDB vs Qdrant comparative study for the Legal EASE legal knowledge base — 5-run edition.

Runs the full benchmark N times (default 5) and aggregates mean +/- std so the numbers are
evidence-backed rather than single-shot. All runs use the SAME 9k-vector corpus and the SAME
InLegalBERT embeddings, so only the vector database differs.

Measured per run:
  * Indexing        — upsert time + throughput (vectors/sec) building the index from scratch
  * Query latency   — percentiles (p50/p90/p95/p99), throughput; filtered vs unfiltered
  * Retrieval quality — recall@k vs an exact brute-force (numpy) ground truth
  * Cross-DB agreement — top-k overlap, top-1 agreement, score MAE between Chroma and Qdrant
  * Resource usage  — on-disk index size + peak process RSS (each DB in an isolated subprocess)
  * Delete          — time to delete a metadata-filtered subset (per-document eviction proxy)

Outputs:
  docs/benchmark_data.json      — per-run + aggregate metrics (feeds the visual report)
  docs/vector_db_comparison.md  — aggregated markdown summary

Run from repo root (after indexing the KB into Chroma):
    python scripts/benchmark_vector_dbs.py --runs 5
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time

import numpy as np

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO_ROOT, "backend"))
from rag import settings  # noqa: E402

K = 10
LAT_RUNS = 25            # timed repetitions per query within a run
BATCH = 512

QUERIES = [
    "Is a non-refundable security deposit legally enforceable in India?",
    "What is the maximum penalty a court will enforce for early termination of a lease?",
    "Can a landlord increase rent unilaterally at his sole discretion?",
    "Are post-employment non-compete clauses valid under Indian law?",
    "What does Section 74 of the Indian Contract Act say about penalties and liquidated damages?",
    "Is a 36-month lock-in with a full-term penalty fair to a tenant?",
    "What are unfair contract terms under the Consumer Protection Act 2019?",
    "Is a personal guarantee covering family assets enforceable?",
    "Can a lender charge 60% per annum interest on default?",
    "What notice period is required to terminate a rental agreement in India?",
    "Are arbitration clauses seated in Singapore or Delaware enforceable for an Indian contract?",
    "What are a tenant's rights regarding refund of the security deposit?",
    "Is a clause waiving the right to approach a consumer forum valid?",
    "Can an employer reduce an employee's salary at its sole discretion?",
    "Is an indemnity clause without any monetary limit enforceable?",
    "What happens if a lease deed above 12 months is not registered?",
    "Are class-action waivers enforceable in India?",
    "Can intellectual property created on personal time be assigned to the employer?",
    "What is the effect of a unilateral variation clause in a loan agreement?",
    "Is a perpetual confidentiality obligation reasonable in an NDA?",
    "What remedies does a tenant have against forfeiture of a deposit?",
    "Is a six-month resignation notice period for an employee enforceable?",
    "What is restraint of trade under Section 27 of the Indian Contract Act?",
    "Are late-payment fees of Rs 5000 per day without a cap enforceable?",
    "Can a landlord terminate a lease without cause or notice?",
    "What protection does the Transfer of Property Act give to lessees?",
    "Is a foreign governing law valid for a purely domestic Indian contract?",
    "How do liquidated damages differ from a penalty under Indian law?",
]


def dir_size(path: str) -> int:
    total = 0
    for root, _, files in os.walk(path):
        for f in files:
            try:
                total += os.path.getsize(os.path.join(root, f))
            except OSError:
                pass
    return total


# --------------------------------------------------------------------------- #
# Worker: benchmark one backend once (isolated subprocess).                    #
# --------------------------------------------------------------------------- #
def run_worker(backend, data_path, meta_path, store_path, out_path):
    d = np.load(data_path)
    embs = d["embeddings"].astype(np.float32)
    qvecs = d["query_vecs"].astype(np.float32)
    gt = d["gt_topk"]
    meta = json.load(open(meta_path, encoding="utf-8"))
    ids, docs, metas = meta["ids"], meta["documents"], meta["metadatas"]
    id2idx = {i: n for n, i in enumerate(ids)}

    if backend == "chroma":
        from rag.chroma_store import ChromaStore
        store = ChromaStore("bench", dim=int(embs.shape[1]), path=store_path)
    else:
        from rag.qdrant_store import QdrantStore
        store = QdrantStore("bench", dim=int(embs.shape[1]), path=store_path)

    # Start from an empty collection every run. Local mode already gets a fresh folder per run, but a
    # Qdrant/Chroma *server* keeps collections between runs, so an explicit reset keeps the index
    # build measurement honest (a true from-scratch build).
    store.reset()

    t0 = time.time()
    for s in range(0, len(ids), BATCH):
        store.upsert(ids[s:s + BATCH], embs[s:s + BATCH].tolist(),
                     docs[s:s + BATCH], metas[s:s + BATCH])
    index_time = time.time() - t0
    # Local store keeps data under store_path; a server keeps it in the container (measured via docker).
    disk = dir_size(store_path)

    lat, per_idx, per_scores = [], [], []
    for qv in qvecs:
        ql = qv.tolist()
        store.query(ql, top_k=K)
        hits = None
        for _ in range(LAT_RUNS):
            t = time.time(); hits = store.query(ql, top_k=K); lat.append((time.time() - t) * 1000)
        per_idx.append([id2idx.get(h.id, -1) for h in hits])
        per_scores.append([round(h.score, 6) for h in hits])

    flat = []
    for qv in qvecs:
        ql = qv.tolist()
        store.query(ql, top_k=K, where={"doc_type": "statute"})
        for _ in range(LAT_RUNS):
            t = time.time(); store.query(ql, top_k=K, where={"doc_type": "statute"})
            flat.append((time.time() - t) * 1000)

    recalls = []
    for qi in range(len(qvecs)):
        got = {i for i in per_idx[qi] if i >= 0}
        recalls.append(len(got & set(gt[qi].tolist())) / K)

    before = store.count()
    t = time.time(); store.delete({"doc_type": "glossary"}); delete_time = time.time() - t
    after = store.count()
    store.close()

    json.dump({
        "backend": backend, "n_vectors": len(ids),
        "index_time_s": index_time, "throughput_vps": len(ids) / index_time if index_time else 0,
        "disk_bytes": disk,
        "lat_unfiltered_ms": lat, "lat_filtered_ms": flat,
        "recall_at_k": float(np.mean(recalls)),
        "per_query_idx": per_idx, "per_query_scores": per_scores,
        "delete_time_ms": delete_time * 1000, "deleted_count": before - after,
    }, open(out_path, "w"))


# --------------------------------------------------------------------------- #
# Orchestrator                                                                 #
# --------------------------------------------------------------------------- #
def pctl(samples):
    a = np.array(samples)
    return {"mean": float(a.mean()), "p50": float(np.percentile(a, 50)),
            "p90": float(np.percentile(a, 90)), "p95": float(np.percentile(a, 95)),
            "p99": float(np.percentile(a, 99)), "min": float(a.min()), "max": float(a.max()),
            "qps": 1000.0 / float(a.mean())}


def spawn_and_poll_rss(backend, data_path, meta_path, store_path, out_path):
    cmd = [sys.executable, os.path.abspath(__file__), "--worker", backend,
           "--data", data_path, "--meta", meta_path, "--store", store_path, "--out", out_path]
    proc = subprocess.Popen(cmd)
    peak = 0
    try:
        import psutil
        p = psutil.Process(proc.pid)
        while proc.poll() is None:
            try:
                rss = p.memory_info().rss
                for c in p.children(recursive=True):
                    rss += c.memory_info().rss
                peak = max(peak, rss)
            except Exception:
                pass
            time.sleep(0.05)
    except ImportError:
        peak = None
    proc.wait()
    if proc.returncode != 0:
        raise RuntimeError(f"{backend} worker exited with code {proc.returncode}")
    return peak


def extract_corpus():
    from rag.chroma_store import ChromaStore
    src = ChromaStore(settings.KB_COLLECTION)
    n = src.count()
    print(f"Extracting {n} vectors from existing '{settings.KB_COLLECTION}' (chroma)...")
    got = src._col.get(include=["embeddings", "documents", "metadatas"])
    src.close()
    return got["ids"], np.array(got["embeddings"], dtype=np.float32), got["documents"], got["metadatas"]


def correlation(a, b):
    overlaps, deltas = [], []
    for qi in range(len(QUERIES)):
        ia = {i for i in a["per_query_idx"][qi] if i >= 0}
        ib = {i for i in b["per_query_idx"][qi] if i >= 0}
        overlaps.append(len(ia & ib) / K)
        sa = {idx: sc for idx, sc in zip(a["per_query_idx"][qi], a["per_query_scores"][qi])}
        sb = {idx: sc for idx, sc in zip(b["per_query_idx"][qi], b["per_query_scores"][qi])}
        for idx in set(sa) & set(sb):
            if idx >= 0:
                deltas.append(abs(sa[idx] - sb[idx]))
    top1 = np.mean([1.0 if a["per_query_idx"][qi][0] == b["per_query_idx"][qi][0] else 0.0
                    for qi in range(len(QUERIES))])
    return {"overlap_at_k": float(np.mean(overlaps)), "top1_agreement": float(top1),
            "score_mae": float(np.mean(deltas)) if deltas else 0.0}


def mean_std(vals):
    a = np.array(vals, dtype=float)
    return {"mean": float(a.mean()), "std": float(a.std()), "min": float(a.min()), "max": float(a.max())}


def aggregate(runs):
    """Aggregate a list of per-run result dicts into mean/std per metric per backend."""
    out = {"chroma": {}, "qdrant": {}, "correlation": {}}
    scalar = ["index_time_s", "throughput_vps", "disk_bytes", "recall_at_k",
              "peak_rss_bytes", "delete_time_ms"]
    pcts = ["mean", "p50", "p90", "p95", "p99", "max", "qps"]
    for be in ("chroma", "qdrant"):
        for m in scalar:
            out[be][m] = mean_std([r[be][m] for r in runs])
        for lat in ("lat_unfiltered", "lat_filtered"):
            out[be][lat] = {p: mean_std([r[be][lat][p] for r in runs]) for p in pcts}
    for m in ("overlap_at_k", "top1_agreement", "score_mae"):
        out["correlation"][m] = mean_std([r["correlation"][m] for r in runs])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--worker", choices=["chroma", "qdrant"])
    ap.add_argument("--data"); ap.add_argument("--meta")
    ap.add_argument("--store"); ap.add_argument("--out")
    ap.add_argument("--runs", type=int, default=5)
    args = ap.parse_args()

    if args.worker:
        run_worker(args.worker, args.data, args.meta, args.store, args.out)
        return

    ids, embs, docs, metas = extract_corpus()
    from rag.embeddings import Embedder
    print(f"Embedding {len(QUERIES)} benchmark queries...")
    qvecs = np.array(Embedder.get().embed(QUERIES), dtype=np.float32)
    sims = embs @ qvecs.T
    gt = np.argsort(-sims, axis=0)[:K, :].T

    tmp = tempfile.mkdtemp(prefix="vdb_bench_")
    data_path = os.path.join(tmp, "data.npz")
    meta_path = os.path.join(tmp, "meta.json")
    np.savez(data_path, embeddings=embs, query_vecs=qvecs, gt_topk=gt)
    json.dump({"ids": ids, "documents": docs, "metadatas": metas},
              open(meta_path, "w", encoding="utf-8"))

    runs = []
    for run_i in range(args.runs):
        print(f"\n########## RUN {run_i+1}/{args.runs} ##########", flush=True)
        run = {}
        for backend in ["chroma", "qdrant"]:
            store_path = os.path.join(tmp, f"store_{backend}_{run_i}")
            out_path = os.path.join(tmp, f"out_{backend}_{run_i}.json")
            peak = spawn_and_poll_rss(backend, data_path, meta_path, store_path, out_path)
            r = json.load(open(out_path, encoding="utf-8"))
            run[backend] = {
                "index_time_s": r["index_time_s"], "throughput_vps": r["throughput_vps"],
                "disk_bytes": r["disk_bytes"], "recall_at_k": r["recall_at_k"],
                "peak_rss_bytes": peak or 0, "delete_time_ms": r["delete_time_ms"],
                "deleted_count": r["deleted_count"], "n_vectors": r["n_vectors"],
                "lat_unfiltered": pctl(r["lat_unfiltered_ms"]),
                "lat_filtered": pctl(r["lat_filtered_ms"]),
                "per_query_idx": r["per_query_idx"], "per_query_scores": r["per_query_scores"],
            }
            print(f"  {backend:7} index {r['index_time_s']:.1f}s | "
                  f"q p95 {run[backend]['lat_unfiltered']['p95']:.2f}ms | "
                  f"recall@{K} {r['recall_at_k']:.3f} | RSS {(peak/1e6 if peak else 0):.0f}MB", flush=True)
        run["correlation"] = correlation(run["chroma"], run["qdrant"])
        # strip bulky per-query arrays from stored run (keep only correlation)
        for be in ("chroma", "qdrant"):
            run[be].pop("per_query_idx", None); run[be].pop("per_query_scores", None)
        runs.append(run)

    agg = aggregate(runs)
    data = {"meta": {"n_vectors": int(embs.shape[0]), "n_queries": len(QUERIES),
                     "runs": args.runs, "k": K, "lat_runs": LAT_RUNS,
                     "embedding_model": settings.EMBEDDING_MODEL, "dim": int(embs.shape[1])},
            "runs": runs, "aggregate": agg}

    os.makedirs(os.path.join(REPO_ROOT, "docs"), exist_ok=True)
    json.dump(data, open(os.path.join(REPO_ROOT, "docs", "benchmark_data.json"), "w"), indent=2)
    write_markdown(data)
    import shutil
    shutil.rmtree(tmp, ignore_errors=True)
    print(f"\nWrote docs/benchmark_data.json and docs/vector_db_comparison.md ({args.runs} runs).")


def _ms(x):  # bytes -> MB string
    return f"{x/1e6:.1f}"


def write_markdown(data):
    agg = data["aggregate"]; c = agg["chroma"]; q = agg["qdrant"]; corr = agg["correlation"]
    m = data["meta"]

    def ms(v):  # mean +/- std
        return f"{v['mean']:.2f} ± {v['std']:.2f}"

    def msf(v, f=1):
        return f"{v['mean']:.{f}f} ± {v['std']:.{f}f}"

    L = []; A = L.append
    A(f"# ChromaDB vs Qdrant — Comparative Study (Legal EASE), {m['runs']}-run average\n")
    A(f"Corpus: **{m['n_vectors']} vectors** ({m['embedding_model']}, {m['dim']}-dim, cosine). "
      f"Both DBs loaded with identical embeddings; each backend benchmarked in an isolated subprocess. "
      f"**{m['runs']} independent runs**, {m['n_queries']} queries, {m['lat_runs']} timed reps each, "
      f"top-k={m['k']}. Values are **mean ± std** across runs.\n")

    A("## 1. Indexing performance")
    A("| Metric | ChromaDB | Qdrant |\n|---|---|---|")
    A(f"| Index build time (s) | {msf(c['index_time_s'])} | {msf(q['index_time_s'])} |")
    A(f"| Throughput (vectors/s) | {c['throughput_vps']['mean']:.0f} ± {c['throughput_vps']['std']:.0f} "
      f"| {q['throughput_vps']['mean']:.0f} ± {q['throughput_vps']['std']:.0f} |")
    A(f"| On-disk index (MB) | {_ms(c['disk_bytes']['mean'])} | {_ms(q['disk_bytes']['mean'])} |\n")

    A("## 2. Query latency — unfiltered (ms)")
    A("| Percentile | ChromaDB | Qdrant |\n|---|---|---|")
    for p in ["mean", "p50", "p90", "p95", "p99"]:
        A(f"| {p} | {ms(c['lat_unfiltered'][p])} | {ms(q['lat_unfiltered'][p])} |")
    A(f"| throughput (q/s) | {c['lat_unfiltered']['qps']['mean']:.0f} | {q['lat_unfiltered']['qps']['mean']:.0f} |\n")

    A("## 3. Query latency — metadata-filtered doc_type=statute (ms)")
    A("| Percentile | ChromaDB | Qdrant |\n|---|---|---|")
    for p in ["mean", "p95", "p99"]:
        A(f"| {p} | {ms(c['lat_filtered'][p])} | {ms(q['lat_filtered'][p])} |")
    A("")

    A("## 4. Retrieval quality — recall@k vs exact brute-force")
    A("| Metric | ChromaDB | Qdrant |\n|---|---|---|")
    A(f"| recall@{m['k']} | {c['recall_at_k']['mean']:.3f} ± {c['recall_at_k']['std']:.3f} "
      f"| {q['recall_at_k']['mean']:.3f} ± {q['recall_at_k']['std']:.3f} |\n")

    A("## 5. Cross-DB agreement (same query, both stores)")
    A("| Metric | Value |\n|---|---|")
    A(f"| top-{m['k']} overlap | {corr['overlap_at_k']['mean']:.3f} ± {corr['overlap_at_k']['std']:.3f} |")
    A(f"| top-1 agreement | {corr['top1_agreement']['mean']:.3f} |")
    A(f"| mean abs. score difference | {corr['score_mae']['mean']:.2e} |\n")

    A("## 6. Resource usage")
    A("| Metric | ChromaDB | Qdrant |\n|---|---|---|")
    A(f"| Peak process RSS (MB) | {_ms(c['peak_rss_bytes']['mean'])} | {_ms(q['peak_rss_bytes']['mean'])} |")
    A(f"| On-disk (MB) | {_ms(c['disk_bytes']['mean'])} | {_ms(q['disk_bytes']['mean'])} |\n")

    A("## 7. Delete performance (metadata-filtered subset)")
    A("| Metric | ChromaDB | Qdrant |\n|---|---|---|")
    A(f"| delete time (ms) | {msf(c['delete_time_ms'])} | {msf(q['delete_time_ms'])} |\n")

    A("*Full per-run data + charts: `docs/benchmark_data.json` and the visual report. "
      "Answer-quality comparison: `scripts/compare_answers.py`.*")

    open(os.path.join(REPO_ROOT, "docs", "vector_db_comparison.md"), "w", encoding="utf-8").write("\n".join(L))


if __name__ == "__main__":
    main()
