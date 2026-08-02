"""LLM provider abstraction layer."""
import json
import re
import tempfile
from dataclasses import dataclass
from typing import Protocol

import requests


@dataclass
class ConnectionCheckResult:
    ok: bool
    stage: str
    status_code: int | None = None
    endpoint: str = ""
    safe_message: str = ""
    response_content_type: str | None = None


class OneBitProviderError(RuntimeError):
    def __init__(self, stage="", code="", safe_message="", exit_code=None,
                 response_type=None, safe_stdout="", safe_stderr="",
                 stdout_encoding=None, stderr_encoding=None, duration_seconds=None):
        self.stage = stage
        self.code = code
        self.safe_message = safe_message
        self.exit_code = exit_code
        self.response_type = response_type
        self.safe_stdout = safe_stdout or ""
        self.safe_stderr = safe_stderr or ""
        self.stdout_encoding = stdout_encoding
        self.stderr_encoding = stderr_encoding
        self.duration_seconds = duration_seconds
        super().__init__(safe_message)


class LLMProvider(Protocol):
    def check_connection(self) -> ConnectionCheckResult: ...
    def generate(self, system_prompt: str, user_prompt: str, *, model: str,
                 temperature: float, max_tokens: int) -> str: ...


class MockLLMProvider:
    def __init__(self, model="mock"):
        self.model = model

    def check_connection(self) -> ConnectionCheckResult:
        return ConnectionCheckResult(ok=True, stage="mock", safe_message="Mock provider — всегда доступен")

    def generate(self, system_prompt, user_prompt, *, model="mock", temperature=0.1, max_tokens=4096):
        schema_match = re.search(r'Return valid JSON conforming to this schema:\s*(\{.*\})', user_prompt, re.DOTALL)
        if schema_match:
            try:
                schema = json.loads(schema_match.group(1))
                result = {}
                for key in schema.get("properties", {}):
                    if key in schema.get("required", []):
                        result[key] = f"Mock {key}"
                if "topic_blocks" in schema.get("required", []):
                    result["topic_blocks"] = [{"topic_id": "mock_1", "title": "Mock Topic",
                        "discussion_content": "Mock discussion content for the meeting analysis.",
                        "conclusion": "Mock conclusion text.", "status_text": "Mock status"}]
                return json.dumps(result, ensure_ascii=False)
            except Exception:
                pass
        return json.dumps({"status": "ok", "message": "Mock response"}, ensure_ascii=False)


class OpenAICompatibleProvider:
    def __init__(self, base_url="", api_key="", model="gpt-4o",
                 models_path="/v1/models", chat_path="/v1/chat/completions",
                 timeout_seconds=120):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.models_path = models_path
        self.chat_path = chat_path
        self.timeout_seconds = timeout_seconds

    def _build_url(self, path: str) -> str:
        clean_path = path.lstrip("/")
        return f"{self.base_url}/{clean_path}"

    def check_connection(self) -> ConnectionCheckResult:
        url = self._build_url(self.models_path)
        try:
            resp = requests.get(url, headers={"Authorization": f"Bearer {self.api_key}"},
                               timeout=min(15, self.timeout_seconds))
            if resp.status_code == 200:
                return ConnectionCheckResult(ok=True, stage="models_api", status_code=200,
                    endpoint=url, safe_message="Соединение установлено", response_content_type=resp.headers.get("content-type"))
            if resp.status_code == 405:
                return ConnectionCheckResult(ok=False, stage="models_api", status_code=405,
                    endpoint=url,
                    safe_message="Сервер доступен, но endpoint или HTTP method не поддерживается. Проверьте provider и подтверждённый API prefix.",
                    response_content_type=resp.headers.get("content-type"))
            return ConnectionCheckResult(ok=False, stage="models_api", status_code=resp.status_code,
                endpoint=url,
                safe_message=f"HTTP {resp.status_code}: проверьте URL и API key",
                response_content_type=resp.headers.get("content-type"))
        except requests.RequestException as e:
            return ConnectionCheckResult(ok=False, stage="models_api", endpoint=url,
                safe_message=f"Ошибка соединения: {str(e)[:200]}")

    def generate(self, system_prompt, user_prompt, *, model="", temperature=0.1, max_tokens=4096):
        url = self._build_url(self.chat_path)
        resp = requests.post(url,
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            json={"model": model or self.model, "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}],
                "temperature": temperature, "max_tokens": max_tokens},
            timeout=self.timeout_seconds)
        if resp.status_code == 405:
            raise RuntimeError(f"HTTP 405 at {url}: сервер доступен, но endpoint или HTTP method не поддерживается. Проверьте provider и подтверждённый API prefix.")
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]


class OneBitNewtonCLIProvider:
    def __init__(self, cli_path="C:\\Users\\egore\\AppData\\Local\\NewtonCLI\\newton.cmd",
                 transport="native", model="gpt4", token="", timeout_seconds=120):
        from services.newton_cli import build_newton_command as _bnc
        self.cli_path = cli_path
        self.transport = transport
        if model not in ("llama", "gpt4"):
            model = "gpt4"
        self.model = model
        self.token = token
        self.timeout_seconds = timeout_seconds
        self._bnc = _bnc

    def check_connection(self) -> ConnectionCheckResult:
        from services.process_runner import run_process
        args = self._bnc(self.cli_path, "version")
        result = run_process(args, timeout_seconds=min(15, self.timeout_seconds),
                            secret_values=[self.token] if self.token else None)
        if result.returncode == 0:
            return ConnectionCheckResult(ok=True, stage="cli_version",
                safe_message=f"Newton CLI {result.stdout.strip()[:100]}")
        return ConnectionCheckResult(ok=False, stage="cli_version",
            safe_message=f"CLI exit {result.returncode}: {result.stderr[:200]}")

    def generate(self, system_prompt, user_prompt, *, model="", temperature=0.1, max_tokens=4096):
        import os as _os

        from services.process_runner import classify_auth_error, run_process

        if not self.token:
            raise OneBitProviderError(stage="provider_config", code="ONEBIT_TOKEN_MISSING",
                safe_message="Токен БИТ Ньютон не указан. Укажите токен в настройках LLM.")

        mdl = model if model in ("llama", "gpt4") else self.model
        fd, output_path = tempfile.mkstemp(suffix=".json", prefix="newton_out_")
        _os.close(fd)

        try:
            base = self._bnc(self.cli_path)
            args = base + ["summarize", "-", "--model", mdl, "--output", output_path]
            if system_prompt:
                # Clean surrogates that break json.dumps in CLI
                clean_sp = system_prompt.encode("utf-8", errors="replace").decode("utf-8")
                args += ["--system-prompt", clean_sp[:4000]]

            env = _os.environ.copy()
            env["NEWTON_TOKEN"] = self.token
            env["PYTHONIOENCODING"] = "utf-8"

            # Clean user_prompt from surrogates too
            clean_up = user_prompt.encode("utf-8", errors="replace").decode("utf-8")

            proc_result = run_process(args, input_text=clean_up, env=env,
                                     timeout_seconds=self.timeout_seconds,
                                     secret_values=[self.token])

            if proc_result.returncode != 0:
                auth_code, auth_msg = classify_auth_error(proc_result.stderr, proc_result.returncode)
                full_stderr = proc_result.stderr[:2000]
                # Save full stderr to debug
                try:
                    import os as _os
                    _os.makedirs("debug/cli_errors", exist_ok=True)
                    _ts = __import__("datetime").datetime.now().strftime("%Y%m%d_%H%M%S")
                    with open(f"debug/cli_errors/summarize_{_ts}.log", "w", encoding="utf-8") as _f:
                        _f.write(f"EXIT: {proc_result.returncode}\nARGS: {args}\nSTDERR:\n{full_stderr}\nSTDOUT:\n{proc_result.stdout[:500]}")
                except Exception:
                    pass
                if auth_code:
                    raise OneBitProviderError(stage="cli_execution", code=auth_code,
                        safe_message=auth_msg, exit_code=proc_result.returncode,
                        safe_stderr=full_stderr,
                        stderr_encoding=proc_result.stderr_encoding,
                        duration_seconds=proc_result.duration_seconds)
                raise OneBitProviderError(stage="cli_execution", code="CLI_NONZERO_EXIT",
                    safe_message=f"Newton CLI exit {proc_result.returncode}: {full_stderr[:500]}",
                    exit_code=proc_result.returncode,
                    safe_stderr=full_stderr,
                    stderr_encoding=proc_result.stderr_encoding,
                    duration_seconds=proc_result.duration_seconds)

            if not _os.path.exists(output_path):
                raise OneBitProviderError(stage="output_check", code="OUTPUT_FILE_MISSING",
                    safe_message="CLI не создал выходной файл. Проверьте токен и права.")

            file_size = _os.path.getsize(output_path)
            if file_size == 0:
                raise OneBitProviderError(stage="output_check", code="OUTPUT_FILE_EMPTY",
                    safe_message="CLI создал пустой выходной файл. Проверьте токен и модель.")

            with open(output_path, encoding="utf-8") as f:
                output = f.read().strip()

            if not output:
                raise OneBitProviderError(stage="output_read", code="EMPTY_RESPONSE",
                    safe_message="Ответ CLI пуст.", response_type="empty")

            return output
        finally:
            try:
                _os.unlink(output_path)
            except OSError:
                pass


class OneBitNewtonTranscriptionProvider:
    def __init__(self, config=None):
        if config is None:
            from services.runtime_config import RuntimeConfig
            config = RuntimeConfig().get_onebit_config()
        self.config = config

    def check_connection(self) -> ConnectionCheckResult:
        from services.newton_cli import build_newton_command
        from services.process_runner import run_process
        args = build_newton_command(self.config.cli_path, "transcribe", "--help")
        r = run_process(
            args,
            timeout_seconds=15,
            secret_values=[self.config.token] if self.config.token else None,
        )
        if r.returncode == 0:
            return ConnectionCheckResult(
                ok=True, stage="cli_available",
                safe_message="Newton CLI доступен для транскрибации",
            )
        return ConnectionCheckResult(
            ok=False, stage="cli_error",
            safe_message=f"CLI error: {r.stderr[:200]}",
        )

    def transcribe(self, audio_path: str, output_dir: str = "", engine: str = "v3") -> str:
        import os as _os

        if not self.config.token:
            raise OneBitProviderError(stage="config", code="NO_TOKEN",
                safe_message="Токен не указан")

        fd, out = tempfile.mkstemp(suffix=".txt", prefix="newton_trans_")
        _os.close(fd)
        try:
            env = _os.environ.copy()
            env["NEWTON_TOKEN"] = self.config.token
            env["PYTHONIOENCODING"] = "utf-8"
            from services.newton_cli import build_newton_command
            from services.process_runner import run_process
            args = build_newton_command(self.config.cli_path, "transcribe", str(audio_path),
                                        "--engine", engine, "--output", out)
            r = run_process(
                args,
                env=env, timeout_seconds=self.config.timeout_seconds,
                secret_values=[self.config.token] if self.config.token else None,
            )
            if r.returncode != 0:
                raise RuntimeError(f"Transcription failed: {r.stderr[:300]}")
            if not _os.path.exists(out) or _os.path.getsize(out) == 0:
                raise RuntimeError("Transcription produced no output")
            return open(out, encoding="utf-8").read()
        finally:
            try:
                _os.unlink(out)
            except OSError:
                pass
