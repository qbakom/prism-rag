"""Warstwa embeddingów - zamiana tekstu na wektory.

Abstrakcja nad modelem embeddingów. Używamy sentence-transformers
bo obsługuje dowolny model z HuggingFace i robi batching automatycznie.

Lazy loading: model ładuje się dopiero przy pierwszym użyciu,
nie przy imporcie modułu. Dzięki temu testy API nie muszą ściągać 2GB modelu.
"""

import logging

from sentence_transformers import SentenceTransformer

from src.config import get_settings

logger = logging.getLogger(__name__)


class Embedder:
    """Wrapper na model embeddingów z lazy loadingiem."""

    def __init__(self, model_name: str | None = None) -> None:
        self._model_name = model_name or get_settings().embedding_model
        self._model: SentenceTransformer | None = None

    @property
    def model(self) -> SentenceTransformer:
        """Lazy load - model ładuje się przy pierwszym wywołaniu."""
        if self._model is None:
            logger.info("Loading embedding model: %s", self._model_name)
            self._model = SentenceTransformer(self._model_name)
            logger.info("Model loaded. Dimension: %d", self.dimension)
        return self._model

    @property
    def dimension(self) -> int:
        """Wymiarowość wektorów - potrzebna przy tworzeniu kolekcji w Qdrant."""
        return self.model.get_sentence_embedding_dimension()

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Zamień listę tekstów na listę wektorów.

        sentence-transformers robi batching pod spodem,
        więc podanie 100 tekstów naraz jest szybsze niż 100x po jednym.
        """
        embeddings = self.model.encode(texts, show_progress_bar=False)
        return embeddings.tolist()

    def embed_query(self, query: str) -> list[float]:
        """Embed pojedynczego zapytania - convenience method."""
        return self.embed([query])[0]
