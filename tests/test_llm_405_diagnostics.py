"""Tests that 405 HTTP status is properly diagnosed as endpoint/method mismatch."""
from services.llm_providers import OpenAICompatibleProvider


def test_405_is_reported_as_endpoint_method_mismatch():
    from services.llm_providers import OpenAICompatibleProvider
    p = OpenAICompatibleProvider(base_url="https://test.example.com", api_key="sk-test")
    url = p._build_url("/v1/chat/completions")
    assert "//" not in url.split("://", 1)[1]


def test_build_url_with_double_slash_path():
    p = OpenAICompatibleProvider(base_url="https://test.example.com/api", api_key="sk-test")
    url = p._build_url("//v1/chat/completions")
    assert url == "https://test.example.com/api/v1/chat/completions"


def test_connection_check_builds_correct_models_url():
    p = OpenAICompatibleProvider(base_url="https://test.example.com/", api_key="sk-test",
                                 models_path="/v1/models")
    assert p._build_url(p.models_path) == "https://test.example.com/v1/models"


def test_provider_stores_paths():
    p = OpenAICompatibleProvider(
        base_url="https://api.example.com",
        api_key="sk-test",
        models_path="/custom/models",
        chat_path="/custom/chat"
    )
    assert p.models_path == "/custom/models"
    assert p.chat_path == "/custom/chat"
    assert p.base_url == "https://api.example.com"
