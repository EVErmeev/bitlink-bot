import json
import hashlib
from pathlib import Path
import settings
import requests


class LLMConfigurationError(Exception):
    pass


class LLMClient:
    def __init__(self, api_url=None, api_key=None, model=None):
        self.mock_mode = settings.LLM_MOCK
        self.api_url = api_url or settings.LLM_API_URL
        self.api_key = api_key or settings.LLM_API_KEY
        self.model = model or settings.LLM_MODEL

        if not self.mock_mode:
            missing = []
            if not self.api_url:
                missing.append("LLM_API_URL")
            if not self.api_key:
                missing.append("LLM_API_KEY")
            if missing:
                raise LLMConfigurationError(
                    f"LLM_MOCK=false, но отсутствуют настройки: {', '.join(missing)}. "
                    f"Укажите их в .env или установите LLM_MOCK=true."
                )

    def generate(self, system_prompt: str, user_prompt: str,
                 temperature: float = 0.3, max_tokens: int = 4096) -> str:
        if self.mock_mode:
            return self._mock_generate(system_prompt, user_prompt)

        try:
            resp = requests.post(
                f"{self.api_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                },
                timeout=120,
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            raise RuntimeError(f"LLM API error: {e}") from e

    def generate_json(self, system_prompt, user_prompt, json_schema, *,
                      temperature=0.1, max_retries=3) -> dict:
        for attempt in range(max_retries):
            response = self.generate(
                system_prompt,
                user_prompt + "\n\nReturn valid JSON conforming to this schema:\n"
                + json.dumps(json_schema),
                temperature=temperature,
            )
            try:
                parsed = json.loads(response)
                import jsonschema
                try:
                    jsonschema.validate(instance=parsed, schema=json_schema)
                except jsonschema.ValidationError as ve:
                    if attempt < max_retries - 1:
                        continue
                    raise RuntimeError(
                        f"LLM output failed schema validation after {max_retries} retries: {ve}"
                    ) from ve
                return parsed
            except json.JSONDecodeError:
                if attempt < max_retries - 1:
                    continue
                raise RuntimeError(
                    f"LLM output is not valid JSON after {max_retries} retries"
                )

    def _save_llm_artifacts(self, debug_dir, system_prompt, user_prompt,
                            response_raw, parsed, schema):
        debug_path = Path(debug_dir)
        debug_path.mkdir(parents=True, exist_ok=True)

        request_data = {
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
        }
        with open(debug_path / "llm_request.json", "w", encoding="utf-8") as f:
            json.dump(request_data, f, indent=2, ensure_ascii=False)

        with open(debug_path / "llm_response_raw.txt", "w", encoding="utf-8") as f:
            f.write(response_raw)

        with open(debug_path / "llm_response_parsed.json", "w", encoding="utf-8") as f:
            json.dump(parsed, f, indent=2, ensure_ascii=False)

        schema_result = {"schema": schema, "valid": True}
        with open(debug_path / "llm_schema_validation.json", "w", encoding="utf-8") as f:
            json.dump(schema_result, f, indent=2, ensure_ascii=False)

    def _mock_generate(self, system_prompt: str, user_prompt: str) -> str:
        if '"json"' in user_prompt.lower() or '"schema"' in user_prompt.lower() \
                or 'json schema' in user_prompt.lower() or 'valid json' in user_prompt.lower() \
                or 'return valid json' in user_prompt.lower():
            return json.dumps({
                "mock": True,
                "message": "Mock JSON response from LLM mock mode",
                "model": self.model or "mock",
            })
        return (
            "Протокол встречи (учебный mock-шаблон). "
            f"Модель: {self.model or 'mock'}. "
            "В реальном режиме здесь будет результат LLM-генерации."
        )

    def check_connection(self) -> bool:
        if self.mock_mode:
            return True
        try:
            resp = requests.get(
                f"{self.api_url}/models",
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=10,
            )
            return resp.status_code == 200
        except Exception:
            return False