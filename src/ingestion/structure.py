"""Detekcja struktury dokumentu - rozdziały, sekcje, nagłówki.

Książka techniczna to nie "worek tekstu". Ma hierarchię:
  Książka -> Część -> Rozdział -> Sekcja -> Podsekcja

Bez tej informacji RAG nie umie odpowiedzieć na "przepytaj mnie z rozdziału 3".

Podejście: szukamy wzorców nagłówków w tekście (regex).
Nie jest to 100% dokładne, ale dla 80% książek technicznych działa dobrze.
Ulepszenia na przyszłość: font size z PyMuPDF, Marker (PDF->Markdown).
"""

import re
from dataclasses import dataclass

from src.ingestion.base import Document

# Wzorce nagłówków typowe dla książek technicznych (PL + EN)
CHAPTER_PATTERNS = [
    # "Chapter 1: Title" / "Chapter 1. Title"
    re.compile(r"^(?:Chapter|Rozdział)\s+(\d+)[.:]\s*(.+)", re.IGNORECASE),
    # "CHAPTER 1" (sam numer, tytuł w kolejnej linii)
    re.compile(r"^(?:CHAPTER|ROZDZIAŁ)\s+(\d+)\s*$", re.IGNORECASE),
]

SECTION_PATTERNS = [
    # "1.2 Title" / "1.2. Title"
    re.compile(r"^(\d+\.\d+)\.?\s+(.+)"),
    # "Section 1.2: Title"
    re.compile(r"^(?:Section|Sekcja)\s+(\d+\.\d+)[.:]\s*(.+)", re.IGNORECASE),
]


@dataclass
class DetectedHeading:
    """Wykryty nagłówek z pozycją w tekście."""

    level: str  # "chapter" | "section"
    number: str  # "3" | "3.2"
    title: str  # "Transformata Fouriera"
    line_index: int  # która linia w dokumencie


def detect_headings(text: str) -> list[DetectedHeading]:
    """Znajdź nagłówki rozdziałów i sekcji w tekście."""
    headings: list[DetectedHeading] = []
    lines = text.split("\n")

    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue

        # Sprawdź patterny chapter
        matched = False
        for pattern in CHAPTER_PATTERNS:
            match = pattern.match(stripped)
            if match:
                groups = match.groups()
                number = groups[0]
                title = groups[1].strip() if len(groups) > 1 else ""
                headings.append(
                    DetectedHeading("chapter", number, title, i)
                )
                matched = True
                break

        if matched:
            continue

        # Wzorzec: sam numer (1-20) na linii + tytuł (zaczyna się literą) na następnej
        # Typowy format w książkach akademickich: "3\nClassification"
        # Warunki: numer 1-20, pierwsza linia strony, tytuł zaczyna się literą
        # (wyklucza etykiety z wykresów typu "0\n20\n40\n60")
        if re.match(r"^\d{1,2}$", stripped) and 1 <= int(stripped) <= 20 and i < 3:
            next_title = ""
            for j in range(i + 1, min(i + 3, len(lines))):
                candidate = lines[j].strip()
                if candidate:
                    next_title = candidate
                    break
            # Tytuł musi zaczynać się literą - filtruje etykiety osi wykresów
            if next_title and next_title[0].isalpha():
                headings.append(
                    DetectedHeading("chapter", stripped, next_title, i)
                )
            continue

        # Sprawdź patterny section
        for pattern in SECTION_PATTERNS:
            match = pattern.match(stripped)
            if match:
                headings.append(
                    DetectedHeading("section", match.group(1), match.group(2).strip(), i)
                )
                break

    return headings


def enrich_with_structure(documents: list[Document]) -> list[Document]:
    """Dodaj metadane chapter/section do dokumentów na podstawie wykrytych nagłówków.

    Analizuje tekst każdego dokumentu (strony) i propaguje
    aktualny rozdział/sekcję do metadanych.
    Stan (current_chapter) przenosi się między stronami -
    bo nagłówek rozdziału jest na jednej stronie, a treść na kolejnych.
    """
    current_chapter: str = ""
    current_chapter_title: str = ""
    current_section: str = ""
    current_section_title: str = ""

    enriched: list[Document] = []

    for doc in documents:
        headings = detect_headings(doc.content)

        for heading in headings:
            if heading.level == "chapter":
                current_chapter = heading.number
                current_chapter_title = heading.title
                current_section = ""
                current_section_title = ""
            elif heading.level == "section":
                current_section = heading.number
                current_section_title = heading.title

        new_metadata = {**doc.metadata}
        if current_chapter:
            new_metadata["chapter"] = current_chapter
            new_metadata["chapter_title"] = current_chapter_title
        if current_section:
            new_metadata["section"] = current_section
            new_metadata["section_title"] = current_section_title

        enriched.append(Document(content=doc.content, metadata=new_metadata))

    return enriched
