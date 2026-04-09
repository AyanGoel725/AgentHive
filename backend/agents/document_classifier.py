"""
Document Classifier Agent — Fast, deterministic classification.
Uses temperature=0.0 for zero hallucination in type detection.
Uses the LLM pool for instant access (no per-call instantiation).
"""
from __future__ import annotations

import json

from core.config import FAST_MODEL_NAME, is_demo_mode
from core.schemas import ClassificationResult, DocumentType
from core.utils import estimate_reading_time
from core.llm_pool import get_llm

_CLASSIFY_PROMPT = """\
You are a document classification expert. Analyze the document content below and classify it.

DOCUMENT CONTENT (first ~3000 chars):
{content_sample}

Return ONLY a valid JSON object with this exact structure:
{{
  "document_type": "<one of: questionnaire, form, report, spreadsheet, presentation, contract, invoice, resume, academic, technical, unknown>",
  "confidence": <float 0.0-1.0>,
  "is_form_or_questionnaire": <true/false>,
  "reasoning": "<1-2 sentence explanation>",
  "detected_sections": ["<section name>", ...],
  "language": "<ISO 639-1 language code, e.g. 'en'>",
  "estimated_word_count": <integer>
}}

RULES:
- Base your classification ONLY on the content provided. Do NOT guess or assume.
- Mark is_form_or_questionnaire=true ONLY if the document explicitly contains questions
  to be answered, input fields, checkboxes, or survey-style content.
- Confidence should reflect how certain you are based on the evidence in the text.
- Return ONLY the JSON. No markdown, no explanation.
"""


class DocumentClassifierAgent:
    """
    Uses LLM to classify document type and detect if it's a form/questionnaire.
    Falls back to rule-based classification if LLM is unavailable.
    Temperature=0.0 for deterministic, hallucination-free classification.
    """

    def classify(self, raw_text: str, file_type: str) -> ClassificationResult:
        """Classify the document based on its content."""
        # Excel/CSV are always spreadsheets — skip LLM
        if file_type in ("excel", "csv"):
            return self._classify_spreadsheet(raw_text)

        # For PDFs: use LLM or fallback
        if not is_demo_mode():
            return self._classify_with_llm(raw_text)
        return self._classify_with_rules(raw_text)

    def _classify_spreadsheet(self, raw_text: str) -> ClassificationResult:
        """Spreadsheet classification — detect if it's a form/questionnaire."""
        text_lower = raw_text.lower()
        is_questionnaire = any(
            kw in text_lower
            for kw in ["question", "response", "answer", "rating", "survey", "feedback"]
        )
        word_count = len(raw_text.split())
        return ClassificationResult(
            document_type=DocumentType.SPREADSHEET,
            confidence=0.95,
            is_form_or_questionnaire=is_questionnaire,
            reasoning="File is an Excel/CSV spreadsheet. "
            + ("Contains survey/questionnaire indicators." if is_questionnaire else ""),
            detected_sections=["Data Sheet"],
            language="en",
            estimated_reading_time_minutes=estimate_reading_time(word_count),
        )

    def _classify_with_llm(self, raw_text: str) -> ClassificationResult:
        """LLM-powered classification using the pooled fast model at temperature=0.0."""
        from langchain.schema import HumanMessage

        llm = get_llm(FAST_MODEL_NAME, temperature=0.0)

        content_sample = raw_text[:3000]
        prompt = _CLASSIFY_PROMPT.format(content_sample=content_sample)

        try:
            response = llm.invoke([HumanMessage(content=prompt)])
            content = response.content.strip()
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]

            data = json.loads(content)
            word_count = data.get("estimated_word_count", len(raw_text.split()))

            return ClassificationResult(
                document_type=DocumentType(
                    data.get("document_type", "unknown")
                ),
                confidence=float(data.get("confidence", 0.7)),
                is_form_or_questionnaire=bool(
                    data.get("is_form_or_questionnaire", False)
                ),
                reasoning=data.get("reasoning", ""),
                detected_sections=data.get("detected_sections", []),
                language=data.get("language", "en"),
                estimated_reading_time_minutes=estimate_reading_time(word_count),
            )
        except (json.JSONDecodeError, KeyError, ValueError):
            return self._classify_with_rules(raw_text)

    def _classify_with_rules(self, raw_text: str) -> ClassificationResult:
        """Rule-based fallback classifier using keyword heuristics."""
        text_lower = raw_text.lower()
        word_count = len(raw_text.split())

        q_indicators = [
            "?", "please answer", "your response", "check all that apply",
            "select one", "rate the following", "on a scale", "q1.", "q2.",
            "question 1", "section", "survey", "questionnaire", "fill in"
        ]
        q_score = sum(1 for kw in q_indicators if kw in text_lower)

        type_map = {
            DocumentType.INVOICE: ["invoice", "billing", "amount due", "total", "payment"],
            DocumentType.CONTRACT: ["agreement", "terms and conditions", "hereby", "party", "clause"],
            DocumentType.RESUME: ["experience", "education", "skills", "objective", "references"],
            DocumentType.ACADEMIC: ["abstract", "methodology", "references", "doi:", "journal"],
            DocumentType.REPORT: ["executive summary", "findings", "recommendations", "conclusion"],
            DocumentType.TECHNICAL: ["architecture", "api", "configuration", "deployment", "spec"],
        }

        detected_type = DocumentType.UNKNOWN
        max_score = 0
        for doc_type, keywords in type_map.items():
            score = sum(1 for kw in keywords if kw in text_lower)
            if score > max_score:
                max_score = score
                detected_type = doc_type

        is_form = q_score >= 3
        if is_form:
            detected_type = (
                DocumentType.QUESTIONNAIRE
                if q_score >= 5
                else DocumentType.FORM
            )

        return ClassificationResult(
            document_type=detected_type,
            confidence=min(0.5 + (max_score * 0.1), 0.85),
            is_form_or_questionnaire=is_form,
            reasoning=f"Rule-based classification. Detected {q_score} question indicators.",
            detected_sections=[],
            language="en",
            estimated_reading_time_minutes=estimate_reading_time(word_count),
        )


# Singleton
classifier_agent = DocumentClassifierAgent()
