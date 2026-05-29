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


# --- Ścieżka nauki (klikalny tryb document-driven) ---


class TopicInfo(BaseModel):
    """Pojedynczy temat (rozdział) na ścieżce nauki."""

    chapter: str | None = Field(description="Identyfikator rozdziału (np. '3')")
    title: str = Field(description="Tytuł rozdziału/sekcji do wyświetlenia")
    chunk_count: int = Field(description="Ile fragmentów składa się na temat")


class ReadResponse(BaseModel):
    """Materiał do przeczytania dla danego tematu (konsumpcja)."""

    chapter: str | None
    content: str = Field(description="Ciągły tekst rozdziału w kolejności czytania")
    filename: str | None = None


class QuizGenerateRequest(BaseModel):
    """Request o wygenerowanie klikalnego quizu dla tematu."""

    collection: str = Field(default="default")
    chapter: str | None = Field(default=None, description="Rozdział. None = cała kolekcja.")
    num_questions: int = Field(default=4, ge=1, le=10)


class QuizQuestion(BaseModel):
    """Pojedyncze pytanie ABCD."""

    question: str
    options: list[str]
    correct_index: int
    explanation: str = ""


class QuizResponse(BaseModel):
    """Zestaw pytań ABCD dla tematu."""

    chapter: str | None
    questions: list[QuizQuestion] = []
