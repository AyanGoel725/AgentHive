"""
✍️ Summarization Agent
───────────────────────
Generates multi-level summaries:
  1. Executive summary (TL;DR — 2-3 sentences)
  2. Detailed summary (structured, sectioned)
  3. Key points with importance ratings
  4. Topic tags and sentiment

Uses the FAST model (gemini-2.0-flash) for speed with large context window.
"""
from __future__ import annotations

import json

from core.config import GOOGLE_API_KEY, FAST_MODEL_NAME, is_demo_mode
from core.schemas import KeyPoint, SummaryResult
from core.utils import truncate_for_llm

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
  "sentiment": "positive|neutral|negative",
  "word_count_original": <integer>
}}

Guidelines:
- The detailed_summary should be genuinely detailed, covering every major section.
- Key points should be specific, not generic. Include numbers/facts where available.
- List 5-10 key points.
- Topics should be 3-8 concise tags (e.g., "IT Strategy", "Risk Management").
- Sentiment reflects the overall tone of the document.
"""


class SummarizationAgent:
    """Generates rich, multi-level document summaries using the FAST model."""

    def summarize(self, raw_text: str, doc_id: str, doc_type: str = "unknown") -> SummaryResult:
        """
        Generate a full summary of the document.
        Uses Flash model with up to 120k chars (~30k tokens) for thorough analysis.
        """
        word_count = len(raw_text.split())

        if is_demo_mode():
            return self._demo_summarize(raw_text, doc_id, word_count)

        from langchain_google_genai import ChatGoogleGenerativeAI
        from langchain.schema import HumanMessage

        llm = ChatGoogleGenerativeAI(
            model=FAST_MODEL_NAME,
            google_api_key=GOOGLE_API_KEY,
            temperature=0.3,
        )

        # Use much more content — up to 30k tokens with Flash's large context
        content = truncate_for_llm(raw_text, max_tokens=30000)

        prompt = _SUMMARY_PROMPT.format(
            doc_type=doc_type,
            content=content,
        )

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
                original_wc = data.get("word_count_original", word_count)
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

        # Graceful degradation — return a minimal summary
        print(f"⚠️ Summarization fallback after {last_error}")
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
