# Sprawozdanie z projektu indywidualnego — PRISM

## 1. Cel projektu

Celem projektu było zbudowanie prywatnego, lokalnego systemu RAG (Retrieval-Augmented
Generation) wspomagającego naukę z własnych materiałów PDF — wykładów, skryptów,
podręczników. W przeciwieństwie do gotowych narzędzi typu ChatPDF czy NotebookLM, które
działają jako czat (użytkownik musi sam wymyślić pytania), zbudowałem **klikalny tryb nauki**:
system prowadzi użytkownika przez materiał — ścieżka tematów, czytanie, automatycznie
generowany quiz ze sprawdzeniem wiedzy i przejściem do kolejnego tematu.

Projekt testowałem na dwóch korpusach: podręczniku „Fair ML Book" (angielski) oraz
„Metody numeryczne — wykłady na Wydziale Elektrycznym PW" (duża ilość wzorów).

## 2. Opis funkcjonalny

Zaimplementowałem następujące funkcje:

- **Tematyki** — każda książka/przedmiot to osobna kolekcja w bazie wektorowej. Użytkownik
  tworzy nową tematykę i wgrywa do niej PDF-y (obsługa wielu plików, drag&drop).
- **Ścieżka nauki** — automatyczna segmentacja książki na rozdziały. Czytanie rozdziału
  jako ciągłego tekstu (z deduplikacją nakładających się fragmentów).
- **Quiz ABCD** — generowany przez LLM z treści rozdziału, z automatyczną oceną
  (porównanie z `correct_index`), wynikiem (X/N + procent) i przejściem do następnego tematu.
- **Zapytaj książkę** — trzy tryby pracy z materiałem: *Pytanie* (klasyczny RAG Q&A
  z cytowaniem źródeł), *Wyjaśnij* (tutorskie wyjaśnienie konceptu z analogiami),
  *Połącz* (analiza powiązań między konceptami).
- **Zarządzanie materiałami** — lista plików w tematyce, usuwanie pojedynczych plików
  lub całej tematyki.

## 3. Architektura

Zastosowałem **architekturę warstwową** z wyraźnym podziałem odpowiedzialności. Każda
warstwa zależy tylko od warstwy poniżej i komunikuje się przez jasno zdefiniowane interfejsy.

```
┌─────────────────────────────────────────────┐
│  Frontend (React + TypeScript)               │  warstwa prezentacji
├─────────────────────────────────────────────┤
│  API (FastAPI) — routes + Pydantic models    │  warstwa API / kontrakt
├─────────────────────────────────────────────┤
│  Logika: ingestion / rag / study             │  warstwa domenowa
├─────────────────────────────────────────────┤
│  vectorstore (Qdrant) + embeddings (bge-m3)  │  warstwa danych
└─────────────────────────────────────────────┘
```

**Przepływ danych — ingestion (wgrywanie PDF):**

```
bajty PDF → PdfParser → enrich_with_structure → DocumentChunker → Embedder → QdrantStore
            (tekst+TOC)   (rozdziały)            (fragmenty)       (wektory)   (zapis)
```

**Przepływ danych — zapytanie (RAG):**

```
pytanie → Embedder → QdrantStore.search → Retriever → prompt + kontekst → Generator (Gemini) → odpowiedź
          (wektor)   (top-k podobnych)    (fragmenty)                       (LLM)
```

## 4. Wydzielone moduły

Kod backendu podzieliłem na **siedem pakietów**, każdy o jednej odpowiedzialności:

### 4.1. `src/config.py`
Konfiguracja przez Pydantic Settings — wszystkie parametry (host/port Qdrant, model
embeddingów, backend LLM, klucz API) czytane ze zmiennych środowiskowych / pliku `.env`.
Nic nie jest zahardkodowane.

### 4.2. `src/ingestion/` — przetwarzanie dokumentów
Najważniejszy pakiet pod względem logiki. Wydzieliłem:
- **`base.py`** — klasa `Document` (dataclass: treść + metadane).
- **`pdf_parser.py`** — parser oparty na PyMuPDF (fitz). Wyciąga tekst strona po stronie,
  zachowuje numery stron (do cytowania źródeł), wyciąga TOC (zakładki PDF-a). Zawiera też
  tablicę mapowań symboli Private Use Area → Unicode (rozwiązanie problemu wzorów, p. 7).
- **`structure.py`** — detekcja struktury (rozdziałów). Trzystopniowa strategia:
  TOC z PDF-a → jawne nagłówki regex → segmentacja po zakresach stron.
- **`chunker.py`** — dzielenie dokumentów na fragmenty (RecursiveCharacterTextSplitter,
  1000 znaków, overlap 200).
- **`pipeline.py`** — orkiestrator: spina parser → strukturę → chunker w jeden przepływ.
  Reszta systemu woła tylko `pipeline.run()` i nie musi znać szczegółów.

### 4.3. `src/embeddings/` — wektoryzacja
- **`embedder.py`** — wrapper na model `BAAI/bge-m3` (sentence-transformers, dim=1024).
  Zamienia tekst na wektory; działa na GPU jeśli dostępne.

### 4.4. `src/vectorstore/` — baza wektorowa
- **`qdrant_store.py`** — warstwa abstrakcji nad Qdrant. CRUD kolekcji, dodawanie punktów,
  wyszukiwanie podobieństwa (z opcjonalnym pre-filtrowaniem po metadanych), listowanie
  tematów/plików, usuwanie. Obsługuje tryb in-memory (do testów, bez Dockera).

### 4.5. `src/rag/` — Retrieval-Augmented Generation
- **`retriever.py`** — pobiera najbardziej podobne fragmenty z Qdrant.
- **`prompts.py`** — budowanie promptów (system prompt z zasadami: odpowiadaj tylko
  z kontekstu, cytuj źródła, nie halucynuj).
- **`generator.py`** — komunikacja z LLM (Gemini / Ollama).
- **`engine.py`** — orkiestrator RAG: retrieval → prompt → generacja → odpowiedź ze źródłami.

### 4.6. `src/study/` — tryb nauki
- **`engine.py`** — orkiestrator trybu nauki.
- **`modes.py`** — definicje trybów (quiz / explain / connect), każdy z własnym promptem.
- **`quiz.py`** — generowanie i walidacja quizu (Pydantic), z retry przy niepoprawnym JSON.
- **`text.py`** — algorytm `stitch_overlapping` sklejający fragmenty w ciągły tekst bez
  powtórzeń (kompensuje overlap z chunkingu).

### 4.7. `src/api/` — warstwa API (FastAPI)
- **`main.py`** — punkt wejścia, montuje routery.
- **`dependencies.py`** — wstrzykiwanie zależności (np. współdzielony QdrantStore).
- **`models/`** — modele Pydantic (request/response) dla ingest, query, study.
- **`routes/`** — endpointy pogrupowane tematycznie:
  - `health.py` — `GET /health`
  - `collections.py` — `GET /collections/`, `GET /{name}/files`, `DELETE /{name}/files`, `DELETE /{name}`
  - `ingest.py` — `POST /ingest/` (multipart, upload PDF)
  - `study.py` — `GET /study/topics`, `GET /study/read`, `POST /study/quiz`, `POST /study/`
  - `query.py` — `POST /query/` (RAG Q&A)

### 4.8. Frontend (`frontend/src/`)
- **`api.ts`** — cienki klient HTTP (fetch), z cache'owaniem odczytów rozdziałów.
- **`types.ts`** — typy TypeScript będące lustrem modeli Pydantic z backendu.
- **`App.tsx`** — główny komponent (ścieżka, czytanie, quiz, panel Zapytaj, uploader, zarządzanie).
- **`Markdown.tsx`** — renderer markdownu odpowiedzi LLM (react-markdown + remark-gfm).

## 5. Stack technologiczny i uzasadnienie wyborów

| Komponent | Technologia | Dlaczego |
|---|---|---|
| Backend | FastAPI (Python 3.11+) | Async, automatyczna walidacja Pydantic, OpenAPI/Swagger out-of-the-box |
| Baza wektorowa | Qdrant | Open-source, łatwy Docker, tryb in-memory do testów, brak vendor lock-in |
| Embeddingi | BAAI/bge-m3 | Wielojęzyczny (PL+EN), lokalny (GPU), dim=1024 — dobry balans jakość/rozmiar |
| LLM | Google Gemini 2.5 Flash | Szybki, tani, dobra jakość po polsku; alternatywnie lokalna Ollama |
| Parser PDF | PyMuPDF (fitz) | Szybki, dostęp do struktury (TOC), pozycji tekstu |
| Chunking | RecursiveCharacterTextSplitter | Tnie po naturalnych granicach (akapity, zdania), nie w połowie wyrazu |
| Frontend | React + TypeScript + Tailwind + Vite | Typowanie, szybki dev server, komponenty |
| Testy | pytest | 48 testów, in-memory Qdrant + lekki embedder (bez Dockera/GPU) |
| Wdrożenie | systemd + Caddy + Docker | Trwały backend, reverse proxy z TLS-em, izolacja Qdrant |

## 6. Decyzje architektoniczne

- **Podział na warstwy** zamiast monolitu — żeby móc wymienić np. bazę wektorową albo LLM
  bez przepisywania logiki. `QdrantStore` to fasada — gdyby przejść na inną bazę, zmienia
  się jeden plik.
- **Orkiestratory** (`pipeline.py`, `rag/engine.py`, `study/engine.py`) — warstwa API nie
  zna szczegółów przetwarzania, woła tylko jedną metodę. Łatwiej testować i rozwijać.
- **Konfiguracja przez środowisko** — ten sam kod działa lokalnie (Ollama) i na serwerze
  (Gemini), różni je tylko `.env`.
- **Typy front ↔ back** — `types.ts` odzwierciedla modele Pydantic, co daje spójność
  kontraktu API i wychwytuje błędy na etapie kompilacji TS.

## 7. Problemy i rozwiązania

### 7.1. Symbole matematyczne jako „□" (Private Use Area)
Podręcznik z metod numerycznych używał fontu symbolicznego, który koduje znaki równości,
litery greckie i operatory w obszarze Private Use Area Unicode (np. `U+F03D` zamiast `=`).
PyMuPDF wyciągał je dosłownie — **82% fragmentów** zawierało nieczytelne „□". Rozwiązałem
to tablicą 80+ mapowań Symbol Font → Unicode aplikowaną podczas parsowania
(`pdf_parser._clean_pua`). Po naprawie: 0% fragmentów z PUA.

### 7.2. Fałszywe rozdziały w ścieżce nauki
Pierwsza wersja detekcji rozdziałów (heurystyka regex) interpretowała numery stron jako
nagłówki, generując nonsensowne rozdziały o tytułach „H", „e", „k". Przebudowałem
`structure.py` na **trzystopniowy fallback**: (1) TOC z metadanych PDF-a, (2) jawne nagłówki
„Rozdział N", (3) segmentacja po zakresach stron („Strony 1–19"). Dodatkowo TOC przechodzi
**bramkę jakości** (≥6 rozdziałów, żaden nie pokrywa >60% stron) — bo niektóre PDF-y mają
tylko zakładki produkcyjne („okładka", „środki") zamiast rozdziałów.

### 7.3. Powtórzenia w czytaniu
Chunking z overlapem 200 znaków powodował powtórzenia tekstu przy sklejaniu fragmentów.
Napisałem `stitch_overlapping` (`study/text.py`), który wykrywa i usuwa nakładające się
końcówki/początki sąsiednich fragmentów.

### 7.4. Niepoprawny JSON z LLM
Gemini czasem zwracał quiz w niepoprawnym formacie. Dodałem walidację Pydantic + retry
(do 3 prób) w `quiz.py`.

## 8. Testy

Napisałem **48 testów** (pytest) pokrywających: parsowanie, detekcję struktury, chunking,
operacje na bazie wektorowej, tryby nauki i endpointy. Środowisko testowe (`conftest.py`)
nie wymaga Dockera ani GPU — używa Qdrant w trybie in-memory i lekkiego embeddera
`all-MiniLM-L6-v2`, dzięki czemu testy wykonują się w ~4 sekundy.

## 9. Wdrożenie

System wdrożyłem na własnym serwerze:
- **Backend** jako usługa systemd (auto-restart przy awarii, auto-start po reboot),
  uvicorn na porcie 8011.
- **Qdrant** w kontenerze Docker (port 6333), dane persystowane na dysku.
- **Caddy** jako reverse proxy: `/prism/api/*` → backend, `/prism/*` → zbudowany frontend
  (statyczne pliki), z timeoutem 30 min na długie operacje (embedding dużych PDF-ów).
- **Frontend** zbudowany przez Vite (`base=/prism/`, `VITE_API_URL=/prism/api`).

## 10. Podsumowanie i dalszy rozwój

Zbudowałem działający, wdrożony system, który realizuje główne założenie — klikalną naukę
z własnych PDF-ów. Najwięcej nauczyłem się przy problemach „brudnych danych" (fonty PUA,
brak struktury w PDF-ach), które wymagały solidnych fallbacków zamiast założenia, że każdy
PDF jest czysty.

Kierunki dalszego rozwoju:
- **OCR** (Gemini Vision) dla skanów i notatek ręcznych — obecny parser czyta tylko warstwę
  tekstową PDF-a.
- **Śledzenie postępu** nauki + algorytm powtórek (FSRS).
- **Hybrid search** (dense + sparse) z rerankerem `bge-reranker-v2-m3`.
- **Lepszy parser** (Docling/Marker) zachowujący tabele i wzory w formie strukturalnej.
