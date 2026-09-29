"""Environment and path defaults for the tutor app."""

from __future__ import annotations

import os
from pathlib import Path

from tutor.env_bootstrap import load_project_env

ROOT = Path(__file__).resolve().parents[1]
load_project_env()

DEFAULT_BASE_MODEL = "google/gemma-3-4b-it"
FALLBACK_BASE_MODEL = "unsloth/gemma-3-4b-it"

LANG_SUFFIX = "မြန်မာဘာသာဖြင့်သာ ရှင်းပြပါ"


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


def env_float(name: str, default: float) -> float:
    value = os.environ.get(name, "").strip()
    return float(value) if value else default


def env_bool(name: str, default: bool) -> bool:
    value = os.environ.get(name, "").strip().lower()
    if not value:
        return default
    return value in ("1", "true", "yes", "on")


def inference_device_map() -> str | dict[str, int]:
    """Device map for 4-bit inference (single GPU by default)."""
    raw = os.environ.get("TUTOR_DEVICE_MAP", "").strip().lower()
    if raw == "auto":
        return "auto"
    return {"": 0}


ADAPTER_PATH = env_path("TUTOR_ADAPTER", ROOT / "outputs" / "lora_adapter")
BASE_MODEL = env_str("TUTOR_BASE_MODEL", DEFAULT_BASE_MODEL)
MAX_NEW_TOKENS = env_int("TUTOR_MAX_NEW_TOKENS", 384)
NO_REPEAT_NGRAM = env_int("TUTOR_NO_REPEAT_NGRAM", 12)
REPETITION_PENALTY = env_float("TUTOR_REPETITION_PENALTY", 1.12)
GRADIO_HOST = env_str("TUTOR_HOST", "0.0.0.0")
GRADIO_PORT = env_int("TUTOR_PORT", 7860)
API_HOST = env_str("TUTOR_API_HOST", "0.0.0.0")
API_PORT = env_int("TUTOR_API_PORT", 8001)
CORS_ORIGINS = env_csv("TUTOR_CORS_ORIGINS", "http://localhost:5173")
API_KEY = env_str("TUTOR_API_KEY", "")
MAX_CODE_CHARS = env_int("TUTOR_MAX_CODE_CHARS", 16384)
MIN_VRAM_GIB = env_float("TUTOR_MIN_VRAM_GIB", 5.0)
TTS_ENABLED = env_bool("TUTOR_TTS_ENABLED", True)
TTS_VOICE = env_str("TUTOR_TTS_VOICE", "my-MM-ThihaNeural")
TTS_VOICE_FALLBACK = "my-MM-NilarNeural"
TTS_AUTOPLAY = env_bool("TUTOR_TTS_AUTOPLAY", False)
TTS_CACHE_DIR = ROOT / ".cache" / "tts"
STYLE_GUIDE_ENABLED = env_bool("TUTOR_STYLE_GUIDE", True)
INFERENCE_PROMPT_PATH = env_path(
    "TUTOR_INFERENCE_PROMPT_PATH",
    ROOT / "data" / "inference_prompt.md",
)
