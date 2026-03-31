"""Smoke testy API - pełny flow: ingest -> query -> results."""

import fitz
from fastapi.testclient import TestClient


def _make_pdf(text: str = "Testowa treść dokumentu") -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), text)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def test_health_check(client: TestClient):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_query_validation_empty_question(client: TestClient):
    response = client.post("/query/", json={"question": ""})
    assert response.status_code == 422


def test_ingest_pdf(client: TestClient):
    """Upload PDF -> parse -> chunk -> embed -> Qdrant."""
    pdf_bytes = _make_pdf("Treść wykładu o transformacie Fouriera.")
    response = client.post(
        "/ingest/",
        files={"file": ("fizyka.pdf", pdf_bytes, "application/pdf")},
        data={"collection": "uczelnia"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "fizyka.pdf"
    assert data["collection"] == "uczelnia"
    assert data["chunks_created"] >= 1


def test_ingest_unsupported_format(client: TestClient):
    response = client.post(
        "/ingest/",
        files={"file": ("notes.docx", b"fake", "application/octet-stream")},
    )
    assert response.status_code == 400


def test_ingest_then_query(client: TestClient):
    """End-to-end: wrzuć PDF -> zadaj pytanie -> dostań trafne wyniki."""
    # Ingest
    pdf = _make_pdf("Transformata Fouriera zamienia sygnał z dziedziny czasu na częstotliwości.")
    client.post(
        "/ingest/",
        files={"file": ("fizyka.pdf", pdf, "application/pdf")},
        data={"collection": "test_e2e"},
    )

    # Query
    response = client.post(
        "/query/",
        json={"question": "Co robi transformata Fouriera?", "collection": "test_e2e"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["sources"]) >= 1
    assert data["sources"][0]["filename"] == "fizyka.pdf"


def test_list_collections(client: TestClient):
    """Po ingestion kolekcja powinna być widoczna."""
    pdf = _make_pdf("test")
    client.post(
        "/ingest/",
        files={"file": ("t.pdf", pdf, "application/pdf")},
        data={"collection": "my_col"},
    )

    response = client.get("/collections/")
    assert response.status_code == 200
    names = [c["name"] for c in response.json()]
    assert "my_col" in names
