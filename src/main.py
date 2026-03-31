"""Punkt wejścia aplikacji PRISM.

Wzorzec "app factory" - funkcja create_app() tworzy i konfiguruje FastAPI.
Dlaczego funkcja a nie globalna zmienna?
- Testy mogą tworzyć osobną instancję z innym configiem
- Łatwiejsze mockowanie zależności
- Jasny lifecycle: tworzenie -> konfiguracja -> start
"""

from fastapi import FastAPI

from src.api.routes import collections, health, ingest, query, study


def create_app() -> FastAPI:
    app = FastAPI(
        title="PRISM",
        description="Personal Retrieval & Intelligence System for Memory",
        version="0.1.0",
    )

    # Montowanie routerów - każdy moduł rejestruje swoje endpointy
    app.include_router(health.router)
    app.include_router(ingest.router)
    app.include_router(query.router)
    app.include_router(collections.router)
    app.include_router(study.router)

    return app


# Uvicorn szuka tej zmiennej: `uvicorn src.main:app`
app = create_app()
