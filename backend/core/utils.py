"""
Shared utility functions used across agents.
"""
import hashlib
import re
import time
import uuid
from pathlib import Path
from typing import Any


def generate_doc_id() -> str:
    """Generate a short, unique document identifier."""
    return uuid.uuid4().hex[:12]


def compute_file_hash(file_path: Path) -> str:
    """SHA-256 hash of a file for deduplication."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def clean_text(text: str) -> str:
    """
    Normalize whitespace and remove junk characters from extracted text.
    Preserves paragraph breaks.
    """
    # Normalize line endings
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # Remove excessive blank lines (keep max 2)
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Remove null bytes
    text = text.replace("\x00", "")
    # Normalize whitespace within lines
    lines = [" ".join(line.split()) for line in text.splitlines()]
    return "\n".join(lines).strip()


def estimate_tokens(text: str) -> int:
    """Rough token count estimate (1 token ≈ 4 characters)."""
    return len(text) // 4


def estimate_reading_time(word_count: int, wpm: int = 200) -> float:
    """Estimate reading time in minutes."""
    return round(word_count / wpm, 1)


def truncate_for_llm(text: str, max_tokens: int = 30000) -> str:
    """
    Truncate text to fit within LLM context window.
    Preserves beginning and end for better context.
    Default raised to 30k tokens (~120k chars) for Flash model's large context.
    """
    max_chars = max_tokens * 4
    if len(text) <= max_chars:
        return text
    # Keep 80% from start, 20% from end
    start_len = int(max_chars * 0.8)
    end_len = int(max_chars * 0.2)
    return (
        text[:start_len]
        + "\n\n[... content truncated for processing ...]\n\n"
        + text[-end_len:]
    )


class Timer:
    """Simple context manager for timing operations."""

    def __init__(self):
        self.elapsed: float = 0.0

    def __enter__(self):
        self._start = time.perf_counter()
        return self

    def __exit__(self, *args: Any):
        self.elapsed = round(time.perf_counter() - self._start, 3)
