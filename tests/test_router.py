"""Ask router (no live Gemini)."""

from tutor.router import classify_route, clear_route_cache, set_route_generate_fn


def test_classify_parses_json(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("tutor.router.ROUTER_CACHE_DIR", tmp_path)
    monkeypatch.setattr("tutor.router.resolved_gemini_api_keys", lambda: [])
    clear_route_cache()
    set_route_generate_fn(lambda messages, **kwargs: '{"route":"programming"}')
    try:
        assert classify_route("useState hook") == "programming"
        assert classify_route("useState hook") == "programming"
    finally:
        set_route_generate_fn(None)
        clear_route_cache()


def test_classify_skips_ambiguous_without_key_or_inject(monkeypatch) -> None:
    monkeypatch.setattr("tutor.router.resolved_gemini_api_keys", lambda: [])
    set_route_generate_fn(None)
    clear_route_cache()
    assert classify_route("hello there") is None


def test_rules_miit_without_llm(monkeypatch) -> None:
    monkeypatch.setattr("tutor.router.resolved_gemini_api_keys", lambda: [])
    set_route_generate_fn(None)
    clear_route_cache()
    assert classify_route("Cynthia Myint ဆိုတာ ဘယ်သူလဲ?") == "miit"


def test_binary_search_is_programming_even_if_llm_says_other(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("tutor.router.ROUTER_CACHE_DIR", tmp_path)
    monkeypatch.setattr("tutor.router.resolved_gemini_api_keys", lambda: [])
    clear_route_cache()
    set_route_generate_fn(lambda messages, **kwargs: '{"route":"other"}')
    try:
        assert classify_route("binary search algo") == "programming"
        assert (
            classify_route("ရှင်းပြပါ", "def binary_search(arr, target):\n    return 0")
            == "programming"
        )
    finally:
        set_route_generate_fn(None)
        clear_route_cache()


def test_non_ce_theory_is_other(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("tutor.router.ROUTER_CACHE_DIR", tmp_path)
    monkeypatch.setattr("tutor.router.resolved_gemini_api_keys", lambda: [])
    clear_route_cache()
    set_route_generate_fn(lambda messages, **kwargs: '{"route":"other"}')
    try:
        assert classify_route("Newton's second law ဆိုတာ ဘာလဲ?") == "other"
        assert classify_route("photosynthesis ဆိုတာ ဘာလဲ?") == "other"
        assert classify_route("Pythagorean theorem ရှင်းပြပါ") == "other"
    finally:
        set_route_generate_fn(None)
        clear_route_cache()


def test_ohms_law_is_programming_even_if_llm_says_other(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("tutor.router.ROUTER_CACHE_DIR", tmp_path)
    monkeypatch.setattr("tutor.router.resolved_gemini_api_keys", lambda: [])
    clear_route_cache()
    set_route_generate_fn(lambda messages, **kwargs: '{"route":"other"}')
    try:
        assert classify_route("Ohm's law ဆိုတာ ဘာလဲ?") == "programming"
        assert classify_route("Kirchhoff's voltage law ရှင်းပြပါ") == "programming"
    finally:
        set_route_generate_fn(None)
        clear_route_cache()


def test_weather_stays_other(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("tutor.router.ROUTER_CACHE_DIR", tmp_path)
    monkeypatch.setattr("tutor.router.resolved_gemini_api_keys", lambda: [])
    clear_route_cache()
    set_route_generate_fn(lambda messages, **kwargs: '{"route":"other"}')
    try:
        assert classify_route("What's the weather in Yangon?") == "other"
    finally:
        set_route_generate_fn(None)
        clear_route_cache()


def test_followup_inherits_miit_without_llm(monkeypatch) -> None:
    monkeypatch.setattr("tutor.router.resolved_gemini_api_keys", lambda: [])
    set_route_generate_fn(None)
    clear_route_cache()
    history = [{"question": "Cynthia Myint ဆိုတာ ဘယ်သူလဲ?", "answer": "MIIT professor"}]
    assert classify_route("သူမ ဘာတွေ သုတေသနလုပ်လဲ?", history=history) == "miit"


def test_cse_more_followup_stays_miit_even_if_llm_says_other(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setattr("tutor.router.ROUTER_CACHE_DIR", tmp_path)
    monkeypatch.setattr("tutor.router.resolved_gemini_api_keys", lambda: [])
    clear_route_cache()
    called = {"n": 0}

    def boom(messages, **kwargs):
        called["n"] += 1
        return '{"route":"other"}'

    set_route_generate_fn(boom)
    history = [
        {
            "question": "B.E (Hons.) CSE မှာခုနှစ် ဘယ်ဘာသာတွေကို သင်ကြားပေးပါသလဲ။",
            "answer": "Year I စသင်သည်။",
        }
    ]
    try:
        assert classify_route("နောက်ထပ် ရှိသေးလား။", history=history) == "miit"
        assert called["n"] == 0
    finally:
        set_route_generate_fn(None)
        clear_route_cache()


def test_second_followup_walks_back_to_cse_topic(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("tutor.router.ROUTER_CACHE_DIR", tmp_path)
    monkeypatch.setattr("tutor.router.resolved_gemini_api_keys", lambda: [])
    clear_route_cache()
    called = {"n": 0}

    def boom(messages, **kwargs):
        called["n"] += 1
        return '{"route":"other"}'

    set_route_generate_fn(boom)
    history = [
        {
            "question": "B.E (Hons.) CSE မှာခုနှစ် ဘယ်ဘာသာတွေကို သင်ကြားပေးပါသလဲ။",
            "answer": "Year I စသင်သည်။",
        },
        {
            "question": "ကျွန်တော့်ကို အသေးစိတ် ပြောပြပါ။",
            "answer": "အပို semester များ ရှိပါသည်။",
        },
    ]
    try:
        assert classify_route("နောက်ထပ် ရှိသေးလား။", history=history) == "miit"
        assert called["n"] == 0
    finally:
        set_route_generate_fn(None)
        clear_route_cache()
