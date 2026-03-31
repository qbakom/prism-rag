"""A w RAG - Augmented. Budowanie promptu z kontekstem.

Prompt engineering to nie byle co - to JEDYNY sposób kontroli nad LLM.
Zły prompt = halucynacje, brak cytowań, odpowiedzi "nie wiem".
Dobry prompt = grounded odpowiedzi ze źródłami.

Kluczowe techniki użyte tutaj:
1. System prompt definiuje ROLĘ i OGRANICZENIA modelu
2. Kontekst wstrzykiwany przed pytaniem (LLM "widzi" fragmenty jako swój input)
3. Instrukcja cytowania źródeł - bez tego LLM wymyśla odpowiedzi z powietrza
"""

from src.rag.retriever import RetrievedChunk

SYSTEM_PROMPT = (
    "Jesteś PRISM - prywatnym asystentem wiedzy. "
    "Odpowiadasz WYŁĄCZNIE na podstawie dostarczonych fragmentów kontekstu.\n\n"
    "ZASADY:\n"
    "1. Odpowiadaj w języku pytania (polski/angielski).\n"
    "2. Jeśli kontekst nie zawiera odpowiedzi, powiedz: "
    '"Nie znalazłem odpowiedzi w dostępnych materiałach."\n'
    "3. NIE wymyślaj informacji spoza kontekstu - to jest krytyczne.\n"
    "4. Przy każdym stwierdzeniu podaj źródło w formacie [plik, s. X].\n"
    "5. Jeśli fragmenty są sprzeczne, zaznacz to.\n"
    "6. Odpowiadaj zwięźle ale kompletnie."
)


def build_context(chunks: list[RetrievedChunk]) -> str:
    """Formatuj znalezione fragmenty jako kontekst dla LLM.

    Każdy fragment ma nagłówek z metadanymi, żeby LLM mógł cytować źródło.
    Numerujemy fragmenty, bo pomaga to LLM w odwoływaniu się do nich.
    """
    if not chunks:
        return "Brak dostępnych fragmentów kontekstu."

    parts: list[str] = []
    for i, chunk in enumerate(chunks, 1):
        header = f"[Fragment {i}] Źródło: {chunk.filename}"
        if chunk.page_number is not None:
            header += f", s. {chunk.page_number}"
        parts.append(f"{header}\n{chunk.content}")

    return "\n\n---\n\n".join(parts)


def build_messages(
    question: str,
    chunks: list[RetrievedChunk],
) -> list[dict[str, str]]:
    """Zbuduj listę wiadomości w formacie chat (Ollama /api/chat).

    Struktura:
    1. system - rola i zasady
    2. user - kontekst + pytanie

    Kontekst idzie PRZED pytaniem, bo LLM zwraca większą uwagę
    na początek i koniec promptu (tzw. "lost in the middle" problem).
    """
    context = build_context(chunks)

    user_message = f"""KONTEKST (fragmenty z bazy wiedzy):
{context}

PYTANIE: {question}"""

    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_message},
    ]
