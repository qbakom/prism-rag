# PRISM — architektura (handoff wizualny)

Dokument projektowy dla sesji implementacyjnej. Cztery diagramy + opis modułów +
decyzje do podjęcia. Diagramy renderowane z `src/` (D2 / Mermaid / GraphViz przez Kroki).

> **Dyscyplina zakresu (z handoffu):** jeden segment — klikalny tryb nauki — zrobiony
> solidnie. NIE przepisujemy działającego core'a, NIE dokładamy featurów „bo fajne".
> Świadomie odłożone: medyczny, agentowy, głosowy (ASR), DKT, portfolio.

## Diagramy

| Plik | Co pokazuje |
|------|-------------|
| `01-current.svg` | Architektura obecna (as-is) — warstwy i przepływ danych |
| `02-target.svg` | Architektura docelowa (to-be) — etapy roadmapy nałożone na moduły |
| `03-flow.svg` | Przepływ trybu nauki — Faza A (ingestion) + Faza B (nauka) |
| `04-progress-model.svg` | Model danych progresu/FSRS (Stage 3/5) |

## Moduły (stan obecny)

| Warstwa | Moduł | Odpowiedzialność |
|---------|-------|------------------|
| Frontend | `App.tsx` | Lewy panel = ścieżka tematów (klik) → prawy = czytanie + „Sprawdź się" → karty ABCD (klik = ocena) |
| Frontend | `api.ts` / `types.ts` | Klient REST (`VITE_API_URL`), typy kontraktów |
| API | `routes/study.py` | `/study/topics`, `/study/read`, `/study/quiz` (+ legacy `/study/`) |
| API | `routes/{ingest,query,collections,health}.py` | Upload PDF, RAG-query, lista/usuwanie kolekcji, health |
| API | `dependencies.py` | Wstrzykiwanie singletonów (embedder, store, engine) |
| Rdzeń | `study/engine.py` | Orkiestracja: retrieval → tryb nauki → LLM; `quiz()` bierze materiał z `read_chapter` |
| Rdzeń | `study/quiz.py` | Budowa promptu quizu + defensywny parsing JSON (ABCD) |
| Rdzeń | `rag/retriever.py` | embed → search → **dedup** (klucz = pierwsze 200 znaków) |
| Rdzeń | `rag/generator.py` | Fabryka LLM (`ollama` \| `gemini`), `.model`, `is_available()` |
| Ingestion | `ingestion/pdf_parser.py` | PyMuPDF → tekst stron |
| Ingestion | `ingestion/structure.py` | Detekcja rozdziałów/sekcji (mapa książki) |
| Ingestion | `ingestion/chunker.py` | `RecursiveCharacterTextSplitter` (size=1000, overlap=200) |
| Embeddings | `embeddings/embedder.py` | `BAAI/bge-m3` (dense+sparse+ColBERT), dim=1024 |
| Vector store | `vectorstore/qdrant_store.py` | `search`, `list_topics`, `read_chapter`, `_scroll_all` |

## Ewolucja (etapy roadmapy → moduły)

- **Stage 1 — Polish (najpierw):** dedup overlapu w `read_chapter` (bug widoczny w UI),
  retry generacji quizu (`quiz.py`/`engine.quiz`), cache odczytów na froncie. Małe, pewne.
- **Stage 2 — Docling:** podmiana `pdf_parser` za abstrakcją `DocumentParser`
  (wzory→LaTeX, tabele, lepsze rozdziały → lepsza ścieżka i quiz).
- **Stage 3 — Progres:** `reading_progress` + `quiz_attempt`; localStorage → backend SQLite.
- **Stage 4 — Jakość retrievalu:** hybrid (dense+sparse BM25, bge-m3 daje sparse) + reranker
  `bge-reranker-v2-m3`. Znaczenie przy wielu książkach.
- **Stage 5 — Spaced repetition:** `fsrs_card` + `py-fsrs`, „powtórki na dziś".

## Decyzje do podjęcia jutro

1. **Próg architektoniczny:** zostajemy przy monolicie FastAPI z wymiennymi modułami
   (rekomendacja — zgodne z „jeden segment solidnie") — potwierdzić.
2. **Persistencja (Stage 3):** localStorage-only czy od razu SQLite na backendzie?
   (model danych w `04-progress-model.svg`).
3. **Kolejność:** czy Stage 1 (polish) idzie pierwszy, czy przeskakujemy do Stage 2/4.
4. **Granica jednostki FSRS:** karta per-rozdział czy per-pytanie/pojęcie (wpływa na schemat).
