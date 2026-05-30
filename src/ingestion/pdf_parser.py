"""Parser PDF-ów oparty na PyMuPDF (fitz).

PyMuPDF jest szybki i dobrze radzi sobie ze strukturą dokumentu.
Ekstrakcja per-strona zachowuje informację o lokalizacji tekstu,
co jest kluczowe dla cytowania źródeł ("Źródło: fizyka.pdf, s. 45").
"""

import re

import fitz  # PyMuPDF importuje się jako "fitz" (historyczna nazwa)

from src.ingestion.base import Document

# Symbol font → Unicode. PDF-y z fontem symbolicznym (np. podręczniki z wzorami)
# kodują =, greckie litery i operatory jako Private Use Area (\uF0xx).
# PyMuPDF je zwraca dosłownie → wyświetlają się jako □.
_SYMBOL_MAP: dict[int, str] = {
    0xF020: " ", 0xF021: "!", 0xF023: "#", 0xF025: "%", 0xF026: "&",
    0xF028: "(", 0xF029: ")", 0xF02A: "*", 0xF02B: "+", 0xF02C: ",",
    0xF02D: "−", 0xF02E: ".", 0xF02F: "/",
    0xF030: "0", 0xF031: "1", 0xF032: "2", 0xF033: "3", 0xF034: "4",
    0xF035: "5", 0xF036: "6", 0xF037: "7", 0xF038: "8", 0xF039: "9",
    0xF03A: ":", 0xF03B: ";", 0xF03C: "<", 0xF03D: "=", 0xF03E: ">",
    0xF041: "Α", 0xF042: "Β", 0xF043: "Χ", 0xF044: "Δ", 0xF045: "Ε",
    0xF046: "Φ", 0xF047: "Γ", 0xF048: "Η", 0xF049: "Ι", 0xF04B: "Κ",
    0xF04C: "Λ", 0xF04D: "Μ", 0xF04E: "Ν", 0xF04F: "Ο", 0xF050: "Π",
    0xF051: "Θ", 0xF052: "Ρ", 0xF053: "Σ", 0xF054: "Τ", 0xF055: "Υ",
    0xF057: "Ω", 0xF058: "Ξ", 0xF059: "Ψ", 0xF05A: "Ζ",
    0xF05B: "[", 0xF05D: "]",
    0xF061: "α", 0xF062: "β", 0xF063: "χ", 0xF064: "δ", 0xF065: "ε",
    0xF066: "φ", 0xF067: "γ", 0xF068: "η", 0xF069: "ι", 0xF06A: "ϕ",
    0xF06B: "κ", 0xF06C: "λ", 0xF06D: "μ", 0xF06E: "ν", 0xF06F: "ο",
    0xF070: "π", 0xF071: "θ", 0xF072: "ρ", 0xF073: "σ", 0xF074: "τ",
    0xF075: "υ", 0xF076: "ϖ", 0xF077: "ω", 0xF078: "ξ", 0xF079: "ψ",
    0xF07A: "ζ", 0xF07B: "{", 0xF07C: "|", 0xF07D: "}",
    0xF0A3: "≤", 0xF0A5: "∞", 0xF0A7: "♣", 0xF0A8: "♦",
    0xF0B1: "±", 0xF0B3: "≥", 0xF0B4: "×", 0xF0B5: "∝",
    0xF0B6: "∂", 0xF0B7: "•", 0xF0B8: "÷", 0xF0B9: "≠",
    0xF0BA: "≡", 0xF0BB: "≈",
    0xF0D5: "∏", 0xF0D6: "√", 0xF0D7: "·", 0xF0D8: "¬",
    0xF0D9: "∧", 0xF0DA: "∨",
    0xF0E5: "∑", 0xF0F2: "∫",
}
_PUA_TRANS = str.maketrans(_SYMBOL_MAP)
_PUA_RE = re.compile(r"[\uE000-\uF8FF]")


def _clean_pua(text: str) -> str:
    """Zamień PUA (Symbol font) na Unicode, usuń resztę nierozpoznanych."""
    text = text.translate(_PUA_TRANS)
    return _PUA_RE.sub("", text)


class PdfParser:
    """Parsuje PDF -> lista Document (jeden na stronę) + TOC."""

    def __init__(self) -> None:
        self.toc: list[list] = []

    def parse(self, file_bytes: bytes, filename: str) -> list[Document]:
        """Wyciąga tekst z każdej strony PDF-a.

        Zwraca listę Document z metadanymi: filename, page_number, total_pages.
        Pomija puste strony (np. strona tytułowa bez tekstu).
        Mapuje symbole PUA (□) na Unicode (=, α, Σ…).
        """
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        self.toc = doc.get_toc()
        documents: list[Document] = []

        for page_num in range(len(doc)):
            page = doc[page_num]
            text = _clean_pua(page.get_text()).strip()

            if not text:
                continue

            documents.append(
                Document(
                    content=text,
                    metadata={
                        "filename": filename,
                        "page_number": page_num + 1,
                        "total_pages": len(doc),
                    },
                )
            )

        doc.close()
        return documents
