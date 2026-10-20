"""Week 5: Compare semantic search and BM25 using human relevance judgments.

Gold labels are 0 = not relevant, 1 = somewhat relevant, 2 = very relevant.
A relevance file must contain query, row_index, relevance (see README).
Do NOT use model similarity scores as gold labels.
"""
import argparse
import csv
import json
import statistics
import time
from pathlib import Path

from scripts.bm25_search import BM25Searcher
from scripts.semantic_search import SemanticSearcher


def precision_at_k(results, relevant_rows, k=5):
    """Fraction of the top k results that humans marked relevant (>=1)."""
    return sum(item["row_index"] in relevant_rows for item in results[:k]) / k


def timed_search(searcher, query, repetitions=30, k=10):
    """Time warm end-to-end search: query embedding + FAISS, not index build."""
    searcher.search(query, top_k=k)  # Warm up the model and caches once.
    milliseconds = []
    for _ in range(repetitions):
        start = time.perf_counter()
        searcher.search(query, top_k=k)
        milliseconds.append((time.perf_counter() - start) * 1000)
    milliseconds.sort()
    return {"median_ms": statistics.median(milliseconds),
            "p95_ms": milliseconds[int(0.95 * (len(milliseconds) - 1))]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--index-dir", default="data/models")
    ap.add_argument("--judgments", default="data/week5_relevance.csv")
    args = ap.parse_args()

    searcher = SemanticSearcher()
    searcher.load(args.index_dir)
    keyword = BM25Searcher(searcher.listings)  # Exact SAME listings for a fair comparison.
    path = Path(args.judgments)

    if not path.exists():
        print(f"No human judgments yet: {path}")
        print("Create a CSV with columns: query,row_index,relevance")
        print("Judge at least 50 query-result pairs, then rerun.")
        return

    # Group manual relevance labels by query.
    judgments = {}
    with path.open(newline="", encoding="utf-8") as file:
        for row in csv.DictReader(file):
            q = row["query"]
            idx = int(row["row_index"])
            grade = int(row["relevance"])
            if grade not in (0, 1, 2):
                raise ValueError("Relevance grades must be 0, 1 or 2")
            judgments.setdefault(q, {})[idx] = grade

    if sum(len(v) for v in judgments.values()) < 50:
        print("Warning: fewer than 50 judged query-result pairs")

    for name, engine in [("Semantic", searcher), ("BM25", keyword)]:
        scores = []
        for q, graded_rows in judgments.items():
            # Unjudged retrieved documents are NOT automatically irrelevant.
            # Evaluate only if the top 5 are all judged, to avoid misleading scores.
            top = engine.search(q, top_k=5)
            if len(top) < 5 or any(x["row_index"] not in graded_rows for x in top):
                continue
            relevant = {i for i, grade in graded_rows.items() if grade >= 1}
            scores.append(precision_at_k(top, relevant))
        print(f"{name} mean Precision@5 on fully judged queries: "
              + (f"{statistics.mean(scores):.3f} ({len(scores)} queries)" if scores else "N/A: judge top 5 first"))

    # Speed should be tested using a 10k-listing saved index.
    latency = timed_search(searcher, next(iter(judgments)))
    print(f"Warm semantic latency: median {latency['median_ms']:.1f}ms; "
          f"p95 {latency['p95_ms']:.1f}ms; indexed {searcher.index.ntotal} listings")


if __name__ == "__main__":
    main()
