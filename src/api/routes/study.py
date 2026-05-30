"""Endpointy modułu study - nauka z książek technicznych.

Trzy tryby:
- quiz: "przepytaj mnie z rozdziału 3" -> 5 pytań z odpowiedziami
- explain: "wyjaśnij transformatę Fouriera" -> tłumaczenie z analogiami
- connect: "jak FFT łączy się z próbkowaniem?" -> analiza powiązań
"""

from fastapi import APIRouter, Depends

from src.api.dependencies import get_store, get_study_engine
from src.api.models.query import Source
from src.api.models.study import (
    QuizGenerateRequest,
    QuizQuestion,
    QuizResponse,
    ReadResponse,
    StudyRequest,
    TopicInfo,
)
from src.api.models.study import StudyResponse as StudyResponseModel
from src.study.engine import StudyEngine
from src.study.text import stitch_overlapping
from src.vectorstore.qdrant_store import QdrantStore

router = APIRouter(prefix="/study", tags=["study"])


@router.post("/", response_model=StudyResponseModel)
async def study(
    request: StudyRequest,
    engine: StudyEngine = Depends(get_study_engine),
) -> StudyResponseModel:
    result = engine.study(
        question=request.question,
        collection=request.collection,
        mode=request.mode,
        chapter=request.chapter,
        top_k=request.top_k,
    )

    sources = [
        Source(
            filename=chunk.filename,
            page=chunk.page_number,
            chunk_text=chunk.content,
        )
        for chunk in result.sources
    ]

    return StudyResponseModel(
        content=result.content,
        mode=result.mode,
        chapter=result.chapter,
        sources=sources,
    )


@router.get("/topics", response_model=list[TopicInfo])
async def list_topics(
    collection: str,
    store: QdrantStore = Depends(get_store),
) -> list[TopicInfo]:
    """Ścieżka nauki: uporządkowana lista tematów (rozdziałów) w kolekcji."""
    return [TopicInfo(**t) for t in store.list_topics(collection)]


@router.get("/read", response_model=ReadResponse)
async def read_topic(
    collection: str,
    chapter: str | None = None,
    store: QdrantStore = Depends(get_store),
) -> ReadResponse:
    """Materiał do przeczytania dla tematu - ciągły tekst w kolejności czytania."""
    items = store.read_chapter(collection, chapter)
    content = stitch_overlapping([i["content"] for i in items])
    filename = items[0]["filename"] if items else None
    return ReadResponse(chapter=chapter, content=content, filename=filename)


@router.post("/quiz", response_model=QuizResponse)
async def generate_quiz(
    request: QuizGenerateRequest,
    engine: StudyEngine = Depends(get_study_engine),
) -> QuizResponse:
    """Wygeneruj klikalne pytania ABCD dla tematu (zero pisania, auto-ocena)."""
    questions = engine.quiz(
        collection=request.collection,
        chapter=request.chapter,
        num_questions=request.num_questions,
    )
    return QuizResponse(
        chapter=request.chapter,
        questions=[QuizQuestion(**q) for q in questions],
    )
