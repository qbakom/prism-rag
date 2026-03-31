"""Endpoint do przeszukiwania bazy wiedzy - pełny RAG.

Flow: pytanie -> embed -> search Qdrant -> build prompt -> Ollama -> odpowiedź + źródła.
Jeśli Ollama nie jest uruchomiona, zwraca surowe fragmenty (graceful degradation).
"""

from fastapi import APIRouter, Depends

from src.api.dependencies import get_rag_engine
from src.api.models.query import QueryRequest, QueryResponse, Source
from src.rag.engine import RAGEngine

router = APIRouter(prefix="/query", tags=["query"])


@router.post("/", response_model=QueryResponse)
async def query_knowledge_base(
    request: QueryRequest,
    engine: RAGEngine = Depends(get_rag_engine),
) -> QueryResponse:
    collection = request.collection or "default"

    result = engine.query(
        question=request.question,
        collection=collection,
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

    return QueryResponse(answer=result.answer, sources=sources)
