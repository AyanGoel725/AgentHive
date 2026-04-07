"""
AgentHive — 📥 Ingestion Agent
Reads PDF and Excel files, extracts raw content.
"""

from __future__ import annotations
import fitz  # PyMuPDF
import pandas as pd
from pathlib import Path
from core.schemas import DocumentMeta


def ingest_pdf(file_path: str | Path) -> tuple[str, DocumentMeta]:
    """Extract text from every page of a PDF and return raw text + metadata."""
    file_path = Path(file_path)
    doc = fitz.open(str(file_path))

    pages_text: list[str] = []
    for page in doc:
        pages_text.append(page.get_text("text"))
    doc.close()

    full_text = "\n\n".join(pages_text)
    meta = DocumentMeta(
        filename=file_path.name,
        file_type="pdf",
        page_count=len(pages_text),
        text_preview=full_text[:300].strip(),
    )
    return full_text, meta


def ingest_excel(file_path: str | Path) -> tuple[pd.DataFrame, DocumentMeta]:
    """Read an Excel/CSV file into a DataFrame and return it + metadata."""
    file_path = Path(file_path)

    if file_path.suffix.lower() == ".csv":
        df = pd.read_csv(str(file_path))
    else:
        df = pd.read_excel(str(file_path))

    meta = DocumentMeta(
        filename=file_path.name,
        file_type="excel",
        columns=list(df.columns),
        row_count=len(df),
        text_preview=df.head(3).to_string()[:300],
    )
    return df, meta


def ingest(file_path: str | Path) -> tuple[str | pd.DataFrame, DocumentMeta]:
    """Auto-detect file type and delegate to the correct ingestion handler."""
    path = Path(file_path)
    ext = path.suffix.lower()

    if ext == ".pdf":
        return ingest_pdf(path)
    elif ext in (".xlsx", ".xls", ".csv"):
        return ingest_excel(path)
    else:
        raise ValueError(f"Unsupported file type: {ext}")
