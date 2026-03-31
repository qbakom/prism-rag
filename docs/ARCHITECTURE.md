# PRISM - Mapa Architektury

## 🏗️ Diagram warstw

```
┌─────────────────────────────────────────────────────────────────┐
│                        🌐 API Layer                             │
│  src/api/routes/   ← Endpointy HTTP (FastAPI)                   │
│  ┌─────────┬─────────┬──────────┬───────────┬─────────┐        │
│  │ health  │ ingest  │  query   │collections│  study  │        │
│  └────┬────┴────┬────┴────┬─────┴─────┬─────┴────┬────┘        │
│       │         │         │           │          │              │
│  src/api/models/   ← Pydantic schemas (request/response)        │
│  src/api/dependencies.py   ← DI container (singletony)          │
└───────┼─────────┼─────────┼───────────┼──────────┼──────────────┘
        │         │         │           │          │
        ▼         ▼         ▼           ▼          ▼
┌─────────────────────────────────────────────────────────────────┐
│                     📚 Domain Layer                             │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  ingestion/  │  │    rag/      │  │   study/     │          │
│  │  ──────────  │  │  ──────────  │  │  ──────────  │          │
│  │  pipeline    │  │  engine      │  │  engine      │          │
│  │  chunker     │  │  retriever   │  │  modes       │          │
│  │  pdf_parser  │  │  generator   │  │              │          │
│  │  structure   │  │  prompts     │  │              │          │
│  └──────┬───────┘  └──────┬───────┘  └──────────────┘          │
│         │                 │                                     │
└─────────┼─────────────────┼─────────────────────────────────────┘
          │                 │
          ▼                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                   🔧 Infrastructure Layer                       │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ embeddings/  │  │ vectorstore/ │  │   Ollama     │          │
│  │  embedder    │  │ qdrant_store │  │  (external)  │          │
│  │  ──────────  │  │  ──────────  │  │              │          │
│  │  BGE-M3      │  │    Qdrant    │  │  Llama 3     │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│                                                                 │
│  src/config.py  ← Pydantic Settings (.env)                      │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🔄 Flow danych

### 1. Ingest (upload dokumentu)
```
POST /ingest
     │
     ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   PDF/file      │───▶│    pipeline     │───▶│    chunker      │
│   (bajty)       │    │   (orkiestracja)│    │   (dzielenie)   │
└─────────────────┘    └─────────────────┘    └────────┬────────┘
                                                       │
     ┌─────────────────────────────────────────────────┘
     ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   embedder      │───▶│  qdrant_store   │───▶│     Qdrant      │
│   (wektory)     │    │   (CRUD)        │    │   (persisted)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### 2. Query (pytanie do RAG)
```
POST /query {"question": "Co to jest FFT?", "collection": "uczelnia"}
     │
     ▼
┌─────────────────┐
│   RAG Engine    │  ← Fasada orkiestrująca cały flow
└────────┬────────┘
         │
    ┌────┴────┐
    ▼         ▼
┌───────┐  ┌───────────┐
│Retriev│  │ Generator │
│  er   │  │           │
└───┬───┘  └─────┬─────┘
    │            │
    ▼            ▼
┌───────┐  ┌───────────┐
│Qdrant │  │  Ollama   │
│(search│  │  (LLM)    │
└───────┘  └───────────┘

Output: {"answer": "FFT to...", "sources": [...]}
```

---

## 📁 Mapa modułów - "Gdzie szukać?"

| Szukam... | Plik/Folder | Opis |
|-----------|-------------|------|
| **Konfiguracja** | `src/config.py` | Wszystkie ustawienia (.env) |
| **Startowy punkt API** | `src/main.py` | App factory, montowanie routerów |
| **Endpointy HTTP** | `src/api/routes/*.py` | health, ingest, query, collections, study |
| **Schematy request/response** | `src/api/models/*.py` | Pydantic validation |
| **DI / Singletony** | `src/api/dependencies.py` | Tworzenie embeddera, store, engine |
| **Parsowanie PDF** | `src/ingestion/pdf_parser.py` | PyMuPDF extraction |
| **Chunking tekstu** | `src/ingestion/chunker.py` | RecursiveCharacterTextSplitter |
| **Detekcja struktury** | `src/ingestion/structure.py` | Rozdziały, sekcje, hierarchia |
| **Pipeline ingestion** | `src/ingestion/pipeline.py` | Orkiestracja: bytes → chunks |
| **Embeddingi** | `src/embeddings/embedder.py` | BGE-M3, sentence-transformers |
| **Operacje na Qdrant** | `src/vectorstore/qdrant_store.py` | add, search, delete, list |
| **RAG orkiestracja** | `src/rag/engine.py` | Łączy retriever + generator |
| **Wyszukiwanie** | `src/rag/retriever.py` | embed → Qdrant → top-K |
| **Generowanie (LLM)** | `src/rag/generator.py` | Klient Ollama |
| **Prompty systemowe** | `src/rag/prompts.py` | Szablony dla LLM |
| **Tryby nauki** | `src/study/modes.py` | quiz, explain, connect |
| **Study engine** | `src/study/engine.py` | Specjalny RAG dla nauki |

---

## 🧪 Testy - "Gdzie testować?"

```
tests/
├── conftest.py           ← Fixtures współdzielone (fake PDF, mock Qdrant)
├── test_api.py           ← Testy HTTP endpointów (TestClient)
├── test_ingestion/       ← Testy parsowania i chunkingu
├── test_rag/             ← Testy retriever, generator, engine
├── test_study/           ← Testy trybów nauki
└── test_vectorstore/     ← Testy operacji na Qdrant
```

**Uruchomienie:** `uv run pytest`

---

## 🔌 Dependency Injection - jak to działa?

```python
# src/api/dependencies.py

@lru_cache  # ← Singleton! Ładuje model RAZ
def get_embedder() -> Embedder:
    return Embedder()

@lru_cache
def get_store() -> QdrantStore:
    embedder = get_embedder()  # ← Reużywa tego samego embeddera
    return QdrantStore(embedding_dimension=embedder.dimension)

@lru_cache
def get_rag_engine() -> RAGEngine:
    # ... składa wszystko razem
```

**W endpoincie:**
```python
@router.post("/query")
async def query(
    request: QueryRequest,
    engine: RAGEngine = Depends(get_rag_engine),  # ← FastAPI wstrzykuje
):
    return engine.query(request.question)
```

**W testach można podmienić:**
```python
app.dependency_overrides[get_rag_engine] = lambda: MockEngine()
```

---

## 📊 Statystyki kodu

| Moduł | Pliki | Linie | Największy plik |
|-------|-------|-------|-----------------|
| `api/` | 10 | ~200 | routes/ingest.py (59) |
| `ingestion/` | 5 | ~350 | structure.py (139) |
| `rag/` | 5 | ~350 | generator.py (96) |
| `study/` | 3 | ~200 | engine.py (115) |
| `vectorstore/` | 2 | ~140 | qdrant_store.py (135) |
| `embeddings/` | 2 | ~55 | embedder.py (51) |
| **TOTAL** | **33** | **~1500** | |

---

## 🚀 Jak dodać nową funkcjonalność?

### Nowy endpoint:
1. `src/api/routes/nowy.py` - router z endpointem
2. `src/api/models/nowy.py` - schematy Pydantic (opcjonalnie)
3. `src/main.py` - `app.include_router(nowy.router)`
4. `tests/test_api.py` - test HTTP

### Nowy parser (np. Markdown):
1. `src/ingestion/markdown_parser.py` - implementacja `DocumentParser`
2. `src/ingestion/pipeline.py` - dodaj do `PARSERS` dict
3. `tests/test_ingestion/test_markdown.py` - testy

### Nowy tool agentowy (Krok 5):
1. `src/agents/tools/nowy_tool.py` - implementacja Tool
2. `src/agents/router.py` - zarejestruj tool
3. `tests/test_agents/` - testy

---

## 📐 Wzorce architektoniczne

| Wzorzec | Gdzie | Po co |
|---------|-------|-------|
| **App Factory** | `main.py` | Testowalność, osobne instancje |
| **Repository** | `qdrant_store.py` | Abstrakcja nad bazą |
| **Facade** | `rag/engine.py`, `ingestion/pipeline.py` | Ukrywa złożoność |
| **Strategy** | `study/modes.py` | Różne tryby nauki |
| **Dependency Injection** | `dependencies.py` | Luźne powiązania, mocki |
| **Protocol** | `ingestion/base.py` | Interfejs dla parserów |

---

## 🎯 Quick Reference - najczęstsze operacje

```bash
# Uruchom API
uv run uvicorn src.main:app --reload

# Testy
uv run pytest -v

# Lint
uv run ruff check src/ tests/

# Qdrant
docker compose up qdrant -d

# Sprawdź czy Qdrant działa
curl http://localhost:6333/collections
```
