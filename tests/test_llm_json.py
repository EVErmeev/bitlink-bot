import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from services.llm_service import LLMClient


class TestLLMGenerateJSON:
    @pytest.fixture
    def client(self):
        return LLMClient()

    def test_llm_generate_json_valid_response(self, client, monkeypatch):
        schema = {"type": "object", "properties": {"title": {"type": "string"}}, "required": ["title"]}
        def mock_gen(sp, up, temperature=0.1, max_tokens=4096):
            return '{"title": "Test Meeting"}'
        monkeypatch.setattr(client, 'generate', mock_gen)
        result, raw = client.generate_json(
            "Generate a JSON with a title field",
            "Return: {\"title\": \"Test Meeting\"}",
            json_schema=schema,
        )
        assert "title" in result
        assert isinstance(result["title"], str)

    def test_llm_invalid_json_retries(self, client, monkeypatch):
        schema = {"type": "object", "properties": {"x": {"type": "integer"}}}
        call_count = [0]
        def mock_gen(sp, up, temperature=0.1, max_tokens=4096):
            call_count[0] += 1
            if call_count[0] < 3:
                return "not valid json {{{"
            return '{"x": 42}'
        monkeypatch.setattr(client, 'generate', mock_gen)
        result, raw = client.generate_json("sys", "user", schema)
        assert result == {"x": 42}
        assert call_count[0] == 3

    def test_llm_schema_mismatch_retries(self, client, monkeypatch):
        schema = {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}
        call_count = [0]
        def mock_gen(sp, up, temperature=0.1, max_tokens=4096):
            call_count[0] += 1
            if call_count[0] < 2:
                return '{"wrong_field": 123}'
            return '{"name": "Correct"}'
        monkeypatch.setattr(client, 'generate', mock_gen)
        result, raw = client.generate_json("sys", "user", schema)
        assert result == {"name": "Correct"}
        assert call_count[0] == 2

    def test_llm_invalid_after_retries_marks_item_failed(self, client, monkeypatch):
        schema = {"type": "object", "properties": {"a": {"type": "string"}}, "required": ["a"]}
        def mock_gen(sp, up, temperature=0.1, max_tokens=4096):
            return "not json"
        monkeypatch.setattr(client, 'generate', mock_gen)
        with pytest.raises(RuntimeError, match="not valid JSON"):
            client.generate_json("sys", "user", schema)

    def test_template_receives_parsed_llm_json(self, client, monkeypatch):
        schema = {"type": "object", "properties": {
            "protocol_title": {"type": "string"},
            "key_outcomes": {"type": "string"},
        }, "required": ["protocol_title"]}
        def mock_gen(sp, up, temperature=0.1, max_tokens=4096):
            return '{"protocol_title": "My Protocol", "key_outcomes": "All tasks completed"}'
        monkeypatch.setattr(client, 'generate', mock_gen)
        result, raw = client.generate_json("sys", "Generate protocol", schema)
        assert result["protocol_title"] == "My Protocol"
        assert result["key_outcomes"] == "All tasks completed"
