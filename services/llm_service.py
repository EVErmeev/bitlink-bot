import json
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

    def _mock_generate(self, system_prompt: str, user_prompt: str) -> str:
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