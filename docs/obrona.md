# PRISM — opis na obronę projektu

## 1. Problem i motywacja (slajd 1)

**Bullet points:**
- Studenci uczą się z PDF-ów (wykłady, skrypty, książki) — ale PDF to martwy format
- Typowy flow: otwórz PDF → czytaj liniowo → nie wiesz ile zapamiętałeś
- Istniejące narzędzia RAG (ChatPDF, NotebookLM) to czat — trzeba wiedzieć co zapytać
- Brakuje **klikalnego trybu nauki**: materiał → czytanie → sprawdzenie się → dalej

**Skrypt:**
> Problem jest prosty: masz 300-stronicowy podręcznik z metod numerycznych w PDF-ie
> i musisz się go nauczyć na egzamin. Otwierasz go, czytasz, ale nie wiesz ile
> zapamiętałeś. Istniejące narzędzia AI (ChatPDF, NotebookLM) dają Ci czat —
> ale musisz sam wymyślić pytania. PRISM odwraca ten model: Ty klikasz, system
> prowadzi. Ścieżka nauki, czytanie fragmentami, automatyczny quiz ABCD z oceną,
> przejście do następnego tematu. Jak Duolingo, ale na Twoje własne materiały.

---

## 2. Architektura systemu (slajd 2)

**Bullet points:**
- Pipeline: PDF → PyMuPDF (parser) → chunking (1000 znaków, overlap 200) → embedding (bge-m3, dim=1024) → Qdrant (baza wektorowa)
- Backend: FastAPI + Pydantic, REST API
- Frontend: React + TypeScript + Tailwind
- LLM: Google Gemini 2.5 Flash (generacja quizów, wyjaśnienia, RAG)
- Retrieval: dense search w Qdrant → top-k fragmentów → kontekst dla LLM

**Skrypt:**
> Architektura składa się z trzech warstw. Warstwa ingestion przetwarza PDF-y:
> PyMuPDF wyciąga tekst strona po stronie, potem RecursiveCharacterTextSplitter
> dzieli go na fragmenty 1000-znakowe z overlapem 200 znaków, żeby nie ciąć
> zdań w połowie. Każdy fragment jest wektoryzowany modelem bge-m3 (BAAI,
> dim=1024) i zapisywany w Qdrant — bazie wektorowej działającej w Dockerze.
>
> Warstwa API (FastAPI) udostępnia endpointy: ingestion, kolekcje, ścieżkę nauki,
> quiz, RAG Q&A i tryby explain/connect. Warstwa frontendowa (React+TypeScript)
> jest klikalna — użytkownik nie pisze zapytań, tylko klika tematy, czyta, robi
> quiz i przechodzi dalej.

**Diagram (do narysowania / z docs/architecture/):**
```
PDF → PyMuPDF → Chunker → bge-m3 → Qdrant
                                       │
         React UI ← FastAPI ← Retriever ── search
                     │
                     └── Gemini (quiz / explain / RAG)
```

---

## 3. Kluczowe funkcje (slajd 3)

**Bullet points:**
- **Tematyki**: każda książka/skrypt = osobna tematyka, upload wielu PDF z UI
- **Ścieżka nauki**: automatyczna segmentacja na rozdziały (z TOC PDF-a lub zakresami stron)
- **Czytanie**: ciągły tekst rozdziału (overlap-aware dedup, bez powtórzeń)
- **Quiz ABCD**: generowany z materiału, auto-ocena, wynik X/N + %, przejście do następnego tematu
- **Zapytaj książkę**: 3 tryby — Pytanie (RAG Q&A), Wyjaśnij (tutor), Połącz (relacje między konceptami)
- **Zarządzanie materiałami**: lista plików w tematyce, usuwanie, dodawanie

**Skrypt:**
> PRISM ma sześć głównych funkcji. Po pierwsze, tematyki — każdy przedmiot
> (metody numeryczne, fairness w ML) to osobna kolekcja, w której wgrywasz
> swoje PDF-y przez drag&drop. Po drugie, ścieżka nauki — system automatycznie
> segmentuje książkę na rozdziały (jeśli PDF ma spis treści) albo na zakresy
> stron (fallback). Po trzecie, czytanie — ciągły tekst rozdziału z deduplikacją
> overlappingowych fragmentów. Po czwarte, quiz ABCD — Gemini generuje pytania
> testujące zrozumienie materiału z konkretnego rozdziału, z poprawną odpowiedzią
> i wyjaśnieniem. Po piąte, panel "Zapytaj książkę" z trzema trybami: wolne
> pytanie (RAG), wyjaśnienie konceptu z analogiami i TL;DR, oraz łączenie
> konceptów ("jak fairness łączy się z kalibracją?"). Po szóste, zarządzanie
> materiałami — widzisz jakie pliki są w tematyce i możesz je usuwać.

---

## 4. Wyzwania techniczne (slajd 4)

**Bullet points:**
- **Problem fontów PUA**: podręczniki techniczne kodują symbole matematyczne (=, α, Σ) w Private Use Area Unicode → wyświetlają się jako □. Rozwiązanie: tabela 80+ mapowań Symbol Font → Unicode w parserze.
- **Detekcja rozdziałów**: heurystyka regex dawała fałszywe rozdziały (numery stron interpretowane jako nagłówki). Rozwiązanie: 3-stopniowy fallback (TOC bookmarki → jawne nagłówki „Rozdział N" → segmenty po stronach).
- **Jakość TOC**: PDF-y mają "zakładki produkcyjne" (okładka, środki) zamiast rozdziałów. Bramka jakości: ≥6 rozdziałów i żaden nie >60% stron.
- **Overlap w czytaniu**: chunki nachodzą na siebie (200 znaków overlap) → powtórzenia w tekście. Algorytm `stitch_overlapping` je deduplikuje.
- **Retry quizu**: Gemini nie zawsze generuje valid JSON → 3 próby z walidacją Pydantic.

**Skrypt:**
> Najtrudniejszym problemem technicznym okazały się fonty matematyczne. Podręcznik
> z metod numerycznych używał fontu Symbol, który mapuje znaki równości, litery
> greckie i operatory na Private Use Area Unicode. PyMuPDF wyciągał je dosłownie —
> 82% fragmentów miało znaki □ zamiast wzorów. Rozwiązaniem jest tabela mapowań
> 80+ symboli (np. U+F03D → =, U+F061 → α), aplikowana podczas parsowania.
>
> Drugi problem to detekcja struktury. Nie każdy PDF ma zakładki (bookmarks).
> Heurystyka oparta na regex interpretowała numery stron jako nagłówki rozdziałów,
> generując nonsensowne rozdziały o tytułach "H", "e", "k". Zbudowałem
> trzystopniowy fallback: najpierw próbujemy TOC z metadanych PDF-a (jeśli
> przechodzi bramkę jakości), potem jawne nagłówki "Rozdział N", a na końcu
> segmentujemy po zakresach stron. To gwarantuje czytelną ścieżkę dla dowolnego PDF-a.

---

## 5. Demo (slajd 5 — live demo)

**Scenariusz demo (2-3 minuty):**

1. **Wejście**: otwórz kuba.suby.pl/prism → pokaż dropdown "Tematyka" z dwoma kolekcjami (fairml, metody_numeryczne)
2. **Upload nowego**: klik "+ Nowy temat" → wpisz nazwę → drag&drop PDF → pokaż status uploadu
3. **Ścieżka**: przełącz na metody_numeryczne → pokaż "Strony 1–19", "Strony 20–38" itd.
4. **Czytanie**: klik na segment → pokaż ciągły tekst z czytelnym polskim i wzorami (= α Σ zamiast □)
5. **Quiz**: klik "Sprawdź się" → pokaż 3 pytania ABCD → odpowiedz → wynik + wyjaśnienie
6. **Zapytaj książkę**: wpisz "wyjaśnij rozkład LU" w trybie Wyjaśnij → pokaż odpowiedź z markdown + źródła
7. **Zarządzanie**: klik "Zarządzaj" → pokaż listę plików → (opcjonalnie) usuń jeden

**Tip:** przygotuj pytanie do quizu wcześniej, żeby nie czekać na generację na żywo.

---

## 6. Stack technologiczny (slajd 6 — opcjonalny)

| Komponent | Technologia |
|---|---|
| Backend | Python 3.11+, FastAPI, Pydantic |
| Baza wektorowa | Qdrant (Docker) |
| Embeddingi | BAAI/bge-m3 (1024 dim) |
| LLM | Google Gemini 2.5 Flash |
| Parser PDF | PyMuPDF (fitz) |
| Chunking | LangChain RecursiveCharacterTextSplitter |
| Frontend | React 19, TypeScript, Tailwind CSS v4, Vite |
| Markdown | react-markdown + remark-gfm |
| Testy | pytest (48 testów) |
| Deploy | systemd + Caddy (reverse proxy) + Docker |
| VCS | Git + GitHub |

---

## 7. Co dalej / roadmapa (slajd 7)

**Bullet points:**
- OCR dla skanów/notatek ręcznych (Gemini Vision → tekst → chunk → embed)
- Progres nauki (tracking co przeczytane, wynik quizów, powtórki FSRS)
- Hybrid search + reranker (bge-reranker-v2-m3)
- Lepszy parser (Docling / Marker → zachowanie tabel i wzorów)
- Parsowanie Spisu Treści z tekstu PDF (gdy brak bookmarków ale jest TOC w treści)

**Skrypt:**
> W przyszłości planuję dodać OCR przez Gemini Vision, co pozwoli wgrywać
> ręcznie pisane notatki — teraz parser wyciąga tylko warstwę tekstową PDF-a.
> Chcę też dodać tracking postępu nauki (co przeczytane, wyniki quizów) z
> algorytmem powtórek FSRS, który decyduje kiedy wrócić do materiału.
> Na poziomie retrievalu — przejście z dense search na hybrid (sparse+dense)
> z rerankerem bge-reranker-v2-m3 powinno znacząco poprawić trafność wyników.

---

## 8. Pytania, na które warto się przygotować

1. **Dlaczego nie ChatGPT/NotebookLM?** → Bo to czat — musisz wiedzieć co zapytać. PRISM jest klikalny, prowadzi Cię przez materiał. Plus: prywatność — Twoje materiały zostają lokalnie.

2. **Dlaczego Qdrant a nie Pinecone/Weaviate?** → Open-source, łatwy Docker, in-memory tryb do testów. Pinecone = vendor lock-in, Weaviate = cięższy.

3. **Dlaczego bge-m3 a nie OpenAI embeddings?** → Wielojęzyczny (polski + angielski), działa lokalnie (GPU), nie wymaga API key, dim=1024 to dobry balans jakość/rozmiar.

4. **Jak radzisz sobie z halucynacjami?** → System prompt nakazuje odpowiadać WYŁĄCZNIE z kontekstu + cytować [plik, s. X]. Fallback gdy brak odpowiedzi: "Nie znalazłem w materiałach."

5. **Jak testujesz?** → 48 testów pytest. Testy nie wymagają Dockera ani GPU — conftest ustawia Qdrant in-memory + lekki embedder (all-MiniLM-L6-v2).

6. **Co z dużymi PDF-ami?** → Chunking 1000/200 znaków skaluje się liniowo. 300-stronowy podręcznik = ~675 chunków, ingest <1s (po załadowaniu modelu).

---

## Struktura prezentacji (sugerowane slajdy)

| # | Slajd | Czas |
|---|---|---|
| 1 | Problem i motywacja | 1.5 min |
| 2 | Architektura | 2 min |
| 3 | Kluczowe funkcje | 2 min |
| 4 | Wyzwania techniczne | 2 min |
| 5 | Live demo | 3 min |
| 6 | Stack (opcjonalny) | 30s |
| 7 | Roadmapa | 1 min |
| — | Pytania | — |
| | **Razem** | **~12 min** |
