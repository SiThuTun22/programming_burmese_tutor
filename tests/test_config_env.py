"""Config helpers (no GPU)."""

from tutor import config


def test_env_int_default() -> None:
    assert config.env_int("__MISSING_TUTOR_VAR__", 42) == 42


def test_env_str_default() -> None:
    assert config.env_str("__MISSING_TUTOR_VAR__", "default") == "default"


def test_env_csv_splits() -> None:
    assert config.env_csv("__MISSING__", "a, b ,c") == ["a", "b", "c"]


def test_root_points_at_repo() -> None:
    assert (config.ROOT / "pyproject.toml").is_file()


def test_env_file_is_hybrid_chat() -> None:
    text = (config.ROOT / ".env.example").read_text(encoding="utf-8")
    assert text.index("DATABASE_URL=") < text.index("GEMINI_API_KEYS=")
    assert "JWT_SECRET=" in text
    assert "GEMINI_MODEL=gemini-3.1-flash-lite" in text
    assert "GEMINI_TIMEOUT_SECONDS=120" in text
    assert "GEMINI_MAX_TOKENS=" in text
    assert "GEMINI_COOLING_SECONDS=60" in text
    assert "GEMINI_EMBEDDING_MODEL=gemini-embedding-001" in text
    assert "RAG_TOP_K=5" in text
    assert "TTS_ENGLISH_RATE=-5%" in text
    assert "TUTOR_BACKEND=aaa" in text
    assert "GEMINI_TUTOR_TEMPERATURE=0.8" in text
    assert "TUTOR_TEMPERATURE=0.85" in text
    assert "TUTOR_TOP_P=0.95" in text
    assert "MIIT_TEMPERATURE=0.7" in text
    assert "MIIT_TOP_P=0.9" in text
    assert "GEMINI_API_KEY" in text
    assert "GEMINI_API_KEYS" in text
    assert "GEMINI_API_KEY_FALLBACK" in text
    assert "GEMINI_TTS_NAMES_API_KEY" in text
    assert "HYBRID_CHAT_PROVIDER=gemini" in text
    assert "OPENROUTER_API_KEY" not in text


def test_aaa_config_aliases(monkeypatch) -> None:
    monkeypatch.delenv("GEMINI_MAX_TOKENS", raising=False)
    monkeypatch.delenv("TUTOR_CLOUD_MAX_TOKENS", raising=False)
    import importlib

    import tutor.config as cfg

    importlib.reload(cfg)
    assert cfg.CLOUD_MAX_TOKENS == 2048

    monkeypatch.setenv("TUTOR_CLOUD_MAX_TOKENS", "3072")
    importlib.reload(cfg)
    assert cfg.CLOUD_MAX_TOKENS == 3072

    monkeypatch.setenv("GEMINI_MAX_TOKENS", "1024")
    importlib.reload(cfg)
    assert cfg.CLOUD_MAX_TOKENS == 1024

    monkeypatch.delenv("RAG_TOP_K", raising=False)
    monkeypatch.setenv("MIIT_TOP_K", "3")
    importlib.reload(cfg)
    assert cfg.RAG_TOP_K == 3
    assert cfg.MIIT_TOP_K == 3

    monkeypatch.setenv("RAG_TOP_K", "7")
    importlib.reload(cfg)
    assert cfg.RAG_TOP_K == 7

    monkeypatch.delenv("GEMINI_EMBEDDING_MODEL", raising=False)
    monkeypatch.setenv("GEMINI_EMBED_MODEL", "custom-embed")
    importlib.reload(cfg)
    assert cfg.GEMINI_EMBEDDING_MODEL == "custom-embed"

    for name in (
        "GEMINI_MAX_TOKENS",
        "TUTOR_CLOUD_MAX_TOKENS",
        "RAG_TOP_K",
        "MIIT_TOP_K",
        "GEMINI_EMBED_MODEL",
        "GEMINI_EMBEDDING_MODEL",
    ):
        monkeypatch.delenv(name, raising=False)
    importlib.reload(cfg)


def test_clamp_temperature() -> None:
    assert config.clamp_temperature(-1) == 0.0
    assert config.clamp_temperature(0.85) == 0.85
    assert config.clamp_temperature(3) == 2.0


def test_clamp_top_p() -> None:
    assert config.clamp_top_p(0.0) == 1e-6
    assert config.clamp_top_p(0.95) == 0.95
    assert config.clamp_top_p(1.5) == 1.0


def test_generation_config_routes() -> None:
    tutor = config.generation_config("gemini")
    assert tutor["temperature"] == config.TUTOR_TEMPERATURE
    assert tutor["top_p"] == config.TUTOR_TOP_P
    miit = config.generation_config("miit")
    assert miit["temperature"] == config.MIIT_TEMPERATURE
    assert miit["top_p"] == config.MIIT_TOP_P
