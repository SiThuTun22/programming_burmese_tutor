"""Gemini client helpers (no live API)."""

import httpx

from tutor.gemini_client import (
    _retry_delay_seconds,
    embedding_vectors_from_response,
    exception_retry_delay,
)


class _FakeEmbedding:
    def __init__(self, values: list[float]) -> None:
        self.values = values


class _FakeEmbedResponse:
    def __init__(self, embeddings: list[_FakeEmbedding]) -> None:
        self.embeddings = embeddings


def test_embedding_vectors_from_response() -> None:
    response = _FakeEmbedResponse([_FakeEmbedding([0.1, 0.2]), _FakeEmbedding([0.3])])
    assert embedding_vectors_from_response(response) == [[0.1, 0.2], [0.3]]


def test_retry_delay_parses_429_message() -> None:
    class Err(Exception):
        code = 429

    msg = "429 RESOURCE_EXHAUSTED ... Please retry in 43.835452802s."
    err = Err(msg)
    assert _retry_delay_seconds(err) >= 44.0


def test_retry_delay_non_429() -> None:
    class Err(Exception):
        code = 400

    assert _retry_delay_seconds(Err("bad")) == 0.0


def test_exception_retry_delay_connect_error() -> None:
    assert exception_retry_delay(httpx.ConnectError("reset"), 0) == 1.0
    assert exception_retry_delay(httpx.ConnectError("reset"), 3) == 8.0
    assert exception_retry_delay(httpx.ConnectError("reset"), 10) == 60.0


def test_exception_retry_delay_client_5xx() -> None:
    from google.genai.errors import ClientError

    exc = ClientError(503, {}, None)
    assert exception_retry_delay(exc, 0) == 5.0


def test_exception_retry_delay_server_503_backoff() -> None:
    from google.genai.errors import ServerError

    exc = ServerError(503, {"error": {"status": "UNAVAILABLE"}}, None)
    assert exception_retry_delay(exc, 0) == 5.0
    assert exception_retry_delay(exc, 1) == 10.0
    assert exception_retry_delay(exc, 2) == 20.0
    assert exception_retry_delay(exc, 3) == 30.0
    assert exception_retry_delay(exc, 8) == 30.0


def test_exception_retry_delay_client_400_not_retryable() -> None:
    from google.genai.errors import ClientError

    exc = ClientError(400, {}, None)
    assert exception_retry_delay(exc, 0) is None


def test_gemini_generate_config_disables_thinking_on_2_5(monkeypatch) -> None:
    from tutor.gemini_client import GeminiClient

    captured_kwargs = {}

    class DummyModels:
        def generate_content(self, **kwargs):
            captured_kwargs.update(kwargs)
            class Resp:
                text = "အောင်မြင်ပါသည်"
            return Resp()

    class DummyClient:
        models = DummyModels()

    monkeypatch.setattr("google.genai.Client", lambda **kw: DummyClient())

    client = GeminiClient(api_key="test_key", fallback_api_key="", generate_model="gemini-2.5-flash")
    result = client.generate([{"role": "user", "content": "မင်္ဂလာပါ"}], max_new_tokens=2048)
    assert result == "အောင်မြင်ပါသည်"
    config = captured_kwargs.get("config", {})
    assert config.get("max_output_tokens") == 2048
    assert config.get("thinking_config") == {"thinking_budget": 0}
    assert config.get("temperature") == 0.85
    assert config.get("top_p") == 0.95


def test_gemini_generate_honors_sampling_override(monkeypatch) -> None:
    from tutor.gemini_client import GeminiClient

    captured_kwargs = {}

    class DummyModels:
        def generate_content(self, **kwargs):
            captured_kwargs.update(kwargs)

            class Resp:
                text = "ok"

            return Resp()

    class DummyClient:
        models = DummyModels()

    monkeypatch.setattr("google.genai.Client", lambda **kw: DummyClient())
    client = GeminiClient(api_key="test_key", fallback_api_key="", generate_model="gemini-2.0-flash")
    client.generate(
        [{"role": "user", "content": "hi"}],
        temperature=0.3,
        top_p=0.5,
    )
    config = captured_kwargs.get("config", {})
    assert config.get("temperature") == 0.3
    assert config.get("top_p") == 0.5


def test_generate_quota_switches_to_fallback_embed_stays_primary(monkeypatch, capsys) -> None:
    from google.genai.errors import ClientError
    from tutor.gemini_client import CHAT_FALLBACK_WARNING, GeminiClient

    generate_keys: list[str] = []
    embed_keys: list[str] = []

    class DummyModels:
        def __init__(self, api_key: str) -> None:
            self.api_key = api_key

        def generate_content(self, **kwargs):
            del kwargs
            generate_keys.append(self.api_key)
            if self.api_key == "primary":
                raise ClientError(429, {"error": {"status": "RESOURCE_EXHAUSTED"}}, None)

            class Resp:
                text = "fallback-ok"

            return Resp()

        def embed_content(self, **kwargs):
            del kwargs
            embed_keys.append(self.api_key)

            class Item:
                values = [1.0]

            class Resp:
                embeddings = [Item()]

            return Resp()

    class DummyClient:
        def __init__(self, api_key: str) -> None:
            self.models = DummyModels(api_key)

    monkeypatch.setattr("google.genai.Client", lambda **kw: DummyClient(kw["api_key"]))
    client = GeminiClient(api_key="primary", fallback_api_key="secondary")
    out = client.generate([{"role": "user", "content": "hi"}])
    assert out == "fallback-ok"
    assert client.using_chat_fallback
    captured = capsys.readouterr()
    assert CHAT_FALLBACK_WARNING in captured.out
    assert generate_keys == ["primary", "secondary"]
    assert client.embed(["x"]) == [[1.0]]
    assert embed_keys == ["primary"]
    assert client.generate([{"role": "user", "content": "again"}]) == "fallback-ok"
    assert generate_keys == ["primary", "secondary", "secondary"]


def test_generate_quota_without_fallback_retries(monkeypatch) -> None:
    from google.genai.errors import ClientError
    from tutor.gemini_client import GeminiClient

    sleeps: list[float] = []
    monkeypatch.setattr("tutor.gemini_client.time.sleep", sleeps.append)

    class DummyModels:
        def generate_content(self, **kwargs):
            del kwargs
            raise ClientError(429, {}, None)

    class DummyClient:
        models = DummyModels()

    monkeypatch.setattr("google.genai.Client", lambda **kw: DummyClient())
    client = GeminiClient(api_key="primary", fallback_api_key="")
    try:
        client.generate([{"role": "user", "content": "hi"}])
    except ClientError as exc:
        assert getattr(exc, "code", None) == 429
    else:
        raise AssertionError("expected 429 after retries")
    assert sleeps
    assert sleeps[0] == 50.0

