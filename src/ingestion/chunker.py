"""Strategie chunkingu - jak ciąć tekst na fragmenty.

DLACZEGO CHUNKING JEST WAŻNY:
- LLM ma ograniczone okno kontekstowe (np. 8k tokenów)
- Embedding model najlepiej działa na krótkich fragmentach (256-512 tokenów)
- Za duży chunk = embedding "rozmywa się", traci precyzję
- Za mały chunk = brakuje kontekstu, odpowiedź jest niepełna

OVERLAP (nakładanie się):
- Chunki nachodzą na siebie o chunk_overlap znaków
- Dzięki temu jeśli ważne zdanie jest na granicy dwóch chunków,
  przynajmniej jeden z nich zawiera je w całości
- Przykład z overlap=100:
  Chunk 1: "...koniec akapitu. Ważne twierdzenie: transformata Fo..."
  Chunk 2: "Ważne twierdzenie: transformata Fouriera przekształca..."
  → Chunk 2 ma pełne zdanie dzięki overlap!

RecursiveCharacterTextSplitter (z LangChain) to industry standard:
- Próbuje ciąć po paragrafach (\\n\\n), potem po zdaniach (. ), potem po słowach
- "Recursive" bo schodzi coraz niżej w hierarchii separatorów
"""

from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.ingestion.base import Document


class DocumentChunker:
    """Tnie dokumenty na mniejsze fragmenty z zachowaniem metadanych."""

    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200) -> None:
        """
        Args:
            chunk_size: max długość chunka w znakach (~250 tokenów dla polskiego)
            chunk_overlap: ile znaków nakłada się między sąsiednimi chunkami
        """
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            # Hierarchia separatorów - próbuje ciąć od "najładniejszego"
            separators=[
                "\n\n",  # 1. podział na paragrafy (najlepszy)
                "\n",    # 2. podział na linie
                ". ",    # 3. podział na zdania
                " ",     # 4. podział na słowa (ostateczność)
            ],
            length_function=len,
        )

    def chunk(self, documents: list[Document]) -> list[Document]:
        """Podziel listę dokumentów na mniejsze chunki.

        Każdy chunk dziedziczy metadane rodzica (filename, page_number)
        i dostaje dodatkowe: chunk_index (który to fragment z danej strony).
        """
        chunks: list[Document] = []

        for doc in documents:
            splits = self.splitter.split_text(doc.content)

            for i, split_text in enumerate(splits):
                chunks.append(
                    Document(
                        content=split_text,
                        metadata={
                            **doc.metadata,  # dziedzicz metadane (filename, page, etc.)
                            "chunk_index": i,
                        },
                    )
                )

        return chunks
