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


CLOUD_MAX_TOKENS = env_int("TUTOR_CLOUD_MAX_TOKENS", 3072)
TUTOR_TEMPERATURE = clamp_temperature(env_float("TUTOR_TEMPERATURE", 0.85))
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
TTS_VOICE = env_str("TUTOR_TTS_VOICE", "my-MM-NilarNeural")
TTS_VOICE_FALLBACK = "my-MM-ThihaNeural"
TTS_AUTOPLAY = env_bool("TUTOR_TTS_AUTOPLAY", False)
TTS_CACHE_DIR = ROOT / ".cache" / "tts"
TUTOR_BACKEND = env_str("TUTOR_BACKEND", "hybrid").strip().lower()
GEMINI_API_KEY = env_str("GEMINI_API_KEY", "")
GEMINI_API_KEY_FALLBACK = env_str("GEMINI_API_KEY_FALLBACK", "")
GEMINI_TTS_NAMES_API_KEY = env_str("GEMINI_TTS_NAMES_API_KEY", "")
GEMINI_MODEL = env_str("GEMINI_MODEL", "gemini-2.0-flash")
GEMINI_EMBED_MODEL = env_str("GEMINI_EMBED_MODEL", "gemini-embedding-001")
MIIT_DIR = ROOT / "data" / "miit"
MIIT_INDEX_PATH = env_path("MIIT_INDEX_PATH", MIIT_DIR / "index.json")
MIIT_TOP_K = env_int("MIIT_TOP_K", 3)
MIIT_MIN_SIMILARITY = env_float("MIIT_MIN_SIMILARITY", 0.55)
MIIT_RETRIEVAL = env_str("MIIT_RETRIEVAL", "embed").strip().lower()
HYBRID_DEBUG = env_bool("TUTOR_HYBRID_DEBUG", False)
HYBRID_CHAT_PROVIDER = env_str("HYBRID_CHAT_PROVIDER", "gemini").strip().lower()
OPENROUTER_API_KEY = env_str("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = env_str(
    "OPENROUTER_MODEL", "meta-llama/llama-3.2-3b-instruct:free"
)
OPENROUTER_BASE_URL = env_str("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
