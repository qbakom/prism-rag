"""Fixtures dla testów.

Kluczowe decyzje:
- Qdrant in-memory (:memory:) = nie potrzeba Dockera do testów
- Mały model embeddingów (all-MiniLM-L6-v2, 80MB) = szybkie testy
- dependency_overrides = podmieniamy singletony na testowe instancje
- RAG + study engine z prawdziwym retrieverem, Ollama = fallback
"""

import pytest
from fastapi.testclient import TestClient
from qdrant_client import QdrantClient

from src.api.dependencies import (
    get_embedder,
    get_rag_engine,
    get_store,
    get_study_engine,
)
from src.embeddings.embedder import Embedder
from src.main import create_app
from src.rag.engine import RAGEngine
from src.rag.generator import Generator
from src.rag.retriever import Retriever
from src.study.engine import StudyEngine
from src.vectorstore.qdrant_store import QdrantStore

TEST_EMBEDDING_MODEL = "all-MiniLM-L6-v2"


@pytest.fixture(autouse=True)
def _isolate_llm_backend(monkeypatch: pytest.MonkeyPatch):
    """Odetnij testy od lokalnego .env dewelopera.

    Bez tego Generator() czyta prawdziwy backend (np. gemini + klucz API),
    przez co testy zakładające ollama/fallback są niedeterministyczne.
    Wymuszamy backend=ollama (w testach i tak niedostępny -> fallback)
    i czyścimy cache Settings, bo jest @lru_cache.
    """
    from src.config import get_settings

    monkeypatch.setenv("LLM_BACKEND", "ollama")
    monkeypatch.setenv("GOOGLE_API_KEY", "")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture(scope="session")
def test_embedder() -> Embedder:
    """Embedder z małym modelem. scope=session = ładuje się RAZ na całą sesję testów."""
    return Embedder(model_name=TEST_EMBEDDING_MODEL)


@pytest.fixture
def test_store(test_embedder: Embedder) -> QdrantStore:
    """Qdrant in-memory - czysta baza na każdy test."""
    client = QdrantClient(":memory:")
    return QdrantStore(client=client, embedding_dimension=test_embedder.dimension)


@pytest.fixture
def client(test_embedder: Embedder, test_store: QdrantStore) -> TestClient:
    """Test client z prawdziwym retrieverem. Ollama niedostępna = fallback."""
    app = create_app()

    retriever = Retriever(embedder=test_embedder, store=test_store)
    generator = Generator()
    rag_engine = RAGEngine(retriever=retriever, generator=generator)
    study_engine = StudyEngine(retriever=retriever, generator=generator)

    app.dependency_overrides[get_embedder] = lambda: test_embedder
    app.dependency_overrides[get_store] = lambda: test_store
    app.dependency_overrides[get_rag_engine] = lambda: rag_engine
    app.dependency_overrides[get_study_engine] = lambda: study_engine
    return TestClient(app)
