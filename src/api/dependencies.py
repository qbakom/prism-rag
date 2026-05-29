"""FastAPI Dependency Injection - singletony współdzielone między endpointami.

Depends() w FastAPI to DI framework:
- Endpoint deklaruje "potrzebuję Embeddera" -> FastAPI woła get_embedder()
- W testach podmieniamy zależność na mocka bez dotykania kodu endpointu
- Singletony (lru_cache) = model embeddingów ładuje się RAZ, nie przy każdym requeście
"""

from functools import lru_cache

from src.embeddings.embedder import Embedder
from src.rag.engine import RAGEngine
from src.rag.generator import Generator
from src.rag.retriever import Retriever
from src.study.engine import StudyEngine
from src.vectorstore.qdrant_store import QdrantStore


@lru_cache
def get_embedder() -> Embedder:
    embedder = Embedder()
    _ = embedder.dimension
    return embedder


@lru_cache
def get_store() -> QdrantStore:
    embedder = get_embedder()
    return QdrantStore(embedding_dimension=embedder.dimension)


def _get_retriever_and_generator() -> tuple[Retriever, Generator]:
    embedder = get_embedder()
    store = get_store()
    return Retriever(embedder=embedder, store=store), Generator()


@lru_cache
def get_rag_engine() -> RAGEngine:
    retriever, generator = _get_retriever_and_generator()
    return RAGEngine(retriever=retriever, generator=generator)


@lru_cache
def get_study_engine() -> StudyEngine:
    retriever, generator = _get_retriever_and_generator()
    return StudyEngine(retriever=retriever, generator=generator, store=get_store())
