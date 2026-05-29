"""G w RAG - Generation. Obsługuje wiele backendów LLM.

Backendy:
- gemini: Google Gemini API (GOOGLE_API_KEY) - szybki, tani
- ollama: Lokalny LLM (localhost:11434) - prywatny, wymaga GPU/CPU

Wybór backendu przez env LLM_BACKEND=gemini|ollama (default: gemini)
"""

import logging
from abc import ABC, abstractmethod

import httpx
from dotenv import load_dotenv

from src.config import get_settings

load_dotenv()

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 120.0


class BaseGenerator(ABC):
    """Abstrakcyjna klasa dla generatorów LLM."""

    @abstractmethod
    def generate(self, messages: list[dict[str, str]]) -> str:
        """Generuj odpowiedź na podstawie messages."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Sprawdź czy backend jest dostępny."""
        pass


class GeminiGenerator(BaseGenerator):
    """Generator używający Google Gemini API."""

    def __init__(self, model: str = "gemini-2.5-flash") -> None:
        self._model = model
        self._client = None

    def _get_client(self):
        """Lazy init klienta Gemini (wymaga GOOGLE_API_KEY)."""
        if self._client is None:
            from google import genai

            from src.config import get_settings

            api_key = get_settings().google_api_key
            if not api_key:
                raise ConnectionError(
                    "Brak GOOGLE_API_KEY. Ustaw w .env lub eksportuj:\n"
                    "export GOOGLE_API_KEY=twoj_klucz"
                )
            self._client = genai.Client(api_key=api_key)
        return self._client

    def generate(self, messages: list[dict[str, str]]) -> str:
        """Wyślij wiadomości do Gemini i zwróć odpowiedź."""
        client = self._get_client()

        # Konwersja z OpenAI format na Gemini format
        # Gemini nie ma "system" role - łączymy z pierwszym user message
        system_content = ""
        user_content = ""

        for msg in messages:
            if msg["role"] == "system":
                system_content = msg["content"]
            elif msg["role"] == "user":
                user_content = msg["content"]

        # Łączymy system prompt z pytaniem
        full_prompt = f"{system_content}\n\n{user_content}" if system_content else user_content

        response = client.models.generate_content(
            model=self._model,
            contents=full_prompt,
        )
        return response.text

    def is_available(self) -> bool:
        """Sprawdź czy Gemini API jest dostępne."""
        try:
            self._get_client()
            return True
        except Exception:
            return False


class OllamaGenerator(BaseGenerator):
    """Generator używający lokalnego Ollama."""

    def __init__(
        self,
        base_url: str | None = None,
        model: str = "llama3.2",
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        self._base_url = base_url or get_settings().ollama_base_url
        self._model = model
        self._timeout = timeout

    def generate(self, messages: list[dict[str, str]]) -> str:
        """Wyślij wiadomości do Ollama i zwróć odpowiedź."""
        payload = {
            "model": self._model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": 0.3,
                "num_ctx": 8192,
            },
        }

        try:
            response = httpx.post(
                f"{self._base_url}/api/chat",
                json=payload,
                timeout=self._timeout,
            )
        except httpx.ConnectError as e:
            raise ConnectionError(
                f"Nie mogę połączyć się z Ollama ({self._base_url}). "
                "Upewnij się, że Ollama jest uruchomiona: `ollama serve`"
            ) from e

        if response.status_code != 200:
            raise RuntimeError(f"Ollama error {response.status_code}: {response.text}")

        return response.json()["message"]["content"]

    def is_available(self) -> bool:
        """Sprawdź czy Ollama jest uruchomiona i model jest dostępny."""
        try:
            resp = httpx.get(f"{self._base_url}/api/tags", timeout=5.0)
            if resp.status_code != 200:
                return False
            models = [m["name"] for m in resp.json().get("models", [])]
            return any(self._model in m for m in models)
        except httpx.ConnectError:
            return False


class Generator(BaseGenerator):
    """Fabryka generatorów - wybiera backend na podstawie config."""

    def __init__(self) -> None:
        from src.config import get_settings

        backend = get_settings().llm_backend.lower()

        if backend == "gemini":
            self._impl = GeminiGenerator()
            logger.info("Używam Gemini API jako backend LLM")
        elif backend == "ollama":
            self._impl = OllamaGenerator()
            logger.info("Używam Ollama jako backend LLM")
        else:
            raise ValueError(f"Nieznany backend: {backend}. Użyj: gemini|ollama")

    def generate(self, messages: list[dict[str, str]]) -> str:
        return self._impl.generate(messages)

    def is_available(self) -> bool:
        return self._impl.is_available()

    @property
    def model(self) -> str:
        """Nazwa aktywnego modelu (deleguje do wybranej implementacji backendu)."""
        return self._impl._model
