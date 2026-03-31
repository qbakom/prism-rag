"""Testy Qdrant store - CRUD i wyszukiwanie wektorowe."""

from src.embeddings.embedder import Embedder
from src.ingestion.base import Document
from src.vectorstore.qdrant_store import QdrantStore


class TestQdrantStore:
    def test_ensure_collection_creates(self, test_store: QdrantStore):
        test_store.ensure_collection("test")
        assert "test" in test_store.list_collections()

    def test_ensure_collection_idempotent(self, test_store: QdrantStore):
        """Dwukrotne tworzenie tej samej kolekcji nie powinno rzucić błędu."""
        test_store.ensure_collection("test")
        test_store.ensure_collection("test")
        assert test_store.list_collections().count("test") == 1

    def test_add_and_search(
        self, test_store: QdrantStore, test_embedder: Embedder
    ):
        """End-to-end: dodaj dokumenty -> wyszukaj podobne."""
        docs = [
            Document(content="Python to język programowania", metadata={"src": "a"}),
            Document(content="Kot lubi mleko", metadata={"src": "b"}),
            Document(content="FastAPI to framework webowy w Pythonie", metadata={"src": "c"}),
        ]

        vectors = test_embedder.embed([d.content for d in docs])
        test_store.add_documents("test", docs, vectors)

        # Szukamy czegoś o programowaniu
        query_vec = test_embedder.embed_query("programowanie webowe")
        results = test_store.search("test", query_vec, top_k=2)

        assert len(results) == 2
        # FastAPI/Python powinny być wyżej niż kot
        contents = [r["content"] for r in results]
        assert any("Python" in c or "FastAPI" in c for c in contents)

    def test_collection_count(
        self, test_store: QdrantStore, test_embedder: Embedder
    ):
        docs = [Document(content="test", metadata={})]
        vectors = test_embedder.embed(["test"])
        test_store.add_documents("count_test", docs, vectors)

        assert test_store.collection_count("count_test") == 1

    def test_delete_collection(self, test_store: QdrantStore):
        test_store.ensure_collection("to_delete")
        test_store.delete_collection("to_delete")
        assert "to_delete" not in test_store.list_collections()
