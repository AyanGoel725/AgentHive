"""
LLM Connection Pool — Singleton instances for ChatGoogleGenerativeAI.
Eliminates per-call instantiation overhead (~200-400ms per agent call).
Thread-safe and keyed by (model_name, temperature).
"""
from __future__ import annotations

import threading
from typing import Any

from core.config import GOOGLE_API_KEY, is_demo_mode


_lock = threading.Lock()
_pool: dict[tuple[str, float], Any] = {}


def get_llm(model_name: str, temperature: float = 0.0) -> Any:
    """
    Return a cached ChatGoogleGenerativeAI instance for the given
    model + temperature combo.  Thread-safe; creates on first access.
    """
    if is_demo_mode():
        return None

    key = (model_name, temperature)
    if key not in _pool:
        with _lock:
            # Double-check after acquiring lock
            if key not in _pool:
                from langchain_google_genai import ChatGoogleGenerativeAI

                _pool[key] = ChatGoogleGenerativeAI(
                    model=model_name,
                    google_api_key=GOOGLE_API_KEY,
                    temperature=temperature,
                )
    return _pool[key]
