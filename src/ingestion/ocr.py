"""OCR stron-obrazów przez Gemini Vision.

PyMuPDF wyciąga tylko warstwę tekstową PDF-a. Skany i pismo odręczne nie mają
takiej warstwy → 0 tekstu. Tu renderujemy stronę na obraz i odczytujemy ją
modelem wizyjnym Gemini. Używane jako fallback dla pustych stron w parserze.
"""

import logging

from src.config import get_settings

logger = logging.getLogger(__name__)

OCR_PROMPT = (
    "Przepisz CAŁY tekst widoczny na tym obrazie strony dokumentu. "
    "Zachowaj strukturę: akapity, listy, nagłówki. "
    "Wzory matematyczne zapisz w czytelnej formie tekstowej (np. notacja typu LaTeX: "
    "x^2, sqrt(x), sum, integral). "
    "Jeśli to pismo odręczne — odczytaj najlepiej jak potrafisz. "
    "Zwróć WYŁĄCZNIE przepisany tekst, bez komentarzy, nagłówków typu 'Oto tekst:' itp."
)


class GeminiOCR:
    """OCR oparty na Gemini Vision (ten sam klucz co generacja)."""

    def __init__(self, model: str = "gemini-2.5-flash") -> None:
        self._model = model
        self._client = None

    def _get_client(self):
        if self._client is None:
            from google import genai

            api_key = get_settings().google_api_key
            if not api_key:
                raise ConnectionError("Brak GOOGLE_API_KEY — OCR niedostępny.")
            self._client = genai.Client(api_key=api_key)
        return self._client

    def available(self) -> bool:
        """OCR możliwy tylko gdy mamy klucz Gemini."""
        return bool(get_settings().google_api_key)

    def ocr_image(self, png_bytes: bytes) -> str:
        """Odczytaj tekst z obrazu PNG. Zwraca pusty string przy błędzie."""
        from google.genai import types

        try:
            client = self._get_client()
            response = client.models.generate_content(
                model=self._model,
                contents=[
                    types.Part.from_bytes(data=png_bytes, mime_type="image/png"),
                    OCR_PROMPT,
                ],
            )
            return (response.text or "").strip()
        except Exception as e:  # noqa: BLE001 - jeden błąd OCR nie może wywalić ingestu
            logger.warning("OCR strony nie powiódł się: %s", e)
            return ""
