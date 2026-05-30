# PRISM

Personal Retrieval & Intelligence System for Memory — prywatny, lokalny RAG
do **nauki z własnych książek/skryptów PDF**. Klikasz, nie piszesz.

PRISM nie jest kolejnym czat-RAG-iem. Rdzeń to **klikalny tryb nauki**:

> książka → ścieżka tematów (rozdziały) → klik temat → czytanie →
> klikalne pytania ABCD (auto-ocena via `correct_index`) → wynik →
> następny temat

Plus swobodny tryb **„Zapytaj książkę"** (RAG Q&A, Wyjaśnij, Połącz), kiedy
chcesz przeskoczyć liniową ścieżkę i po prostu o coś zapytać.

## Co to potrafi

- 📚 **Tematyka jako first-class** — każda książka/skrypt to osobna tematyka
  (np. `fairml`, `metody_numeryczne`). Tworzysz nową przyciskiem „+ Nowy temat"
  i wgrywasz PDF-y (multi-file) z UI.
- 🗺️ **Ścieżka nauki** — automatycznie wykryte rozdziały, klikalna lista.
- 📖 **Czytanie rozdziałów** — ciągły tekst sklejony z fragmentów
  (overlap-aware, bez duplikatów).
- ✅ **Quiz ABCD** — generowany z materiału rozdziału, z wyjaśnieniem przy każdym
  pytaniu, wynikiem (X/N + %), oceną i przejściem do następnego tematu.
- 💬 **Zapytaj książkę** — trzy tryby z różnymi promptami systemowymi:
  - **Pytanie** (`/query`) — RAG Q&A z cytowaniem `[plik, s. X]`
  - **Wyjaśnij** (`/study explain`) — tutorski styl z analogiami i TL;DR
  - **Połącz** (`/study connect`) — analiza powiązań między konceptami
- 🧾 **Markdown** w odpowiedziach LLM (nagłówki, listy, kod, tabele).

## Stack

| Warstwa | Co |
|---|---|
| Backend | FastAPI + Pydantic-Settings, Python 3.11+ |
| Vector store | Qdrant (Docker) |
| Embeddings | `BAAI/bge-m3` (dense, dim=1024) — `sentence-transformers` |
| LLM | Google Gemini (`gemini-2.5-flash`) lub lokalna Ollama |
| Parser | PyMuPDF |
| Chunker | `RecursiveCharacterTextSplitter` (1000 znaków, overlap 200) |
| Frontend | React + TypeScript + Vite + Tailwind v4 |
| Markdown | `react-markdown` + `remark-gfm` |
| Pakiety | `uv` (Python) + `npm` (front) |
| Testy | `pytest` (48 zielonych) |

## Szybki start

Wymagania: Python 3.11+, Node 20+, Docker, [`uv`](https://docs.astral.sh/uv/).

```bash
# 1. Qdrant
docker compose up -d

# 2. Backend
cp .env.example .env
# wpisz GOOGLE_API_KEY (https://aistudio.google.com/apikey)
# albo ustaw LLM_BACKEND=ollama i uruchom `ollama serve`
uv sync --extra dev
uv run uvicorn src.main:app --host 0.0.0.0 --port 8000

# 3. Frontend (osobny terminal)
cd frontend
npm install
npm run dev
# → http://localhost:5173
```

Otwórz UI, kliknij **„+ Nowy temat"**, nazwij („metody numeryczne"), wgraj
PDF-y. Przy pierwszym wgraniu backend pobierze `BAAI/bge-m3` (~2 GB) — to
jednorazowo. Embedding leci na GPU jeśli `torch` go widzi.

## Konfiguracja (`.env`)

```ini
APP_HOST=0.0.0.0
APP_PORT=8000

QDRANT_HOST=localhost
QDRANT_PORT=6333

LLM_BACKEND=gemini          # albo "ollama"
GOOGLE_API_KEY=             # wymagane dla LLM_BACKEND=gemini

OLLAMA_BASE_URL=http://localhost:11434
EMBEDDING_MODEL=BAAI/bge-m3
```

Bez `GOOGLE_API_KEY` (i bez Ollamy) retrieval i czytanie nadal działają —
generacja (quiz / Wyjaśnij / Połącz) pokazuje fallback z surowymi fragmentami.

## API w skrócie

| Endpoint | Co robi |
|---|---|
| `GET /collections/` | Lista tematyk z liczbą fragmentów |
| `DELETE /collections/{name}` | Usuń tematykę |
| `POST /ingest/` (multipart) | Wgraj PDF — pole `file`, opcjonalnie `collection` |
| `GET /study/topics?collection=…` | Ścieżka tematów (rozdziały) |
| `GET /study/read?collection=…&chapter=…` | Ciągły tekst rozdziału |
| `POST /study/quiz` | Klikalne pytania ABCD dla rozdziału |
| `POST /study/` | Tryby `explain` / `connect` (free-form pytanie) |
| `POST /query/` | RAG Q&A — wolne pytanie o tematykę + źródła |
| `GET /health` | Healthcheck |

Pełna dokumentacja (Swagger) na `/docs` po uruchomieniu.

## Architektura

Diagramy i opis modułów: [`docs/architecture/`](docs/architecture/) (`01` as-is,
`02` to-be, `03` flow nauki, `04` model progresu).

Skrót:

```
PDF → PyMuPDF (struktura) → Chunker (1000/200) → bge-m3 → Qdrant
                                                            │
                                                            ▼
              UI ← FastAPI ← StudyEngine ← Retriever ─── search
                              │
                              └── Generator (Gemini / Ollama)
```

## Testy

```bash
uv run pytest -q
```

`tests/conftest.py` wymusza lekkie środowisko: Qdrant in-memory + embedder
`all-MiniLM-L6-v2` + ollama-fallback, żeby suite leciał bez Dockera i bez sieci.

## Status

Stage 1 (polish) zakończony. Roadmapa: Stage 2 — parser Docling; Stage 3 —
progres nauki (reading_progress / quiz_attempt, SQLite); Stage 4 — hybrid search
+ reranker `bge-reranker-v2-m3`; Stage 5 — powtórki FSRS (`py-fsrs`).

## Licencja

Prywatny projekt — używasz na własną odpowiedzialność.
