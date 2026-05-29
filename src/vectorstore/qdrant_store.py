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

    def _scroll_all(
        self,
        collection: str,
        scroll_filter: models.Filter | None = None,
        cap: int = 5000,
    ) -> list[models.Record]:
        """Pobierz wszystkie punkty (do `cap`) z kolekcji.

        Scroll = paginowane przeglądanie BEZ wektora zapytania (inaczej niż search).
        Używamy go gdy chcemy "przejść po całej książce", a nie szukać podobieństwa.
        """
        records: list[models.Record] = []
        offset = None
        while len(records) < cap:
            batch, offset = self._client.scroll(
                collection_name=collection,
                scroll_filter=scroll_filter,
                limit=256,
                offset=offset,
                with_payload=True,
                with_vectors=False,
            )
            records.extend(batch)
            if offset is None:
                break
        return records

    def list_topics(self, collection: str) -> list[dict]:
        """Lista tematów (rozdziałów) w kolekcji - podstawa "ścieżki nauki".

        Grupuje punkty po `chapter`, liczy fragmenty i ustala kolejność wg
        numeru strony. To zamienia płaską kolekcję w uporządkowaną mapę książki.
        """
        if collection not in self.list_collections():
            return []

        topics: dict[str, dict] = {}
        for rec in self._scroll_all(collection):
            payload = rec.payload or {}
            chapter = payload.get("chapter")
            key = str(chapter) if chapter is not None else "_none"
            # kolejność: strona, a w razie braku - indeks fragmentu
            order = payload.get("page_number")
            if order is None:
                order = payload.get("chunk_index") or 0

            if key not in topics:
                title = (
                    payload.get("chapter_title")
                    or payload.get("section")
                    or (f"Rozdział {chapter}" if chapter is not None else "Bez rozdziału")
                )
                topics[key] = {
                    "chapter": chapter,
                    "title": title,
                    "chunk_count": 0,
                    "order": order,
                }
            topics[key]["chunk_count"] += 1
            topics[key]["order"] = min(topics[key]["order"], order)

        return sorted(topics.values(), key=lambda t: t["order"])

    def read_chapter(self, collection: str, chapter: str | None = None) -> list[dict]:
        """Pobierz treść rozdziału (lub całość) w kolejności czytania.

        Sortuje po stronie i indeksie fragmentu, żeby tekst był ciągły -
        to jest "materiał do konsumpcji" w trybie nauki.
        """
        if collection not in self.list_collections():
            return []

        scroll_filter = None
        if chapter:
            scroll_filter = models.Filter(
                must=[
                    models.FieldCondition(
                        key="chapter",
                        match=models.MatchValue(value=chapter),
                    )
                ]
            )

        items = [
            {
                "content": (rec.payload or {}).get("content", ""),
                "page_number": (rec.payload or {}).get("page_number"),
                "chunk_index": (rec.payload or {}).get("chunk_index"),
                "filename": (rec.payload or {}).get("filename", "unknown"),
            }
            for rec in self._scroll_all(collection, scroll_filter)
        ]
        items.sort(
            key=lambda x: (
                x["page_number"] if x["page_number"] is not None else 0,
                x["chunk_index"] if x["chunk_index"] is not None else 0,
            )
        )
        return items

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
