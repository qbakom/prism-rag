"""Study Engine - orkiestracja trybów nauki.

Łączy retriever (wyszukiwanie fragmentów) z trybami nauki (quiz, explain, connect).
Każdy tryb generuje inny typ interakcji z tym samym materiałem.

Kluczowa różnica vs zwykły RAG:
- RAG: "odpowiedz na pytanie"
- Study: "pomóż mi się NAUCZYĆ tego materiału" (inny cel = inny prompt)
"""

import logging
from dataclasses import dataclass

from src.rag.generator import Generator
from src.rag.retriever import RetrievedChunk, Retriever
from src.study.modes import StudyMode, build_study_messages

logger = logging.getLogger(__name__)


@dataclass
class StudyResponse:
    """Odpowiedź modułu study."""

    content: str
    mode: StudyMode
    sources: list[RetrievedChunk]
    chapter: str | None


class StudyEngine:
    """Silnik nauki - retrieval + tryby nauki + LLM."""

    def __init__(self, retriever: Retriever, generator: Generator) -> None:
        self._retriever = retriever
        self._generator = generator

    def study(
        self,
        question: str,
        collection: str,
        mode: StudyMode,
        chapter: str | None = None,
        top_k: int = 8,
    ) -> StudyResponse:
        """Główna metoda - uruchom tryb nauki.

        Args:
            question: pytanie/temat do nauki
            collection: kolekcja z materiałami
            mode: tryb nauki (quiz/explain/connect)
            chapter: opcjonalny filtr na rozdział
            top_k: ile fragmentów pobrać (więcej = bogatszy kontekst)
        """
        # Dla quizu pobieramy więcej kontekstu - potrzebujemy materiału na 5 pytań
        effective_top_k = top_k if mode != StudyMode.QUIZ else max(top_k, 10)

        chunks = self._retriever.retrieve(
            query=question,
            collection=collection,
            top_k=effective_top_k,
            chapter=chapter,
        )

        if not chunks:
            hint = f" w rozdziale {chapter}" if chapter else ""
            return StudyResponse(
                content=f"Nie znalazłem materiałów{hint} w kolekcji '{collection}'.",
                mode=mode,
                sources=[],
                chapter=chapter,
            )

        messages = build_study_messages(question, chunks, mode)

        if not self._generator.is_available():
            logger.warning("Ollama niedostępna - zwracam surowe fragmenty")
            fallback = self._build_fallback(chunks, mode, chapter)
            return StudyResponse(
                content=fallback,
                mode=mode,
                sources=chunks,
                chapter=chapter,
            )

        content = self._generator.generate(messages)

        return StudyResponse(
            content=content,
            mode=mode,
            sources=chunks,
            chapter=chapter,
        )

    @staticmethod
    def _build_fallback(
        chunks: list[RetrievedChunk],
        mode: StudyMode,
        chapter: str | None,
    ) -> str:
        """Fallback gdy Ollama nie jest dostępna."""
        header = f"⚠️ Ollama nie jest uruchomiona. Tryb: {mode.value}"
        if chapter:
            header += f", Rozdział: {chapter}"
        header += "\n\nZnalezione fragmenty:\n\n"

        parts = []
        for i, chunk in enumerate(chunks, 1):
            src = f"[{chunk.filename}"
            if chunk.page_number:
                src += f", s. {chunk.page_number}"
            src += "]"
            parts.append(f"{i}. {src}\n{chunk.content[:300]}")

        return header + "\n\n".join(parts)
