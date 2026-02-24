"""Tests for langent.store.vector"""
import pytest
from langent.store.vector import VectorStore


class TestVectorStore:
    def test_init_creates_collection(self, vector_store):
        assert vector_store.count() == 0
        assert vector_store.collection_name == "test_collection"

    def test_add_documents(self, vector_store):
        docs = ["Hello world", "AI is amazing", "Vector databases are fast"]
        metas = [{"source": "a"}, {"source": "b"}, {"source": "c"}]
        added = vector_store.add_documents(docs, metas)
        assert added == 3
        assert vector_store.count() == 3

    def test_add_documents_deduplication(self, vector_store):
        docs = ["Hello world"]
        metas = [{"source": "a"}]
        vector_store.add_documents(docs, metas)
        added_again = vector_store.add_documents(docs, metas)
        assert added_again == 0
        assert vector_store.count() == 1

    def test_add_empty_documents(self, vector_store):
        assert vector_store.add_documents([]) == 0

    def test_search_returns_results(self, vector_store):
        docs = [
            "Machine learning algorithms",
            "Natural language processing with transformers",
            "Computer vision using CNNs",
        ]
        metas = [{"source": f"doc{i}"} for i in range(3)]
        vector_store.add_documents(docs, metas)

        results = vector_store.search("NLP and language models", top_k=2)
        assert len(results) == 2
        assert all("id" in r for r in results)
        assert all("score" in r for r in results)
        assert all("document" in r for r in results)

    def test_delete_by_ids(self, vector_store):
        docs = ["Doc A", "Doc B"]
        metas = [{"source": "a"}, {"source": "b"}]
        vector_store.add_documents(docs, metas, ids=["id_a", "id_b"])
        assert vector_store.count() == 2

        vector_store.delete(ids=["id_a"])
        assert vector_store.count() == 1

    def test_list_collections(self, vector_store):
        collections = vector_store.list_collections()
        assert "test_collection" in collections

    def test_repr(self, vector_store):
        r = repr(vector_store)
        assert "VectorStore" in r
        assert "test_collection" in r

    def test_make_id_deterministic(self, vector_store):
        id1 = vector_store._make_id("test_string")
        id2 = vector_store._make_id("test_string")
        assert id1 == id2
        assert len(id1) == 16
