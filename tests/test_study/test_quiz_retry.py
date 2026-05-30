"""Testy ponawiania generowania quizu przy niepoprawnym JSON z LLM."""

from unittest.mock import MagicMock

from src.study.engine import QUIZ_MAX_ATTEMPTS, StudyEngine

_VALID = (
    '{"questions": [{"question": "Co to FFT?", '
    '"options": ["a", "b", "c", "d"], "correct_index": 0, "explanation": "bo"}]}'
)


def _engine(generate_outputs: list[str]) -> StudyEngine:
    generator = MagicMock()
    generator.is_available.return_value = True
    generator.generate.side_effect = generate_outputs

    store = MagicMock()
    store.read_chapter.return_value = [{"content": "Materiał o FFT.", "filename": "x"}]

    return StudyEngine(retriever=MagicMock(), generator=generator, store=store)


class TestQuizRetry:
    def test_succeeds_first_try(self):
        engine = _engine([_VALID])
        out = engine.quiz(collection="c", chapter="1")
        assert len(out) == 1
        assert engine._generator.generate.call_count == 1

    def test_retries_then_succeeds(self):
        # Pierwsza odpowiedź to śmieci, druga poprawna.
        engine = _engine(["nie-json", _VALID])
        out = engine.quiz(collection="c", chapter="1")
        assert len(out) == 1
        assert engine._generator.generate.call_count == 2

    def test_gives_up_after_max_attempts(self):
        engine = _engine(["zły"] * QUIZ_MAX_ATTEMPTS)
        out = engine.quiz(collection="c", chapter="1")
        assert out == []
        assert engine._generator.generate.call_count == QUIZ_MAX_ATTEMPTS
