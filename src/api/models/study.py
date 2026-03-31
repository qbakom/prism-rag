"""Schematy request/response dla modułu study."""

from pydantic import BaseModel, Field

from src.api.models.query import Source
from src.study.modes import StudyMode


class StudyRequest(BaseModel):
    """Request do endpointu study."""

    question: str = Field(
        ...,
        min_length=1,
        description="Pytanie lub temat do nauki",
    )
    collection: str = Field(
        default="default",
        description="Kolekcja z materiałami (np. nazwa książki)",
    )
    mode: StudyMode = Field(
        default=StudyMode.EXPLAIN,
        description="Tryb nauki: quiz, explain, connect",
    )
    chapter: str | None = Field(
        default=None,
        description="Filtr na rozdział (np. '3'). None = szukaj wszędzie.",
    )
    top_k: int = Field(
        default=8,
        ge=1,
        le=30,
        description="Ile fragmentów pobrać jako kontekst",
    )


class StudyResponse(BaseModel):
    """Odpowiedź z modułu study."""

    content: str = Field(description="Wygenerowana treść (quiz/wyjaśnienie/analiza)")
    mode: StudyMode
    chapter: str | None
    sources: list[Source] = []
