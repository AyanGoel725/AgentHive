"""
AgentHive — ✍️ Summarization Agent
Generates document summaries using LLM or demo fallback.
"""

from __future__ import annotations
from core.config import GOOGLE_API_KEY, MODEL_NAME, is_demo_mode


SUMMARIZE_PROMPT = """You are a document summarization expert. Provide a concise, well-structured summary of the following text.
Focus on:
- Key points and main ideas
- Important facts, figures, and entities
- Actionable insights

If a user query is provided, tailor the summary to address that query specifically.

Document text:
{text}

{query_section}

Provide a clear, professional summary:"""


def summarize(text: str, query: str | None = None) -> str:
    """Generate a summary of the given text."""
    if is_demo_mode():
        return _demo_summarize(text, query)

    from langchain_google_genai import ChatGoogleGenerativeAI
    from langchain.schema import HumanMessage

    llm = ChatGoogleGenerativeAI(
        model=MODEL_NAME,
        google_api_key=GOOGLE_API_KEY,
        temperature=0.3,
    )

    query_section = f"User query: {query}" if query else ""
    prompt = SUMMARIZE_PROMPT.format(text=text[:6000], query_section=query_section)

    response = llm.invoke([HumanMessage(content=prompt)])
    return response.content


def _demo_summarize(text: str, query: str | None = None) -> str:
    """Demo mode fallback — produces a reasonable summary without LLM."""
    sentences = [s.strip() for s in text.replace("\n", ". ").split(". ") if len(s.strip()) > 20]

    if len(sentences) <= 3:
        summary_sentences = sentences
    else:
        # Take first, middle, and last important sentences
        summary_sentences = [
            sentences[0],
            sentences[len(sentences) // 3],
            sentences[2 * len(sentences) // 3],
            sentences[-1],
        ]

    summary = "📄 **Document Summary** (Demo Mode)\n\n"
    summary += "**Key Points:**\n"
    for i, s in enumerate(summary_sentences[:5], 1):
        summary += f"  {i}. {s}.\n"

    summary += f"\n**Document Stats:** {len(sentences)} sentences extracted, {len(text)} characters total."

    if query:
        summary += f"\n\n**Query Focus:** \"{query}\" — In demo mode, full query-focused summarization requires a Gemini API key."

    return summary
