"""
🎯 Orchestrator Agent
──────────────────────
The central brain of the system for Use Case 1.
Coordinates the full pipeline with PARALLEL execution where possible:
  1. Ingest (sequential — needs file)
  2. Classify + Build Vector Index (PARALLEL — both need raw text only)
  3. Summarize + Extract Questions + Extract Data (PARALLEL — need raw text + classification)
  4. Return complete result

Also handles follow-up queries by routing to the understanding agent.
"""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Optional

from core.schemas import (
    FullAnalysisResult,
    ProcessingStatus,
    QueryResponse,
    DocumentMetadata,
)
from core.utils import Timer

from agents.ingestion import ingestion_agent, IngestionResult
from agents.document_classifier import classifier_agent
from agents.summarization import summarization_agent
from agents.question_extractor import question_extractor_agent
from agents.understanding import understanding_agent
from agents.extraction import extract_structured


class OrchestratorAgent:
    """
    Manages the full document analysis pipeline and query routing.
    Stores results in memory keyed by doc_id.
    Uses parallel execution for speed.
    """

    def __init__(self):
        # In-memory store: doc_id → FullAnalysisResult
        self._results: dict[str, FullAnalysisResult] = {}
        # Store ingestion results for raw data access
        self._ingestions: dict[str, IngestionResult] = {}

    async def analyze_document(
        self,
        file_path: Path,
        doc_id: str,
        status_callback=None,
    ) -> FullAnalysisResult:
        """
        Run the complete document analysis pipeline with parallel stages.

        Pipeline stages:
          INGESTING → [CLASSIFYING + INDEXING] (parallel) →
          [SUMMARIZING + EXTRACTING] (parallel) → COMPLETE
        """
        pipeline: list[str] = []

        async def update_status(status: ProcessingStatus, message: str):
            if status_callback:
                await status_callback(status, message)

        with Timer() as total_timer:
            # ── Stage 1: Ingestion (sequential) ──────────────────────────────
            await update_status(ProcessingStatus.INGESTING, "Reading document...")
            pipeline.append("IngestionAgent")

            ingestion = await asyncio.to_thread(
                ingestion_agent.ingest, file_path, doc_id
            )
            self._ingestions[doc_id] = ingestion

            # ── Stage 2: Classification + Vector Index (PARALLEL) ────────────
            await update_status(ProcessingStatus.CLASSIFYING, "Classifying & indexing document...")
            pipeline.append("DocumentClassifierAgent")
            pipeline.append("UnderstandingAgent")

            # Prepare the index ready event BEFORE starting the task
            understanding_agent.get_ready_event(doc_id)

            classify_task = asyncio.to_thread(
                classifier_agent.classify,
                ingestion.raw_text,
                ingestion.metadata.file_type,
            )
            index_task = asyncio.to_thread(
                understanding_agent.build_index,
                ingestion.raw_text,
                doc_id,
            )

            # Run classification and indexing in parallel
            classification, _num_chunks = await asyncio.gather(
                classify_task, index_task
            )

            # ── Stage 3: Summarization + Extraction (PARALLEL) ───────────────
            await update_status(ProcessingStatus.SUMMARIZING, "Generating summary & extracting data...")
            pipeline.append("SummarizationAgent")

            # Always run summarization
            summarize_task = asyncio.to_thread(
                summarization_agent.summarize,
                ingestion.raw_text,
                doc_id,
                classification.document_type.value,
            )

            # Always run structured data extraction
            pipeline.append("ExtractionAgent")
            extraction_task = asyncio.to_thread(
                extract_structured,
                ingestion.raw_text,
            )

            # Conditionally run question extraction
            questions_task = None
            if classification.is_form_or_questionnaire:
                await update_status(
                    ProcessingStatus.EXTRACTING,
                    "Detected questionnaire/form — extracting questions..."
                )
                pipeline.append("QuestionExtractorAgent")
                questions_task = asyncio.to_thread(
                    question_extractor_agent.extract_questions,
                    ingestion.raw_text,
                    doc_id,
                )

            # Gather all parallel tasks
            if questions_task:
                summary, extracted_data, questions = await asyncio.gather(
                    summarize_task, extraction_task, questions_task
                )
            else:
                summary, extracted_data = await asyncio.gather(
                    summarize_task, extraction_task
                )
                questions = None

            await update_status(ProcessingStatus.COMPLETE, "Analysis complete!")

        result = FullAnalysisResult(
            doc_id=doc_id,
            metadata=ingestion.metadata,
            classification=classification,
            summary=summary,
            questions=questions,
            extracted_data=extracted_data,
            processing_time_seconds=total_timer.elapsed,
            agent_pipeline=pipeline,
        )

        self._results[doc_id] = result
        return result

    async def query_document(
        self, doc_id: str, query: str
    ) -> QueryResponse:
        """
        Answer a follow-up question about an already-analyzed document.
        Waits for the vector index to be ready before querying.
        """
        if doc_id not in self._results:
            return QueryResponse(
                doc_id=doc_id,
                query=query,
                answer="Document not found. Please upload and analyze the document first.",
                relevant_sections=[],
                confidence=0.0,
            )

        # Wait for index to be ready (with timeout)
        index_ready = await understanding_agent.wait_for_index(doc_id, timeout=30.0)
        if not index_ready:
            return QueryResponse(
                doc_id=doc_id,
                query=query,
                answer="The document index is still being built. Please try again in a few seconds.",
                relevant_sections=[],
                confidence=0.0,
            )

        # Run the Q&A in a thread to avoid blocking
        answer, chunks, confidence = await asyncio.to_thread(
            understanding_agent.answer_query, query, doc_id
        )

        return QueryResponse(
            doc_id=doc_id,
            query=query,
            answer=answer,
            relevant_sections=chunks[:3],
            confidence=confidence,
        )

    def get_result(self, doc_id: str) -> Optional[FullAnalysisResult]:
        """Retrieve cached analysis result."""
        return self._results.get(doc_id)

    def list_documents(self) -> list[DocumentMetadata]:
        """List all analyzed documents."""
        return [r.metadata for r in self._results.values()]

    def delete_document(self, doc_id: str) -> bool:
        """Remove a document and its associated data."""
        if doc_id not in self._results:
            return False
        del self._results[doc_id]
        self._ingestions.pop(doc_id, None)
        understanding_agent.remove_index(doc_id)
        return True


# Singleton
orchestrator = OrchestratorAgent()
