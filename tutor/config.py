"""Environment and path defaults for the tutor app."""

from __future__ import annotations

import os
from pathlib import Path

from tutor.env_bootstrap import load_project_env

ROOT = Path(__file__).resolve().parents[1]
load_project_env()


def env_path(name: str, default: Path) -> Path:
    value = os.environ.get(name, "").strip()
    return Path(value) if value else default


def env_int(name: str, default: int) -> int:
    value = os.environ.get(name, "").strip()
    return int(value) if value else default


def env_str(name: str, default: str) -> str:
    value = os.environ.get(name, "").strip()
    return value if value else default


def env_csv(name: str, default: str) -> list[str]:
    raw = os.environ.get(name, "").strip()
    if not raw:
        raw = default
    return [part.strip() for part in raw.split(",") if part.strip()]


def env_bool(name: str, default: bool) -> bool:
    value = os.environ.get(name, "").strip().lower()
    if not value:
        return default
    return value in ("1", "true", "yes", "on")


def env_float(name: str, default: float) -> float:
    value = os.environ.get(name, "").strip()
    return float(value) if value else default


def env_int_optional(name: str) -> int | None:
    value = os.environ.get(name, "").strip()
    return int(value) if value else None


def env_str_chain(*names: str, default: str) -> str:
    for name in names:
        value = os.environ.get(name, "").strip()
        if value:
            return value
    return default


def clamp_temperature(value: float) -> float:
    return max(0.0, min(2.0, float(value)))


def clamp_top_p(value: float) -> float:
    return max(1e-6, min(1.0, float(value)))


def generation_config(route: str | None = None) -> dict[str, float]:
    if (route or "").strip().lower() == "miit":
        return {
            "temperature": clamp_temperature(MIIT_TEMPERATURE),
            "top_p": clamp_top_p(MIIT_TOP_P),
        }
    return {
        "temperature": clamp_temperature(TUTOR_TEMPERATURE),
        "top_p": clamp_top_p(TUTOR_TOP_P),
    }


CLOUD_MAX_TOKENS = (
    env_int_optional("GEMINI_MAX_TOKENS")
    or env_int_optional("TUTOR_CLOUD_MAX_TOKENS")
    or 2048
)
GEMINI_TIMEOUT_SECONDS = env_int("GEMINI_TIMEOUT_SECONDS", 120)
GEMINI_PREFLIGHT_PROBE = env_bool("GEMINI_PREFLIGHT_PROBE", True)
TUTOR_TEMPERATURE = clamp_temperature(
    env_float(
        "TUTOR_TEMPERATURE",
        env_float("GEMINI_TUTOR_TEMPERATURE", 0.85),
    )
)
TUTOR_TOP_P = clamp_top_p(env_float("TUTOR_TOP_P", 0.95))
MIIT_TEMPERATURE = clamp_temperature(env_float("MIIT_TEMPERATURE", 0.7))
MIIT_TOP_P = clamp_top_p(env_float("MIIT_TOP_P", 0.9))
GRADIO_HOST = env_str("TUTOR_HOST", "0.0.0.0")
GRADIO_PORT = env_int("TUTOR_PORT", 7860)
API_HOST = env_str("TUTOR_API_HOST", "0.0.0.0")
API_PORT = env_int("TUTOR_API_PORT", 8001)
CORS_ORIGINS = env_csv("TUTOR_CORS_ORIGINS", "http://localhost:5173")
API_KEY = env_str("TUTOR_API_KEY", "")
MAX_CODE_CHARS = env_int("TUTOR_MAX_CODE_CHARS", 16384)
TTS_ENABLED = env_bool("TUTOR_TTS_ENABLED", True)
TTS_SKIP_GEMINI_HELPERS = env_bool("TTS_SKIP_GEMINI_HELPERS", False)
TTS_VOICE = env_str("TUTOR_TTS_VOICE", "my-MM-NilarNeural")
TTS_VOICE_FALLBACK = "my-MM-ThihaNeural"
TTS_AUTOPLAY = env_bool("TUTOR_TTS_AUTOPLAY", False)
TTS_CACHE_DIR = ROOT / ".cache" / "tts"
TTS_ENGLISH_RATE = env_str("TTS_ENGLISH_RATE", "-5%")
TTS_LEXICON_PATH = env_path("TTS_LEXICON_PATH", TTS_CACHE_DIR / "lexicon.json")
TTS_SPELL_PATH = env_path("TTS_SPELL_PATH", TTS_CACHE_DIR / "spell.json")
TUTOR_BACKEND = env_str("TUTOR_BACKEND", "aaa").strip().lower()
GEMINI_API_KEYS = env_csv("GEMINI_API_KEYS", "")
GEMINI_API_KEY = env_str("GEMINI_API_KEY", "")
GEMINI_API_KEY_FALLBACK = env_str("GEMINI_API_KEY_FALLBACK", "")
GEMINI_TTS_NAMES_API_KEY = env_str("GEMINI_TTS_NAMES_API_KEY", "")
GEMINI_COOLING_SECONDS = env_int("GEMINI_COOLING_SECONDS", 60)
GEMINI_MODEL = env_str("GEMINI_MODEL", "gemini-3.1-flash-lite")
GEMINI_EMBEDDING_MODEL = env_str_chain(
    "GEMINI_EMBEDDING_MODEL",
    "GEMINI_EMBED_MODEL",
    default="gemini-embedding-001",
)
GEMINI_EMBED_MODEL = GEMINI_EMBEDDING_MODEL
MIIT_DIR = ROOT / "data" / "miit"
MIIT_INDEX_PATH = env_path("MIIT_INDEX_PATH", MIIT_DIR / "index.json")
RAG_TOP_K = env_int_optional("RAG_TOP_K") or env_int_optional("MIIT_TOP_K") or 5
MIIT_TOP_K = RAG_TOP_K
MIIT_MIN_SIMILARITY = env_float("MIIT_MIN_SIMILARITY", 0.55)
MIIT_RETRIEVAL = env_str("MIIT_RETRIEVAL", "embed").strip().lower()
HYBRID_DEBUG = env_bool("TUTOR_HYBRID_DEBUG", False)
HYBRID_CHAT_PROVIDER = env_str("HYBRID_CHAT_PROVIDER", "gemini").strip().lower()
