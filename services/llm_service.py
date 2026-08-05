import json
from pathlib import Path

import settings
from services.llm_providers import (
    LLMProvider,
    MockLLMProvider,
    OneBitNewtonCLIProvider,
    OpenAICompatibleProvider,
)


class LLMConfigurationError(Exception):
    pass


class LLMClient:
    def __init__(self, api_url=None, api_key=None, model=None, mock_mode=None, timeout_seconds=120,
                 provider_type=None, cli_path=None, cli_transport="native",
                 models_path="/v1/models", chat_path="/v1/chat/completions"):
        if mock_mode is None:
            mock_mode = settings.LLM_MOCK
        self.mock_mode = mock_mode
        self.model = model or settings.LLM_MODEL
        self.timeout_seconds = timeout_seconds
        self.api_url = api_url or settings.LLM_API_URL
        self.api_key = api_key or settings.LLM_API_KEY

        pt = provider_type or getattr(settings, 'LLM_PROVIDER', None) or ("mock" if mock_mode else "openai_compatible")
        self.provider_type = pt

        if (not provider_type and mock_mode) or pt == "mock":
            self._provider: LLMProvider = MockLLMProvider(model=self.model)
        elif pt == "openai_compatible":
            self._provider = OpenAICompatibleProvider(
                base_url=self.api_url, api_key=self.api_key, model=self.model,
                models_path=models_path, chat_path=chat_path, timeout_seconds=timeout_seconds)
        elif pt == "onebit_newton_cli":
            import os
            self._provider = OneBitNewtonCLIProvider(
                cli_path=cli_path or getattr(settings, 'ONEBIT_CLI_PATH', 'newton'),
                transport=cli_transport or getattr(settings, 'ONEBIT_CLI_TRANSPORT', 'native'),
                model=self.model if self.model in ("llama", "gpt4") else "gpt4",
                token=api_key or self.api_key or os.getenv("NEWTON_TOKEN", ""),
                timeout_seconds=timeout_seconds)
        else:
            raise LLMConfigurationError(f"Unknown LLM provider: {pt}")

    def generate(self, system_prompt, user_prompt,
                 temperature=0.3, max_tokens=4096):
        return self._provider.generate(system_prompt, user_prompt, model=self.model,
                                       temperature=temperature, max_tokens=max_tokens)

    def generate_json(self, system_prompt, user_prompt, json_schema, *,
                      temperature=0.1, max_retries=3):
        from services.json_response_parser import parse_and_validate_json
        from services.llm_providers import OneBitProviderError
        import time

        last_cli_error = None
        for attempt in range(max_retries):
            try:
                raw_response = self.generate(
                    system_prompt,
                    user_prompt + "\n\nReturn valid JSON conforming to this schema:\n"
                    + json.dumps(json_schema),
                    temperature=temperature,
                )
            except OneBitProviderError as e:
                # Transient Newton CLI failures (e.g. "Ошибка: unknown", exit 1)
                # should be retried, not surfaced immediately.
                last_cli_error = e
                if attempt < max_retries - 1:
                    time.sleep(2 * (attempt + 1))
                    continue
                raise
            try:
                parsed, errors = parse_and_validate_json(
                    raw_response, json_schema, max_repair_attempts=0, generate_fn=None
                )
                return parsed, raw_response
            except RuntimeError:
                if attempt < max_retries - 1:
                    continue
                raise
        raise RuntimeError(f"JSON generation failed after {max_retries} retries")

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

    def check_connection(self):
        return self._provider.check_connection().ok
