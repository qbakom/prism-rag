# PRISM - Raport z testu systemu

**Data:** 2026-03-31  
**Wersja:** 0.1.0

---

## Środowisko

| Komponent | Wartość |
|-----------|---------|
| GPU | NVIDIA RTX 2080 Ti (11 GB VRAM, 6.9 GB dostępne) |
| LLM | Ollama + llama3.2 (2 GB) |
| Embeddings | BAAI/bge-m3 |
| Vector DB | Qdrant (localhost:6333) |

---

## Test: Ingestion

```bash
curl -X POST http://localhost:8000/ingest/ \
  -F "file=@fairmlbook.pdf" \
  -F "collection=fairml"
```

**Wynik:**
- ✅ Status: 200 OK
- 📄 Plik: `fairmlbook.pdf`
- 🗂️ Kolekcja: `fairml`
- 📦 Chunki: **1162** fragmentów

---

## Test: Query (RAG)

Pytanie o fairness → system zwrócił odpowiedź LLM z 5 źródłami (strony 4, 30, 209, 238).

**Graceful degradation:** Gdy Ollama nie działa → zwraca surowe fragmenty z ostrzeżeniem.

---

## Test: Study Mode

Tryb `explain` działa. Zwraca fragmenty pogrupowane per strona z kontekstem.

**Znany problem:** Duplikaty fragmentów (ta sama strona 2x). Do naprawy w retrieverze.

---

## Podsumowanie

| Funkcja | Status |
|---------|--------|
| PDF → Chunki | ✅ |
| Embeddings | ✅ |
| Qdrant storage | ✅ |
| Semantic search | ✅ |
| LLM generation | ✅ |
| Study modes | ✅ |
| Graceful degradation | ✅ |

**Do poprawy:**
- [ ] Deduplikacja fragmentów w retrieverze
- [ ] Domyślna kolekcja gdy nie podano

---

## Komendy

```bash
# API
uv run uvicorn src.main:app --reload

# UI
uv run streamlit run src/ui/app.py

# Ollama
ollama serve
ollama pull llama3.2
```
