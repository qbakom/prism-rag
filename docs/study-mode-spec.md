# Study Mode — Faza 3: synteza i specyfikacja (rekomendacja)

> Wejście: `study-mode-design.md` (Fazy 1+2, przyziemne) + `deep-research-study.md`
> (ambitna wizja zero-typing/wektorowa). Tu: ocena wg dowodów + wykonalności w PRISM,
> jedna rekomendowana koncepcja, MVP i mapowanie na istniejący kod.
> Kontekst skali: [[project-scope]] — jeden segment, zrobiony solidnie. Bazą jakości
> jest research z `research-pdf-rag.md` (Docling + hybrid/rerank).

---

## 0. Główny przeskok względem obecnego kodu

Obecny `study/` jest **query-driven**: użytkownik zadaje pytanie → retrieval → prompt
(quiz/explain/connect). Wizja jest **document-driven**: książka → *knowledge nodes* →
**kurowana ścieżka** → nauka z minimalnym frictionem (konsumpcja + lekkie aktywne
przypominanie). To jest sedno — i to jest wyróżnik projektu.

Filozofia (z obu dokumentów, trzymamy ją jako "duszę"): **najpierw konsumpcja dobrze
podanego materiału, potem aktywne przypominanie — bez zmuszania do ciągłego pisania.**

---

## 1. Ocena pomysłów: co bierzemy, co przycinamy, co odrzucamy

| Pomysł (źródło) | Werdykt | Uzasadnienie (dowód + wykonalność) |
|---|---|---|
| **Knowledge-node pipeline** (książka → węzły z LaTeX + opisem semantycznym) | ✅ **rdzeń** | Buduje na `structure.py` + Docling. Bez tego nie ma reszty. Wykonalne. |
| **Cold Start = progressive reveal** (Forte, CTML/Mayer, cognitive load) | ✅ **bierzemy** | Mocna podstawa (Sweller, Mayer). MVP = poziomy szczegółowości, nie fancy suwak. |
| **Cram = priorytetyzacja "co czytać"** (Bjork desirable difficulties) | ✅ **bierzemy** | LLM rankuje sekcje wg ważności/gęstości. To realizuje Twój scenariusz "sesja za pasem". |
| **Active recall przez cloze** (testing effect, prediction error) | ✅ **bierzemy** | Roediger & Karpicke 2006 — solidne. Ukrycie terminu/zmiennej we wzorze = trywialne technicznie. |
| **Spaced repetition: FSRS** | ✅ **bierzemy** | Realny, otwarty algorytm (Ye 2022, ACM SIGKDD; Anki ≥23.10). Jest biblioteka `py-fsrs`. Tania, mocna, cytowalna. |
| **Zero-typing self-explanation: głos → ASR → ocena cosinusowa** (Chi 1994 + ASAG) | ✅ **wyróżnik** | Whisper lokalnie + bge-m3 (cosine) + LLM jako weryfikator pojęć. Wykonalne i to JEST "ciekawe". Dla v2. |
| **Implicit Knowledge Tracing (DKT/LSTM na telemetrii: dwell time, gesty, 60 fps on-device)** | ❌ **odrzucamy (future)** | Wymaga danych treningowych, własnego LSTM, telemetrii UI — miesiące pracy, kruche, niemierzalne w tym zakresie. Pragmatyczny zamiennik: ocena FSRS wprost z wyniku cosine, bez "biometrii". |
| **Gestowe suwaki semantyczne / "archipelag", 60 fps** | ⚠️ **przycinamy do UI later** | Ładna metafora, ale to projekt UI mobilnego. MVP w Streamlit = expander/slider poziomu detalu. Nie blokuj rdzenia tym. |
| Framing "neuromorficzny / kontrolowana halucynacja" | 🗑️ **pomijamy** | Retoryka, nie spec. Zostawiamy fakty (prediction error → uzasadnia cloze), wyrzucamy patos. |

**Szczera uwaga o `deep-research-study.md`:** jest inspirujący i dobrze ocytowany
(FSRS, Chi, Bjork, Mayer, ASAG — realne źródła), ale mocno przeładowany i miejscami
hand-wavy (DKT na telemetrii w 60 fps, "FSRS przypięty do embeddingów"). Bierzemy z
niego **mechanizmy**, odrzucamy **przesadę inżynieryjną** — zgodnie z zasadą "jeden
segment solidnie".

---

## 2. Rekomendowana koncepcja: **"Guided Reading + Low-Friction Recall"**

Jedna spójna pętla, dwa tryby wejścia, jeden mechanizm utrwalania:

```
KSIĄŻKA ──(pipeline)──▶ KNOWLEDGE NODES ──┬─▶ COLD START (progresywne odkrywanie)
                                          └─▶ CRAM (priorytetyzacja: co czytać)
                                                       │
                                            ▼ po konsumpcji węzła
                                   ACTIVE RECALL (cloze / głos)
                                                       │
                                            ▼ wynik (0..1)
                                   FSRS SCHEDULER (kiedy powtórzyć)
```

- **Cold Start** — nowy przedmiot: pokaż szkielet (rozdziały → definicje → wzory),
  użytkownik progresywnie odsłania szczegóły; po sekcji 1-2 lekkie cloze.
- **Cram** — sesja: LLM rankuje sekcje wg ważności/gęstości i mówi *co i w jakiej
  kolejności* przeczytać; krótkie, intensywne cloze na rdzeniu.
- **Recall** — wspólny: cloze (MVP) lub auto-wyjaśnienie głosem (v2), wynik karmi FSRS.

---

## 3. Knowledge node — struktura danych

```python
@dataclass
class KnowledgeNode:
    id: str                      # stabilny hash (plik+rozdział+offset)
    collection: str
    filename: str
    chapter: str | None          # z structure.py
    section: str | None
    page_number: int | None
    title: str                   # nagłówek / nazwa pojęcia
    body: str                    # tekst węzła
    formulas: list[str]          # LaTeX wyciągnięty przez Docling
    semantic_desc: str           # 1-2 zdania od LLM: "co to znaczy" (dla embeddingu)
    importance: float            # 0..1, ranking ważności (LLM/heurystyka) — dla Cram
    # stan nauki (FSRS):
    stability: float | None
    difficulty: float | None
    due: str | None              # ISO date kolejnej powtórki
```

Przechowywanie: payload w Qdrant (obok wektora bge-m3 z `body + semantic_desc`).
Stan FSRS aktualizowany in-place w payloadzie.

---

## 4. Mapowanie na istniejący kod

| Co | Gdzie | Status |
|---|---|---|
| Ekstrakcja struktury + wzorów | `ingestion/` (Docling) + `structure.py` | rozbudowa (Docling z `research-pdf-rag.md`) |
| Budowa knowledge nodes | **nowy** `study/nodes.py` (model) + `study/builder.py` (pipeline) | nowe |
| Tryby Cold Start / Cram | rozszerzyć `study/modes.py` (`StudyMode`) + prompty | rozbudowa |
| Orkiestracja | rozszerzyć `study/engine.py` o metody `cold_start()`, `cram_plan()`, `recall()` | rozbudowa |
| Harmonogram powtórek (FSRS) | **nowy** `study/scheduler.py` (wrapper na `py-fsrs`) | nowe |
| Active recall (cloze) | **nowy** `study/recall.py` | nowe |
| Ocena głosowa (v2) | **nowy** `study/voice.py` (Whisper) + reużycie bge-m3/cosine z `embeddings/` | nowe, później |
| Retrieval/cosine | `rag/retriever.py`, `vectorstore/qdrant_store.py`, `embeddings/embedder.py` | reużycie |
| API | `api/routes/study.py`, `api/models/study.py` | rozbudowa |
| UI | `ui/app.py` (Streamlit) | rozbudowa |

---

## 5. MVP i kolejność (pod "narrow, solid")

**v0 — fundament (to jest realny rdzeń projektu):**
1. Docling w ingestion (z `research-pdf-rag.md`) → wzory jako LaTeX, struktura.
2. `study/nodes.py` + `study/builder.py`: książka → knowledge nodes w Qdrant.
3. **Cram plan**: `engine.cram_plan(collection)` → LLM rankuje sekcje, zwraca
   uporządkowaną listę "co przeczytać" z uzasadnieniem. (Twój scenariusz sesji.)
4. **Cloze recall**: `recall.py` ukrywa kluczowy termin/zmienną w węźle → użytkownik
   przypomina → reveal. Bez oceny AI na start (sam ocenia: znałem/nie).

**v1 — utrwalanie:**
5. FSRS (`scheduler.py`, `py-fsrs`): wynik recall → harmonogram `due`. Tryb
   "powtórki na dziś". To domyka pętlę nauki i jest mocno cytowalne.
6. **Cold Start**: progresywne odsłanianie (UI: poziomy detalu).

**v2 — wyróżnik (jeśli czas/chęć):**
7. Zero-typing self-explanation: Whisper (lokalnie) → transkrypcja → cosine(bge-m3)
   vs węzeł referencyjny + LLM-weryfikator pojęć → wynik karmi FSRS.

**Future (świadomie poza zakresem):** implicit DKT na telemetrii, gestowe suwaki
60 fps on-device, mobilne UI. Parkujemy w README.

---

## 6. Otwarte decyzje (do ustalenia z użytkownikiem)

1. **Skala granularności węzła** — sekcja czy akapit? (Sekcja = mniej węzłów,
   prostszy MVP; akapit = dokładniejsze recall, więcej LLM-calls przy budowie.)
2. **Czy v0 ma już oceniać recall AI, czy self-rated?** (Self-rated = szybciej do
   MVP i zgodne z FSRS; AI grading dopiero z głosem w v2.)
3. **Głos w v2 — Whisper rozmiar modelu?** (base/small lokalnie vs jakość PL.)
4. **Cram: skąd "ważność"?** — sam LLM z treści, czy użytkownik podaje zakres
   egzaminu/zagadnienia (jak w `study-mode-design.md` Koncepcja B)?
5. Czy budujemy nodes **przy ingest** (wolniej, raz) czy **na żądanie** per kolekcja?
