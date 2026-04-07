"""
AgentHive — 🔊 Voice Agent
Minimal backend component. Voice I/O is handled in the browser via Web Speech API.
This agent formats responses for optimal text-to-speech readback.
"""

from __future__ import annotations
import re


def format_for_speech(text: str) -> str:
    """
    Convert an agent response into text that sounds natural when read
    aloud by the browser's SpeechSynthesis API.
    """
    # Remove markdown formatting
    speech = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    speech = re.sub(r"\*([^*]+)\*", r"\1", speech)
    speech = re.sub(r"#{1,6}\s+", "", speech)
    speech = re.sub(r"`([^`]+)`", r"\1", speech)

    # Remove bullet points / list markers
    speech = re.sub(r"^\s*[-•]\s+", "", speech, flags=re.MULTILINE)
    speech = re.sub(r"^\s*\d+\.\s+", "", speech, flags=re.MULTILINE)

    # Collapse multiple newlines
    speech = re.sub(r"\n{2,}", ". ", speech)
    speech = re.sub(r"\n", " ", speech)

    # Clean up double periods
    speech = re.sub(r"\.{2,}", ".", speech)
    speech = re.sub(r"\s{2,}", " ", speech)

    return speech.strip()
