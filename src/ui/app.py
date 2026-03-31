"""PRISM Chat UI - Streamlit frontend.

Uruchomienie: uv run streamlit run src/ui/app.py
Wymaga API: uv run uvicorn src.main:app --reload
"""

import httpx
import streamlit as st

API_URL = "http://localhost:8000"
TIMEOUT = httpx.Timeout(timeout=180.0)

st.set_page_config(page_title="PRISM", page_icon="P", layout="wide")


# --- API calls ---


def api_get(path: str):
    try:
        return httpx.get(f"{API_URL}{path}", timeout=5.0).json()
    except httpx.ConnectError:
        return None


def api_post(path: str, **kwargs):
    return httpx.post(f"{API_URL}{path}", timeout=TIMEOUT, **kwargs).json()


def get_collections() -> list[str]:
    data = api_get("/collections/")
    if data is None:
        return []
    return [c["name"] for c in data]


# --- Sidebar ---

with st.sidebar:
    st.markdown("### PRISM")
    st.caption("Personal Retrieval & Intelligence System for Memory")

    collections = get_collections()
    if not collections:
        st.error("API niedostepne. Uruchom: `uv run uvicorn src.main:app`")
        st.stop()

    collection = st.selectbox("Kolekcja", collections)

    mode = st.radio(
        "Tryb",
        ["chat", "quiz", "explain", "connect"],
        captions=["Zwykly RAG", "Przepytaj mnie", "Wyjasnienie", "Polacz koncepty"],
    )

    st.divider()

    st.markdown("##### Upload PDF")
    upload_col = st.text_input("Kolekcja docelowa", value=collection)
    uploaded_file = st.file_uploader("Wybierz plik", type=["pdf"], label_visibility="collapsed")
    if uploaded_file and st.button("Wrzuc", use_container_width=True):
        with st.spinner("Przetwarzanie..."):
            result = api_post(
                "/ingest/",
                files={"file": (uploaded_file.name, uploaded_file.getvalue())},
                data={"collection": upload_col},
            )
            count = result.get("chunks_created", "?")
            st.success(f"Dodano {count} fragmentow z {uploaded_file.name}")

# --- Chat ---

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("sources"):
            with st.expander(f"Zrodla ({len(msg['sources'])})"):
                for src in msg["sources"]:
                    page = src.get("page")
                    loc = f"{src['filename']}"
                    if page:
                        loc += f", s. {page}"
                    st.caption(loc)

if prompt := st.chat_input("Zadaj pytanie..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Generowanie odpowiedzi..."):
            try:
                if mode == "chat":
                    result = api_post("/query/", json={
                        "question": prompt,
                        "collection": collection,
                    })
                    answer = result.get("answer", "Brak odpowiedzi")
                    sources = result.get("sources", [])
                else:
                    result = api_post("/study/", json={
                        "question": prompt,
                        "collection": collection,
                        "mode": mode,
                    })
                    answer = result.get("content", "Brak odpowiedzi")
                    sources = result.get("sources", [])
            except httpx.ReadTimeout:
                answer = "Timeout - Ollama potrzebuje wiecej czasu. Sprobuj krotsz pytanie."
                sources = []

        st.markdown(answer)

        if sources:
            with st.expander(f"Zrodla ({len(sources)})"):
                for src in sources:
                    page = src.get("page")
                    loc = f"{src['filename']}"
                    if page:
                        loc += f", s. {page}"
                    st.caption(loc)

        st.session_state.messages.append({
            "role": "assistant",
            "content": answer,
            "sources": sources,
        })
