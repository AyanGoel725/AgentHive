"""
📥 Ingestion Agent
─────────────────
Reads PDF and Excel/CSV files and returns raw content + rich metadata.
Handles multi-page PDFs, multi-sheet Excel workbooks, and CSVs.
Reads documents THOROUGHLY — every page, every sheet.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import fitz  # PyMuPDF
import pandas as pd

from core.schemas import DocumentMetadata
from core.utils import clean_text, generate_doc_id


class IngestionResult:
    """Container for ingestion output regardless of file type."""

    def __init__(
        self,
        raw_text: str,
        metadata: DocumentMetadata,
        dataframes: Optional[dict[str, pd.DataFrame]] = None,
        page_texts: Optional[list[str]] = None,
    ):
        self.raw_text = raw_text
        self.metadata = metadata
        self.dataframes = dataframes or {}      # sheet_name → DataFrame
        self.page_texts = page_texts or []      # Per-page text (PDFs)


class IngestionAgent:
    """Handles file reading and raw content extraction."""

    SUPPORTED_EXTENSIONS = {".pdf", ".xlsx", ".xls", ".csv"}

    def ingest(self, file_path: Path, doc_id: str) -> IngestionResult:
        """
        Entry point — detects file type and dispatches to the correct handler.
        Reads the ENTIRE document thoroughly.
        """
        ext = file_path.suffix.lower()
        if ext not in self.SUPPORTED_EXTENSIONS:
            raise ValueError(
                f"Unsupported file type '{ext}'. "
                f"Supported: {', '.join(self.SUPPORTED_EXTENSIONS)}"
            )

        if ext == ".pdf":
            return self._ingest_pdf(file_path, doc_id)
        else:
            return self._ingest_excel(file_path, doc_id, ext)

    # ── PDF ────────────────────────────────────────────────────────────────────

    def _ingest_pdf(self, file_path: Path, doc_id: str) -> IngestionResult:
        """Extract text from EVERY page of a PDF using PyMuPDF."""
        doc = fitz.open(str(file_path))
        page_texts: list[str] = []
        all_text_parts: list[str] = []

        for page_num, page in enumerate(doc, start=1):
            # Extract text with layout preservation
            raw = page.get_text("text")
            cleaned = clean_text(raw)
            page_texts.append(cleaned)
            if cleaned:
                all_text_parts.append(f"--- Page {page_num} ---\n{cleaned}")

        full_text = "\n\n".join(all_text_parts)

        metadata = DocumentMetadata(
            doc_id=doc_id,
            filename=file_path.name,
            file_type="pdf",
            file_size_bytes=file_path.stat().st_size,
            page_count=len(doc),
        )
        doc.close()

        return IngestionResult(
            raw_text=full_text,
            metadata=metadata,
            page_texts=page_texts,
        )

    # ── Excel / CSV ────────────────────────────────────────────────────────────

    def _ingest_excel(
        self, file_path: Path, doc_id: str, ext: str
    ) -> IngestionResult:
        """Read ALL sheets from an Excel file or parse a CSV."""
        dataframes: dict[str, pd.DataFrame] = {}
        text_parts: list[str] = []

        if ext == ".csv":
            df = pd.read_csv(file_path, encoding="utf-8", on_bad_lines="skip")
            dataframes["Sheet1"] = df
            text_parts.append(self._dataframe_to_text(df, "Sheet1"))
            sheet_names = ["Sheet1"]
            total_rows = len(df)
            total_cols = len(df.columns)
        else:
            xls = pd.ExcelFile(file_path)
            sheet_names = xls.sheet_names
            total_rows, total_cols = 0, 0

            for sheet in sheet_names:
                df = pd.read_excel(xls, sheet_name=sheet)
                dataframes[sheet] = df
                text_parts.append(self._dataframe_to_text(df, sheet))
                total_rows = max(total_rows, len(df))
                total_cols = max(total_cols, len(df.columns))

        full_text = "\n\n".join(text_parts)

        metadata = DocumentMetadata(
            doc_id=doc_id,
            filename=file_path.name,
            file_type="excel" if ext != ".csv" else "csv",
            file_size_bytes=file_path.stat().st_size,
            sheet_names=sheet_names,
            row_count=total_rows,
            column_count=total_cols,
        )

        return IngestionResult(
            raw_text=full_text,
            metadata=metadata,
            dataframes=dataframes,
        )

    def _dataframe_to_text(self, df: pd.DataFrame, sheet_name: str) -> str:
        """
        Convert a DataFrame to human-readable text for LLM processing.
        Includes column names, ALL rows (up to 200), and basic stats.
        """
        parts = [f"=== Sheet: {sheet_name} ==="]
        parts.append(f"Columns ({len(df.columns)}): {', '.join(str(c) for c in df.columns)}")
        parts.append(f"Rows: {len(df)}")
        parts.append("")

        # Include all rows (up to 500 for large sheets)
        sample = df.head(500)
        parts.append("Data Preview:")
        parts.append(sample.to_string(index=False, max_colwidth=80))

        # Numeric summary if applicable
        numeric_cols = df.select_dtypes(include="number")
        if not numeric_cols.empty:
            parts.append("\nNumeric Summary:")
            parts.append(numeric_cols.describe().to_string())

        return "\n".join(parts)


# Singleton instance
ingestion_agent = IngestionAgent()
