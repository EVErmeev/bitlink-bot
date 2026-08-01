"""Tests for services/process_runner — encoding, edge cases, and safety."""
import os

import pytest

from services.process_runner import (
    ProcessExecutionResult,
    classify_auth_error,
    decode_process_output,
    redact_secrets,
    run_process,
    safe_excerpt,
)

# ── decode_process_output ──

def test_decode_utf8():
    data = "Привет, мир".encode()
    text, enc = decode_process_output(data)
    assert text == "Привет, мир"
    assert enc == "utf-8"


def test_decode_bom():
    data = "Привет".encode("utf-8-sig")
    text, enc = decode_process_output(data)
    assert text == "Привет"
    assert enc == "utf-8-sig"


def test_decode_cp1251_cyrillic():
    data = "Документ №123".encode("cp1251")
    text, enc = decode_process_output(data)
    assert len(text) > 0
    assert enc != "empty"
    assert enc != "utf-8"


def test_decode_cp866_cyrillic():
    data = "Текст на CP866".encode("cp866")
    text, enc = decode_process_output(data)
    assert len(text) > 0
    assert enc != "empty"


def test_decode_none_input():
    text, enc = decode_process_output(None)
    assert text == ""
    assert enc == "empty"


def test_decode_empty_bytes():
    text, enc = decode_process_output(b"")
    assert text == ""
    assert enc == "empty"


def test_decode_unknown_bytes_never_raises():
    junk = bytes(range(256))
    try:
        text, enc = decode_process_output(junk)
    except Exception:
        pytest.fail("decode_process_output() raised on unknown bytes")
    assert isinstance(text, str)
    assert isinstance(enc, str)
    assert len(enc) > 0


# ── run_process ──

def test_run_process_binary_pipes():
    result = run_process(["cmd.exe", "/d", "/s", "/c", "echo hello"], timeout_seconds=5)
    assert result.returncode == 0
    assert "hello" in result.stdout.lower()


def test_run_process_returns_strings_for_empty_pipes():
    result = run_process(["cmd.exe", "/d", "/s", "/c", "exit /b 0"], timeout_seconds=5)
    assert isinstance(result.stdout, str)
    assert isinstance(result.stderr, str)
    assert result.returncode == 0


def test_run_process_stdin():
    import sys
    if sys.platform != "win32":
        pytest.skip("Windows-only test")
    result = run_process(
        ["cmd.exe", "/d", "/s", "/c", "more > nul & echo done"],
        input_text="test line",
        timeout_seconds=5,
    )
    assert isinstance(result.stdout, str)


def test_run_process_file_not_found():
    result = run_process(["nonexistent_executable_abc123"], timeout_seconds=5)
    assert result.returncode == -1
    assert "not found" in result.stderr.lower()


def test_run_process_timeout():
    import sys
    if sys.platform != "win32":
        pytest.skip("Windows-only test")
    result = run_process(["cmd.exe", "/d", "/s", "/c", "ping 127.0.0.1 -n 30 > nul"],
                        timeout_seconds=1)
    assert result.returncode == -1
    assert "timed out" in result.stderr.lower()


def test_run_process_env():
    import sys
    if sys.platform != "win32":
        pytest.skip("Windows-only test")
    result = run_process(
        ["cmd.exe", "/d", "/s", "/c", "echo %TEST_VAR%"],
        env={"TEST_VAR": "test_value", "SystemRoot": os.environ.get("SystemRoot", "C:\\Windows")},
        timeout_seconds=5,
    )
    assert "test_value" in result.stdout


# ── safe_excerpt ──

def test_safe_excerpt_normal():
    assert safe_excerpt("hello world", 5) == "hello"


def test_safe_excerpt_none():
    assert safe_excerpt(None) == ""


def test_safe_excerpt_shorter():
    assert safe_excerpt("ab", 100) == "ab"


# ── redact_secrets ──

def test_redact_secrets_removes_token():
    result = redact_secrets("Token is abc-def-ghi-123", ["abc-def-ghi-123"])
    assert "abc-def-ghi-123" not in result
    assert "<redacted>" in result


def test_redact_secrets_empty():
    assert redact_secrets("text", []) == "text"
    assert redact_secrets("text", None) == "text"


def test_redact_secrets_short_secret_not_redacted():
    result = redact_secrets("Token is ab", ["ab"])
    assert "ab" in result


# ── classify_auth_error ──

def test_classify_auth_malformed_token():
    code, msg = classify_auth_error("malformed token: not enough segments", 1)
    assert code == "AUTH_TOKEN_MALFORMED"
    assert "JWT" in msg


def test_classify_auth_401_unauthorized():
    code, msg = classify_auth_error("HTTP 401 Unauthorized: token invalid", 1)
    assert code == "AUTH_FAILED"


def test_classify_auth_403_forbidden():
    code, msg = classify_auth_error("HTTP 403 Forbidden", 1)
    assert code == "AUTH_FORBIDDEN"


def test_classify_auth_returncode_zero_returns_empty():
    code, msg = classify_auth_error("some error", 0)
    assert code == ""
    assert msg == ""


def test_classify_auth_unknown_error():
    code, msg = classify_auth_error("something went wrong", 2)
    assert code == "CLI_NONZERO_EXIT"
    assert "2" in msg


# ── ProcessExecutionResult dataclass ──

def test_result_defaults():
    r = ProcessExecutionResult()
    assert r.returncode == -1
    assert r.stdout == ""
    assert r.stderr == ""
    assert r.stdout_encoding == ""
    assert r.stderr_encoding == ""
    assert r.duration_seconds == 0.0


def test_result_fields_writable():
    r = ProcessExecutionResult()
    r.returncode = 0
    r.stdout = "OK"
    r.stderr = "ERR"
    r.stdout_encoding = "utf-8"
    r.stderr_encoding = "cp866"
    r.duration_seconds = 1.5
    assert r.returncode == 0
    assert r.stdout == "OK"
    assert r.stderr == "ERR"
    assert r.stdout_encoding == "utf-8"
    assert r.stderr_encoding == "cp866"
    assert r.duration_seconds == 1.5


# ── Duration is tracked ──

def test_run_process_tracks_duration():
    result = run_process(["cmd.exe", "/d", "/s", "/c", "echo ok"], timeout_seconds=5)
    assert result.duration_seconds > 0


# ── Args safe redaction ──

def test_run_process_redacts_secrets_in_args_safe():
    result = run_process(
        ["cmd.exe", "/d", "/s", "/c", "echo my-test-secret"],
        secret_values=["my-test-secret"],
        timeout_seconds=5,
    )
    assert "<redacted>" in " ".join(result.args_safe) or "my-test-secret" not in " ".join(result.args_safe)
