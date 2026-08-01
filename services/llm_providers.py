"""LLM provider abstraction layer."""
import json
import re
import subprocess
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


class OneBitCLIProvider:
    def __init__(self, cli_path="newton", transport="native", model="",
                 timeout_seconds=120):
        self.cli_path = cli_path
        self.transport = transport  # native | wsl
        self.model = model
        self.timeout_seconds = timeout_seconds

    def check_connection(self) -> ConnectionCheckResult:
        try:
            args = self._build_args(["--version"])
            result = subprocess.run(args, capture_output=True, text=True,
                                   timeout=min(15, self.timeout_seconds), shell=False)
            if result.returncode == 0:
                return ConnectionCheckResult(ok=True, stage="cli_version",
                    safe_message=f"CLI обнаружен: {result.stdout.strip()[:200]}")
            return ConnectionCheckResult(ok=False, stage="cli_version",
                safe_message=f"CLI вернул код {result.returncode}: {result.stderr[:200]}")
        except FileNotFoundError:
            return ConnectionCheckResult(ok=False, stage="cli_path",
                safe_message=f"CLI не найден по пути: {self.cli_path}. Установите newton CLI.")
        except Exception as e:
            return ConnectionCheckResult(ok=False, stage="cli_error",
                safe_message=f"Ошибка CLI: {str(e)[:200]}")

    def _build_args(self, extra_args: list[str]) -> list[str]:
        if self.transport == "wsl":
            return ["wsl.exe"] + [self.cli_path] + extra_args
        return [self.cli_path] + extra_args

    def generate(self, system_prompt, user_prompt, *, model="", temperature=0.1, max_tokens=4096):
        combined_prompt = f"System: {system_prompt}\n\nUser: {user_prompt}"
        args = self._build_args(["--model", model or self.model or "default"])
        result = subprocess.run(args, input=combined_prompt, capture_output=True,
                               text=True, timeout=self.timeout_seconds, shell=False,
                               encoding="utf-8")
        if result.returncode != 0:
            raise RuntimeError(f"CLI exited with code {result.returncode}: {result.stderr[:300]}")
        output = result.stdout
        json_blocks = re.findall(r'```(?:json)?\s*\n?(.*?)```', output, re.DOTALL)
        if len(json_blocks) == 1:
            return json_blocks[0].strip()
        if len(json_blocks) > 1:
            raise RuntimeError("CLI returned multiple JSON code blocks — expected single valid JSON object.")
        stripped = output.strip()
        if stripped.startswith("{") and stripped.endswith("}"):
            return stripped
        raise RuntimeError(f"CLI output is not valid JSON: {stripped[:300]}")
