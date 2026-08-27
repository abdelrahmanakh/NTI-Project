# ============================================================
# Gemini EduRAG - Configuration
# ============================================================

import os
from pathlib import Path

from dotenv import load_dotenv


# ============================================================
# PROJECT ROOT
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent


# ============================================================
# ENVIRONMENT
# ============================================================

ENV_FILE = PROJECT_ROOT / ".env"

load_dotenv(
    dotenv_path=ENV_FILE
)


# ============================================================
# API KEYS
# ============================================================

GEMINI_API_KEY = os.getenv(
    "GEMINI_API_KEY",
    "",
).strip()

GROQ_API_KEY = os.getenv(
    "GROQ_API_KEY",
    "",
).strip()


# ============================================================
# MODEL CONFIGURATION
# ============================================================

# ------------------------------------------------------------
# Gemini
# ------------------------------------------------------------

GEMINI_CHAT_MODEL = os.getenv(
    "GEMINI_CHAT_MODEL",
    "gemini-3.5-flash",
).strip()

GEMINI_EMBED_MODEL = os.getenv(
    "GEMINI_EMBED_MODEL",
    "gemini-embedding-001",
).strip()

GEMINI_TTS_MODEL = os.getenv(
    "GEMINI_TTS_MODEL",
    "gemini-2.5-flash-preview-tts",
).strip()


# ------------------------------------------------------------
# Groq
# ------------------------------------------------------------

GROQ_CHAT_MODEL = os.getenv(
    "GROQ_CHAT_MODEL",
    "openai/gpt-oss-120b",
).strip()

GROQ_FALLBACK_MODEL_1 = os.getenv(
    "GROQ_FALLBACK_MODEL_1",
    "meta-llama/llama-4-scout-17b-16e-instruct",
).strip()

GROQ_FALLBACK_MODEL_2 = os.getenv(
    "GROQ_FALLBACK_MODEL_2",
    "qwen/qwen3-32b",
).strip()


# ============================================================
# RAG CONFIGURATION
# ============================================================

CHROMA_PERSIST_DIRECTORY = os.getenv(
    "CHROMA_PERSIST_DIRECTORY",
    str(PROJECT_ROOT / "data" / "chroma"),
).strip()

CHROMA_COLLECTION_NAME = os.getenv(
    "CHROMA_COLLECTION_NAME",
    "documents",
).strip()


# ------------------------------------------------------------
# Chunking
# ------------------------------------------------------------

CHUNK_SIZE = int(
    os.getenv(
        "CHUNK_SIZE",
        "500",
    )
)

CHUNK_OVERLAP = int(
    os.getenv(
        "CHUNK_OVERLAP",
        "100",
    )
)


# ------------------------------------------------------------
# Retrieval
# ------------------------------------------------------------

TOP_K = int(
    os.getenv(
        "TOP_K",
        "3",
    )
)


# ============================================================
# STORAGE DIRECTORIES
# ============================================================

DATA_DIR = PROJECT_ROOT / "data"

OCR_CACHE_DIR = DATA_DIR / "ocr_cache"

YOUTUBE_CACHE_DIR = DATA_DIR / "youtube_cache"

PODCAST_CACHE_DIR = DATA_DIR / "podcast_cache"

PODCAST_OUTPUT_DIR = DATA_DIR / "podcasts"


# ============================================================
# CREATE REQUIRED DIRECTORIES
# ============================================================

for directory in [
    DATA_DIR,
    OCR_CACHE_DIR,
    YOUTUBE_CACHE_DIR,
    PODCAST_CACHE_DIR,
    PODCAST_OUTPUT_DIR,
]:

    directory.mkdir(
        parents=True,
        exist_ok=True,
    )


# ============================================================
# VALIDATION HELPERS
# ============================================================

def has_gemini() -> bool:
    """
    Return True if Gemini API is configured.
    """

    return bool(
        GEMINI_API_KEY
    )


def has_groq() -> bool:
    """
    Return True if Groq API is configured.
    """

    return bool(
        GROQ_API_KEY
    )


def validate_configuration() -> dict:
    """
    Return a simple configuration status report.

    This does NOT make API calls.
    """

    return {
        "gemini": has_gemini(),
        "groq": has_groq(),
        "gemini_chat_model": GEMINI_CHAT_MODEL,
        "gemini_embedding_model": GEMINI_EMBED_MODEL,
        "gemini_tts_model": GEMINI_TTS_MODEL,
        "groq_chat_model": GROQ_CHAT_MODEL,
        "groq_fallback_1": GROQ_FALLBACK_MODEL_1,
        "groq_fallback_2": GROQ_FALLBACK_MODEL_2,
        "chroma_collection": CHROMA_COLLECTION_NAME,
        "top_k": TOP_K,
        "chunk_size": CHUNK_SIZE,
        "chunk_overlap": CHUNK_OVERLAP,
    }


# ============================================================
# WARNINGS
# ============================================================

if not GEMINI_API_KEY:

    print(
        "WARNING: GEMINI_API_KEY is not configured."
    )


if not GROQ_API_KEY:

    print(
        "WARNING: GROQ_API_KEY is not configured."
    )