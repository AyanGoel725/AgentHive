"""
AgentHive — FastAPI Application Entry Point
Use Case 1: Document Intelligence (PDF/Excel -> Summary + Question Extraction)
"""
from __future__ import annotations

import asyncio
import shutil
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from core.config import (
    UPLOAD_DIR,
    MAX_FILE_SIZE_MB,
    ENABLE_MOCK_MODE,
    validate_config,
    is_demo_mode,
)
from core.schemas import (
    FullAnalysisResult,
    ProcessingStatus,
    QueryRequest,
    QueryResponse,
    UploadResponse,
    DocumentMetadata,
    VoiceFormatRequest,
    VoiceFormatResponse,
)
from core.utils import generate_doc_id
from agents.orchestrator import orchestrator
from agents.voice import format_for_speech

# ── App Setup ──────────────────────────────────────────────────────────────────

app = FastAPI(
    title="AgentHive - Document Intelligence",
    description="Multi-agent system for PDF/Excel document analysis (Philips UC1)",
    version="2.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ALLOWED_EXTENSIONS = {".pdf", ".xlsx", ".xls", ".csv"}
MAX_FILE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

# In-memory status tracking for polling
_processing_status: dict[str, dict] = {}


# ── Startup ────────────────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup():
    warnings = validate_config()
    for w in warnings:
        print(f"[WARNING] CONFIG: {w}")
    # NOTE: No emojis in print() — Windows CP1252 terminal cannot encode them
    print(f"[INFO] AgentHive started | Mock Mode: {is_demo_mode()} | Upload Dir: {UPLOAD_DIR}")


# ── Health ─────────────────────────────────────────────────────────────────────

@app.get("/api/health")
async def health():
    return {
        "status": "healthy",
        "mock_mode": is_demo_mode(),
        "version": "2.0.0",
        "agents": [
            "IngestionAgent",
            "DocumentClassifierAgent",
            "SummarizationAgent",
            "QuestionExtractorAgent",
            "ExtractionAgent",
            "UnderstandingAgent",
            "OrchestratorAgent",
        ],
    }


# ── Upload + Analyze ───────────────────────────────────────────────────────────

@app.post("/api/upload", response_model=UploadResponse)
async def upload_document(file: UploadFile = File(...)):
    """
    Upload a PDF or Excel file. Triggers the full analysis pipeline.
    Returns immediately with pending status — poll /status for completion.
    """
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{suffix}'. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    file_bytes = await file.read()
    if len(file_bytes) > MAX_FILE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Max size: {MAX_FILE_SIZE_MB}MB",
        )

    doc_id = generate_doc_id()
    save_path = UPLOAD_DIR / f"{doc_id}{suffix}"
    save_path.write_bytes(file_bytes)

    _processing_status[doc_id] = {
        "status": ProcessingStatus.PENDING,
        "message": "Queued for processing",
    }

    file_size = len(file_bytes)
    immediate_metadata = DocumentMetadata(
        doc_id=doc_id,
        filename=file.filename or f"document{suffix}",
        file_type="pdf" if suffix == ".pdf" else ("csv" if suffix == ".csv" else "excel"),
        file_size_bytes=file_size,
    )

    async def status_callback(status: ProcessingStatus, message: str):
        _processing_status[doc_id] = {"status": status, "message": message}

    async def run_pipeline():
        try:
            await orchestrator.analyze_document(
                file_path=save_path,
                doc_id=doc_id,
                status_callback=status_callback,
            )
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            with open("error_log.txt", "a") as f:
                f.write(f"Error {doc_id}: {str(e)}\n{tb}\n")
            _processing_status[doc_id] = {
                "status": ProcessingStatus.ERROR,
                "message": str(e),
            }
            print(f"[ERROR] Pipeline error for {doc_id}: {e}")

    asyncio.create_task(run_pipeline())

    return UploadResponse(
        doc_id=doc_id,
        metadata=immediate_metadata,
        status=ProcessingStatus.PENDING,
        message="Document uploaded. Processing started in background.",
    )


# ── Get Analysis Result ────────────────────────────────────────────────────────

@app.get("/api/documents/{doc_id}/analysis", response_model=FullAnalysisResult)
async def get_analysis(doc_id: str):
    """Retrieve the full analysis result for a document."""
    result = orchestrator.get_result(doc_id)
    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"Document '{doc_id}' not found or still processing."
        )
    return result


# ── Processing Status ──────────────────────────────────────────────────────────

@app.get("/api/documents/{doc_id}/status")
async def get_status(doc_id: str):
    """Poll the processing status of a document."""
    status = _processing_status.get(doc_id)
    if not status:
        raise HTTPException(status_code=404, detail="Document not found.")
    return status


# ── Query / Q&A ───────────────────────────────────────────────────────────────

@app.post("/api/query", response_model=QueryResponse)
async def query_document(request: QueryRequest):
    """Ask a follow-up question about an analyzed document."""
    result = orchestrator.get_result(request.doc_id)
    if not result:
        raise HTTPException(
            status_code=404,
            detail="Document not found. Upload a document first."
        )
    response = await orchestrator.query_document(request.doc_id, request.query)
    return response


# ── Voice ──────────────────────────────────────────────────────────────────────

@app.post("/api/voice/format", response_model=VoiceFormatResponse)
async def voice_format(request: VoiceFormatRequest):
    """Format text for optimal text-to-speech readback."""
    speech_text = format_for_speech(request.text)
    return VoiceFormatResponse(speech_text=speech_text)


# ── List Documents ─────────────────────────────────────────────────────────────

@app.get("/api/documents", response_model=list[DocumentMetadata])
async def list_documents():
    """List all uploaded and analyzed documents."""
    return orchestrator.list_documents()


# ── Delete Document ────────────────────────────────────────────────────────────

@app.delete("/api/documents/{doc_id}")
async def delete_document(doc_id: str):
    """Remove a document and all its analysis data."""
    deleted = orchestrator.delete_document(doc_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Document not found.")

    for ext in ALLOWED_EXTENSIONS:
        path = UPLOAD_DIR / f"{doc_id}{ext}"
        path.unlink(missing_ok=True)

    _processing_status.pop(doc_id, None)
    return {"message": f"Document '{doc_id}' deleted successfully."}


# ── Export ─────────────────────────────────────────────────────────────────────

@app.get("/api/documents/{doc_id}/export/json")
async def export_json(doc_id: str):
    """Export full analysis as JSON."""
    result = orchestrator.get_result(doc_id)
    if not result:
        raise HTTPException(status_code=404, detail="Document not found.")
    return JSONResponse(content=result.model_dump(mode="json"))


@app.get("/api/documents/{doc_id}/export/markdown")
async def export_markdown(doc_id: str):
    """Export analysis as a formatted Markdown report."""
    result = orchestrator.get_result(doc_id)
    if not result:
        raise HTTPException(status_code=404, detail="Document not found.")

    md = _build_markdown_report(result)
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse(
        content=md,
        media_type="text/markdown",
        headers={
            "Content-Disposition": f'attachment; filename="{doc_id}_report.md"'
        },
    )


def _build_markdown_report(result: FullAnalysisResult) -> str:
    """Build a Markdown report from analysis results."""
    lines = [
        "# Document Analysis Report",
        "",
        f"**File**: {result.metadata.filename}  ",
        f"**Type**: {result.classification.document_type.value}  ",
        f"**Analyzed**: {result.metadata.upload_timestamp.strftime('%Y-%m-%d %H:%M UTC')}  ",
        f"**Processing Time**: {result.processing_time_seconds}s  ",
        "",
        "---",
        "",
        "## Executive Summary",
        "",
        result.summary.executive_summary,
        "",
        "---",
        "",
        "## Detailed Summary",
        "",
        result.summary.detailed_summary,
        "",
        "---",
        "",
        "## Key Points",
        "",
    ]

    for kp in result.summary.key_points:
        icon = "[HIGH]" if kp.importance == "high" else "[MED]" if kp.importance == "medium" else "[LOW]"
        lines.append(f"- {icon} {kp.point}")

    lines += ["", "---", "", "## Topics", ""]
    lines.append(", ".join(f"`{t}`" for t in result.summary.topics))

    if result.questions:
        lines += [
            "", "---", "",
            f"## Extracted Questions ({result.questions.total_questions})",
            ""
        ]
        current_section = None
        for q in result.questions.questions:
            if q.section != current_section:
                current_section = q.section
                if current_section:
                    lines += ["", f"### {current_section}", ""]
            if q.category.value == "section_header":
                lines.append(f"#### {q.text}")
            else:
                num = f"{q.number} " if q.number else ""
                req = " *(required)*" if q.is_required else ""
                lines.append(f"- **{num}{q.text}**{req}")
                for opt in q.options:
                    lines.append(f"  - {opt}")

    return "\n".join(lines)


# ── Run ────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
