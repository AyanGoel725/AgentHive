"""
AgentHive — 🎯 Orchestrator Agent
The brain of the system: classifies user intent and routes queries to the correct agent.
"""

from __future__ import annotations
from core.config import GOOGLE_API_KEY, MODEL_NAME, is_demo_mode
from core.schemas import AgentInfo, QueryResponse
from agents import voice as voice_agent
import pandas as pd


# ── Agent registry ───────────────────────────────────────────────────

AGENTS = {
    "summarization": AgentInfo(
        name="Summarization Agent",
        icon="✍️",
        description="Generates concise document summaries",
    ),
    "extraction": AgentInfo(
        name="Extraction Agent",
        icon="🧾",
        description="Extracts structured data as JSON",
    ),
    "excel_insight": AgentInfo(
        name="Excel Insight Agent",
        icon="📊",
        description="Analyzes datasets for trends and insights",
    ),
    "search": AgentInfo(
        name="Understanding Agent",
        icon="🧠",
        description="Performs semantic search across documents",
    ),
}


# ── Intent keywords ──────────────────────────────────────────────────

INTENT_MAP = {
    "summarization": [
        "summarize", "summary", "overview", "brief", "recap",
        "key points", "main ideas", "tldr", "tl;dr", "outline",
    ],
    "extraction": [
        "extract", "json", "structured", "fields", "parse",
        "entities", "data extraction", "convert to json",
        "key-value", "pull out", "get fields",
    ],
    "excel_insight": [
        "analyze", "analysis", "trend", "insight", "pattern",
        "top values", "statistics", "correlat", "excel",
        "data analysis", "chart", "distribution", "compare",
    ],
    "search": [
        "search", "find", "where", "look for", "locate",
        "what does it say about", "mention", "reference",
    ],
}


def classify_intent(query: str, file_type: str | None = None) -> str:
    """
    Classify the user's intent to determine which agent to call.
    Uses keyword matching first, then LLM fallback for ambiguous queries.
    """
    q = query.lower().strip()

    # Score each intent
    scores: dict[str, int] = {}
    for intent, keywords in INTENT_MAP.items():
        score = sum(1 for kw in keywords if kw in q)
        scores[intent] = score

    best = max(scores, key=scores.get)  # type: ignore
    if scores[best] > 0:
        return best

    # If file is Excel and no clear intent, default to excel_insight
    if file_type == "excel":
        return "excel_insight"

    # If no clear intent, try LLM classification (or default in demo mode)
    if not is_demo_mode():
        return _llm_classify(query)

    # Demo fallback: default to summarization
    return "summarization"


def _llm_classify(query: str) -> str:
    """Use LLM to classify ambiguous queries."""
    from langchain_google_genai import ChatGoogleGenerativeAI
    from langchain.schema import HumanMessage

    llm = ChatGoogleGenerativeAI(
        model=MODEL_NAME,
        google_api_key=GOOGLE_API_KEY,
        temperature=0.0,
    )

    prompt = f"""Classify this user query into one of these categories:
- "summarization" (user wants a summary or overview)
- "extraction" (user wants structured data / JSON output)
- "excel_insight" (user wants data analysis, trends, statistics)
- "search" (user wants to find specific information)

Query: "{query}"

Respond with ONLY the category name, nothing else:"""

    response = llm.invoke([HumanMessage(content=prompt)])
    result = response.content.strip().lower().strip('"')

    if result in INTENT_MAP:
        return result
    return "summarization"


def route_query(
    query: str,
    text: str | None = None,
    df: pd.DataFrame | None = None,
    vector_store=None,
    file_type: str | None = None,
    is_voice: bool = False,
) -> QueryResponse:
    """
    Main entry point: classify intent, invoke the appropriate agent,
    and return a unified response.
    """
    intent = classify_intent(query, file_type)
    agent_info = AGENTS[intent]

    try:
        if intent == "summarization":
            from agents.summarization import summarize
            content = text or "No document text available."
            answer = summarize(content, query)
            return QueryResponse(
                success=True,
                agent=agent_info,
                answer=answer,
                audio_text=voice_agent.format_for_speech(answer) if is_voice else "",
            )

        elif intent == "extraction":
            from agents.extraction import extract_structured
            content = text or "No document text available."
            structured = extract_structured(content)
            answer = "✅ Structured data extracted successfully. See the JSON output panel."
            return QueryResponse(
                success=True,
                agent=agent_info,
                answer=answer,
                structured_data=structured,
                audio_text=voice_agent.format_for_speech(
                    f"I've extracted structured data from the document. Found {len(structured)} fields."
                ) if is_voice else "",
            )

        elif intent == "excel_insight":
            if df is None:
                return QueryResponse(
                    success=False,
                    agent=agent_info,
                    error="No Excel/CSV file uploaded. Please upload a dataset first.",
                )
            from agents.excel_insight import analyze_dataframe
            insights = analyze_dataframe(df, query)
            return QueryResponse(
                success=True,
                agent=agent_info,
                answer=insights["narrative"],
                insights=insights["stats"],
                audio_text=voice_agent.format_for_speech(insights["narrative"]) if is_voice else "",
            )

        elif intent == "search":
            if vector_store is None:
                return QueryResponse(
                    success=False,
                    agent=agent_info,
                    error="No document indexed. Please upload a document first.",
                )
            from agents.understanding import semantic_search
            results = semantic_search(query, vector_store, k=5)
            answer = "🔍 **Search Results:**\n\n"
            for i, chunk in enumerate(results, 1):
                answer += f"**Result {i}:**\n{chunk}\n\n---\n\n"
            return QueryResponse(
                success=True,
                agent=agent_info,
                answer=answer,
                audio_text=voice_agent.format_for_speech(
                    f"I found {len(results)} relevant sections. " +
                    (results[0][:200] if results else "No results found.")
                ) if is_voice else "",
            )

        else:
            return QueryResponse(
                success=False,
                agent=agent_info,
                error=f"Unknown intent: {intent}",
            )

    except Exception as e:
        return QueryResponse(
            success=False,
            agent=agent_info,
            error=str(e),
        )
