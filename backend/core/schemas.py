"""
All Pydantic models for request/response shapes across the API.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


# ── Enums ──────────────────────────────────────────────────────────────────────

class DocumentType(str, Enum):
    QUESTIONNAIRE = "questionnaire"
    FORM = "form"
    REPORT = "report"
    SPREADSHEET = "spreadsheet"
    PRESENTATION = "presentation"
    CONTRACT = "contract"
    INVOICE = "invoice"
    RESUME = "resume"
    ACADEMIC = "academic"
    TECHNICAL = "technical"
    UNKNOWN = "unknown"


class ProcessingStatus(str, Enum):
    PENDING = "pending"
    INGESTING = "ingesting"
    CLASSIFYING = "classifying"
    SUMMARIZING = "summarizing"
    EXTRACTING = "extracting"
    INDEXING = "indexing"
    COMPLETE = "complete"
    ERROR = "error"


class QuestionCategory(str, Enum):
    DEMOGRAPHIC = "demographic"
    OPEN_ENDED = "open_ended"
    MULTIPLE_CHOICE = "multiple_choice"
    RATING = "rating"
    YES_NO = "yes_no"
    FILL_IN = "fill_in"
    SECTION_HEADER = "section_header"
    UNKNOWN = "unknown"


# ── Document Models ────────────────────────────────────────────────────────────

class DocumentMetadata(BaseModel):
    doc_id: str
    filename: str
    file_type: str                          # "pdf" | "excel" | "csv"
    file_size_bytes: int
    page_count: Optional[int] = None        # PDF only
    sheet_names: Optional[list[str]] = None  # Excel only
    row_count: Optional[int] = None         # Excel/CSV only
    column_count: Optional[int] = None
    upload_timestamp: datetime = Field(default_factory=datetime.utcnow)


class UploadResponse(BaseModel):
    doc_id: str
    metadata: DocumentMetadata
    status: ProcessingStatus
    message: str


# ── Classification Models ──────────────────────────────────────────────────────

class ClassificationResult(BaseModel):
    document_type: DocumentType
    confidence: float = Field(ge=0.0, le=1.0)
    is_form_or_questionnaire: bool
    reasoning: str
    detected_sections: list[str] = Field(default_factory=list)
    language: str = "en"
    estimated_reading_time_minutes: float = 0.0


# ── Summary Models ─────────────────────────────────────────────────────────────

class KeyPoint(BaseModel):
    point: str
    importance: str   # "high" | "medium" | "low"
    page_reference: Optional[str] = None


class SummaryResult(BaseModel):
    doc_id: str
    executive_summary: str              # 2-3 sentence TL;DR
    detailed_summary: str               # Full detailed summary
    key_points: list[KeyPoint]          # Bullet-point highlights
    topics: list[str]                   # Main topic tags
    sentiment: str                      # "positive" | "neutral" | "negative"
    word_count_original: int
    summary_compression_ratio: float    # e.g. 0.12 = 88% compression


# ── Question Extraction Models ─────────────────────────────────────────────────

class ExtractedQuestion(BaseModel):
    question_id: str
    number: Optional[str] = None        # "Q1", "1.", "a)", etc.
    text: str
    category: QuestionCategory
    is_required: Optional[bool] = None
    options: list[str] = Field(default_factory=list)   # For MCQ
    section: Optional[str] = None
    page_number: Optional[int] = None
    sub_questions: list["ExtractedQuestion"] = Field(default_factory=list)


ExtractedQuestion.model_rebuild()


class QuestionExtractionResult(BaseModel):
    doc_id: str
    total_questions: int
    sections: list[str]
    questions: list[ExtractedQuestion]
    has_rating_scales: bool
    has_open_ended: bool
    has_multiple_choice: bool
    extraction_confidence: float = Field(ge=0.0, le=1.0)


# ── Full Analysis Result ───────────────────────────────────────────────────────

class FullAnalysisResult(BaseModel):
    doc_id: str
    metadata: DocumentMetadata
    classification: ClassificationResult
    summary: SummaryResult
    questions: Optional[QuestionExtractionResult] = None   # Only if form/questionnaire
    extracted_data: Optional[dict] = None                  # Structured data extraction
    processing_time_seconds: float
    agent_pipeline: list[str]           # Which agents ran, in order


# ── API Request/Response ───────────────────────────────────────────────────────

class QueryRequest(BaseModel):
    doc_id: str
    query: str
    context_window: int = 5


class QueryResponse(BaseModel):
    doc_id: str
    query: str
    answer: str
    relevant_sections: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)


class VoiceFormatRequest(BaseModel):
    text: str


class VoiceFormatResponse(BaseModel):
    speech_text: str


class ErrorResponse(BaseModel):
    error: str
    detail: str
    doc_id: Optional[str] = None
