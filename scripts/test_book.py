"""Skrypt do testowania PRISM na prawdziwej książce.

Uruchomienie: uv run python scripts/test_book.py
Wymaga: Qdrant (docker compose up qdrant -d)
Opcjonalnie: Ollama (ollama serve) - bez tego działa w trybie fallback
"""

import sys
import time
from pathlib import Path

# Dodaj root projektu do path
sys.path.insert(0, str(Path(__file__).parent.parent))

from qdrant_client import QdrantClient

from src.embeddings.embedder import Embedder
from src.ingestion.pipeline import IngestionPipeline
from src.rag.generator import Generator
from src.rag.retriever import Retriever
from src.study.engine import StudyEngine
from src.study.modes import StudyMode
from src.vectorstore.qdrant_store import QdrantStore

BOOK_PATH = "/home/qba/studia/books/fairmlbook.pdf"
COLLECTION = "fairml"
# In-memory Qdrant - nie potrzeba Dockera do testu
USE_IN_MEMORY = True


def main():
    print("=" * 60)
    print("PRISM - Test na prawdziwej książce")
    print("=" * 60)

    # --- 1. Embedder ---
    print("\n[1/4] Ładowanie modelu embeddingów...")
    t = time.time()
    embedder = Embedder()
    print(f"  Model: {embedder._model_name}")
    print(f"  Wymiar: {embedder.dimension}")
    print(f"  Czas: {time.time() - t:.1f}s")

    # --- 2. Ingestion ---
    print(f"\n[2/4] Ingestion: {BOOK_PATH}")
    t = time.time()

    with open(BOOK_PATH, "rb") as f:
        file_bytes = f.read()
    print(f"  Rozmiar pliku: {len(file_bytes) / 1024 / 1024:.1f} MB")

    pipeline = IngestionPipeline(chunk_size=1500, chunk_overlap=200)
    chunks = pipeline.run(file_bytes, "fairmlbook.pdf")
    print(f"  Chunków: {len(chunks)}")
    print(f"  Czas parsowania: {time.time() - t:.1f}s")

    # Pokaż statystyki rozdziałów
    chapters = {}
    for chunk in chunks:
        ch = chunk.metadata.get("chapter", "brak")
        chapters[ch] = chapters.get(ch, 0) + 1
    print(f"  Rozdziały znalezione: {dict(sorted(chapters.items()))}")

    # Pokaż sample chunka
    sample = chunks[10] if len(chunks) > 10 else chunks[0]
    print(f"\n  Przykładowy chunk (#{10}):")
    print(f"    Metadata: {sample.metadata}")
    print(f"    Tekst: {sample.content[:200]}...")

    # --- 3. Embedding + Qdrant ---
    print(f"\n[3/4] Embedding {len(chunks)} chunków i zapis do Qdrant...")
    t = time.time()

    if USE_IN_MEMORY:
        client = QdrantClient(":memory:")
        store = QdrantStore(client=client, embedding_dimension=embedder.dimension)
    else:
        store = QdrantStore(embedding_dimension=embedder.dimension)

    # Sprawdź czy kolekcja już istnieje
    if COLLECTION in store.list_collections():
        existing = store.collection_count(COLLECTION)
        print(f"  Kolekcja '{COLLECTION}' już istnieje ({existing} punktów). Usuwam...")
        store.delete_collection(COLLECTION)

    # Embed w batchach (pamięć)
    BATCH_SIZE = 64
    total = 0
    for i in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[i : i + BATCH_SIZE]
        texts = [c.content for c in batch]
        vectors = embedder.embed(texts)
        store.add_documents(COLLECTION, batch, vectors)
        total += len(batch)
        print(f"  Batch {i // BATCH_SIZE + 1}: {total}/{len(chunks)} chunków")

    print(f"  Czas: {time.time() - t:.1f}s")
    print(f"  Punktów w Qdrant: {store.collection_count(COLLECTION)}")

    # --- 4. Query + Study ---
    print("\n[4/4] Testowanie query i study modes...")

    retriever = Retriever(embedder=embedder, store=store)
    generator = Generator()
    study_engine = StudyEngine(retriever=retriever, generator=generator)

    print(f"\n  Ollama dostępna: {generator.is_available()}")

    # Test queries
    queries = [
        ("What is fairness in machine learning?", None, StudyMode.EXPLAIN),
        ("Quiz me on classification parity", None, StudyMode.QUIZ),
        (
            "How does individual fairness relate to group fairness?",
            None,
            StudyMode.CONNECT,
        ),
    ]

    for question, chapter, mode in queries:
        print(f"\n{'─' * 50}")
        print(f"  Mode: {mode.value}")
        print(f"  Q: {question}")
        if chapter:
            print(f"  Chapter filter: {chapter}")

        result = study_engine.study(
            question=question,
            collection=COLLECTION,
            mode=mode,
            chapter=chapter,
            top_k=5,
        )

        print(f"  Sources: {len(result.sources)} fragments")
        for s in result.sources[:3]:
            src_info = f"    - {s.filename}, s.{s.page_number}"
            if s.chapter:
                src_info += f" (ch.{s.chapter})"
            src_info += f" [score: {s.score:.3f}]"
            print(src_info)

        print(f"  Answer ({len(result.content)} chars):")
        # Pokaż pierwsze 500 znaków odpowiedzi
        preview = result.content[:500]
        for line in preview.split("\n"):
            print(f"    {line}")
        if len(result.content) > 500:
            print("    ...")

    print(f"\n{'=' * 60}")
    print("DONE. System działa na prawdziwej książce!")
    print(f"Kolekcje w Qdrant: {store.list_collections()}")


if __name__ == "__main__":
    main()
