"""Klient Qdrant - operacje na bazie wektorowej.

Qdrant przechowuje "punkty" (point) = wektor + payload (metadane).
Punkty żyją w "kolekcjach" - osobna kolekcja per domena (uczelnia, medycyna).

Dwa tryby pracy:
- Docker: dane persystowane na dysku, przeżywają restart
- In-memory (":memory:"): do testów, bez Dockera, dane giną po zamknięciu
"""

import logging
import uuid

from qdrant_client import QdrantClient, models

from src.config import get_settings
from src.ingestion.base import Document

logger = logging.getLogger(__name__)


class QdrantStore:
    """Warstwa abstrakcji nad Qdrant - CRUD kolekcji i wyszukiwanie."""

    def __init__(
        self,
        client: QdrantClient | None = None,
        embedding_dimension: int = 1024,
    ) -> None:
        if client is not None:
            self._client = client
        else:
            settings = get_settings()
            self._client = QdrantClient(
                host=settings.qdrant_host,
                port=settings.qdrant_port,
            )
        self._dimension = embedding_dimension

    def ensure_collection(self, name: str) -> None:
        """Utwórz kolekcję jeśli nie istnieje. Idempotentne."""
        existing = [c.name for c in self._client.get_collections().collections]
        if name not in existing:
            self._client.create_collection(
                collection_name=name,
                vectors_config=models.VectorParams(
                    size=self._dimension,
                    distance=models.Distance.COSINE,
                ),
            )
            logger.info("Created collection '%s' (dim=%d)", name, self._dimension)

    def add_documents(
        self,
        collection: str,
        documents: list[Document],
        vectors: list[list[float]],
    ) -> int:
        """Wrzuć dokumenty z wektorami do kolekcji. Zwraca liczbę dodanych punktów."""
        self.ensure_collection(collection)

        points = [
            models.PointStruct(
                id=str(uuid.uuid4()),
                vector=vector,
                payload={
                    "content": doc.content,
                    **doc.metadata,
                },
            )
            for doc, vector in zip(documents, vectors, strict=True)
        ]

        self._client.upsert(collection_name=collection, points=points)
        logger.info("Added %d points to '%s'", len(points), collection)
        return len(points)

    def search(
        self,
        collection: str,
        query_vector: list[float],
        top_k: int = 5,
        filters: dict[str, str] | None = None,
    ) -> list[dict]:
        """Wyszukaj najbardziej podobne dokumenty. Zwraca payloady + score.

        Args:
            filters: opcjonalne filtry na metadane, np. {"chapter": "3"}
                     Qdrant przefiltruje PRZED wyszukiwaniem (pre-filtering),
                     więc top_k wyników pochodzi tylko z odfiltrowanych punktów.
        """
        query_filter = None
        if filters:
            # Budujemy filtr Qdrant: wszystkie warunki muszą być spełnione (AND)
            conditions = [
                models.FieldCondition(
                    key=key,
                    match=models.MatchValue(value=value),
                )
                for key, value in filters.items()
            ]
            query_filter = models.Filter(must=conditions)

        # Jeśli kolekcja nie istnieje - zwróć pusty wynik zamiast 500
        existing = [c.name for c in self._client.get_collections().collections]
        if collection not in existing:
            return []

        results = self._client.query_points(
            collection_name=collection,
            query=query_vector,
            query_filter=query_filter,
            limit=top_k,
            with_payload=True,
        )

        return [
            {
                "content": point.payload.get("content", ""),
                "score": point.score,
                "metadata": {
                    k: v for k, v in point.payload.items() if k != "content"
                },
            }
            for point in results.points
        ]

    def list_collections(self) -> list[str]:
        """Lista nazw wszystkich kolekcji."""
        return [c.name for c in self._client.get_collections().collections]

    def delete_collection(self, name: str) -> None:
        """Usuń kolekcję i wszystkie dane w niej."""
        self._client.delete_collection(collection_name=name)
        logger.info("Deleted collection '%s'", name)

    def collection_count(self, name: str) -> int:
        """Ile punktów jest w kolekcji."""
        info = self._client.get_collection(collection_name=name)
        return info.points_count or 0
