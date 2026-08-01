"""Tests for LLM provider selection logic."""
import pytest

from services.llm_providers import (
    MockLLMProvider,
    OneBitNewtonCLIProvider,
    OpenAICompatibleProvider,
)


def test_mock_provider_is_created_when_provider_type_is_mock():
    from services.llm_service import LLMClient
    client = LLMClient(mock_mode=True, provider_type="mock")
    assert isinstance(client._provider, MockLLMProvider)


def test_openai_provider_is_created_when_provider_type_is_openai_compatible():
    from services.llm_service import LLMClient
    client = LLMClient(api_url="https://api.example.com", api_key="sk-test",
                       model="gpt-4o", mock_mode=False, provider_type="openai_compatible")
    assert isinstance(client._provider, OpenAICompatibleProvider)


def test_openai_provider_selectable_even_when_mock_mode_is_true():
    from services.llm_service import LLMClient
    client = LLMClient(api_url="https://api.example.com", api_key="sk-test",
                       model="gpt-4o", mock_mode=True, provider_type="openai_compatible")
    assert isinstance(client._provider, OpenAICompatibleProvider)


def test_onebit_cli_provider_is_created_when_provider_type_is_onebit_newton_cli():
    from services.llm_service import LLMClient
    client = LLMClient(mock_mode=False, provider_type="onebit_newton_cli", cli_path="newton")
    assert isinstance(client._provider, OneBitNewtonCLIProvider)


def test_mock_provider_falls_back_to_mock_schema_generation():
    from services.llm_service import LLMClient
    client = LLMClient(mock_mode=True, provider_type="mock")
    schema = {"type": "object", "properties": {"test_field": {"type": "string"}}, "required": ["test_field"]}
    parsed, _ = client.generate_json("system", "user", schema)
    assert parsed["test_field"] == "Mock test_field"


def test_provider_type_falls_back_to_settings_when_none():
    from services.llm_providers import MockLLMProvider
    from services.llm_service import LLMClient
    # When mock_mode=True and no provider_type, should use mock
    client = LLMClient(mock_mode=True, provider_type=None)
    assert isinstance(client._provider, MockLLMProvider)


def test_provider_type_defaults_to_mock_when_mock_mode_true_and_no_provider_type():
    from services.llm_service import LLMClient
    client = LLMClient(mock_mode=True, provider_type=None)
    assert isinstance(client._provider, MockLLMProvider)


def test_unknown_provider_type_raises_configuration_error():
    from services.llm_service import LLMClient, LLMConfigurationError
    with pytest.raises(LLMConfigurationError, match="Unknown LLM provider"):
        LLMClient(mock_mode=False, provider_type="nonexistent_provider", api_url="https://api.example.com", api_key="sk-test")


def test_check_connection_delegates_to_provider():
    from services.llm_service import LLMClient
    client = LLMClient(mock_mode=True, provider_type="mock")
    assert client.check_connection() is True
