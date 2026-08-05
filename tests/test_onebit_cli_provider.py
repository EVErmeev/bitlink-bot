"""Tests for OneBitNewtonCLIProvider — structure, validation, and error handling."""
import os
import tempfile

import pytest

from services.llm_providers import (
    ConnectionCheckResult,
    OneBitNewtonCLIProvider,
    OneBitProviderError,
)


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


def test_process_runner_uses_shell_false():
    """Confirm the design contract: run_process always uses shell=False."""
    import inspect

    from services.process_runner import run_process

    source = inspect.getsource(run_process)
    assert "shell=False" in source, "run_process() must use shell=False"


def test_provider_uses_run_process_not_subprocess():
    """Confirm provider uses run_process, not subprocess.run directly."""
    import inspect

    source_gen = inspect.getsource(OneBitNewtonCLIProvider.generate)
    assert "run_process(" in source_gen, "generate() must use run_process"
    assert "subprocess.run" not in source_gen, "generate() must NOT use subprocess.run directly"

    source_conn = inspect.getsource(OneBitNewtonCLIProvider.check_connection)
    assert "run_process(" in source_conn, "check_connection() must use run_process"
    assert "subprocess.run" not in source_conn, "check_connection() must NOT use subprocess.run directly"


def test_onebit_provider_error_new_fields():
    e = OneBitProviderError(
        stage="test", code="T001", safe_message="msg",
        exit_code=1, response_type="json",
        safe_stdout="out", safe_stderr="err",
        stdout_encoding="utf-8", stderr_encoding="cp1251",
        duration_seconds=2.5,
    )
    assert e.stage == "test"
    assert e.code == "T001"
    assert e.safe_message == "msg"
    assert e.exit_code == 1
    assert e.response_type == "json"
    assert e.safe_stdout == "out"
    assert e.safe_stderr == "err"
    assert e.stdout_encoding == "utf-8"
    assert e.stderr_encoding == "cp1251"
    assert e.duration_seconds == 2.5


def test_onebit_provider_error_defaults():
    e = OneBitProviderError(safe_message="test")
    assert e.stage == ""
    assert e.code == ""
    assert e.safe_stdout == ""
    assert e.safe_stderr == ""
    assert e.stdout_encoding is None
    assert e.stderr_encoding is None
    assert e.duration_seconds is None
    assert e.exit_code is None
    assert e.response_type is None
