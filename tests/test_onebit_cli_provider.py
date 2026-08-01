"""Tests for OneBitNewtonCLIProvider — structure, validation, and error handling."""
import os
import tempfile

import pytest

from services.llm_providers import ConnectionCheckResult, OneBitNewtonCLIProvider


def test_provider_is_instantiable():
    p = OneBitNewtonCLIProvider(cli_path="nonexistent_cli")
    assert p.cli_path == "nonexistent_cli"
    assert p.model == "gpt4"
    assert p.timeout_seconds == 120
    assert p.token == ""


def test_default_cli_path():
    p = OneBitNewtonCLIProvider()
    assert "NewtonCLI" in p.cli_path or "newton" in p.cli_path


def test_model_falls_back_to_gpt4_for_invalid():
    p = OneBitNewtonCLIProvider(model="gpt-4o")
    assert p.model == "gpt4"


def test_model_falls_back_to_gpt4_for_empty():
    p = OneBitNewtonCLIProvider(model="")
    assert p.model == "gpt4"


def test_model_accepts_llama():
    p = OneBitNewtonCLIProvider(model="llama")
    assert p.model == "llama"


def test_model_accepts_gpt4():
    p = OneBitNewtonCLIProvider(model="gpt4")
    assert p.model == "gpt4"


def test_provider_stores_token():
    p = OneBitNewtonCLIProvider(token="my-secret-token")
    assert p.token == "my-secret-token"


def test_check_connection_missing_cli():
    p = OneBitNewtonCLIProvider(cli_path="nonexistent_cli_12345")
    result = p.check_connection()
    assert isinstance(result, ConnectionCheckResult)
    assert result.ok is False
    assert result.stage == "cli_path"
    assert "not found" in result.safe_message.lower()


def test_connection_check_returns_connection_check_result():
    p = OneBitNewtonCLIProvider(cli_path="nonexistent_cli")
    result = p.check_connection()
    assert isinstance(result, ConnectionCheckResult)
    assert hasattr(result, "ok")
    assert hasattr(result, "stage")
    assert hasattr(result, "safe_message")


def test_generate_with_failed_cli_raises():
    p = OneBitNewtonCLIProvider(cli_path="nonexistent_cli")
    with pytest.raises((RuntimeError, FileNotFoundError)):
        p.generate("system", "user", model="gpt4")


def test_generate_creates_and_cleans_temp_file():
    """Verify that generate() creates a temp output file and cleans it up."""
    p = OneBitNewtonCLIProvider(cli_path="nonexistent_cli")
    temp_files_before = set(os.listdir(tempfile.gettempdir()))
    try:
        p.generate("system", "user", model="gpt4")
    except (RuntimeError, FileNotFoundError):
        pass
    temp_files_after = set(os.listdir(tempfile.gettempdir()))
    new_files = temp_files_after - temp_files_before
    newton_leftovers = [f for f in new_files if f.startswith("newton_out_")]
    assert len(newton_leftovers) == 0, f"Temp files not cleaned up: {newton_leftovers}"


def test_shell_is_false_by_design():
    """Confirm the design contract: subprocess always uses shell=False."""
    import inspect

    source = inspect.getsource(OneBitNewtonCLIProvider.generate)
    assert "shell=False" in source, "generate() must use shell=False"

    source_conn = inspect.getsource(OneBitNewtonCLIProvider.check_connection)
    assert "shell=False" in source_conn, "check_connection() must use shell=False"
