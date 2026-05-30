"""Detekcja struktury dokumentu - rozdziały, sekcje, nagłówki.

Dwa tryby:
1. TOC-based (preferowany): PDF ma osadzone zakładki (get_toc) → przypisanie
   rozdziału po zakresie stron. Dokładne i niezawodne.
2. Heurystyczny (fallback): regex na nagłówkach w tekście. Działa dla ~80%
   książek technicznych, ale podatny na fałszywe trafienia (numery stron itp.).
"""

import re
from dataclasses import dataclass

from src.ingestion.base import Document

CHAPTER_PATTERNS = [
    re.compile(r"^(?:Chapter|Rozdział)\s+(\d+)[.:]\s*(.+)", re.IGNORECASE),
    re.compile(r"^(?:CHAPTER|ROZDZIAŁ)\s+(\d+)\s*$", re.IGNORECASE),
]

SECTION_PATTERNS = [
    re.compile(r"^(\d+\.\d+)\.?\s+(.+)"),
    re.compile(r"^(?:Section|Sekcja)\s+(\d+\.\d+)[.:]\s*(.+)", re.IGNORECASE),
]


@dataclass
class DetectedHeading:
    level: str
    number: str
    title: str
    line_index: int


def detect_headings(text: str) -> list[DetectedHeading]:
    """Znajdź nagłówki rozdziałów i sekcji w tekście (fallback heurystyczny)."""
    headings: list[DetectedHeading] = []
    lines = text.split("\n")

    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue

        matched = False
        for pattern in CHAPTER_PATTERNS:
            match = pattern.match(stripped)
            if match:
                groups = match.groups()
                number = groups[0]
                title = groups[1].strip() if len(groups) > 1 else ""
                headings.append(DetectedHeading("chapter", number, title, i))
                matched = True
                break

        if matched:
            continue

        for pattern in SECTION_PATTERNS:
            match = pattern.match(stripped)
            if match:
                headings.append(
                    DetectedHeading("section", match.group(1), match.group(2).strip(), i)
                )
                break

    return headings


@dataclass
class TocChapter:
    """Rozdział z TOC PDF-a."""
    number: str
    title: str
    start_page: int


def _parse_toc(toc: list[list]) -> list[TocChapter]:
    """Zamień surowy TOC z PyMuPDF na listę rozdziałów (level 1 = chapters).

    Format PyMuPDF TOC: [[level, title, page], ...]
    Level 1 = rozdziały, level 2+ = podsekcje.
    """
    chapters: list[TocChapter] = []
    num_re = re.compile(r"^(\d+(?:\.\d+)*)")

    for entry in toc:
        if len(entry) < 3:
            continue
        level, title, page = entry[0], str(entry[1]).strip(), int(entry[2])
        if level != 1 or not title:
            continue
        m = num_re.match(title)
        number = m.group(1) if m else str(len(chapters) + 1)
        chapters.append(TocChapter(number=number, title=title, start_page=page))

    return chapters


def _enrich_from_toc(
    documents: list[Document], toc_chapters: list[TocChapter]
) -> list[Document]:
    """Przypisz rozdział na podstawie zakresów stron z TOC."""
    toc_chapters.sort(key=lambda c: c.start_page)
    enriched: list[Document] = []

    for doc in documents:
        page = doc.metadata.get("page_number", 0)
        chapter = None
        for i, ch in enumerate(toc_chapters):
            end = toc_chapters[i + 1].start_page if i + 1 < len(toc_chapters) else 999999
            if ch.start_page <= page < end:
                chapter = ch
                break

        new_metadata = {**doc.metadata}
        if chapter:
            new_metadata["chapter"] = chapter.number
            new_metadata["chapter_title"] = chapter.title

        enriched.append(Document(content=doc.content, metadata=new_metadata))

    return enriched


def _enrich_by_page_ranges(
    documents: list[Document], target_segments: int = 15
) -> list[Document]:
    """Ostateczny fallback: podziel książkę na segmenty po zakresach stron.

    Gdy PDF nie ma ani TOC, ani jawnych nagłówków „Rozdział N", to jedyny
    sposób na czytelną, nawigowalną ścieżkę — zamiast jednego worka „Bez rozdziału".
    Segmenty są uczciwie nazwane „Strony X–Y" (nie udają rozdziałów semantycznych).
    """
    if not documents:
        return documents

    pages = [d.metadata.get("page_number", 0) for d in documents]
    min_p, max_p = min(pages), max(pages)
    span = max(max_p - min_p + 1, 1)
    seg_size = max(span // target_segments, 5)  # min 5 stron na segment

    enriched: list[Document] = []
    for doc in documents:
        p = doc.metadata.get("page_number", min_p)
        idx = (p - min_p) // seg_size
        start = min_p + idx * seg_size
        end = min(start + seg_size - 1, max_p)
        md = {**doc.metadata}
        md["chapter"] = str(idx + 1)
        md["chapter_title"] = f"Strony {start}–{end}"
        enriched.append(Document(content=doc.content, metadata=md))
    return enriched


def enrich_with_structure(
    documents: list[Document], *, toc: list[list] | None = None
) -> list[Document]:
    """Dodaj metadane chapter/section do dokumentów.

    Kolejność: TOC PDF-a (najlepsze) → jawne nagłówki regex → segmenty po stronach.
    """
    if toc:
        toc_chapters = _parse_toc(toc)
        if toc_chapters:
            return _enrich_from_toc(documents, toc_chapters)

    # Heurystyka regex (jawne „Rozdział N" / „Chapter N").
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

    # Jeśli heurystyka nie znalazła ŻADNEGO jawnego rozdziału — segmenty po stronach.
    detected = {d.metadata.get("chapter") for d in enriched if d.metadata.get("chapter")}
    if not detected:
        return _enrich_by_page_ranges(documents)

    return enriched
