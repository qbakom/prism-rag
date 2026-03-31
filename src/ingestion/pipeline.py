"""Pipeline ingestion - orkiestracja całego procesu przetwarzania pliku.

Flow: bajty -> parser -> detekcja struktury -> chunker -> gotowe chunki
                           (rozdziały/sekcje)

Pipeline jest punktem wejścia dla reszty systemu. Endpoint /ingest wywołuje
pipeline.run() i nie musi wiedzieć JAK tekst jest wyciągany ani JAK jest cięty.
"""

import logging

from src.ingestion.base import Document
from src.ingestion.chunker import DocumentChunker
from src.ingestion.pdf_parser import PdfParser
from src.ingestion.structure import enrich_with_structure

logger = logging.getLogger(__name__)

PARSERS: dict[str, type] = {
    ".pdf": PdfParser,
}


class IngestionPipeline:
    """Przetwarza plik: parsowanie -> struktura -> chunking -> lista Document."""

    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200) -> None:
        self.chunker = DocumentChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)

    def run(self, file_bytes: bytes, filename: str) -> list[Document]:
        """Przetwórz plik i zwróć chunki gotowe do embeddingu.

        Raises:
            ValueError: jeśli format pliku nie jest obsługiwany.
        """
        ext = self._get_extension(filename)
        parser_cls = PARSERS.get(ext)

        if parser_cls is None:
            supported = ", ".join(PARSERS.keys())
            raise ValueError(
                f"Nieobsługiwany format pliku: '{ext}'. Obsługiwane: {supported}"
            )

        parser = parser_cls()

        # Krok 1: Parsuj plik -> dokumenty (1 per strona)
        documents = parser.parse(file_bytes, filename)
        logger.info("Parsed '%s': %d pages", filename, len(documents))

        # Krok 2: Wykryj strukturę (rozdziały, sekcje) i wzbogać metadane
        documents = enrich_with_structure(documents)

        # Krok 3: Podziel dokumenty na chunki
        chunks = self.chunker.chunk(documents)
        logger.info("Chunked '%s': %d chunks", filename, len(chunks))

        return chunks

    @staticmethod
    def _get_extension(filename: str) -> str:
        """Wyciąga rozszerzenie pliku (np. 'notatki.pdf' -> '.pdf')."""
        dot_index = filename.rfind(".")
        if dot_index == -1:
            return ""
        return filename[dot_index:].lower()
