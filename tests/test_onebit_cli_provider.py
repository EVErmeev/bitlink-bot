"""Tests for OneBitCLIProvider — structure and error handling only (CLI not installed)."""
import pytest

from services.llm_providers import ConnectionCheckResult, OneBitCLIProvider


def test_provider_is_instantiable():
    p = OneBitCLIProvider(cli_path="nonexistent_cli", transport="native")
    assert p.cli_path == "nonexistent_cli"
    assert p.transport == "native"
    assert p.model == ""
    assert p.timeout_seconds == 120


def test_provider_stores_model():
    p = OneBitCLIProvider(cli_path="newton", model="gpt-4o")
    assert p.model == "gpt-4o"


def test_provider_stores_transport():
    p = OneBitCLIProvider(cli_path="newton", transport="wsl")
    assert p.transport == "wsl"


def test_build_args_native():
    p = OneBitCLIProvider(cli_path="newton", transport="native")
    args = p._build_args(["--version"])
    assert args == ["newton", "--version"]


def test_build_args_wsl():
    p = OneBitCLIProvider(cli_path="newton", transport="wsl")
    args = p._build_args(["--model", "gpt-4o"])
    assert args == ["wsl.exe", "newton", "--model", "gpt-4o"]


def test_check_connection_missing_cli():
    p = OneBitCLIProvider(cli_path="nonexistent_cli_12345")
    result = p.check_connection()
    assert isinstance(result, ConnectionCheckResult)
    assert result.ok is False
    assert result.stage == "cli_path"
    assert "не найден" in result.safe_message


def test_connection_check_returns_connection_check_result():
    p = OneBitCLIProvider(cli_path="nonexistent_cli")
    result = p.check_connection()
    assert isinstance(result, ConnectionCheckResult)
    assert hasattr(result, "ok")
    assert hasattr(result, "stage")
    assert hasattr(result, "safe_message")


def test_generate_with_failed_cli_raises():
    p = OneBitCLIProvider(cli_path="nonexistent_cli")
    with pytest.raises((RuntimeError, FileNotFoundError)):
        p.generate("system", "user", model="gpt-4o")
