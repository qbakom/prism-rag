"""Testy RAG engine - retrieval, prompts, generation.

Ollama jest mockowana - testy nie wymagają uruchomionego LLM.
Testujemy: budowanie promptów, flow engine'u, graceful degradation.
"""

from unittest.mock import patch

from src.rag.engine import RAGEngine
from src.rag.generator import Generator
from src.rag.prompts import build_context, build_messages
from src.rag.retriever import RetrievedChunk, Retriever

# --- Testy prompts.py ---

class TestPrompts:
    def test_build_context_formats_chunks(self):
        chunks = [
            RetrievedChunk(
                content="Tekst o Fourierze",
                score=0.9,
                filename="fizyka.pdf",
                page_number=45,
                chunk_index=0,
            ),
        ]
        context = build_context(chunks)
        assert "fizyka.pdf" in context
        assert "s. 45" in context
        assert "Tekst o Fourierze" in context

    def test_build_context_empty(self):
        context = build_context([])
        assert "Brak" in context

    def test_build_messages_structure(self):
        chunks = [
            RetrievedChunk(
                content="treść",
                score=0.8,
                filename="test.pdf",
                page_number=1,
                chunk_index=0,
            ),
        ]
        messages = build_messages("pytanie?", chunks)
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        assert "pytanie?" in messages[1]["content"]
        assert "treść" in messages[1]["content"]


# --- Testy retriever.py ---

class TestRetriever:
    def test_retrieve_filters_by_score(self, test_embedder, test_store):
        """Fragmenty z niskim score powinny być odfiltrowane."""
        from src.ingestion.base import Document

        docs = [
            Document(content="Python to język programowania", metadata={"filename": "a.pdf"}),
            Document(content="Kot pije mleko", metadata={"filename": "b.pdf"}),
        ]
        vectors = test_embedder.embed([d.content for d in docs])
        test_store.add_documents("test", docs, vectors)

        retriever = Retriever(test_embedder, test_store)
        results = retriever.retrieve("programowanie", "test", top_k=2)

        # Powinien znaleźć przynajmniej fragment o Pythonie
        assert len(results) >= 1
        assert all(r.score >= 0.3 for r in results)


# --- Testy engine.py ---

class TestRAGEngine:
    def _make_engine(self, test_embedder, test_store) -> RAGEngine:
        retriever = Retriever(test_embedder, test_store)
        generator = Generator()
        return RAGEngine(retriever=retriever, generator=generator)

    def test_query_no_chunks_returns_message(self, test_embedder, test_store):
        """Pusta kolekcja -> komunikat zamiast błędu."""
        engine = self._make_engine(test_embedder, test_store)
        test_store.ensure_collection("empty")

        result = engine.query("cokolwiek", "empty")
        assert "Nie znalazłem" in result.answer
        assert result.sources == []

    def test_query_ollama_unavailable_returns_fallback(self, test_embedder, test_store):
        """Ollama nie działa -> graceful degradation, zwraca surowe fragmenty."""
        from src.ingestion.base import Document

        docs = [Document(content="Python jest super", metadata={"filename": "t.pdf"})]
        vectors = test_embedder.embed(["Python jest super"])
        test_store.add_documents("test_fb", docs, vectors)

        engine = self._make_engine(test_embedder, test_store)
        result = engine.query("Python", "test_fb")

        # Ollama nie jest uruchomiona w testach -> fallback
        assert result.model == "fallback"
        assert len(result.sources) >= 1
        assert "Ollama" in result.answer or "Python" in result.answer

    @patch.object(Generator, "is_available", return_value=True)
    @patch.object(Generator, "generate", return_value="Python to świetny język do RAG.")
    def test_query_full_rag_with_mocked_llm(
        self, mock_generate, mock_available, test_embedder, test_store
    ):
        """Pełny RAG flow z mockowanym LLM."""
        from src.ingestion.base import Document

        docs = [
            Document(
                content="Python jest popularny w data science",
                metadata={"filename": "langs.pdf", "page_number": 3},
            )
        ]
        vectors = test_embedder.embed([d.content for d in docs])
        test_store.add_documents("test_rag", docs, vectors)

        engine = self._make_engine(test_embedder, test_store)
        result = engine.query("Jaki język do data science?", "test_rag")

        assert result.answer == "Python to świetny język do RAG."
        assert result.model == "llama3.2"
        assert len(result.sources) >= 1
        assert result.sources[0].filename == "langs.pdf"

        # Sprawdź że generator dostał poprawne wiadomości
        mock_generate.assert_called_once()
        messages = mock_generate.call_args[0][0]
        assert messages[0]["role"] == "system"
        assert "Python" in messages[1]["content"]
