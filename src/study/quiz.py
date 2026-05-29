"""Generowanie klikalnych pytań ABCD (multiple choice) jako JSON.

Dlaczego ABCD a nie wolny tekst?
- Zero pisania (klik) = low friction, zgodnie z wizją trybu nauki.
- Ocena za darmo: LLM generujący pytanie ZNA poprawną odpowiedź,
  więc nie potrzebujemy semantycznej oceny odpowiedzi użytkownika.

LLM zwraca tekst, więc prosimy o ścisły JSON i parsujemy go defensywnie
(modele lubią owijać JSON w ```json ... ``` albo dodać komentarz).
"""

import json
import logging
import re

logger = logging.getLogger(__name__)


def build_quiz_messages(material: str, num_questions: int) -> list[dict[str, str]]:
    """Zbuduj prompt wymuszający quiz w formacie JSON."""
    system_prompt = (
        "Jesteś nauczycielem tworzącym pytania wielokrotnego wyboru (ABCD) "
        "sprawdzające ZROZUMIENIE materiału.\n\n"
        "ZASADY:\n"
        "1. Pytania wyłącznie na podstawie dostarczonego materiału.\n"
        "2. Dokładnie 4 opcje odpowiedzi, tylko jedna poprawna.\n"
        "3. Dystraktory (błędne opcje) muszą być wiarygodne, nie absurdalne.\n"
        "4. Krótkie wyjaśnienie dlaczego poprawna odpowiedź jest poprawna.\n"
        "5. Odpowiadaj w języku materiału.\n"
        "6. Zwróć WYŁĄCZNIE poprawny JSON, bez markdown, bez komentarzy.\n\n"
        "FORMAT (dokładnie taki):\n"
        '{"questions": [{"question": "...", "options": ["...", "...", "...", "..."], '
        '"correct_index": 0, "explanation": "..."}]}'
    )
    user_content = (
        f"Stwórz {num_questions} pytań ABCD na podstawie poniższego materiału.\n\n"
        f"MATERIAŁ:\n{material}"
    )
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ]


def parse_quiz_json(raw: str) -> list[dict]:
    """Wyłuskaj i zwaliduj listę pytań z (potencjalnie brudnej) odpowiedzi LLM."""
    if not raw:
        return []

    # Zdejmij ewentualne ```json ... ``` i wytnij pierwszy obiekt {...}
    cleaned = re.sub(r"```(?:json)?", "", raw).strip()
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if not match:
        logger.warning("Quiz JSON nie znaleziony w odpowiedzi LLM")
        return []

    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        logger.warning("Nie udało się sparsować quiz JSON")
        return []

    questions = data.get("questions", []) if isinstance(data, dict) else []
    valid: list[dict] = []
    for q in questions:
        if not isinstance(q, dict):
            continue
        options = q.get("options")
        idx = q.get("correct_index")
        if (
            isinstance(q.get("question"), str)
            and isinstance(options, list)
            and len(options) >= 2
            and isinstance(idx, int)
            and 0 <= idx < len(options)
        ):
            valid.append(
                {
                    "question": q["question"],
                    "options": [str(o) for o in options],
                    "correct_index": idx,
                    "explanation": str(q.get("explanation", "")),
                }
            )
    return valid
