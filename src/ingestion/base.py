"""Abstrakcje dla pipeline'u ingestion.

Protocol (z typing) to pythonowy "interfejs" - definiuje KONTRAKT:
"każdy parser dokumentów MUSI mieć metodę parse() która zwraca listę Document".

Dzięki temu:
- pdf_parser.py implementuje Protocol dla PDF-ów
- jutro markdown_parser.py implementuje ten sam Protocol dla .md
- reszta systemu nie obchodzi JAKI parser - ważne że ma parse()

To jest "duck typing z typami" - jeśli klasa ma metodę parse() z dobrą sygnaturą,
to spełnia Protocol. Nie trzeba dziedziczyć (jak w Javie z implements).
"""

from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class Document:
    """Pojedynczy fragment tekstu z metadanymi.

    To jest PODSTAWOWA jednostka danych w całym systemie.
    Chunk tekstu + informacja skąd pochodzi = możliwość cytowania źródeł.
    """

    content: str
    metadata: dict[str, str | int | float] = field(default_factory=dict)


class DocumentParser(Protocol):
    """Kontrakt: każdy parser musi umieć zamienić surowe bajty na listę Document."""

    def parse(self, file_bytes: bytes, filename: str) -> list[Document]:
        """Parsuj plik i zwróć listę dokumentów (1 dokument = 1 strona/sekcja)."""
        ...
