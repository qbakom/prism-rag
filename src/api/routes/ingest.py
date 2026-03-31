"""Endpoint do wrzucania plików (ingestion).

Pełny flow: upload -> parse -> chunk -> embed -> zapis do Qdrant.
"""

import logging

from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile

from src.api.dependencies import get_embedder, get_store
from src.api.models.ingest import IngestResponse
from src.embeddings.embedder import Embedder
from src.ingestion.pipeline import IngestionPipeline
from src.vectorstore.qdrant_store import QdrantStore

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ingest", tags=["ingestion"])

pipeline = IngestionPipeline()


@router.post("/", response_model=IngestResponse)
async def ingest_file(
    file: UploadFile,
    collection: str = Form(default="default"),
    embedder: Embedder = Depends(get_embedder),
    store: QdrantStore = Depends(get_store),
) -> IngestResponse:
    filename = file.filename or "unknown"
    file_bytes = await file.read()

    # 1. Parse + chunk
    try:
        chunks = pipeline.run(file_bytes, filename)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    if not chunks:
        return IngestResponse(
            filename=filename,
            collection=collection,
            chunks_created=0,
            message="Plik nie zawiera tekstu do przetworzenia",
        )

    # 2. Embed
    texts = [chunk.content for chunk in chunks]
    vectors = embedder.embed(texts)

    # 3. Zapisz do Qdrant
    count = store.add_documents(collection, chunks, vectors)

    logger.info("Ingested '%s' -> '%s': %d chunks", filename, collection, count)
    return IngestResponse(
        filename=filename,
        collection=collection,
        chunks_created=count,
        message=f"Przetworzono i zapisano {count} fragmentów z {filename}",
    )
