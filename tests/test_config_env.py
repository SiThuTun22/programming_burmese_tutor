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


def test_env_file_has_torch_compile_disable() -> None:
    text = (config.ROOT / ".env.example").read_text(encoding="utf-8")
    assert "TORCH_COMPILE_DISABLE=1" in text
    assert "TUTOR_NO_REPEAT_NGRAM" in text
