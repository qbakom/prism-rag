# Research: Przetwarzanie PDF i retrieval dla RAG

> Raport z deep-researchu (fan-out web search + adwersaryjna weryfikacja źródeł).
> Kontekst: PRISM — lokalny, prywatny RAG (Python, Qdrant, embeddingi BAAI/bge-m3,
> LLM Gemini/Ollama). Obecny pipeline: PyMuPDF + RecursiveCharacterTextSplitter
> (chunk_size=1000, overlap=200).
> Cel: poprawić jakość przetwarzania polskojęzycznych skryptów i podręczników
> akademickich (matematyka/fizyka — wzory, tabele, układ dwukolumnowy).

---

## TL;DR — rekomendacja

| # | Co zrobić | Wysiłek | Dlaczego |
|---|-----------|---------|----------|
| **1** | **Docling zamiast PyMuPDF** | ~pół dnia | wzory → LaTeX, tabele, układ dwukolumnowy; obecny PyMuPDF jest 19/21 w obsłudze wzorów |
| **2** | **Hybrid search + reranking** (`BAAI/bge-reranker-v2-m3`) | ~dzień | BGE-M3 i Qdrant już to wspierają; pojedynczo największy zysk trafności |
| 3 | *(opcja)* Contextual Retrieval z lokalnym LLM | ~dzień | -67% błędów retrievalu, ale dokłada krok przy indeksacji |
| ❌ | semantic / late / proposition chunking | — | nie pomaga (zwłaszcza late chunking z BGE-M3) |

---

## 1. Parsery PDF

### Benchmark wzorów matematycznych
Źródło: **Horn & Keuper, *Benchmarking Document Parsers on Mathematical Formula
Extraction from PDFs*, arXiv:2512.09874** (przyjęty na ICPR 2026).
Metoda: 100 syntetycznych PDF-ów, 1411 wzorów inline + 641 display, ocena
LLM-as-a-Judge w skali 0-10 (korelacja z oceną ludzką Pearson r=0.78, znacznie
wyższa niż metryki tekstowe/CDM).

| Parser | Wynik wzorów (0-10) | Lokalnie? | Uwaga |
|--------|--------------------:|-----------|-------|
| Qwen3-VL-235B | 9.76 | GPU (ciężki) | top, duży model |
| Gemini 3 Pro | 9.75 | ❌ chmura | łamie prywatność |
| **PaddleOCR-VL (0.9B)** | **9.65** | ✅ CPU/GPU | najlepszy open-source |
| Mathpix | 9.64 | ❌ płatne API | |
| PP-StructureV3 (<0.3B) | 9.34 | ✅ CPU/GPU | lekki |
| MinerU2.5 (1.2B) | 9.17 | ✅ CPU/GPU/API | |
| olmOCR | 8.94 | GPU | |
| DeepSeek-OCR | 8.55 | GPU | |
| pypdf | 7.69 | ✅ | rule-based |
| **PyMuPDF4LLM (obecny)** | **6.67** | ✅ | 19/21 — jeden z najsłabszych |
| GROBID | 5.70 | ✅ | ostatni na wzorach |

**Wniosek:** rule-based parsery (PyMuPDF, pypdf, pdfminer) wyciągają wzory jako
symbole Unicode zamiast LaTeX-a → systematyczne błędy na materiale matematycznym.
To potwierdza, że jakość parsera jest krytyczna dla treści STEM.

⚠️ **Caveat (uczciwie):** benchmark używa *syntetycznych* PDF-ów; przełożenie na
realne skany nie jest udowodnione. Kierunek (rule-based ≪ layout-aware) potwierdza
jednak drugi benchmark na DocLayNet — patrz niżej.

### Docling vs Marker (dwa główne layout-aware open-source)
Źródła: dokumentacja Docling (IBM Research), porównania społeczności, benchmark tabel.

- **Docling (IBM)** — wzory wyciągane **jako LaTeX**; model TableFormer ogarnia
  scalone komórki i zagnieżdżone nagłówki; rekonstruuje kolejność czytania w
  **układzie dwukolumnowym** (DocLayNet + TableFormer). Dokładność: standard 95%+,
  złożone 90%+. Tabele: **97.9% poprawności komórek** (vs Unstructured ~75%,
  LlamaParse ~0% przez rozjazd kolumn). Open-source, lokalnie. Wolniejszy (~2-6 s/strona).
- **Marker** — szybszy (~1-4 s/strona), ale wykrywa bloki wzorów **bez konwersji
  na LaTeX**, gorzej radzi sobie z tabelami (dzieli scalone komórki). Open-source,
  lokalnie, wymaga ~1 GB modeli przy starcie, GPU pomaga. Flaga `--use_llm`
  poprawia złożone tabele.

### Pozostałe
- **LlamaParse** — chmurowe API (❌ prywatność), **przeplata kolumny** w układzie
  dwukolumnowym → psuje retrieval na skryptach. Najszybszy (~6 s niezależnie od rozmiaru).
- **Nougat (Meta)** — Visual Transformer OCR → markup/LaTeX, pod dokumenty naukowe,
  open-source/lokalny. Bije rule-based parsery na kategorii Scientific, ale wolny
  i **potrafi halucynować**. Źródło: arXiv:2308.13418 (Nougat) + benchmark DocLayNet.
- **GROBID** — najlepszy do **metadanych i bibliografii** (zbudował korpus S2ORC),
  ale **ostatni** na wzorach (5.70). Do bibliografii tak, do matematyki nie.

### Benchmark wieloformatowy (DocLayNet)
Na kategoriach Scientific/Patent **wszystkie** parsery wypadają najgorzej; tam
modele uczone (Nougat dla tekstu, Table Transformer/TATR dla tabel — F1 0.91 na
Scientific vs <0.34 dla rule-based) biją podejścia regułowe. Dla zwykłego tekstu
PyMuPDF/pypdfium2 są wciąż dobre — czyli obecny wybór jest OK do prostego tekstu,
ale nie do trudnych układów i wzorów.

**→ Rekomendacja: Docling** (lokalność + LaTeX + tabele + dwie kolumny, najlepszy
stosunek do wysiłku). PaddleOCR-VL jako alternatywa przy max jakości wzorów i GPU.

---

## 2. Strategie chunkingu

- **Semantic chunking → nie warto.** Wiele źródeł: fixed-size chunking dorównuje
  lub bije semantic na realnych danych; przewaga semantic pojawia się tylko na
  sztucznie „sklejanych" dokumentach o dużej różnorodności tematów. Wpływ strategii
  chunkingu jest przykryty przez jakość embeddingu.
- **Late chunking (Jina AI, arXiv:2409.04701) → nie dla tego przypadku.** Nie bije
  konsekwentnie zwykłego chunkingu, a **konkretnie z BGE-M3 na NFCorpus early
  chunking wygrał z late**. Skoro PRISM używa BGE-M3 — nieopłacalne.
- **Proposition-based / Dense X Retrieval (arXiv:2312.06648)** — realne zyski
  (+12.0 Recall@5), ale wymaga trenowanego modelu „Propositionizer" → za dużo
  pracy na ten etap.

**→ Zostać przy RecursiveCharacterTextSplitter.**

---

## 3. Contextual Retrieval (Anthropic, 2024)

Mechanizm: LLM dopisuje 50-100 tokenów kontekstu do każdego chunka (umieszczając
go w kontekście całego dokumentu) **przed** embeddingiem i indeksowaniem BM25.

Twarde wyniki (Anthropic, „Introducing Contextual Retrieval"):
- same Contextual Embeddings: **-35%** błędów retrievalu (5.7% → 3.7%),
- + Contextual BM25 (hybryda): **-49%** (→ 2.9%),
- **+ reranking: -67%** (5.7% → 1.9%) — najlepszy wynik.
- Koszt: ~$1.02 / mln tokenów dokumentu przy prompt cachingu. Lokalnie z Ollama →
  praktycznie darmowe, ale wolniejsze przy indeksacji.

**→ Najlepszy zysk/wysiłek na jakość, jeśli starczy czasu (krok opcjonalny).**

---

## 4. Hybrid search + reranking

- **BGE-M3 generuje w jednym przebiegu dense (1024d) + sparse (BM25-like) +
  ColBERT** → hybryda dostępna bez drugiego modelu.
- **Qdrant natywnie wspiera hybrid search** (Query API: `prefetch` + fuzja RRF;
  można też ColBERT jako multivector do rerankingu).
- **Hybryda (BM25 + dense, RRF k=60)** poprawia recall — BM25 łapie dokładne/rzadkie
  terminy, dense łapie synonimy/parafrazy; nadrabiają swoje słabości. Walidacja na
  BEIR, MS MARCO.
- **Reranking = pojedynczo największy zysk:** cross-encoder na wierzchu hybrydy
  daje **+17.2 pkt MRR@3 i +12.1 pkt Recall@5** vs sama hybryda. Model:
  `BAAI/bge-reranker-v2-m3`, działa lokalnie (GPU przyspiesza).
- Wagi: 4:1 dense:sparse lepsze niż równe (recepta Anthropic).

---

## 5. Język polski

- **bge-m3 to dobry wybór dla polskiego** — potwierdzone benchmarkami PL-MTEB
  (30 zadań NLP) i PIRB (41 zadań retrievalu). Multilingual E5 też mocny.
- **Hybryda (sparse + dense) poprawia polski retrieval o ~+1.2 do +3.8 NDCG@10.**
- **PIRB** zawiera zbiór *GPT-exams*: 8131 par Q&A z 409 kursów akademickich —
  gotowy materiał do ewaluacji retrievalu na polskiej treści akademickiej.

---

## Narracja akademicka (do sprawozdania)

> „Zmierzyłem, że regułowy parser (PyMuPDF) jest słaby na wzorach matematycznych
> (19/21 w benchmarku arXiv:2512.09874), podmieniłem na layout-aware (Docling),
> który wyciąga wzory jako LaTeX i rekonstruuje układ dwukolumnowy, oraz dodałem
> hybrid search + reranking (`bge-reranker-v2-m3`) — mierząc poprawę trafności
> retrievalu na polskim skrypcie wykładowym."

### Źródła
- Horn & Keuper, *Benchmarking Document Parsers on Mathematical Formula Extraction from PDFs*, arXiv:2512.09874 (ICPR 2026)
- Anthropic, *Introducing Contextual Retrieval* (2024)
- Günther et al. (Jina AI), *Late Chunking*, arXiv:2409.04701
- Chen et al., *Dense X Retrieval (proposition-based)*, arXiv:2312.06648
- Blecher et al. (Meta), *Nougat*, arXiv:2308.13418
- Docling (IBM Research) — dokumentacja i repozytorium
- PL-MTEB i PIRB — benchmarki retrievalu/embeddingów dla języka polskiego
- Benchmark parserów na DocLayNet (kategorie Scientific/Patent, Table Transformer/TATR)
