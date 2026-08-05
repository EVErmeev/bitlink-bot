"""Tests for OpenAICompatibleProvider URL normalization."""
from services.llm_providers import OpenAICompatibleProvider


def test_base_url_trailing_slash_does_not_create_double_slash():
    p = OpenAICompatibleProvider(base_url="https://ys.1bitai.ru/", api_key="sk-test")
    url = p._build_url("/v1/chat/completions")
    assert "//chat" not in url
    assert url == "https://ys.1bitai.ru/v1/chat/completions"


def test_base_url_no_trailing_slash():
    p = OpenAICompatibleProvider(base_url="https://ys.1bitai.ru", api_key="sk-test")
    url = p._build_url("/v1/chat/completions")
    assert url == "https://ys.1bitai.ru/v1/chat/completions"


def test_base_url_trailing_slash_models_path():
    p = OpenAICompatibleProvider(base_url="https://ys.1bitai.ru/", api_key="sk-test")
    url = p._build_url("/v1/models")
    assert "//models" not in url
    assert url == "https://ys.1bitai.ru/v1/models"


def test_base_url_no_trailing_slash_models_path():
    p = OpenAICompatibleProvider(base_url="https://ys.1bitai.ru", api_key="sk-test")
    url = p._build_url("/v1/models")
    assert url == "https://ys.1bitai.ru/v1/models"


def test_path_without_leading_slash():
    p = OpenAICompatibleProvider(base_url="https://ys.1bitai.ru", api_key="sk-test")
    url = p._build_url("v1/chat/completions")
    assert url == "https://ys.1bitai.ru/v1/chat/completions"


def test_custom_models_path():
    p = OpenAICompatibleProvider(base_url="https://api.example.com/v1", api_key="sk-test",
                                 models_path="/v1/models", chat_path="/v1/chat/completions")
    assert p._build_url(p.models_path) == "https://api.example.com/v1/v1/models"
