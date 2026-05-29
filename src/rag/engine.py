"""RAG Engine - orkiestracja pełnego pipeline'u Retrieval-Augmented Generation.

Flow:
1. Retriever znajduje trafne fragmenty w bazie wektorowej
2. Prompts buduje kontekst z fragmentów (Augmented)
3. Generator wysyła kontekst + pytanie do LLM i dostaje odpowiedź

Engine jest "fasadą" - ukrywa złożoność za jedną metodą query().
Endpoint API woła engine.query() i nie musi wiedzieć o retrieverze, promptach, etc.
"""

import logging
from dataclasses import dataclass

from src.rag.generator import Generator
from src.rag.prompts import build_messages
from src.rag.retriever import RetrievedChunk, Retriever

logger = logging.getLogger(__name__)


@dataclass
class RAGResponse:
    """Odpowiedź RAG - tekst + źródła dla transparentności."""

    answer: str
    sources: list[RetrievedChunk]
    model: str


class RAGEngine:
    """Pełny pipeline RAG: pytanie -> retrieval -> augmentation -> generation."""

    def __init__(self, retriever: Retriever, generator: Generator) -> None:
        self._retriever = retriever
        self._generator = generator

    def query(
        self,
        question: str,
        collection: str,
        top_k: int = 5,
    ) -> RAGResponse:
        """Zadaj pytanie do bazy wiedzy i otrzymaj odpowiedź ze źródłami.

        Jeśli Ollama nie jest dostępna, zwraca surowe fragmenty
        zamiast wygenerowanej odpowiedzi (graceful degradation).
        """
        # R - Retrieval
        chunks = self._retriever.retrieve(question, collection, top_k=top_k)
        logger.info("Retrieved %d chunks from '%s'", len(chunks), collection)

        if not chunks:
            return RAGResponse(
                answer="Nie znalazłem pasujących fragmentów w kolekcji "
                       f"'{collection}'. Spróbuj przeformułować pytanie "
                       "lub sprawdź czy wrzuciłeś odpowiednie dokumenty.",
                sources=[],
                model="none",
            )

        # A - Augmented prompt
        messages = build_messages(question, chunks)

        # G - Generation
        if not self._generator.is_available():
            logger.warning("Ollama niedostępna - zwracam surowe fragmenty")
            fallback = "⚠️ Ollama nie jest uruchomiona. Oto znalezione fragmenty:\n\n"
            for i, chunk in enumerate(chunks, 1):
                src = f"[{chunk.filename}"
                if chunk.page_number:
                    src += f", s. {chunk.page_number}"
                src += "]"
                fallback += f"{i}. {src} {chunk.content[:300]}\n\n"
            return RAGResponse(
                answer=fallback,
                sources=chunks,
                model="fallback",
            )

        answer = self._generator.generate(messages)
        logger.info("Generated answer (%d chars) using %s", len(answer), self._generator.model)

        return RAGResponse(
            answer=answer,
            sources=chunks,
            model=self._generator.model,
        )
