"""CRUD kolekcji - zarządzanie domenami wiedzy (uczelnia, medycyna, portfolio)."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from src.api.dependencies import get_store
from src.vectorstore.qdrant_store import QdrantStore

router = APIRouter(prefix="/collections", tags=["collections"])


class CollectionInfo(BaseModel):
    name: str
    documents_count: int


@router.get("/", response_model=list[CollectionInfo])
async def list_collections(
    store: QdrantStore = Depends(get_store),
) -> list[CollectionInfo]:
    names = store.list_collections()
    return [
        CollectionInfo(name=name, documents_count=store.collection_count(name))
        for name in names
    ]


@router.delete("/{name}")
async def delete_collection(
    name: str,
    store: QdrantStore = Depends(get_store),
) -> dict[str, str]:
    store.delete_collection(name)
    return {"message": f"Kolekcja '{name}' usunięta"}
