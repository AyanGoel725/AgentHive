"""
AgentHive — 🧾 Structured Extraction Agent
Converts document text into structured JSON using LLM or demo fallback.
"""

from __future__ import annotations
import json
import re
from core.config import GOOGLE_API_KEY, MODEL_NAME, is_demo_mode


EXTRACTION_PROMPT = """You are a data extraction expert. Analyze the following document text and extract ALL structured information as a JSON object.

Extract entities such as:
- Names, emails, phone numbers, addresses
- Dates, amounts, percentages
- Skills, qualifications, experiences
- Organizations, titles, roles  
- Any key-value pairs or tabular data

Document text:
{text}

Return ONLY valid JSON. No markdown, no explanation — just the JSON object:"""


def extract_structured(text: str, schema_hint: str | None = None) -> dict:
    """Extract structured data from document text and return as dict."""
    if is_demo_mode():
        return _demo_extract(text)

    from langchain_google_genai import ChatGoogleGenerativeAI
    from langchain.schema import HumanMessage

    llm = ChatGoogleGenerativeAI(
        model=MODEL_NAME,
        google_api_key=GOOGLE_API_KEY,
        temperature=0.1,
    )

    prompt = EXTRACTION_PROMPT.format(text=text[:6000])
    if schema_hint:
        prompt += f"\n\nExtract data matching this schema hint: {schema_hint}"

    response = llm.invoke([HumanMessage(content=prompt)])
    raw = response.content.strip()

    # Try to parse JSON from the response
    try:
        # Remove markdown code fences if present
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"raw_extraction": raw, "parse_error": True}


def _demo_extract(text: str) -> dict:
    """Demo mode — extract basic patterns with regex."""
    import re

    result: dict = {}

    # Extract emails
    emails = re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", text)
    if emails:
        result["emails"] = list(set(emails))

    # Extract phone numbers
    phones = re.findall(r"[\+]?[\d\s\-\(\)]{7,15}", text)
    phones = [p.strip() for p in phones if len(p.strip()) >= 7]
    if phones:
        result["phone_numbers"] = list(set(phones[:5]))

    # Extract URLs
    urls = re.findall(r"https?://[^\s<>\"]+", text)
    if urls:
        result["urls"] = list(set(urls))

    # Extract dates
    dates = re.findall(
        r"\b\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}\b|\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2},? \d{4}\b",
        text,
    )
    if dates:
        result["dates"] = list(set(dates[:10]))

    # Extract capitalized names (simple heuristic)
    names = re.findall(r"\b[A-Z][a-z]+ [A-Z][a-z]+\b", text)
    if names:
        result["potential_names"] = list(set(names[:10]))

    # Extract key-value pairs like "Key: Value"
    kv_pairs = re.findall(r"^([A-Za-z ]{2,30}):\s*(.+)$", text, re.MULTILINE)
    if kv_pairs:
        result["fields"] = {k.strip(): v.strip() for k, v in kv_pairs[:20]}

    if not result:
        result = {
            "note": "Demo mode — limited extraction without Gemini API key",
            "text_length": len(text),
            "word_count": len(text.split()),
        }

    result["_mode"] = "demo"
    return result
