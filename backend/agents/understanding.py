"""
AgentHive — 🧠 Understanding Agent
Cleans text, splits into chunks, builds FAISS vector store, runs semantic search.
"""

from __future__ import annotations
from typing import Any
from core.config import CHUNK_SIZE, CHUNK_OVERLAP, GOOGLE_API_KEY, EMBEDDING_MODEL, is_demo_mode


def _get_splitter():
    from langchain.text_splitter import RecursiveCharacterTextSplitter
    return RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""],
    )


def clean_text(raw: str) -> str:
    """Basic text cleaning — collapse whitespace, strip artifacts."""
    import re
    text = re.sub(r"\s+", " ", raw)
    text = re.sub(r"[^\x20-\x7E\n]", "", text)
    return text.strip()


def chunk_text(text: str) -> list[str]:
    """Split cleaned text into overlapping chunks."""
    splitter = _get_splitter()
    docs = splitter.create_documents([text])
    return [d.page_content for d in docs]


def build_vector_store(chunks: list[str]) -> Any:
    """Create a FAISS index from text chunks using Google Gemini embeddings."""
    if is_demo_mode():
        # In demo mode, return a simple list-based "store"
        return {"type": "demo", "chunks": chunks}

    from langchain_google_genai import GoogleGenerativeAIEmbeddings
    from langchain_community.vectorstores import FAISS

    embeddings = GoogleGenerativeAIEmbeddings(
        model=EMBEDDING_MODEL,
        google_api_key=GOOGLE_API_KEY,
    )
    store = FAISS.from_texts(chunks, embeddings)
    return store


def semantic_search(query: str, store: Any, k: int = 5) -> list[str]:
    """Retrieve the top-k most relevant chunks for a query."""
    if isinstance(store, dict) and store.get("type") == "demo":
        # Demo mode: naive keyword matching
        chunks = store["chunks"]
        query_words = set(query.lower().split())
        scored = []
        for c in chunks:
            score = sum(1 for w in query_words if w in c.lower())
            scored.append((score, c))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [c for _, c in scored[:k]]

    docs = store.similarity_search(query, k=k)
    return [d.page_content for d in docs]
