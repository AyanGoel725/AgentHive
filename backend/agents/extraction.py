"""
Structured Extraction Agent — Fast, factual data extraction.
Switched from MODEL_NAME to FAST_MODEL_NAME for speed.
Uses temperature=0.0 for zero hallucination.
Uses the LLM pool for instant access.
"""
from __future__ import annotations

import json
import re

from core.config import FAST_MODEL_NAME, is_demo_mode
from core.llm_pool import get_llm


EXTRACTION_PROMPT = """\
You are a data extraction expert. Extract ALL structured information from the document text below as a JSON object.

Extract entities such as:
- Names, emails, phone numbers, addresses
- Dates, amounts, percentages
- Skills, qualifications, experiences
- Organizations, titles, roles
- Any key-value pairs or tabular data

Document text:
{text}

STRICT RULES:
- Extract ONLY data that is EXPLICITLY stated in the document text above.
- Do NOT infer, guess, or fabricate any data that is not directly present.
- If a field has no data in the document, omit it entirely — do NOT fill it with placeholder values.
- Return ONLY valid JSON. No markdown, no explanation — just the JSON object."""


def extract_structured(text: str, schema_hint: str | None = None) -> dict:
    """Extract structured data from document text and return as dict."""
    if is_demo_mode():
        return _demo_extract(text)

    from langchain.schema import HumanMessage

    llm = get_llm(FAST_MODEL_NAME, temperature=0.0)

    # Send up to 6K chars — sufficient for extraction
    prompt = EXTRACTION_PROMPT.format(text=text[:6000])
    if schema_hint:
        prompt += f"\n\nExtract data matching this schema hint: {schema_hint}"

    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        raw = response.content.strip()

        # Remove markdown code fences if present
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"raw_extraction": raw, "parse_error": True}
    except Exception as e:
        return {"error": str(e)}


def _demo_extract(text: str) -> dict:
    """Demo mode — extract basic patterns with regex."""
    result: dict = {}

    emails = re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", text)
    if emails:
        result["emails"] = list(set(emails))

    phones = re.findall(r"[\+]?[\d\s\-\(\)]{7,15}", text)
    phones = [p.strip() for p in phones if len(p.strip()) >= 7]
    if phones:
        result["phone_numbers"] = list(set(phones[:5]))

    urls = re.findall(r"https?://[^\s<>\"]+", text)
    if urls:
        result["urls"] = list(set(urls))

    dates = re.findall(
        r"\b\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}\b|\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2},? \d{4}\b",
        text,
    )
    if dates:
        result["dates"] = list(set(dates[:10]))

    names = re.findall(r"\b[A-Z][a-z]+ [A-Z][a-z]+\b", text)
    if names:
        result["potential_names"] = list(set(names[:10]))

    kv_pairs = re.findall(r"^([A-Za-z ]{2,30}):\s*(.+)$", text, re.MULTILINE)
    if kv_pairs:
        result["fields"] = {k.strip(): v.strip() for k, v in kv_pairs[:20]}

    if not result:
        result = {
            "note": "Demo mode - limited extraction without Gemini API key",
            "text_length": len(text),
            "word_count": len(text.split()),
        }

    result["_mode"] = "demo"
    return result
