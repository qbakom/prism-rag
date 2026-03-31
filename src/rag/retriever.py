"""R w RAG - Retrieval. Wyszukiwanie dokumentów z bazy wektorowej.

Retriever łączy embedder + vector store w jedną operację:
pytanie (str) -> embedding -> similarity search -> lista trafnych fragmentów.

Oddzielony od generatora, bo:
1. Można testować retrieval bez LLM (szybciej, taniej)
2. Można podmienić strategię wyszukiwania (np. hybrid search) bez ruszania LLM
3. Ten sam retriever może zasilać różne generatory (Ollama, OpenAI, Claude)
"""

from dataclasses import dataclass

from src.embeddings.embedder import Embedder
from src.vectorstore.qdrant_store import QdrantStore


@dataclass
class RetrievedChunk:
    """Fragment znaleziony w bazie - tekst + metadane + score podobieństwa."""

    content: str
    score: float
    filename: str
    page_number: int | None
    chunk_index: int | None
    chapter: str | None = None
    chapter_title: str | None = None
    section: str | None = None


class Retriever:
    """Wyszukuje najbardziej trafne fragmenty dla danego pytania."""

    def __init__(self, embedder: Embedder, store: QdrantStore) -> None:
        self._embedder = embedder
        self._store = store

    def retrieve(
        self,
        query: str,
        collection: str,
        top_k: int = 5,
        score_threshold: float = 0.3,
        chapter: str | None = None,
    ) -> list[RetrievedChunk]:
        """Znajdź najlepsze fragmenty dla pytania.

        Args:
            query: pytanie użytkownika
            collection: nazwa kolekcji Qdrant
            top_k: ile wyników zwrócić
            score_threshold: minimalny score
            chapter: opcjonalny filtr na rozdział (np. "3")
        """
        filters = {}
        if chapter:
            filters["chapter"] = chapter

        query_vector = self._embedder.embed_query(query)
        # Pobieramy więcej wyników żeby po deduplikacji zostało top_k
        raw_results = self._store.search(
            collection, query_vector, top_k=top_k * 3, filters=filters or None
        )

        chunks = []
        seen_contents: set[str] = set()
        for r in raw_results:
            if r["score"] < score_threshold:
                continue

            # Deduplikacja: overlap w chunkingu tworzy prawie identyczne fragmenty.
            # Bierzemy pierwsze 200 znaków jako klucz - wystarczające żeby złapać duplikaty.
            content = r["content"]
            dedup_key = content[:200]
            if dedup_key in seen_contents:
                continue
            seen_contents.add(dedup_key)

            chunks.append(
                RetrievedChunk(
                    content=content,
                    score=r["score"],
                    filename=r["metadata"].get("filename", "unknown"),
                    page_number=r["metadata"].get("page_number"),
                    chunk_index=r["metadata"].get("chunk_index"),
                    chapter=r["metadata"].get("chapter"),
                    chapter_title=r["metadata"].get("chapter_title"),
                    section=r["metadata"].get("section"),
                )
            )

            if len(chunks) >= top_k:
                break

        return chunks
