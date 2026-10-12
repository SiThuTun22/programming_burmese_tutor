from __future__ import annotations

import os
from pathlib import Path

from advanced_alchemy.config import AlembicAsyncConfig, AsyncSessionConfig
from advanced_alchemy.extensions.litestar import SQLAlchemyAsyncConfig
from dotenv import load_dotenv

DEFAULT_DATABASE_URL = 'postgresql+asyncpg://aaa:aaa@localhost:5435/aaa'
DEFAULT_JWT_SECRET = 'change-me-in-production'
DEFAULT_GEMINI_MODEL = 'gemini-2.0-flash'
DEFAULT_GEMINI_TIMEOUT_SECONDS = 120
DEFAULT_GEMINI_MAX_TOKENS = 2048
DEFAULT_GEMINI_VISION_MAX_TOKENS = 512
DEFAULT_GEMINI_VISION_TIMEOUT_SECONDS = 360
DEFAULT_VISION_MAX_PDF_PAGES = 0
DEFAULT_VISION_MAX_IMAGE_EDGE = 768
DEFAULT_GEMINI_COOLING_SECONDS = 60
DEFAULT_GEMINI_TUTOR_TEMPERATURE = 0.8
DEFAULT_GEMINI_EMBEDDING_MODEL = 'gemini-embedding-001'
DEFAULT_GEMINI_EMBEDDING_DIMS = 768
DEFAULT_RAG_TOP_K = 5
DEFAULT_TTS_ENGLISH_RATE = '-5%'
APP_VERSION = '0.1.0'
MIGRATION_PATH = 'migrations'
_env_path = Path('.env')
load_dotenv(_env_path, override=False)


def get_database_url() -> str:
    url = os.environ.get('DATABASE_URL', DEFAULT_DATABASE_URL)
    return url


def get_jwt_secret() -> str:
    raw = os.environ.get('JWT_SECRET')
    if raw is None:
        return DEFAULT_JWT_SECRET
    stripped = raw.strip()
    if len(stripped) == 0:
        return DEFAULT_JWT_SECRET
    return stripped


def _split_key_field(raw: str) -> list[str]:
    return [part.strip() for part in (raw or '').split(',') if part.strip()]


def get_gemini_api_keys() -> list[str]:
    """Same key order as tutor.gemini_pool.resolved_gemini_api_keys."""
    multi = os.environ.get('GEMINI_API_KEYS', '').strip()
    if multi:
        source = _split_key_field(multi)
    else:
        source = _split_key_field(os.environ.get('GEMINI_API_KEY', ''))
    fallback = _split_key_field(os.environ.get('GEMINI_API_KEY_FALLBACK', ''))
    keys: list[str] = []
    seen: set[str] = set()
    for raw in source + fallback:
        if raw in seen:
            continue
        keys.append(raw)
        seen.add(raw)
    return keys


def get_gemini_model() -> str:
    model = os.environ.get('GEMINI_MODEL', DEFAULT_GEMINI_MODEL)
    return model


def get_gemini_vision_model() -> str:
    vision_model = os.environ.get('GEMINI_VISION_MODEL', '')
    stripped = vision_model.strip()
    if len(stripped) == 0:
        chat_model = get_gemini_model()
        return chat_model
    return stripped


def get_gemini_timeout_seconds() -> int:
    raw = os.environ.get('GEMINI_TIMEOUT_SECONDS', str(DEFAULT_GEMINI_TIMEOUT_SECONDS))
    timeout = int(raw)
    return timeout


def get_gemini_max_tokens() -> int:
    raw = os.environ.get('GEMINI_MAX_TOKENS')
    if raw is None:
        return DEFAULT_GEMINI_MAX_TOKENS
    stripped = raw.strip()
    if len(stripped) == 0:
        return DEFAULT_GEMINI_MAX_TOKENS
    max_tokens = int(stripped)
    return max_tokens


def get_gemini_vision_max_tokens() -> int:
    raw = os.environ.get('GEMINI_VISION_MAX_TOKENS', str(DEFAULT_GEMINI_VISION_MAX_TOKENS))
    max_tokens = int(raw)
    return max_tokens


def get_gemini_vision_timeout_seconds() -> int:
    raw = os.environ.get('GEMINI_VISION_TIMEOUT_SECONDS', str(DEFAULT_GEMINI_VISION_TIMEOUT_SECONDS))
    timeout = int(raw)
    return timeout


def get_gemini_cooling_seconds() -> float:
    raw = os.environ.get('GEMINI_COOLING_SECONDS', str(DEFAULT_GEMINI_COOLING_SECONDS))
    cooling = float(raw)
    return cooling


def get_gemini_tutor_temperature() -> float:
    raw = os.environ.get('GEMINI_TUTOR_TEMPERATURE', str(DEFAULT_GEMINI_TUTOR_TEMPERATURE))
    temperature = float(raw)
    return temperature


def get_vision_max_pdf_pages() -> int:
    raw = os.environ.get('VISION_MAX_PDF_PAGES', str(DEFAULT_VISION_MAX_PDF_PAGES))
    max_pages = int(raw)
    return max_pages


def get_vision_max_image_edge() -> int:
    raw = os.environ.get('VISION_MAX_IMAGE_EDGE', str(DEFAULT_VISION_MAX_IMAGE_EDGE))
    max_edge = int(raw)
    return max_edge


def get_gemini_embedding_model() -> str:
    model = os.environ.get('GEMINI_EMBEDDING_MODEL', DEFAULT_GEMINI_EMBEDDING_MODEL)
    return model


def get_gemini_embedding_dims() -> int:
    raw = os.environ.get('GEMINI_EMBEDDING_DIMS', str(DEFAULT_GEMINI_EMBEDDING_DIMS))
    dims = int(raw)
    return dims


def get_rag_top_k() -> int:
    raw = os.environ.get('RAG_TOP_K', str(DEFAULT_RAG_TOP_K))
    top_k = int(raw)
    return top_k


def get_tts_data_dir() -> Path:
    raw = os.environ.get('TTS_DATA_DIR', '')
    stripped = raw.strip()
    if len(stripped) > 0:
        data_dir = Path(stripped)
        return data_dir
    config_path = Path(__file__).resolve()
    lib_dir = config_path.parent
    app_dir = lib_dir.parent
    project_root = app_dir.parent
    data_dir = project_root / 'data'
    return data_dir


def get_tts_lexicon_path() -> Path:
    data_dir = get_tts_data_dir()
    lexicon_path = data_dir / 'tts_lexicon.json'
    return lexicon_path


def get_tts_spell_path() -> Path:
    data_dir = get_tts_data_dir()
    spell_path = data_dir / 'tts_spell.json'
    return spell_path


def get_tts_english_rate() -> str:
    raw = os.environ.get('TTS_ENGLISH_RATE', DEFAULT_TTS_ENGLISH_RATE)
    stripped = raw.strip()
    if len(stripped) == 0:
        return DEFAULT_TTS_ENGLISH_RATE
    return stripped


def get_tts_audio_dir() -> Path:
    data_dir = get_tts_data_dir()
    audio_dir = data_dir / 'tts-audio'
    return audio_dir


def get_knowledge_dir() -> Path:
    raw = os.environ.get('KNOWLEDGE_DIR', '')
    stripped = raw.strip()
    if len(stripped) > 0:
        knowledge_dir = Path(stripped)
        return knowledge_dir
    config_path = Path(__file__).resolve()
    lib_dir = config_path.parent
    app_dir = lib_dir.parent
    project_root = app_dir.parent
    knowledge_dir = project_root / 'knowledge'
    return knowledge_dir


def get_alchemy_config() -> SQLAlchemyAsyncConfig:
    database_url = get_database_url()
    session_config = AsyncSessionConfig(expire_on_commit=False)
    alembic_config = AlembicAsyncConfig(script_location=MIGRATION_PATH)
    alchemy_config = SQLAlchemyAsyncConfig(
        connection_string=database_url,
        session_config=session_config,
        alembic_config=alembic_config,
        before_send_handler='autocommit',
    )
    return alchemy_config
