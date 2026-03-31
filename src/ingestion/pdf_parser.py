"""Parser PDF-ów oparty na PyMuPDF (fitz).

PyMuPDF jest szybki i dobrze radzi sobie ze strukturą dokumentu.
Ekstrakcja per-strona zachowuje informację o lokalizacji tekstu,
co jest kluczowe dla cytowania źródeł ("Źródło: fizyka.pdf, s. 45").
"""

import fitz  # PyMuPDF importuje się jako "fitz" (historyczna nazwa)

from src.ingestion.base import Document


class PdfParser:
    """Parsuje PDF -> lista Document (jeden na stronę)."""

    def parse(self, file_bytes: bytes, filename: str) -> list[Document]:
        """Wyciąga tekst z każdej strony PDF-a.

        Zwraca listę Document z metadanymi: filename, page_number, total_pages.
        Pomija puste strony (np. strona tytułowa bez tekstu).
        """
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        documents: list[Document] = []

        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text().strip()

            if not text:
                continue

            documents.append(
                Document(
                    content=text,
                    metadata={
                        "filename": filename,
                        "page_number": page_num + 1,  # strony od 1, nie od 0
                        "total_pages": len(doc),
                    },
                )
            )

        doc.close()
        return documents
