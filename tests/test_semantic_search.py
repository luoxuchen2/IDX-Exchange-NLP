"""Small Week 5 automated tests. Use a real model only in the optional integration test."""
import numpy as np
import pytest

from scripts.bm25_search import BM25Searcher
from scripts.semantic_search import SemanticSearcher


class FakeModel:
    """A quick pretend encoder, so ordinary tests don't download a large model."""
    def encode(self, texts, **kwargs):
        # Simple word flags: pool, garage, balcony.
        vectors = []
        for text in texts:
            lower = text.lower()
            vec = np.array(["pool" in lower, "garage" in lower,
                            "balcony" in lower], dtype=np.float32)
            length = np.linalg.norm(vec)
            vectors.append(vec / length if length else np.array([1., 0., 0.], dtype=np.float32))
        return np.asarray(vectors)


def fake_searcher():
    # Skip SentenceTransformer initialization and replace it with a fast fake.
    engine = SemanticSearcher.__new__(SemanticSearcher)
    engine.model = FakeModel()
    engine.index = None
    engine.listings = []
    return engine


def test_index_and_search():
    engine = fake_searcher()
    assert engine.build_index(["pool view", "garage space", "balcony view"]) == 3
    assert engine.search("pool", top_k=1)[0]["row_index"] == 0


def test_cannot_search_before_index():
    with pytest.raises(ValueError):
        fake_searcher().search("pool")


def test_empty_query_rejected():
    engine = fake_searcher()
    engine.build_index(["pool home"])
    with pytest.raises(ValueError):
        engine.search("  ")


def test_save_load(tmp_path):
    engine = fake_searcher()
    engine.build_index(["pool home", "garage home"])
    engine.save(tmp_path)
    restored = fake_searcher()
    restored.load(tmp_path)
    assert restored.search("pool", top_k=1)[0]["row_index"] == 0


def test_bm25_returns_matching_keyword():
    bm25 = BM25Searcher(["pool garden home", "garage parking spot", "balcony ocean view"])
    assert bm25.search("garage", top_k=1)[0]["row_index"] == 1
