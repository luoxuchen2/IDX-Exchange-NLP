"""Week 5: Search listing descriptions by meaning, not exact words.

Example: searching for 'bright house' may find 'home filled with sunlight'.
"""
from pathlib import Path

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer


class SemanticSearcher:
    """Turn text into numbers (embeddings) and find the closest matches."""

    def __init__(self, model_name="all-MiniLM-L6-v2"):
        # Download/load the language model once. This model makes 384-number vectors.
        self.model = SentenceTransformer(model_name)
        self.model_name = model_name
        self.index = None  # FAISS will store the listing vectors here.
        self.listings = []  # Keep listing text in the same order as the vectors.

    def build_index(self, remarks_list, batch_size=64):
        """Make one vector per listing and store vectors in the FAISS index."""
        self.listings = [str(text) for text in remarks_list]
        if not self.listings or any(not text.strip() for text in self.listings):
            raise ValueError("Provide at least one nonempty listing description")

        # Batches avoid sending every description through the model at once.
        vectors = self.model.encode(
            self.listings,
            batch_size=batch_size,
            show_progress_bar=True,
            convert_to_numpy=True,
            normalize_embeddings=True,  # Makes inner product equal cosine similarity.
        )
        vectors = np.ascontiguousarray(vectors, dtype=np.float32)

        # IndexFlatIP searches every vector, so results are exact (not approximate).
        self.index = faiss.IndexFlatIP(vectors.shape[1])
        self.index.add(vectors)
        return self.index.ntotal

    def search(self, query, top_k=10):
        """Return top matches with a score and row position."""
        if self.index is None:
            raise ValueError("Build or load an index before searching")
        if not isinstance(query, str) or not query.strip():
            raise ValueError("Query must be nonempty text")
        if not isinstance(top_k, int) or top_k < 1:
            raise ValueError("top_k must be a positive integer")

        # Convert the search phrase to a vector using the SAME model.
        query_vector = self.model.encode(
            [query], convert_to_numpy=True, normalize_embeddings=True
        )
        query_vector = np.ascontiguousarray(query_vector, dtype=np.float32)
        scores, positions = self.index.search(query_vector, min(top_k, self.index.ntotal))

        # A position is the row number in our original list, NOT a database ID.
        return [
            {"row_index": int(i), "listing": self.listings[i], "similarity": float(score)}
            for i, score in zip(positions[0], scores[0]) if i >= 0
        ]

    def save(self, folder):
        """Save FAISS vectors and matching listing text for use next time."""
        if self.index is None:
            raise ValueError("Nothing to save yet")
        import json
        folder = Path(folder)
        folder.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self.index, str(folder / "listings.faiss"))
        (folder / "listing_text.json").write_text(
            json.dumps(self.listings, ensure_ascii=False), encoding="utf-8"
        )

    def load(self, folder):
        """Load previously saved vectors instead of recomputing them."""
        import json
        folder = Path(folder)
        self.index = faiss.read_index(str(folder / "listings.faiss"))
        self.listings = json.loads((folder / "listing_text.json").read_text(encoding="utf-8"))
        if self.index.ntotal != len(self.listings):
            raise ValueError("Saved index and listing text counts do not match")
