"""Testy modułu study - detekcja struktury, tryby nauki, API."""

from unittest.mock import patch

import fitz

from src.ingestion.base import Document
from src.ingestion.structure import detect_headings, enrich_with_structure
from src.rag.generator import Generator
from src.rag.retriever import Retriever
from src.study.engine import StudyEngine
from src.study.modes import StudyMode, build_study_messages

# --- Testy detekcji struktury ---


class TestStructureDetection:
    def test_detect_chapter_english(self):
        text = "Chapter 3: Fourier Transform\nSome content here."
        headings = detect_headings(text)
        assert len(headings) == 1
        assert headings[0].level == "chapter"
        assert headings[0].number == "3"
        assert "Fourier" in headings[0].title

    def test_detect_chapter_polish(self):
        text = "Rozdział 5: Analiza sygnałów\nTreść rozdziału."
        headings = detect_headings(text)
        assert len(headings) == 1
        assert headings[0].number == "5"

    def test_detect_section(self):
        text = "3.2 Discrete Fourier Transform\nThe DFT is defined as..."
        headings = detect_headings(text)
        assert len(headings) == 1
        assert headings[0].level == "section"
        assert headings[0].number == "3.2"

    def test_bare_number_not_detected_as_chapter(self):
        """Gołe numery (np. numer strony) NIE powinny być rozdziałami — to false-positives."""
        text = "3\nClassification\nThe goal of classification is..."
        headings = detect_headings(text)
        assert len(headings) == 0

    def test_enrich_propagates_chapter(self):
        """Rozdział wykryty na stronie 1 powinien propagować się na stronę 2."""
        docs = [
            Document(
                content="Chapter 3: Signals\nIntroduction to signals.",
                metadata={"page_number": 1},
            ),
            Document(
                content="Signals can be continuous or discrete.",
                metadata={"page_number": 2},
            ),
        ]
        enriched = enrich_with_structure(docs)
        assert enriched[0].metadata["chapter"] == "3"
        assert enriched[1].metadata["chapter"] == "3"  # propagated

    def test_enrich_new_chapter_resets_section(self):
        docs = [
            Document(content="Chapter 1: Intro\n1.1 Basics", metadata={}),
            Document(content="Chapter 2: Advanced", metadata={}),
        ]
        enriched = enrich_with_structure(docs)
        assert enriched[0].metadata["chapter"] == "1"
        assert enriched[0].metadata["section"] == "1.1"
        assert enriched[1].metadata["chapter"] == "2"
        # Sekcja powinna być zresetowana po nowym rozdziale
        assert "section" not in enriched[1].metadata or enriched[1].metadata.get("section") == ""


# --- Testy trybów study ---


class TestStudyModes:
    def test_build_quiz_messages(self):
        from src.rag.retriever import RetrievedChunk

        chunks = [
            RetrievedChunk(
                content="FFT to szybki algorytm DFT",
                score=0.9,
                filename="dsp.pdf",
                page_number=42,
                chunk_index=0,
                chapter="3",
                chapter_title="Fourier Transform",
            )
        ]
        messages = build_study_messages("przepytaj mnie", chunks, StudyMode.QUIZ)
        assert messages[0]["role"] == "system"
        assert "quiz" in messages[0]["content"].lower()
        assert "FFT" in messages[1]["content"]
        assert "Rozdział: Fourier Transform" in messages[1]["content"]

    def test_build_connect_messages(self):
        from src.rag.retriever import RetrievedChunk

        chunks = [
            RetrievedChunk(
                content="tekst", score=0.8, filename="a.pdf",
                page_number=1, chunk_index=0,
            )
        ]
        messages = build_study_messages(
            "jak X łączy się z Y?", chunks, StudyMode.CONNECT
        )
        assert "powiązania" in messages[0]["content"].lower()


# --- Testy Study Engine ---


class TestStudyEngine:
    def _make_engine(self, test_embedder, test_store) -> StudyEngine:
        retriever = Retriever(test_embedder, test_store)
        generator = Generator()
        return StudyEngine(retriever=retriever, generator=generator)

    def _seed_data(self, test_embedder, test_store, collection="study_test"):
        """Wrzuć testowe dane z metadanymi rozdziałów."""
        docs = [
            Document(
                content="FFT to szybki algorytm obliczania DFT w O(n log n)",
                metadata={"filename": "dsp.pdf", "chapter": "3", "page_number": 42},
            ),
            Document(
                content="Próbkowanie sygnału musi spełniać twierdzenie Nyquista",
                metadata={"filename": "dsp.pdf", "chapter": "2", "page_number": 20},
            ),
            Document(
                content="Filtr dolnoprzepustowy przepuszcza niskie częstotliwości",
                metadata={"filename": "dsp.pdf", "chapter": "4", "page_number": 60},
            ),
        ]
        vectors = test_embedder.embed([d.content for d in docs])
        test_store.add_documents(collection, docs, vectors)

    def test_study_no_data_returns_message(self, test_embedder, test_store):
        engine = self._make_engine(test_embedder, test_store)
        test_store.ensure_collection("empty")
        result = engine.study("cokolwiek", "empty", StudyMode.EXPLAIN)
        assert "Nie znalazłem" in result.content

    def test_study_chapter_filter(self, test_embedder, test_store):
        """Filtr na rozdział powinien zwracać tylko fragmenty z tego rozdziału."""
        self._seed_data(test_embedder, test_store, "ch_filter")
        engine = self._make_engine(test_embedder, test_store)

        result = engine.study(
            "algorytm", "ch_filter", StudyMode.EXPLAIN, chapter="3"
        )
        # Powinny być źródła, i powinny pochodzić z rozdziału 3
        assert len(result.sources) >= 1
        for src in result.sources:
            assert src.chapter == "3"

    @patch.object(Generator, "is_available", return_value=True)
    @patch.object(Generator, "generate", return_value="Oto quiz:\n1. Co to FFT?")
    def test_study_quiz_with_mocked_llm(
        self, mock_gen, mock_avail, test_embedder, test_store
    ):
        self._seed_data(test_embedder, test_store, "quiz_test")
        engine = self._make_engine(test_embedder, test_store)

        result = engine.study("przepytaj mnie z FFT", "quiz_test", StudyMode.QUIZ)
        assert result.mode == StudyMode.QUIZ
        assert "quiz" in result.content.lower() or "FFT" in result.content
        assert len(result.sources) >= 1


# --- Testy API study endpoint ---


class TestStudyAPI:
    def _ingest_book(self, client):
        """Helper: wrzuć 'książkę' z rozdziałami (więcej tekstu = lepsze embeddingi)."""
        doc = fitz.open()

        page1 = doc.new_page()
        page1.insert_text(
            (72, 72),
            "Chapter 1: Introduction\n"
            "This book covers digital signal processing (DSP). "
            "DSP is the mathematical manipulation of signals "
            "represented as sequences of numbers.",
        )

        page2 = doc.new_page()
        page2.insert_text(
            (72, 72),
            "Chapter 2: Sampling\n"
            "The Nyquist-Shannon sampling theorem states that a signal "
            "must be sampled at least twice its highest frequency. "
            "Sampling converts continuous analog signals to discrete digital form.",
        )

        page3 = doc.new_page()
        page3.insert_text(
            (72, 72),
            "Chapter 3: Fourier Transform\n"
            "The Fast Fourier Transform (FFT) is an efficient algorithm "
            "to compute the Discrete Fourier Transform (DFT). "
            "FFT reduces computation from O(n^2) to O(n log n). "
            "It decomposes a signal into its frequency components.",
        )

        pdf_bytes = doc.tobytes()
        doc.close()

        client.post(
            "/ingest/",
            files={"file": ("dsp_book.pdf", pdf_bytes, "application/pdf")},
            data={"collection": "dsp"},
        )

    def test_study_explain(self, client):
        self._ingest_book(client)
        # Pytanie po angielsku bo testowy model (all-MiniLM-L6-v2) jest English-only.
        # Produkcyjny BGE-M3 obsługuje polski bez problemu.
        response = client.post(
            "/study/",
            json={
                "question": "explain the Fast Fourier Transform algorithm",
                "collection": "dsp",
                "mode": "explain",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["mode"] == "explain"
        assert len(data["sources"]) >= 1

    def test_study_quiz(self, client):
        self._ingest_book(client)
        response = client.post(
            "/study/",
            json={
                "question": "quiz me on Fourier Transform and FFT",
                "collection": "dsp",
                "mode": "quiz",
            },
        )
        assert response.status_code == 200
        assert response.json()["mode"] == "quiz"

    def test_study_connect(self, client):
        self._ingest_book(client)
        response = client.post(
            "/study/",
            json={
                "question": "How does sampling relate to FFT and Fourier?",
                "collection": "dsp",
                "mode": "connect",
            },
        )
        assert response.status_code == 200
        assert response.json()["mode"] == "connect"
        assert len(response.json()["sources"]) >= 1

    def test_study_with_chapter_filter(self, client):
        self._ingest_book(client)
        response = client.post(
            "/study/",
            json={
                "question": "explain everything",
                "collection": "dsp",
                "mode": "explain",
                "chapter": "3",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["chapter"] == "3"
