"""Schematy dla endpointu /ingest (upload plików)."""

from pydantic import BaseModel, Field


class IngestResponse(BaseModel):
    """Odpowiedź po wrzuceniu pliku do systemu."""

    filename: str
    collection: str
    chunks_created: int = Field(description="Ile fragmentów wyekstrahowano z pliku")
    message: str
