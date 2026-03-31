"""Schematy request/response dla endpointu /query.

Pydantic model = kontrakt API. Klient wie co wysłać, serwer wie co zwrócić.
FastAPI automatycznie waliduje requesty i generuje dokumentację (Swagger).
"""

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    """Co użytkownik wysyła gdy zadaje pytanie."""

    question: str = Field(..., min_length=1, description="Pytanie do bazy wiedzy")
    collection: str | None = Field(
        default=None,
        description="Kolekcja do przeszukania (np. 'uczelnia', 'medycyna'). None = auto-routing.",
    )
    top_k: int = Field(default=5, ge=1, le=20, description="Ile fragmentów zwrócić")


class Source(BaseModel):
    """Skąd pochodzi fragment odpowiedzi - cytowanie źródeł."""

    filename: str
    page: int | None = None
    chunk_text: str


class QueryResponse(BaseModel):
    """Co system zwraca jako odpowiedź."""

    answer: str
    sources: list[Source] = []
