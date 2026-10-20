"""Week 5 baseline: BM25 looks for matching words rather than matching meaning."""
import re
import numpy as np
from rank_bm25 import BM25Okapi


def tokenize(text):
    """Convert text to lowercase words; keep the same rule for docs and queries."""
    return re.findall(r"\b\w+\b", str(text).lower())


class BM25Searcher:
    def __init__(self, remarks_list):
        self.listings = [str(t) for t in remarks_list]
        if not self.listings:
            raise ValueError("Need at least one listing")
        # BM25 uses word counts, not sentence embeddings.
        self.bm25 = BM25Okapi([tokenize(t) for t in self.listings])

    def search(self, query, top_k=10):
        """Rank listings by BM25 word-match scores."""
        if not isinstance(query, str) or not query.strip():
            raise ValueError("Query must be nonempty text")
        if not isinstance(top_k, int) or top_k < 1:
            raise ValueError("top_k must be positive")
        scores = self.bm25.get_scores(tokenize(query))
        # Sorting scores highest first yields the most likely keyword matches.
        positions = np.argsort(-scores, kind="stable")[:top_k]
        return [
            {"row_index": int(i), "listing": self.listings[i], "score": float(scores[i])}
            for i in positions
        ]
