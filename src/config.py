"""Centralna konfiguracja aplikacji.

Pydantic Settings automatycznie:
1. Czyta zmienne z .env (lub zmiennych systemowych)
2. Waliduje typy (np. port MUSI być intem)
3. Daje defaulty jeśli zmienna nie istnieje

Dzięki temu NIGDY nie piszemy w kodzie host="localhost" - zawsze config.qdrant_host
"""

from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # API
    app_host: str = "0.0.0.0"
    app_port: int = 8000

    # Qdrant
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333

    # LLM Backend: "gemini" lub "ollama"
    llm_backend: str = "gemini"
    
    # Gemini API
    google_api_key: str = ""

    # Ollama (Krok 4)
    ollama_base_url: str = "http://localhost:11434"

    # Embeddings (Krok 3)
    embedding_model: str = "BAAI/bge-m3"
    
    # HuggingFace token (dla szybszego pobierania modeli)
    hf_token: str = ""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


# lru_cache = singleton pattern - Settings tworzy się RAZ i jest reużywane.
# Bez tego każdy import config tworzył by nowy obiekt i czytał .env od nowa.
@lru_cache
def get_settings() -> Settings:
    return Settings()
