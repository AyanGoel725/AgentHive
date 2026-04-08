"""
Understanding Agent
Chunks text, builds FAISS vector index, and enables semantic search.
Supports follow-up Q&A queries against the document with confidence scoring.

FIXED:
- Correct embedding model name (no 'models/' prefix)
- Graceful fallback when embedding fails — pipeline continues
- Safe asyncio.Event signaling from thread pool
"""
from __future__ import annotations

import asyncio
import threading
from typing import Any

from langchain.text_splitter import RecursiveCharacterTextSplitter

from core.config import (
    GOOGLE_API_KEY,
    QA_MODEL_NAME,
    EMBEDDING_MODEL,
    CHUNK_SIZE,
    CHUNK_OVERLAP,
    is_demo_mode,
)

_QA_PROMPT = """\
You are a precise document Q&A assistant. Answer the question based ONLY on the context provided.
If the answer is not in the context, say "I cannot find this information in the document."

CONTEXT:
{context}

QUESTION: {question}

Provide a clear, direct answer with specific details from the context. \
If the context contains relevant numbers, dates, names, or specific data, include them in your answer.
"""


class UnderstandingAgent:
    """
    Manages text chunking, vector indexing, and semantic search for a document.
    Each document gets its own in-memory FAISS index.

    Gracefully degrades to keyword search if embeddings fail.
    """

    def __init__(self):
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
            separators=["\n\n", "\n", ". ", " ", ""],
        )
        self._indexes: dict[str, Any] = {}       # doc_id -> FAISS index or demo store
        self._index_ready: dict[str, asyncio.Event] = {}   # doc_id -> Event
        # Store the event loop so threads can signal it safely
        self._loop: asyncio.AbstractEventLoop | None = None

    def _get_loop(self) -> asyncio.AbstractEventLoop | None:
        """Get the running event loop, caching it for thread use."""
        if self._loop is None:
            try:
                self._loop = asyncio.get_event_loop()
            except RuntimeError:
                return None
        return self._loop

    def build_index(self, raw_text: str, doc_id: str) -> int:
        """
        Chunk text and build a FAISS vector index for a document.
        Returns number of chunks indexed.
        Signals the ready event when done (or on failure — uses keyword fallback).

        NEVER raises — always marks index as ready with whatever it has.
        """
        chunks = self._splitter.split_text(raw_text)

        if is_demo_mode():
            self._indexes[doc_id] = {"type": "keyword", "chunks": chunks}
            self._signal_ready(doc_id)
            return len(chunks)

        # Try to build FAISS index with Google embeddings
        try:
            from langchain_google_genai import GoogleGenerativeAIEmbeddings
            from langchain_community.vectorstores import FAISS
            from langchain.schema import Document

            # IMPORTANT: Do NOT use 'models/' prefix with langchain-google-genai v2+
            # Correct format: "text-embedding-004"
            # Wrong formats: "models/text-embedding-004", "models/embedding-001"
            embedding_model_name = EMBEDDING_MODEL
            if embedding_model_name.startswith("models/"):
                embedding_model_name = embedding_model_name[len("models/"):]

            embeddings = GoogleGenerativeAIEmbeddings(
                model=embedding_model_name,
                google_api_key=GOOGLE_API_KEY,
                task_type="retrieval_document",
            )

            documents = [
                Document(
                    page_content=chunk,
                    metadata={"doc_id": doc_id, "chunk_id": i}
                )
                for i, chunk in enumerate(chunks)
            ]

            index = FAISS.from_documents(documents, embeddings)
            self._indexes[doc_id] = index
            print(f"[INFO] FAISS index built for {doc_id}: {len(chunks)} chunks")

        except Exception as e:
            # Embedding failed — fall back to keyword search
            # This means the pipeline CONTINUES and summarization still works
            print(
                f"[WARNING] Embedding failed for {doc_id}, using keyword fallback: {e}"
            )
            self._indexes[doc_id] = {"type": "keyword", "chunks": chunks}

        finally:
            # Always signal ready — pipeline must not hang
            self._signal_ready(doc_id)

        return len(chunks)

    def _signal_ready(self, doc_id: str) -> None:
        """
        Signal the index-ready event from a thread pool worker.
        Uses call_soon_threadsafe to safely cross the thread boundary.
        """
        if doc_id not in self._index_ready:
            return

        event = self._index_ready[doc_id]
        loop = self._get_loop()

        if loop is not None and loop.is_running():
            # Safe cross-thread signal
            loop.call_soon_threadsafe(event.set)
        else:
            # Fallback: set directly (will work if check happens after thread finishes)
            try:
                event.set()
            except Exception:
                pass

    def get_ready_event(self, doc_id: str) -> asyncio.Event:
        """
        Get or create an asyncio.Event for index readiness.
        Must be called from the async context BEFORE build_index runs in a thread.
        """
        # Cache the event loop the first time this is called from async context
        try:
            self._loop = asyncio.get_event_loop()
        except RuntimeError:
            pass

        if doc_id not in self._index_ready:
            self._index_ready[doc_id] = asyncio.Event()
        return self._index_ready[doc_id]

    async def wait_for_index(self, doc_id: str, timeout: float = 60.0) -> bool:
        """Wait until the index is ready. Returns True if ready, False on timeout."""
        if doc_id in self._indexes:
            return True

        if doc_id not in self._index_ready:
            # No event registered — index was never requested
            return False

        event = self._index_ready[doc_id]
        try:
            await asyncio.wait_for(event.wait(), timeout=timeout)
            return True
        except asyncio.TimeoutError:
            return False

    def semantic_search(self, query: str, doc_id: str, k: int = 8) -> list[str]:
        """Find the top-k most relevant chunks for a query."""
        if doc_id not in self._indexes:
            return []

        store = self._indexes[doc_id]

        # Keyword fallback (demo mode OR when embedding failed)
        if isinstance(store, dict) and store.get("type") == "keyword":
            chunks = store["chunks"]
            query_words = set(query.lower().split())
            scored = []
            for c in chunks:
                score = sum(1 for w in query_words if w in c.lower())
                scored.append((score, c))
            scored.sort(key=lambda x: x[0], reverse=True)
            return [c for _, c in scored[:k] if c]

        # FAISS semantic search
        try:
            docs = store.similarity_search(query, k=k)
            return [d.page_content for d in docs]
        except Exception as e:
            print(f"[WARNING] FAISS search failed for {doc_id}: {e}")
            return []

    def answer_query(
        self, query: str, doc_id: str, k: int = 8
    ) -> tuple[str, list[str], float]:
        """
        Answer a specific question about the document using retrieved context.
        Returns (answer, relevant_chunks, confidence_score).
        """
        chunks = self.semantic_search(query, doc_id, k=k)

        if is_demo_mode() or doc_id not in self._indexes:
            if not chunks:
                return "No relevant information found in the document.", [], 0.3
            answer = "Based on the document:\n\n" + "\n\n".join(chunks[:3])
            return answer, chunks[:3], 0.6

        # Check if we're using keyword fallback
        store = self._indexes.get(doc_id)
        is_keyword_mode = isinstance(store, dict) and store.get("type") == "keyword"

        if not chunks:
            return (
                "I could not find relevant information in the document for your query.",
                [],
                0.3,
            )

        # Use LLM for answer generation
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            from langchain.schema import HumanMessage

            llm = ChatGoogleGenerativeAI(
                model=QA_MODEL_NAME,
                google_api_key=GOOGLE_API_KEY,
                temperature=0.2,
            )

            context = "\n\n---\n\n".join(chunks)
            prompt = _QA_PROMPT.format(context=context, question=query)

            response = llm.invoke([HumanMessage(content=prompt)])
            answer = response.content.strip()

            # Lower confidence if using keyword search (less precise retrieval)
            base_confidence = 0.75 if is_keyword_mode else 0.9
            confidence = (
                base_confidence
                if len(answer) > 50 and "cannot find" not in answer.lower()
                else 0.4
            )

            return answer, chunks[:3], confidence

        except Exception as e:
            print(f"[WARNING] LLM Q&A failed: {e}")
            # Return raw chunks as answer
            answer = "Based on the document context:\n\n" + "\n\n".join(chunks[:2])
            return answer, chunks[:2], 0.5

    def has_index(self, doc_id: str) -> bool:
        """Check if a document has been indexed."""
        return doc_id in self._indexes

    def remove_index(self, doc_id: str) -> None:
        """Remove a document's index from memory."""
        self._indexes.pop(doc_id, None)
        self._index_ready.pop(doc_id, None)


# Singleton
understanding_agent = UnderstandingAgent()
