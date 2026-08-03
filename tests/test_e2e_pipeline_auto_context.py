import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import services.processing_service as ps
from models.batch import BatchItem
from services.runtime_config import RuntimeConfig


_CONTROL = (
    "Встреча по складскому контуру на базе 1С и Mobile SMARTS (Клеверенс) с ТСД. "
    "Обсуждались приёмка и размещение, маркированный товар, Data Matrix, "
    "управление доставкой. Роял Фуд — владелец товара. "
    "Договорились: подготовить план тестирования на следующую неделю; "
    "утвердить схему размещения; собрать прототип штрихкодирования."
)

_MAIN_LLM = {
    "protocol_title": "Встреча по складскому контуру",
    "general_info": {"meeting_date": "2026-07-31", "meeting_context": "Склад 3PL"},
    "meeting_purpose": "Обсудить складской контур и план пилота.",
    "meeting_context": "Роял Фуд / Склад 3PL.",
    "key_outcomes": ("Согласован план тестирования на следующую неделю. "
                     "Утверждена схема размещения. Собран прототип штрихкодирования."),
    "current_state": [
        {"object": "Приёмка и размещение", "status": "В работе"},
        {"object": "Управление доставкой", "status": "Уточняется"},
    ],
    "participants": [{"name": "Сергей", "role": "Заказчик"}, {"name": "Анна", "role": "Консультант"}],
    "topic_blocks": [
        {"topic_id": "t1", "title": "Приёмка и размещение",
         "discussion_content": "Обсуждали приёмку и размещение маркированного товара. "
                               "Согласовали порядок проверки Data Matrix.",
         "conclusion": "Согласован порядок проверки. Вывод по приёмке утверждён.",
         "status_text": "Согласовано",
         "status_responsible": "Анна", "status_deadline": "11.08.2026"},
    ],
    "decisions": [], "questions": [], "risks": [], "tasks": [],
}


class StubLLM:
    def __init__(self):
        self.calls = []

    def generate_json(self, system_prompt="", user_prompt="", json_schema=None,
                      temperature=0.1, max_retries=1, **kw):
        self.calls.append((system_prompt, user_prompt))
        required = (json_schema or {}).get("required", [])
        if required == ["decisions", "questions", "risks", "tasks"]:
            return {"decisions": [], "questions": [], "risks": [], "tasks": []}, "{}"
        return dict(_MAIN_LLM), json.dumps(_MAIN_LLM, ensure_ascii=False)


def _make_item(tmp, transcript):
    src = tmp / "control.txt"
    src.write_text(transcript, encoding="utf-8")
    dbg = tmp / "debug"
    return BatchItem(
        source_type="local_transcript",
        source_path=src,
        display_name="Встреча по складу 3PL",
        protocol_template="project_detailed",
        protocol_mode="auto",
        dry_run=True,
        debug_directory=dbg,
    )


def test_e2e_auto_context_resolution(monkeypatch, tmp_path):
    monkeypatch.setattr(ps.settings, "PROTOCOL_QUALITY_MODE", "off")
    monkeypatch.setattr("services.client_factory.build_llm_client",
                        lambda config: StubLLM())

    cfg = RuntimeConfig(bitlink_provider="disabled",
                        transcription_provider="mock",
                        llm_provider="mock",
                        confluence_provider="mock",
                        telegram_provider="disabled")
    svc = ps.ProcessingService(config=cfg)
    item = _make_item(tmp_path, _CONTROL)
    result = svc.process_item(item)

    assert result["success"] is True, result.get("error")

    res = json.loads((item.debug_directory / "project_context_resolution.json").read_text(encoding="utf-8"))
    assert res["client_name"] == "Роял Фуд"
    assert res["project_name"] == "Склад 3PL"

    proto = json.loads((item.debug_directory / "protocol.json").read_text(encoding="utf-8"))
    assert proto["client_name"] == "Роял Фуд"
    assert proto["project_name"] == "Склад 3PL"

    html = (item.debug_directory / "protocol_preview.html").read_text(encoding="utf-8")
    assert "Роял Фуд" in html
    assert "Склад 3PL" in html
    assert html.count("<li>") >= 3