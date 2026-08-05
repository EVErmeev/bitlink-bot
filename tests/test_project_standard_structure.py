import json
import sys
from datetime import date, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from models.protocol import (
    DecisionItem,
    Protocol,
    QuestionItem,
    RiskItem,
    TaskItem,
    TopicBlock,
)
from protocol_templates.project_detailed import ProjectDetailedTemplate
from protocol_templates.project_standard import (
    LEGACY_HEADINGS,
    STANDARD_SECTIONS,
    ProjectStandardTemplate,
)
from services.protocol_title import build_protocol_title, extract_short_topic


def _protocol():
    p = Protocol(protocol_id="p", template_id="project_standard", source_context_id="s")
    p.meeting_date = date(2026, 7, 31)
    p.meeting_time = time(10, 30)
    p.client_name = "Роял Фуд"
    p.project_name = "Склад 3PL"
    p.meeting_purpose = (
        "Анализ складских процессов, приёмки, размещения и маркировки товара."
    )
    p.meeting_context = "Проект на этапе моделирования, ведётся склад 3PL."
    p.current_state = "Ожидается рабочая схема приёмки через ТСД."
    p.key_outcomes = (
        "Согласована схема приёмки через ТСД. Определён порядок маркировки. "
        "Назначена задача по настройке ТСД."
    )
    p.participants = [
        {"name": "Семён", "role": "Аналитик"},
        {"name": "Иван", "role": "Не определено"},
        {"name": "Представители проектной команды", "role": ""},
        {"name": "Сотрудники склада", "role": ""},
    ]
    p.topic_blocks.append(TopicBlock(
        topic_id="t1", title="Приёмка", source_context_id="s",
        discussion_content="Обсудили весовые штрихкоды и печать этикеток при приёмке.",
        conclusion="Схема приёмки согласована.", status_text="Согласовано",
        source_item_ids=["i1", "i2"],
    ))
    p.topic_blocks.append(TopicBlock(
        topic_id="t2", title="Маркировка", source_context_id="s",
        discussion_content="Рассмотрели Data Matrix маркированного товара.",
        conclusion="Требует уточнения.", status_text="Требует уточнения",
        source_item_ids=["i3"],
    ))
    p.decisions.append(DecisionItem(
        decision_id="d1", source_context_id="s",
        decision_text="Принять схему приёмки через ТСД.",
        context_and_basis="На основании обсуждения приёмки.",
        responsible="Семён", deadline="31.07.2026",
    ))
    p.decisions.append(DecisionItem(
        decision_id="d2", source_context_id="s",
        decision_text="Утвердить порядок маркировки.",
        context_and_basis="Согласовано с владельцем товара.",
        responsible="Пётр", deadline="05.08.2026",
    ))
    p.questions.append(QuestionItem(
        question_id="q1", source_context_id="s",
        question_text="Когда начнётся тестирование ТСД?",
        to_determine="Дата теста", responsible="Семён", status="Открыт",
    ))
    p.questions.append(QuestionItem(
        question_id="q2", source_context_id="s",
        question_text="Когда начнётся тестирование ТСД?",
        to_determine="Дата теста", responsible="Семён", status="Открыт",
    ))
    p.risks.append(RiskItem(
        risk_id="r1", source_context_id="s", risk_type="Риск",
        risk_text="Задержка маркированных данных.",
        reason="Ожидание поставки.", impact="Сдвиг сроков.", measures="Резерв времени.",
        responsible="Семён",
    ))
    p.tasks.append(TaskItem(
        task_id="w1", source_context_id="s",
        task_text="Настроить ТСД.", basis="Решение по приёмке.",
        expected_result="Рабочий ТСД.", responsible="Семён",
        deadline="01.08.2026", status="Не начато", commitment_confirmed=True,
    ))
    p.tasks.append(TaskItem(
        task_id="w2", source_context_id="s",
        task_text="Подготовить инструкцию маркировки.", basis="Решение по маркировке.",
        expected_result="Инструкция.", responsible="Пётр",
        deadline="10.08.2026", status="Не начато", commitment_confirmed=True,
    ))
    p._standard_source_type = "local_transcript"
    p._standard_source_filename = "local-872b2e3cdd76beb0_transcript.txt"
    p._standard_recording_source = ""
    return p


@pytest.fixture(scope="module")
def standard():
    return ProjectStandardTemplate()


@pytest.fixture(scope="module")
def view(standard):
    return standard.build_standard_view(_protocol())


@pytest.fixture(scope="module")
def html(standard):
    return standard.render_html(_protocol())


class TestTitle:
    def test_standard_title_never_uses_local_filename(self, view):
        assert "local-" not in view["protocol_title"]
        assert "_transcript.txt" not in view["protocol_title"]
        assert ".txt" not in view["protocol_title"]

    def test_standard_title_uses_date_topic_client_project(self, view):
        t = view["protocol_title"]
        assert t.startswith("Протокол от 31.07.26.")
        assert "Приёмка" in t or "Анализ" in t
        assert "Роял Фуд" in t
        # TASK §10: external format is "client + Первый БИТ — тема"; project
        # name is not required in the page title.
        assert "Склад 3PL" not in t

    def test_standard_internal_meeting_title(self):
        t = build_protocol_title(meeting_date=date(2026, 8, 1), short_topic="Разбор эфиров",
                                 meeting_type="internal")
        assert t.startswith("Протокол внутренней встречи от 01.08.26. Разбор эфиров")
        t2 = build_protocol_title(meeting_type="internal", short_topic="Разбор эфиров")
        assert t2 == "Протокол внутренней встречи. Разбор эфиров"

    def test_extract_short_topic_ignores_filename(self, standard):
        p = _protocol()
        p.protocol_title = "local-872b2e3cdd76beb0_transcript.txt"
        topic = extract_short_topic(p)
        assert "local-" not in topic
        assert topic


class TestGeneralInfo:
    def test_standard_general_info_table_contract(self, view):
        gi = view["general_info"]
        assert list(gi.keys()) == [
            "client_name", "topic_project", "meeting_datetime_place", "recording_source",
        ]

    def test_standard_general_info_contains_recording_source(self, view):
        assert "local-872b2e3cdd76beb0_transcript.txt" in view["general_info"]["recording_source"]
        assert view["general_info"]["client_name"] == "Роял Фуд"


class TestParticipants:
    def test_standard_participants_table_contract(self, view):
        for p in view["participants"]:
            assert set(p.keys()) == {"side", "position", "full_name"}

    def test_standard_participants_only_confirmed_attendees(self, view):
        names = {p["full_name"] for p in view["participants"]}
        assert "Семён" in names and "Иван" in names

    def test_standard_participants_have_side(self, view):
        assert all(p["side"] for p in view["participants"])

    def test_standard_does_not_render_group_participant_rows(self, view):
        names = {p["full_name"] for p in view["participants"]}
        assert "Представители проектной команды" not in names
        assert "Сотрудники склада" not in names


class TestContext:
    def test_standard_context_table_has_four_required_keys(self, view):
        assert list(view["meeting_context"].keys()) == [
            "goal", "initial_situation", "main_problem", "expected_result",
        ]
        assert view["meeting_context"]["goal"]
        assert view["meeting_context"]["initial_situation"]


class TestKeyOutcomes:
    def test_standard_key_outcomes_render_as_separate_li(self, html):
        assert html.count("<li>") >= 3


class TestTopics:
    def test_standard_topic_table_contract(self, view):
        for g in view["topic_groups"]:
            assert {"title", "what_discussed", "conclusion", "status"}.issubset(g.keys())

    def test_standard_topics_are_grouped_from_detailed_topics(self, view):
        assert 0 < len(view["topic_groups"]) <= 2
        for g in view["topic_groups"]:
            assert g["source_ids"]

    def test_standard_does_not_render_empty_fixed_topic_blocks(self, view):
        assert view["topic_groups"]
        assert all(g.get("what_discussed") or g.get("title") for g in view["topic_groups"])


class TestDecisions:
    def test_standard_decision_table_contract(self, view):
        for d in view["decision_groups"]:
            assert {"decision_text", "context_and_basis", "responsible", "deadline"}.issubset(d.keys())

    def test_standard_decisions_preserve_source_ids(self, view):
        ids = {sid for d in view["decision_groups"] for sid in d["source_ids"]}
        assert ids == {"d1", "d2"}

    def test_standard_grouping_does_not_merge_different_responsibles(self, view):
        # d1 (Семён) and d2 (Пётр) must remain separate groups.
        assert len(view["decision_groups"]) == 2


class TestQuestions:
    def test_standard_open_questions_are_not_semantically_collapsed(self, view):
        # Only exact-duplicate removal (q2 dropped), q1 stays verbatim.
        assert len(view["open_questions"]) == 1
        assert view["open_questions"][0]["source_ids"] == ["q1"]
        assert view["_debug"]["dropped_questions"]
        assert view["_debug"]["dropped_questions"][0]["drop_reason"] == "exact_duplicate"


class TestRisks:
    def test_standard_risk_table_contract(self, view):
        for r in view["risk_groups"]:
            assert {"risk_type", "risk_text", "reason", "impact", "measures", "responsible"}.issubset(r.keys())

    def test_standard_risks_preserve_reason_impact_strategy(self, view):
        r = view["risk_groups"][0]
        assert r["reason"] and r["impact"] and r["measures"]
        assert r["source_ids"] == ["r1"]


class TestTasks:
    def test_standard_task_table_contract(self, view):
        for t in view["task_groups"]:
            assert {"task_text", "basis", "expected_result", "responsible", "deadline", "status"}.issubset(t.keys())

    def test_standard_tasks_preserve_basis_and_expected_result(self, view):
        for t in view["task_groups"]:
            assert t["basis"] and t["expected_result"]

    def test_standard_grouping_does_not_merge_different_deadlines(self, view):
        # w1 (01.08) and w2 (10.08) have different deadlines -> 2 groups.
        assert len(view["task_groups"]) == 2


class TestGroupingMap:
    def test_standard_grouping_map_has_drop_reason(self, view, standard):
        from services.standard_protocol_grouper import build_grouping_map
        m = build_grouping_map(view)
        assert m["questions"]
        assert m["dropped_items"]
        assert m["dropped_items"][0]["drop_reason"] == "exact_duplicate"


class TestCoverage:
    def test_standard_source_coverage_is_complete(self, view):
        from services.standard_protocol_grouper import source_ids_total
        assert source_ids_total(view["decision_groups"]) == 2
        assert source_ids_total(view["risk_groups"]) == 1
        assert source_ids_total(view["task_groups"]) == 2
        assert source_ids_total(view["open_questions"]) == 1


class TestRender:
    def test_standard_has_no_legacy_sections(self, html):
        for legacy in LEGACY_HEADINGS:
            assert legacy not in html

    def test_standard_xhtml_uses_self_closing_br(self, standard, html):
        import html as html_mod
        from protocol_templates.project_standard import _cell
        # cell helper converts newlines to self-closing <br/>
        assert "<br/>" in _cell("строка один\nстрока два", html_mod.escape)
        # no bare <br> without the self-closing slash may appear anywhere
        assert "<br>" not in html.replace("<br/>", "")

    def test_nine_sections_order(self, html):
        idx = [html.find(sec) for sec in STANDARD_SECTIONS]
        assert all(i >= 0 for i in idx)
        assert idx == sorted(idx)

    def test_title_not_technical_in_html(self, html):
        assert "local-872b2e3cdd76beb0" not in html.split("<body>")[0]


class TestConsistency:
    def test_standard_and_detailed_metadata_match(self, standard):
        from services.standard_protocol_grouper import build_consistency_report
        p = _protocol()
        v = standard.build_standard_view(p)
        rep = build_consistency_report(p, v)
        assert rep["metadata_match"] is True
        assert rep["participants_match"] is True

    def test_standard_and_detailed_registers_are_consistent(self, standard):
        from services.standard_protocol_grouper import build_consistency_report
        p = _protocol()
        v = standard.build_standard_view(p)
        rep = build_consistency_report(p, v)
        for key in ("decision_source_coverage", "question_source_coverage",
                    "risk_source_coverage", "task_source_coverage"):
            assert rep[key] == 1.0

    def test_detailed_protocol_regression_unchanged(self):
        p = _protocol()
        p.template_id = "project_detailed"
        html = ProjectDetailedTemplate().render_html(p)
        assert "Подробный проектный протокол" in html
        assert "Принятые решения" in html
        assert "Обсуждение по тематическим блокам" in html


class TestPipelineWiring:
    def test_standard_pipeline_wiring_dry_run(self, tmp_path, monkeypatch):
        """Offline dry-run: processing_service produces standard title + 9-section
        HTML + standard debug artifacts for a local transcript."""
        import services.processing_service as ps
        from models.batch import BatchItem
        from services.runtime_config import RuntimeConfig

        class StubLLM:
            def generate_json(self, system_prompt="", user_prompt="", json_schema=None,
                              temperature=0.1, max_retries=1, **kw):
                required = (json_schema or {}).get("required", [])
                if required == ["decisions", "questions", "risks", "tasks"]:
                    return {"decisions": [], "questions": [], "risks": [], "tasks": []}, "{}"
                return dict(_MAIN_LLM_STUB), _dump(_MAIN_LLM_STUB)

        monkeypatch.setattr(ps.settings, "PROTOCOL_QUALITY_MODE", "off")
        monkeypatch.setattr("services.client_factory.build_llm_client", lambda config: StubLLM())

        src = tmp_path / "control.txt"
        src.write_text("Встреча по складу 3PL. Роял Фуд. Обсудили приёмку и маркировку.", encoding="utf-8")
        dbg = tmp_path / "debug"
        item = BatchItem(
            source_type="local_transcript", source_path=src,
            display_name="local-872b2e3cdd76beb0_transcript.txt",
            protocol_template="project_standard", protocol_mode="auto",
            dry_run=True, debug_directory=dbg,
        )
        cfg = RuntimeConfig(bitlink_provider="disabled", transcription_provider="mock",
                            llm_provider="mock", confluence_provider="mock",
                            telegram_provider="disabled")
        svc = ps.ProcessingService(config=cfg)
        result = svc.process_item(item)
        assert result["success"] is True, result.get("error")

        proto = json.loads((dbg / "protocol.json").read_text(encoding="utf-8"))
        assert "local-" not in proto["protocol_title"]
        assert "Роял Фуд" in proto["protocol_title"]

        html = (dbg / "protocol_preview.html").read_text(encoding="utf-8")
        for s in STANDARD_SECTIONS:
            assert s in html

        for name in ("standard_protocol_final.json", "standard_protocol_final.html",
                     "standard_grouping_map.json", "standard_vs_detailed_consistency.json",
                     "standard_validation.json", "title_resolution.json"):
            assert (dbg / name).exists(), name


_MAIN_LLM_STUB = {
    "protocol_title": "Встреча по складу 3PL",
    "general_info": {"meeting_date": "2026-07-31", "meeting_context": "Склад 3PL"},
    "meeting_purpose": "Обсудить складской контур.",
    "meeting_context": "Роял Фуд / Склад 3PL.",
    "key_outcomes": "Согласован план тестирования. Утверждена схема размещения.",
    "current_state": "Ожидается пилот приёмки.",
    "participants": [{"name": "Сергей", "role": "Заказчик"}, {"name": "Анна", "role": "Консультант"}],
    "topic_blocks": [{"topic_id": "t1", "title": "Приёмка",
                      "discussion_content": "Обсудили приёмку и маркировку.",
                      "conclusion": "Согласовано.", "status_text": "Согласовано"}],
    "decisions": [], "questions": [], "risks": [], "tasks": [],
}


def _dump(obj):
    import json
    return json.dumps(obj, ensure_ascii=False)