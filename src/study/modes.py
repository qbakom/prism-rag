"""Tryby nauki - specjalizowane strategie promptowania.

Każdy tryb to inny CEL interakcji z materiałem:
- QUIZ: active recall (testowanie się) - 2-3x skuteczniejsze niż ponowne czytanie
- EXPLAIN: zrozumienie konceptu - LLM tłumaczy fragment książki prościej
- CONNECT: łączenie konceptów - "jak X łączy się z Y?" (budowanie mental model)

Każdy tryb ma swój system prompt, bo LLM potrzebuje innej instrukcji
w zależności od tego co chcemy osiągnąć.
"""

from enum import StrEnum

from src.rag.retriever import RetrievedChunk


class StudyMode(StrEnum):
    QUIZ = "quiz"
    EXPLAIN = "explain"
    CONNECT = "connect"


STUDY_PROMPTS: dict[StudyMode, str] = {
    StudyMode.QUIZ: (
        "Jesteś nauczycielem tworzącym quiz sprawdzający zrozumienie materiału.\n\n"
        "ZASADY:\n"
        "1. Wygeneruj pytania TYLKO na podstawie dostarczonych fragmentów.\n"
        "2. Pytania powinny testować ZROZUMIENIE, nie zapamiętywanie faktów.\n"
        "3. Mieszaj typy pytań: otwarte, porównawcze, 'co by się stało gdyby...'.\n"
        "4. Przy każdym pytaniu podaj w nawiasie źródło [plik, s. X].\n"
        "5. Po pytaniach dodaj sekcję '## Odpowiedzi' z krótkimi wyjaśnieniami.\n"
        "6. Odpowiadaj w języku pytania."
    ),
    StudyMode.EXPLAIN: (
        "Jesteś cierpliwym tutorem wyjaśniającym trudne koncepty.\n\n"
        "ZASADY:\n"
        "1. Wyjaśniaj na podstawie dostarczonych fragmentów.\n"
        "2. Zacznij od intuicji / analogii, potem szczegóły techniczne.\n"
        "3. Jeśli koncept wymaga wiedzy wstępnej, zaznacz co trzeba wiedzieć.\n"
        "4. Używaj przykładów z kontekstu.\n"
        "5. Na końcu podsumuj w 2-3 zdaniach (TL;DR).\n"
        "6. Podawaj źródła [plik, s. X]."
    ),
    StudyMode.CONNECT: (
        "Jesteś ekspertem od łączenia konceptów i budowania mental modeli.\n\n"
        "ZASADY:\n"
        "1. Przeanalizuj dostarczone fragmenty i znajdź POWIĄZANIA między konceptami.\n"
        "2. Wyjaśnij: co łączy te koncepty? Gdzie się uzupełniają? Gdzie się różnią?\n"
        "3. Jeśli jeden koncept jest fundamentem drugiego, pokaż tę hierarchię.\n"
        "4. Użyj analogii do wyjaśnienia relacji.\n"
        "5. Na końcu podsumuj relację w 1-2 zdaniach.\n"
        "6. Podawaj źródła [plik, s. X]."
    ),
}


def build_study_messages(
    question: str,
    chunks: list[RetrievedChunk],
    mode: StudyMode,
) -> list[dict[str, str]]:
    """Zbuduj wiadomości dla danego trybu nauki."""
    system_prompt = STUDY_PROMPTS[mode]

    # Formatuj kontekst
    context_parts: list[str] = []
    for i, chunk in enumerate(chunks, 1):
        header = f"[Fragment {i}] Źródło: {chunk.filename}"
        if chunk.page_number is not None:
            header += f", s. {chunk.page_number}"
        if chunk.chapter_title:
            header += f" | Rozdział: {chunk.chapter_title}"
        context_parts.append(f"{header}\n{chunk.content}")

    context = "\n\n---\n\n".join(context_parts)

    # Prefix pytania zależny od trybu
    mode_prefix = {
        StudyMode.QUIZ: "Wygeneruj quiz na podstawie poniższego materiału.\n\n",
        StudyMode.EXPLAIN: "",
        StudyMode.CONNECT: "",
    }

    user_content = (
        f"{mode_prefix[mode]}"
        f"MATERIAŁ:\n{context}\n\n"
        f"PYTANIE: {question}"
    )

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ]
