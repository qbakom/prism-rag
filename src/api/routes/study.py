"""Endpointy modułu study - nauka z książek technicznych.

Trzy tryby:
- quiz: "przepytaj mnie z rozdziału 3" -> 5 pytań z odpowiedziami
- explain: "wyjaśnij transformatę Fouriera" -> tłumaczenie z analogiami
- connect: "jak FFT łączy się z próbkowaniem?" -> analiza powiązań
"""

from fastapi import APIRouter, Depends

from src.api.dependencies import get_study_engine
from src.api.models.query import Source
from src.api.models.study import StudyRequest
from src.api.models.study import StudyResponse as StudyResponseModel
from src.study.engine import StudyEngine

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
