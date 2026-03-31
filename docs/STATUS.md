# PRISM - Status projektu

## 📍 Co to jest
Personal Retrieval & Intelligence System for Memory - RAG system do osobistej bazy wiedzy (notatki z uczelni, badania krwi, portfolio). 100% lokalnie, prywatnie.

## ✅ Zrobione (Kroki 1-4 + Study)

### Krok 1: API Skeleton
- FastAPI app factory pattern (`src/main.py`)
- Pydantic Settings (`src/config.py`)
- Health check endpoint
- Docker Compose z Qdrant

### Krok 2: Ingestion Pipeline
- **PDF Parser** (`src/ingestion/pdf_parser.py`) - PyMuPDF, ekstrakcja per-strona
- **Chunker** (`src/ingestion/chunker.py`) - RecursiveCharacterTextSplitter z LangChain
- **Detekcja struktury** (`src/ingestion/structure.py`) - rozdziały, sekcje
- Endpoint `POST /ingest` - upload PDF → chunki w Qdrant

### Krok 3: Embeddings + Vector Store
- **Embedder** (`src/embeddings/embedder.py`) - sentence-transformers, lazy loading
- **Qdrant Store** (`src/vectorstore/qdrant_store.py`) - CRUD kolekcji, similarity search
- Endpoint `GET /collections`
- Endpoint `POST /query` - semantic search

### Krok 4: RAG Engine
- **Generator** (`src/rag/generator.py`) - multi-backend (Gemini API / Ollama)
- **Retriever** (`src/rag/retriever.py`) - wyszukiwanie + deduplikacja
- **Prompts** (`src/rag/prompts.py`) - system prompts
- **RAG Engine** (`src/rag/engine.py`) - orkiestracja full pipeline
- Graceful degradation (gdy LLM niedostępny → surowe fragmenty)

### Moduł Study
- **Study Engine** (`src/study/engine.py`) - tryby nauki
- **Modes** (`src/study/modes.py`) - quiz/explain/connect
- Filtrowanie po rozdziałach

### Dependency Injection
- `src/api/dependencies.py` - singletony z `@lru_cache`

### Testy
- **38 testów** - wszystkie przechodzą
- Lint czysty (ruff)

---

## 🐛 Do naprawienia

### Memory Leak (do zbadania)
**Kontekst:** Zgłoszony memory leak, brak szczegółów kiedy występuje.

**Potencjalne przyczyny do sprawdzenia:**
1. Model embeddingów (~400MB) - normalne, ale ładuje się raz
2. PDF Parser tworzy nową instancję przy każdym pliku (linia 45 w `pipeline.py`)
3. Gemini client może cache'ować dane
4. Python GC nie zwalnia dużych list od razu

**Jak debugować:**
```bash
# Monitoruj pamięć procesu
watch -n 1 'ps aux | grep uvicorn'

# Albo z memory_profiler:
pip install memory_profiler
mprof run uvicorn src.main:app
mprof plot
```

**Możliwe fixy:**
- Dodać explicit `gc.collect()` po przetworzeniu dużego PDF
- Przenieść `PdfParser()` do singletona jak reszta
- Użyć `weakref` dla chunków jeśli są trzymane za długo

---

## 🎯 Kolejne kroki (TODO)

### Krok 5: Architektura Agentowa
- [ ] `agents/tools/base.py` - abstrakcja Tool
- [ ] `agents/tools/study_tool.py` - przeszukiwanie notatek
- [ ] `agents/tools/medical_tool.py` - analiza badań
- [ ] `agents/router.py` - LLM-based routing

### Krok 6: Frontend
- [ ] `ui/app.py` - Streamlit chat UI
- [ ] Historia konwersacji
- [ ] Upload przez UI
- [ ] Wyświetlanie źródeł

### Rozszerzenia (przyszłość)
- [ ] Reranker (cross-encoder dla lepszej precyzji)
- [ ] OCR na skany
- [ ] Conversation memory
- [ ] Dashboard medyczny (trendy badań)

---

## 📂 Struktura plików

```
src/
├── main.py              # FastAPI entry point
├── config.py            # Pydantic Settings
├── api/
│   ├── routes/          # Endpointy (health, ingest, query, collections, study)
│   ├── models/          # Pydantic schemas
│   └── dependencies.py  # DI singletony
├── ingestion/           # PDF → chunki
├── embeddings/          # tekst → wektory
├── vectorstore/         # Qdrant client
├── rag/                 # Retrieval + Generation
└── study/               # Tryby nauki (quiz/explain/connect)
```

## 🔧 Komendy

```bash
# API
uv run uvicorn src.main:app --reload

# Testy
uv run pytest

# Lint
uv run ruff check src/ tests/

# Qdrant
docker compose up qdrant -d
```
