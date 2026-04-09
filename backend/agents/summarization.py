"""
Summarization Agent — Fast, grounded summaries with anti-hallucination.
Uses temperature=0.1 for fluent but factual output.
Uses the LLM pool for instant access.
"""
from __future__ import annotations

import json

from core.config import FAST_MODEL_NAME, is_demo_mode
from core.schemas import KeyPoint, SummaryResult
from core.utils import truncate_for_llm
from core.llm_pool import get_llm
import re

def get_word_count(text: str) -> int:
    text = text.replace("\n", " ")
    words = re.findall(r'\b\w+\b', text)
    return len(words)

_SUMMARY_PROMPT = """\
You are an expert document analyst. Read the document below and produce a comprehensive analysis.

DOCUMENT TYPE: {doc_type}
DOCUMENT CONTENT:
{content}

Return ONLY a valid JSON object with this exact structure:
{{
  "executive_summary": "<2-3 sentence TL;DR capturing the most important point>",
  "detailed_summary": "<thorough multi-paragraph summary covering all major sections and themes. Minimum 200 words.>",
  "key_points": [
    {{"point": "<specific insight or finding>", "importance": "high|medium|low", "page_reference": "<page X or null>"}},
    ...
  ],
  "topics": ["<topic tag>", ...],
  "sentiment": "positive|neutral|negative"
}}

STRICT RULES:
- The detailed_summary MUST cover every major section of the document.
- Key points MUST be specific facts, numbers, or findings directly from the document.
- Do NOT include ANY information that is not explicitly stated in the document.
- Do NOT infer, speculate, or add external knowledge.
- If the document is short, say so — do NOT pad the summary with invented content.
- List 5-10 key points. Each must cite a specific fact from the text.
- Topics should be 3-8 concise tags.
- Return ONLY the JSON. No markdown fences, no explanation.
"""


class SummarizationAgent:
    """Generates rich, grounded document summaries using the pooled fast model."""

    def summarize(self, raw_text: str, doc_id: str, doc_type: str = "unknown") -> SummaryResult:
        """
        Generate a full summary of the document.
        Uses smart truncation — sends only as much text as needed.
        """
        word_count = get_word_count(raw_text)

        if is_demo_mode():
            return self._demo_summarize(raw_text, doc_id, word_count)

        from langchain.schema import HumanMessage

        llm = get_llm(FAST_MODEL_NAME, temperature=0.1)

        # Smart truncation: small docs get full text, large docs get 30K tokens
        if word_count < 8000:
            content = raw_text
        else:
            content = truncate_for_llm(raw_text, max_tokens=30000)

        prompt = _SUMMARY_PROMPT.format(doc_type=doc_type, content=content)

        # Retry up to 2 times for JSON parse failures
        last_error = None
        for attempt in range(2):
            try:
                response = llm.invoke([HumanMessage(content=prompt)])
                raw_content = response.content.strip()

                # Strip markdown code fences
                if raw_content.startswith("```"):
                    raw_content = raw_content.split("```")[1]
                    if raw_content.startswith("json"):
                        raw_content = raw_content[4:]

                data = json.loads(raw_content)
                original_wc = word_count
                summary_wc = len(data.get("detailed_summary", "").split())

                return SummaryResult(
                    doc_id=doc_id,
                    executive_summary=data["executive_summary"],
                    detailed_summary=data["detailed_summary"],
                    key_points=[
                        KeyPoint(
                            point=kp["point"],
                            importance=kp.get("importance", "medium"),
                            page_reference=kp.get("page_reference"),
                        )
                        for kp in data.get("key_points", [])
                    ],
                    topics=data.get("topics", []),
                    sentiment=data.get("sentiment", "neutral"),
                    word_count_original=original_wc,
                    summary_compression_ratio=round(summary_wc / max(original_wc, 1), 2),
                )

            except (json.JSONDecodeError, KeyError) as e:
                last_error = e
                continue

        # Graceful degradation
        print(f"[WARNING] Summarization fallback after {last_error}")
        return SummaryResult(
            doc_id=doc_id,
            executive_summary=raw_text[:300] + "...",
            detailed_summary=raw_text[:2000],
            key_points=[],
            topics=[doc_type],
            sentiment="neutral",
            word_count_original=word_count,
            summary_compression_ratio=0.0,
        )

    def _demo_summarize(self, text: str, doc_id: str, word_count: int) -> SummaryResult:
        """Demo mode fallback — reasonable summary without LLM."""
        sentences = [s.strip() for s in text.replace("\n", ". ").split(". ") if len(s.strip()) > 20]

        executive = ". ".join(sentences[:3]) + "." if sentences else "No content extracted."
        detailed = ". ".join(sentences[:10]) + "." if sentences else "No content available."

        return SummaryResult(
            doc_id=doc_id,
            executive_summary=f"[Demo Mode] {executive[:300]}",
            detailed_summary=f"[Demo Mode] {detailed[:2000]}",
            key_points=[
                KeyPoint(point=s[:200], importance="medium")
                for s in sentences[:5]
            ],
            topics=["Document Analysis"],
            sentiment="neutral",
            word_count_original=word_count,
            summary_compression_ratio=0.15,
        )


# Singleton
summarization_agent = SummarizationAgent()
