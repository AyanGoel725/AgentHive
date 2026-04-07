"""
AgentHive — FastAPI Application
Multi-Agent Document Intelligence API
"""

from __future__ import annotations

import shutil
import uuid
from pathlib import Path
from typing import Any

import pandas as pd
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from core.config import UPLOAD_DIR, is_demo_mode
from core.schemas import (
    DocumentMeta,
    HealthResponse,
    QueryRequest,
    QueryResponse,
    UploadResponse,
)
from agents.ingestion import ingest
from agents.understanding import clean_text, chunk_text, build_vector_store
from agents.orchestrator import route_query, AGENTS

# ── App ──────────────────────────────────────────────────────────────

app = FastAPI(
    title="AgentHive API",
    description="Multi-Agent Document Intelligence System",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── In-memory document store ─────────────────────────────────────────

documents: dict[str, dict[str, Any]] = {}
# Structure per doc_id:
# {
#     "meta": DocumentMeta,
#     "text": str | None,
#     "df": pd.DataFrame | None,
#     "chunks": list[str],
#     "vector_store": Any,
#     "file_path": str,
# }


# ── Endpoints ────────────────────────────────────────────────────────


@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(
        status="ok",
        demo_mode=is_demo_mode(),
        agents=list(AGENTS.keys()),
    )


@app.post("/api/upload", response_model=UploadResponse)
async def upload_document(file: UploadFile = File(...)):
    """Upload a PDF, Excel, or CSV file for processing."""
    ext = Path(file.filename or "unknown").suffix.lower()
    if ext not in (".pdf", ".xlsx", ".xls", ".csv"):
        raise HTTPException(400, f"Unsupported file type: {ext}. Use PDF, XLSX, XLS, or CSV.")

    # Save file to disk
    doc_id = uuid.uuid4().hex[:12]
    save_path = UPLOAD_DIR / f"{doc_id}_{file.filename}"
    with open(save_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # Ingest
    try:
        content, meta = ingest(save_path)
        meta.id = doc_id
    except Exception as e:
        save_path.unlink(missing_ok=True)
        raise HTTPException(500, f"Ingestion failed: {e}")

    # Process based on file type
    doc_record: dict[str, Any] = {
        "meta": meta,
        "text": None,
        "df": None,
        "chunks": [],
        "vector_store": None,
        "file_path": str(save_path),
    }

    if meta.file_type == "pdf":
        raw_text: str = content  # type: ignore
        cleaned = clean_text(raw_text)
        chunks = chunk_text(cleaned)
        try:
            store = build_vector_store(chunks)
        except Exception:
            store = {"type": "demo", "chunks": chunks}

        doc_record["text"] = cleaned
        doc_record["chunks"] = chunks
        doc_record["vector_store"] = store

    elif meta.file_type == "excel":
        df: pd.DataFrame = content  # type: ignore
        doc_record["df"] = df
        # Also create a text representation for summarization/extraction
        text_repr = df.to_string()[:10000]
        doc_record["text"] = text_repr

    documents[doc_id] = doc_record

    return UploadResponse(
        success=True,
        document=meta,
        message=f"Successfully processed {meta.filename}",
    )


@app.post("/api/query", response_model=QueryResponse)
async def query_document(req: QueryRequest):
    """Send a natural language query to be processed by the appropriate agent."""
    if not req.document_id:
        # Use the most recently uploaded document
        if not documents:
            raise HTTPException(400, "No documents uploaded yet. Please upload a file first.")
        req.document_id = list(documents.keys())[-1]

    doc = documents.get(req.document_id)
    if not doc:
        raise HTTPException(404, f"Document {req.document_id} not found.")

    response = route_query(
        query=req.query,
        text=doc["text"],
        df=doc["df"],
        vector_store=doc["vector_store"],
        file_type=doc["meta"].file_type,
        is_voice=req.voice,
    )
    return response


@app.post("/api/voice/query", response_model=QueryResponse)
async def voice_query(req: QueryRequest):
    """Voice-optimized query endpoint. Same as /api/query but marks voice=True."""
    req.voice = True
    return await query_document(req)


@app.get("/api/documents")
async def list_documents():
    """List all uploaded documents."""
    return {
        "documents": [doc["meta"].model_dump() for doc in documents.values()]
    }


@app.delete("/api/documents/{doc_id}")
async def delete_document(doc_id: str):
    """Delete an uploaded document."""
    doc = documents.pop(doc_id, None)
    if not doc:
        raise HTTPException(404, f"Document {doc_id} not found.")

    # Clean up file
    file_path = Path(doc["file_path"])
    file_path.unlink(missing_ok=True)

    return {"success": True, "message": f"Document {doc_id} deleted."}


# ── Run ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
