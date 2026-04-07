"""
AgentHive — Pydantic Schemas
All API request / response models live here.
"""

from __future__ import annotations
from typing import Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime
import uuid


# ── Upload ───────────────────────────────────────────────────────────

class DocumentMeta(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    filename: str
    file_type: str  # "pdf" | "excel"
    page_count: int | None = None
    columns: list[str] | None = None
    row_count: int | None = None
    uploaded_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    text_preview: str = ""


class UploadResponse(BaseModel):
    success: bool
    document: DocumentMeta
    message: str = ""


# ── Query ────────────────────────────────────────────────────────────

class QueryRequest(BaseModel):
    query: str
    document_id: str | None = None
    voice: bool = False  # True when query came from voice input


class AgentInfo(BaseModel):
    name: str
    icon: str
    description: str


class QueryResponse(BaseModel):
    success: bool
    agent: AgentInfo
    answer: str = ""
    structured_data: dict[str, Any] | None = None
    insights: dict[str, Any] | None = None
    audio_text: str = ""  # Simplified text for TTS read-back
    error: str = ""


# ── Health ───────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str = "ok"
    demo_mode: bool = False
    agents: list[str] = []
