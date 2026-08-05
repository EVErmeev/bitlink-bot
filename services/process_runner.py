"""Windows-safe subprocess runner with automatic encoding detection.
Never uses text=True for CLI calls to avoid _readerthread UnicodeDecodeError."""

import locale
import subprocess
import time
from dataclasses import dataclass, field


@dataclass
class ProcessExecutionResult:
    args_safe: list[str] = field(default_factory=list)
    returncode: int = -1
    stdout: str = ""
    stderr: str = ""
    stdout_encoding: str = ""
    stderr_encoding: str = ""
    stdout_decode_score: float = 0.0
    stderr_decode_score: float = 0.0
    duration_seconds: float = 0.0


def _score_decoded_text(text: str) -> float:
    """Score decoded text. Higher = more likely to be correct."""
    if not text:
        return 0.0
    score = 0.0
    russian_range = sum(1 for c in text if '\u0400' <= c <= '\u04FF')
    score += russian_range * 2
    russian_words = ['транскрибация', 'модель', 'сервис', 'здоров', 'healthy', 'статус',
                     'версия', 'язык', 'русский', 'суммаризация', 'синтез', 'задача']
    for w in russian_words:
        if w in text.lower():
            score += 10
    box_chars = sum(1 for c in text if '\u2500' <= c <= '\u257F')
    score -= box_chars * 3
    control_chars = sum(1 for c in text if ord(c) < 32 and c not in '\n\r\t')
    score -= control_chars * 5
    replacement = text.count('\ufffd')
    score -= replacement * 10
    return score


def _get_windows_console_codepages() -> list[str]:
    """Get relevant Windows code pages for decoding CLI output."""
    pages = []
    try:
        import ctypes
        cp = ctypes.windll.kernel32.GetConsoleOutputCP()
        if cp:
            pages.append(f"cp{cp}")
    except Exception:
        pass
    try:
        cp = ctypes.windll.kernel32.GetOEMCP()
        if cp:
            pages.append(f"cp{cp}")
    except Exception:
        pass
    return pages


def decode_process_output(data: bytes | None, *,
                          preferred_encoding: str | None = None) -> tuple[str, str, float]:
    """Decode binary CLI output. Returns (text, encoding_name, score). Never raises."""
    if not data:
        return "", "empty", 0.0

    if preferred_encoding and preferred_encoding != "auto":
        try:
            text = data.decode(preferred_encoding)
            s = _score_decoded_text(text)
            return text, preferred_encoding, s
        except (UnicodeDecodeError, LookupError):
            pass

    # Try strict UTF-8 first (with BOM)
    if data[:3] == b"\xef\xbb\xbf":
        try:
            text = data.decode("utf-8-sig")
            s = _score_decoded_text(text)
            return text, "utf-8-sig", s
        except UnicodeDecodeError:
            pass

    try:
        text = data.decode("utf-8")
        s = _score_decoded_text(text)
        return text, "utf-8", s
    except UnicodeDecodeError:
        pass

    # Try Windows code pages with scoring
    best_text = ""
    best_score = -999.0
    best_cp = ""

    for cp in _get_windows_console_codepages() + ["cp866", "cp1251"]:
        try:
            text = data.decode(cp)
            s = _score_decoded_text(text)
            if s > best_score:
                best_score = s
                best_text = text
                best_cp = cp
        except (UnicodeDecodeError, LookupError):
            pass

    if best_text:
        return best_text, best_cp, best_score

    # Try locale encoding
    try:
        enc = locale.getpreferredencoding(False)
        if enc.lower() not in ("utf-8", "utf8"):
            text = data.decode(enc, errors="replace")
            s = _score_decoded_text(text)
            return text, enc, s
    except Exception:
        pass

    # Last resort
    text = data.decode("utf-8", errors="replace")
    s = _score_decoded_text(text)
    return text, "utf-8(replace)", s


def safe_excerpt(value: str | None, limit: int = 300) -> str:
    """Return safely truncated string. Never raises on None."""
    if value is None:
        return ""
    return value[:limit]


def redact_secrets(text: str, secrets: list[str] | None = None) -> str:
    """Remove known secret values from text."""
    if not secrets or not text:
        return text
    result = text
    for secret in secrets:
        if secret and len(secret) > 4:
            result = result.replace(secret, "<redacted>")
            result = result.replace(secret.strip(), "<redacted>")
    return result


def run_process(args: list[str], *,
                input_text: str | None = None,
                env: dict[str, str] | None = None,
                timeout_seconds: int = 120,
                secret_values: list[str] | None = None,
                preferred_encoding: str | None = None) -> ProcessExecutionResult:
    """Run subprocess with binary pipes. Safe on Windows with any output encoding."""
    input_bytes = input_text.encode("utf-8") if input_text else None
    args_safe = [a for a in args]
    if secret_values:
        args_safe = redact_secrets(" ".join(args_safe), secret_values).split()

    start = time.monotonic()
    result = ProcessExecutionResult(args_safe=args_safe)

    try:
        proc = subprocess.run(
            args,
            input=input_bytes,
            capture_output=True,
            text=False,
            shell=False,
            timeout=timeout_seconds,
            env=env,
        )
        result.returncode = proc.returncode
        result.stdout, result.stdout_encoding, result.stdout_decode_score = decode_process_output(
            proc.stdout, preferred_encoding=preferred_encoding)
        result.stderr, result.stderr_encoding, result.stderr_decode_score = decode_process_output(
            proc.stderr, preferred_encoding=preferred_encoding)

        if secret_values:
            result.stdout = redact_secrets(result.stdout, secret_values)
            result.stderr = redact_secrets(result.stderr, secret_values)
    except subprocess.TimeoutExpired:
        result.returncode = -1
        result.stderr = f"Process timed out after {timeout_seconds}s"
        result.stderr_encoding = "n/a"
    except FileNotFoundError:
        result.returncode = -1
        result.stderr = f"Executable not found: {args[0] if args else 'unknown'}"
        result.stderr_encoding = "n/a"
    except Exception as e:
        result.returncode = -1
        result.stderr = f"Subprocess error: {e}"
        result.stderr_encoding = "n/a"

    result.duration_seconds = time.monotonic() - start
    return result


def classify_auth_error(stderr: str, returncode: int) -> tuple[str, str]:
    """Classify CLI auth error from stderr and return code."""
    if returncode == 0:
        return "", ""
    if not stderr:
        return "CLI_NONZERO_EXIT", f"CLI exited with code {returncode} (no stderr)"
    sl = stderr.lower()
    if "malformed token" in sl or "not enough segments" in sl:
        return ("AUTH_TOKEN_MALFORMED",
                "Токен отклонён сервисом БИТ Ньютон как некорректный JWT. "
                "Получите новый токен для Newton CLI и повторите проверку.")
    if "401" in sl and ("unauthorized" in sl or "token" in sl or "auth" in sl):
        return ("AUTH_FAILED",
                "Токен отклонён сервисом. Проверьте токен и повторите.")
    if "403" in sl or "forbidden" in sl:
        return ("AUTH_FORBIDDEN",
                "Доступ запрещён (HTTP 403). Проверьте права токена.")
    return ("CLI_NONZERO_EXIT",
            f"CLI завершился с кодом {returncode}: {safe_excerpt(stderr, 200)}")
