"""Testy pipeline'u ingestion.

Tworzymy testowy PDF w pamięci (przez PyMuPDF) zamiast trzymać pliki testowe.
Dzięki temu testy są self-contained i nie zależą od zewnętrznych plików.
"""

import fitz  # PyMuPDF
import pytest

from src.ingestion.base import Document
from src.ingestion.chunker import DocumentChunker
from src.ingestion.pdf_parser import PdfParser
from src.ingestion.pipeline import IngestionPipeline


def make_test_pdf(pages: list[str]) -> bytes:
    """Helper: tworzy PDF w pamięci z podanym tekstem na stronach."""
    doc = fitz.open()
    for text in pages:
        page = doc.new_page()
        page.insert_text((72, 72), text)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


class TestPdfParser:
    def test_extracts_text_from_pages(self):
        pdf = make_test_pdf(["Strona pierwsza", "Strona druga"])
        parser = PdfParser()

        docs = parser.parse(pdf, "test.pdf")

        assert len(docs) == 2
        assert "Strona pierwsza" in docs[0].content
        assert docs[0].metadata["filename"] == "test.pdf"
        assert docs[0].metadata["page_number"] == 1
        assert docs[1].metadata["page_number"] == 2

    def test_skips_empty_pages(self):
        """Puste strony (np. tytułowa) nie powinny tworzyć dokumentów."""
        doc = fitz.open()
        doc.new_page()  # pusta strona
        page = doc.new_page()
        page.insert_text((72, 72), "Treść")
        pdf = doc.tobytes()
        doc.close()

        parser = PdfParser()
        docs = parser.parse(pdf, "test.pdf")

        assert len(docs) == 1
        assert docs[0].metadata["page_number"] == 2


class TestChunker:
    def test_splits_long_text(self):
        """Długi tekst powinien być podzielony na chunki."""
        long_text = "To jest zdanie testowe. " * 100  # ~2400 znaków
        docs = [Document(content=long_text, metadata={"filename": "test.pdf"})]

        chunker = DocumentChunker(chunk_size=500, chunk_overlap=50)
        chunks = chunker.chunk(docs)

        assert len(chunks) > 1
        # Każdy chunk powinien dziedziczyć metadane
        for chunk in chunks:
            assert chunk.metadata["filename"] == "test.pdf"
            assert "chunk_index" in chunk.metadata

    def test_short_text_stays_as_one_chunk(self):
        """Krótki tekst nie powinien być dzielony."""
        docs = [Document(content="Krótki tekst.", metadata={"filename": "test.pdf"})]

        chunker = DocumentChunker(chunk_size=1000)
        chunks = chunker.chunk(docs)

        assert len(chunks) == 1


class TestPipeline:
    def test_full_pipeline_pdf(self):
        """End-to-end: PDF -> parse -> chunk -> lista Document z metadanymi."""
        pdf = make_test_pdf(["Treść pierwszej strony z wykładu o fizyce."])
        pipeline = IngestionPipeline()

        chunks = pipeline.run(pdf, "fizyka.pdf")

        assert len(chunks) >= 1
        assert chunks[0].metadata["filename"] == "fizyka.pdf"
        assert "fizyce" in chunks[0].content or "fizyk" in chunks[0].content

    def test_unsupported_format_raises(self):
        """Nieobsługiwany format -> ValueError z sensownym komunikatem."""
        pipeline = IngestionPipeline()

        with pytest.raises(ValueError, match="Nieobsługiwany format"):
            pipeline.run(b"not a pdf", "notes.docx")
