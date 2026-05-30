"""CRUD kolekcji - zarządzanie domenami wiedzy (uczelnia, medycyna, portfolio)."""

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from src.api.dependencies import get_store
from src.vectorstore.qdrant_store import QdrantStore

router = APIRouter(prefix="/collections", tags=["collections"])


class CollectionInfo(BaseModel):
    name: str
    documents_count: int


class FileInfo(BaseModel):
    filename: str
    chunk_count: int


@router.get("/", response_model=list[CollectionInfo])
async def list_collections(
    store: QdrantStore = Depends(get_store),
) -> list[CollectionInfo]:
    names = store.list_collections()
    return [
        CollectionInfo(name=name, documents_count=store.collection_count(name))
        for name in names
    ]


@router.get("/{name}/files", response_model=list[FileInfo])
async def list_files(
    name: str,
    store: QdrantStore = Depends(get_store),
) -> list[FileInfo]:
    """Lista plików w tematyce z liczbą fragmentów - panel zarządzania materiałami."""
    return [FileInfo(**f) for f in store.list_files(name)]


@router.delete("/{name}/files")
async def delete_file(
    name: str,
    filename: str = Query(..., description="Nazwa pliku do usunięcia z tematyki"),
    store: QdrantStore = Depends(get_store),
) -> dict[str, str | int]:
    """Usuń pojedynczy plik (wszystkie jego fragmenty) z tematyki."""
    deleted = store.delete_file(name, filename)
    return {"message": f"Usunięto '{filename}' ({deleted} fragmentów)", "deleted": deleted}


@router.delete("/{name}")
async def delete_collection(
    name: str,
    store: QdrantStore = Depends(get_store),
) -> dict[str, str]:
    store.delete_collection(name)
    return {"message": f"Kolekcja '{name}' usunięta"}
