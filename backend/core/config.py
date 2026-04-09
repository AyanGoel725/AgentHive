"""
Central configuration - reads .env and exposes typed settings.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", str(BASE_DIR / "uploads")))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# ── Google Gemini ──────────────────────────────────────────────────────────────
GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")

FAST_MODEL_NAME: str = os.getenv("FAST_MODEL_NAME", os.getenv("MODEL_NAME", "gemini-2.5-flash"))
QA_MODEL_NAME: str = os.getenv("QA_MODEL_NAME", os.getenv("MODEL_NAME", "gemini-2.5-flash"))
MODEL_NAME: str = os.getenv("MODEL_NAME", "gemini-2.5-flash")

# IMPORTANT: langchain-google-genai v2+ does NOT accept the 'models/' prefix.
# Strip it here at config load time so every agent gets the correct format.
_raw_embedding = os.getenv("EMBEDDING_MODEL", "text-embedding-004")
EMBEDDING_MODEL: str = (
    _raw_embedding[len("models/"):]
    if _raw_embedding.startswith("models/")
    else _raw_embedding
)

# ── Processing ─────────────────────────────────────────────────────────────────
CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "1000"))
CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "200"))
MAX_FILE_SIZE_MB: int = int(os.getenv("MAX_FILE_SIZE_MB", "50"))

# ── Feature Flags ──────────────────────────────────────────────────────────────
ENABLE_MOCK_MODE: bool = os.getenv("ENABLE_MOCK_MODE", "false").lower() == "true"
DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"

# ── Demo Mode Detection ────────────────────────────────────────────────────────
DEMO_MODE = (
    not bool(GOOGLE_API_KEY)
    or GOOGLE_API_KEY.startswith("your-")
    or ENABLE_MOCK_MODE
)


def is_demo_mode() -> bool:
    """Return True when no valid API key is configured or mock mode is on."""
    return DEMO_MODE


def validate_config() -> list[str]:
    """Return list of configuration warnings."""
    warnings = []
    if not GOOGLE_API_KEY and not ENABLE_MOCK_MODE:
        warnings.append(
            "GOOGLE_API_KEY is not set. Set ENABLE_MOCK_MODE=true for demo."
        )
    return warnings
