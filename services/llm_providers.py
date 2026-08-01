"""LLM provider abstraction layer."""
import json
import os
import re
import subprocess
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
        self.cli_path = cli_path
        self.transport = transport
        if model not in ("llama", "gpt4"):
            model = "gpt4"
        self.model = model
        self.token = token
        self.timeout_seconds = timeout_seconds

    def _build_base_args(self) -> list:
        if self.cli_path.endswith(".cmd") or self.cli_path.endswith(".bat"):
            return [os.environ.get("COMSPEC", "cmd.exe"), "/d", "/s", "/c", self.cli_path]
        return [self.cli_path]

    def check_connection(self) -> ConnectionCheckResult:
        try:
            base = self._build_base_args()
            args = base + ["version"]
            result = subprocess.run(args, capture_output=True, text=True, timeout=15, shell=False)
            if result.returncode == 0:
                return ConnectionCheckResult(ok=True, stage="cli_version",
                    safe_message=f"Newton CLI {result.stdout.strip()[:100]}")
            return ConnectionCheckResult(ok=False, stage="cli_version",
                safe_message=f"CLI exit code {result.returncode}: {result.stderr[:200]}")
        except FileNotFoundError:
            return ConnectionCheckResult(ok=False, stage="cli_path",
                safe_message=f"CLI not found: {self.cli_path}")
        except Exception as e:
            return ConnectionCheckResult(ok=False, stage="cli_error", safe_message=str(e)[:200])

    def generate(self, system_prompt, user_prompt, *, model="", temperature=0.1, max_tokens=4096):
        import os as _os
        import re as re_mod

        mdl = model if model in ("llama", "gpt4") else self.model
        fd, output_path = tempfile.mkstemp(suffix=".json", prefix="newton_out_")
        _os.close(fd)

        try:
            base = self._build_base_args()
            args = base + ["summarize", "-", "--model", mdl, "--output", output_path]
            if system_prompt:
                args += ["--system-prompt", system_prompt]

            env = _os.environ.copy()
            if self.token:
                env["NEWTON_TOKEN"] = self.token

            result = subprocess.run(args, input=user_prompt, capture_output=True,
                                   text=True, shell=False, timeout=self.timeout_seconds,
                                   env=env, encoding="utf-8")
            if result.returncode != 0:
                raise RuntimeError(f"Newton CLI exit {result.returncode}: {result.stderr[:300]}")

            with open(output_path, encoding="utf-8") as f:
                output = f.read().strip()
            if not output:
                raise RuntimeError("Newton CLI produced empty output")

            fences = re_mod.findall(r'```(?:json)?\s*\n?(.*?)```', output, re_mod.DOTALL)
            if len(fences) == 1:
                return fences[0].strip()
            if len(fences) > 1:
                raise RuntimeError(f"Newton CLI returned {len(fences)} JSON blocks — expected single valid JSON object.")

            stripped = output.strip()
            if stripped.startswith("{"):
                return stripped
            raise RuntimeError(f"Output is not valid JSON: {stripped[:300]}")
        finally:
            try:
                _os.unlink(output_path)
            except OSError:
                pass
