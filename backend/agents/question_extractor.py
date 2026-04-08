"""
❓ Question Extractor Agent
────────────────────────────
Specialized agent for extracting ALL questions from forms and questionnaires.
Groups questions by section, detects type (MCQ, open-ended, rating, yes/no),
identifies required fields, and extracts answer options.

This is the crown jewel of Use Case 1.
"""
from __future__ import annotations

import json
import re
import uuid

from core.config import GOOGLE_API_KEY, MODEL_NAME, is_demo_mode
from core.schemas import ExtractedQuestion, QuestionCategory, QuestionExtractionResult
from core.utils import truncate_for_llm

_EXTRACTION_PROMPT = """\
You are an expert form analyst. Your job is to extract EVERY question from the document below.

DOCUMENT CONTENT:
{content}

Extract ALL questions — numbered, lettered, bulleted, or inline. Include:
- Section headers that group questions
- Multiple choice options for each question
- Whether the question appears required (look for asterisks *, "required", "mandatory")
- The question type

Return ONLY a valid JSON object:
{{
  "sections": ["<section name>", ...],
  "questions": [
    {{
      "number": "<Q1, 1., a), etc. or null>",
      "text": "<full question text>",
      "category": "<open_ended|multiple_choice|rating|yes_no|fill_in|section_header|demographic|unknown>",
      "is_required": <true|false|null>,
      "options": ["<option text>", ...],
      "section": "<which section this belongs to or null>",
      "page_number": <integer or null>,
      "sub_questions": [
        {{same structure as parent question}}
      ]
    }},
    ...
  ],
  "has_rating_scales": <true|false>,
  "has_open_ended": <true|false>,
  "has_multiple_choice": <true|false>,
  "extraction_confidence": <float 0.0-1.0>
}}

IMPORTANT:
- Do NOT skip any questions, even if they seem minor.
- For rating scales like "1-5" or "Strongly Agree to Disagree", set category="rating".
- Section headers (like "Section A: Personal Information") should be included as category="section_header".
- Sub-questions (a, b, c under a main question) go in sub_questions array.
- If no questions found, return empty questions array.
"""


class QuestionExtractorAgent:
    """
    Extracts structured question data from forms and questionnaires.
    Works on both PDF forms and Excel-based surveys.
    """

    def extract_questions(
        self, raw_text: str, doc_id: str
    ) -> QuestionExtractionResult:
        """
        Extract all questions from document text.
        """
        if is_demo_mode():
            return self._rule_based_extraction(raw_text, doc_id)

        from langchain_google_genai import ChatGoogleGenerativeAI
        from langchain.schema import HumanMessage

        llm = ChatGoogleGenerativeAI(
            model=MODEL_NAME,
            google_api_key=GOOGLE_API_KEY,
            temperature=0.1,
        )

        content = truncate_for_llm(raw_text, max_tokens=14000)
        prompt = _EXTRACTION_PROMPT.format(content=content)

        try:
            response = llm.invoke([HumanMessage(content=prompt)])
            raw_content = response.content.strip()

            if raw_content.startswith("```"):
                raw_content = raw_content.split("```")[1]
                if raw_content.startswith("json"):
                    raw_content = raw_content[4:]

            data = json.loads(raw_content)
            questions = self._parse_questions(data.get("questions", []))

            return QuestionExtractionResult(
                doc_id=doc_id,
                total_questions=len(
                    [q for q in questions if q.category != QuestionCategory.SECTION_HEADER]
                ),
                sections=data.get("sections", []),
                questions=questions,
                has_rating_scales=data.get("has_rating_scales", False),
                has_open_ended=data.get("has_open_ended", False),
                has_multiple_choice=data.get("has_multiple_choice", False),
                extraction_confidence=float(data.get("extraction_confidence", 0.8)),
            )

        except (json.JSONDecodeError, KeyError, ValueError):
            return self._rule_based_extraction(raw_text, doc_id)

    def _parse_questions(
        self, raw_questions: list[dict]
    ) -> list[ExtractedQuestion]:
        """Parse raw JSON question data into typed ExtractedQuestion objects."""
        questions = []
        for q in raw_questions:
            sub_qs = self._parse_questions(q.get("sub_questions", []))
            try:
                category = QuestionCategory(q.get("category", "unknown"))
            except ValueError:
                category = QuestionCategory.UNKNOWN

            questions.append(
                ExtractedQuestion(
                    question_id=str(uuid.uuid4())[:8],
                    number=q.get("number"),
                    text=q.get("text", ""),
                    category=category,
                    is_required=q.get("is_required"),
                    options=q.get("options", []),
                    section=q.get("section"),
                    page_number=q.get("page_number"),
                    sub_questions=sub_qs,
                )
            )
        return questions

    def _rule_based_extraction(
        self, raw_text: str, doc_id: str
    ) -> QuestionExtractionResult:
        """
        Fallback rule-based question extraction using regex patterns.
        Catches numbered questions, question marks, and common form patterns.
        """
        questions: list[ExtractedQuestion] = []
        lines = raw_text.splitlines()
        current_section: str | None = None

        # Patterns for question detection
        numbered_q = re.compile(r"^\s*(\d+[\.\)]\s*|\w[\.\)]\s*|Q\d+[\.\:\s])")
        question_mark = re.compile(r".{10,}\?$")
        section_header = re.compile(
            r"^(Section|Part|Category|Group)\s+[\w\d]+[\:\-]", re.IGNORECASE
        )

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Section header detection
            if section_header.match(line) and len(line) < 100:
                current_section = line
                questions.append(
                    ExtractedQuestion(
                        question_id=str(uuid.uuid4())[:8],
                        text=line,
                        category=QuestionCategory.SECTION_HEADER,
                        section=current_section,
                    )
                )
                continue

            # Numbered question
            m = numbered_q.match(line)
            if m and len(line) > 10:
                questions.append(
                    ExtractedQuestion(
                        question_id=str(uuid.uuid4())[:8],
                        number=m.group(1).strip(),
                        text=line[m.end():].strip(),
                        category=QuestionCategory.UNKNOWN,
                        section=current_section,
                    )
                )
                continue

            # Question mark ending
            if question_mark.match(line) and len(line) < 200:
                questions.append(
                    ExtractedQuestion(
                        question_id=str(uuid.uuid4())[:8],
                        text=line,
                        category=QuestionCategory.OPEN_ENDED,
                        section=current_section,
                    )
                )

        actual_questions = [
            q for q in questions if q.category != QuestionCategory.SECTION_HEADER
        ]

        return QuestionExtractionResult(
            doc_id=doc_id,
            total_questions=len(actual_questions),
            sections=list({q.section for q in questions if q.section}),
            questions=questions,
            has_rating_scales=False,
            has_open_ended=any(
                q.category == QuestionCategory.OPEN_ENDED for q in actual_questions
            ),
            has_multiple_choice=False,
            extraction_confidence=0.5,
        )


# Singleton
question_extractor_agent = QuestionExtractorAgent()
