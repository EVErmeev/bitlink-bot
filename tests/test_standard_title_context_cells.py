"""TASK-2026-08-05-19BD410: standard title / client+type / context / paragraphs.

Covers the four defect directions for the standard protocol:
  1. title from topic (not meeting_purpose), two-digit year, no ellipsis;
  2. client + meeting type (external/internal/unresolved) with the ural profile;
  3. semantic initial_situation / main_problem (no metadata leak);
  4. cell structure: paragraphs by default, bullets only for true enumeration.
"""
import html as html_mod
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from models.protocol import Protocol, TopicBlock
from protocol_templates.project_standard import ProjectStandardTemplate, _render_cell
from services.meeting_topic_resolver import resolve_meeting_topic
from services.meeting_type_resolver import resolve_meeting_type
from services.protocol_title import build_protocol_title
from services.standard_protocol_compactor import normalize_cell_structure

_P = Path(__file__).resolve().parent.parent
_ESCAPE = html_mod.escape


# ────────────────────────────────────────────────────────────────────────────
# shared fixtures
# ────────────────────────────────────────────────────────────────────────────

def _ural_protocol():
    p = _base_protocol()
    p.meeting_date = date(2026, 7, 31)
    p.meeting_purpose = (
        "Цель встречи — обследовать и согласовать целевую схему работы "
        "производственного блока УралДронЗавода в 1С:ERP."
    )
    p.meeting_context = "31.07.2026, г. Москва, длительность 60 минут."
    p.current_state = "31.07.2026, г. Москва, длительность 60 минут."
    p.client_name = "УралДронЗавод"
    p.project_name = "Внедрение 1С:ERP"
    p._standard_meeting_topic = "Демонстрация процессов блока «Производство»"
    p._standard_meeting_type = "external"
    p._standard_context = {
        "initial_situation": (
            "Продолжается обследование и моделирование производственного блока "
            "УралДронЗавода в 1С:ERP. В работе находятся диспетчирование этапов, "
            "обеспечение материалами, сменные задания, отражение выпуска и расхода, "
            "работа бригад и межцеховые передачи. Часть сценариев подтверждена, "
            "по отдельным требованиям требуется дополнительная проверка или доработка."
        ),
        "main_problem": (
            "Типовой функционал 1С:ERP не полностью покрывает требуемую схему: "
            "посменное списание материалов, смешанный учёт сотрудников и бригад, "
            "контроль загрузки по табелю, частичное выполнение операций и "
            "организация межцеховых передач или кладовых требуют уточнения, "
            "настройки либо функциональной доработки."
        ),
    }
    return p


def _base_protocol():
    from models.protocol import Protocol
    p = Protocol(protocol_id="p", template_id="project_standard", source_context_id="s")
    p.topic_blocks.append(TopicBlock(
        topic_id="t1", title="Диспетчирование этапов", source_context_id="s",
        discussion_content="Рассмотрен процесс производственного диспетчера. "
                           "Диспетчирование этапов. Статус «Начат». Кладовая.",
        conclusion="Требует уточнения.", status_text="Требует уточнения",
        source_item_ids=["i1"]))
    return p


def _view_with_cell(paragraphs=None, bullets=None, structure_type=None):
    cell = {"paragraphs": paragraphs or [], "bullets": bullets or [],
            "source_item_ids": []}
    if structure_type:
        cell["structure_type"] = structure_type
    return {"protocol_title": "T", "general_info": {"client_name": "К", "topic_project": "П",
            "meeting_datetime_place": "31.07.2026", "recording_source": ""},
            "participants": [], "meeting_context": {},
            "key_outcomes": [], "topic_groups": [
                {"title": "Блок", "what_discussed": "", "conclusion": "",
                 "status": "", "source_ids": [], "cell": cell}],
            "decision_groups": [], "open_questions": [],
            "risk_groups": [], "task_groups": []}


# ────────────────────────────────────────────────────────────────────────────
# 1. title / meeting type
# ────────────────────────────────────────────────────────────────────────────

def test_standard_title_uses_topic_not_meeting_purpose():
    p = _protocol_for_title()
    v = ProjectStandardTemplate().build_standard_view(p)
    assert "Цель встречи" not in v["protocol_title"]
    assert "обследовать и согласовать" not in v["protocol_title"]


def test_standard_title_matches_ural_control_sample():
    p = _protocol_for_title()
    v = ProjectStandardTemplate().build_standard_view(p)
    assert v["protocol_title"] == (
        "Протокол от 31.07.26. УралДронЗавод + Первый БИТ — "
        "Демонстрация процессов блока «Производство»"
    )


def test_standard_title_uses_two_digit_year():
    p = _protocol_for_title()
    v = ProjectStandardTemplate().build_standard_view(p)
    assert "31.07.26." in v["protocol_title"]
    assert "31.07.2026" not in v["protocol_title"]


def test_standard_title_contains_client_and_first_bit():
    t = build_protocol_title(meeting_date=date(2026, 7, 31), short_topic="Демонстрация процессов",
                             client_name="УралДронЗавод", meeting_type="external")
    assert "УралДронЗавод" in t
    assert "Первый БИТ" in t


def test_standard_title_has_no_ellipsis():
    p = _protocol_for_title()
    v = ProjectStandardTemplate().build_standard_view(p)
    assert "…" not in v["protocol_title"]


def test_external_meeting_is_not_internal_when_client_missing_initially():
    mt, conf, ev = resolve_meeting_type(
        client_name="", participants=[{"side": "УралДронЗавод"}, {"side": "Первый БИТ"}],
        source_filename="УралДронЗавод + Первый БИТ 31.07.2026.txt", transcript_text="")
    assert mt == "external"
    assert conf == "high"


def test_meeting_type_supports_unresolved():
    mt, conf, _ = resolve_meeting_type(
        source_filename="запись от 01.08.txt", source_title="Совещание",
        participants=[], transcript_text="")
    assert mt == "unresolved"
    assert conf == "low"


def test_ural_profile_is_loaded():
    profs = _load_profiles()
    ids = {p.get("profile_id") for p in profs}
    assert "ural-drone-erp" in ids
    p = next(x for x in profs if x.get("profile_id") == "ural-drone-erp")
    assert p.get("client_name") == "УралДронЗавод"


def test_ural_client_resolved_from_filename():
    from services.project_context_resolver import resolve_project_context
    res = resolve_project_context(
        transcript_text="Встреча по производству 1С:ERP УралДронЗавод.",
        source_filename="УралДронЗавод + Первый БИТ 31.07.2026.txt")
    assert res.client_name in ("УралДронЗавод", "Урал-ДронЗавод")


def test_ural_client_resolved_from_participant_sides():
    from services.project_context_resolver import resolve_project_context
    res = resolve_project_context(
        transcript_text="Совещание по производственному блоку.",
        participants=[
            {"name": "А", "side": "УралДронЗавод"}, {"name": "Б", "side": "Первый БИТ"}])
    assert res.client_name in ("УралДронЗавод", "Урал-ДронЗавод")


def test_llm_project_resolver_receives_actual_context():
    from services import project_context_resolver as pcr
    captured = {}
    class _FakeLLM:
        def generate_json(self, system_prompt="", user_prompt="", json_schema=None,
                          temperature=0.0, max_retries=1, **kw):
            captured["user_prompt"] = user_prompt
            return ({"profile_id": None, "client_name": "УралДронЗавод",
                     "project_name": "Внедрение 1С:ERP", "confidence": "high"}, "{}")
    pcr._resolve_with_llm(
        _FakeLLM(), pcr.load_profiles(),
        transcript_text="встреча УралДронЗавод по производству",
        source_filename="УралДронЗавод + Первый БИТ.txt",
        participants=[{"name": "А", "side": "УралДронЗавод"}])
    assert "УралДронЗавод" in captured.get("user_prompt", "")
    assert "Первый БИТ" in captured.get("user_prompt", "")


def test_meeting_topic_is_noun_phrase():
    topic = resolve_meeting_topic(
        source_title="УралДронЗавод + Первый БИТ — демонстрация процессов блока «Производство»",
        meeting_purpose="Обследовать и согласовать целевую схему работы производственного блока.")
    assert topic == "Демонстрация процессов блока «Производство»"


def test_topic_project_does_not_repeat_goal():
    p = _protocol_for_title()
    v = ProjectStandardTemplate().build_standard_view(p)
    tp = v["general_info"]["topic_project"]
    assert "Цель встречи" not in tp


def _protocol_for_title():
    p = _base_protocol()
    p.meeting_date = date(2026, 7, 31)
    p.meeting_purpose = (
        "Цель встречи — обследовать и согласовать целевую схему работы "
        "производственного блока УралДронЗавода в 1С:ERP."
    )
    p.client_name = "УралДронЗавод"
    p.project_name = "Внедрение 1С:ERP"
    p._standard_meeting_type = "external"
    p._standard_meeting_topic = "Демонстрация процессов блока «Производство»"
    return p


# ────────────────────────────────────────────────────────────────────────────
# 2. render modes: no double title
# ────────────────────────────────────────────────────────────────────────────

def test_confluence_storage_body_has_no_h1_title():
    p = _protocol_for_title()
    t = ProjectStandardTemplate()
    body = t.render_storage_html(p)
    assert "<h1>" not in body
    assert body.strip().startswith("<h2>")


def test_standalone_html_has_exactly_one_h1():
    p = _protocol_for_title()
    html = ProjectStandardTemplate().render_html(p)
    assert html.count("<h1>") == 1


def test_confluence_export_title_occurs_once():
    # storage body has no h1, so the page title appears exactly once (the
    # Confluence page title itself).
    p = _protocol_for_title()
    storage = ProjectStandardTemplate().render_storage_html(p)
    assert storage.count("<h1>") == 0


# ────────────────────────────────────────────────────────────────────────────
# 3. semantic initial_situation / main_problem
# ────────────────────────────────────────────────────────────────────────────

def test_initial_situation_contains_current_project_state():
    p = _protocol_for_title()
    p._standard_context = {
        "initial_situation": "Продолжается обследование производственного блока "
                             "в 1С:ERP. В работе диспетчирование этапов и сменные задания.",
        "main_problem": "Требуется уточнение по посменному списанию материалов.",
    }
    v = ProjectStandardTemplate().build_standard_view(p)
    init = v["meeting_context"]["initial_situation"]
    assert "обследование" in init.lower() or "производственного" in init.lower()


def test_initial_situation_does_not_contain_duration_or_city():
    p = _protocol_for_title()
    v = ProjectStandardTemplate().build_standard_view(p)
    init = v["meeting_context"]["initial_situation"]
    assert "москва" not in init.lower()
    assert "минут" not in init.lower()
    assert "длительность" not in init.lower()


def test_main_problem_contains_consolidated_gaps():
    p = _protocol_for_title()
    p._standard_context = {
        "initial_situation": "Идёт обследование производственного блока.",
        "main_problem": (
            "Типовой функционал не полностью покрывает схему: посменное списание, "
            "смешанный учёт сотрудников и бригад, контроль загрузки по табелю, "
            "частичное выполнение операций и межцеховые передачи требуют доработки."
        ),
    }
    v = ProjectStandardTemplate().build_standard_view(p)
    mp = v["meeting_context"]["main_problem"]
    assert any(k in mp.lower() for k in ("списание", "учёт", "загрузки", "выполнение", "доработк"))


def test_main_problem_does_not_repeat_metadata():
    p = _protocol_for_title()
    v = ProjectStandardTemplate().build_standard_view(p)
    mp = v["meeting_context"]["main_problem"]
    assert "москва" not in mp.lower()
    assert "длительность" not in mp.lower()


# ────────────────────────────────────────────────────────────────────────────
# 4. cell structure: paragraphs by default, list only for true enumeration
# ────────────────────────────────────────────────────────────────────────────

def test_cell_defaults_to_paragraphs():
    cell = normalize_cell_structure({"paragraphs": ["Один"], "bullets": [], "source_item_ids": []})
    assert cell["structure_type"] == "paragraphs"


def test_process_description_is_not_rendered_as_list():
    cell = {"paragraphs": ["Шаг первый.", "Шаг второй.", "Шаг третий."], "bullets": [],
            "structure_type": "paragraphs"}
    out = _render_cell(cell, _ESCAPE)
    assert out.count("<p>") == 3
    assert "<ul>" not in out


def test_speaker_statements_are_paragraphs():
    cell = normalize_cell_structure(
        {"paragraphs": [], "bullets": ["Заказчик: проверить расход.",
                                        "Консультант: подтвердили порядок списания.",
                                        "Заказчик: осталось открыть передачу."],
         "source_item_ids": []})
    assert cell["structure_type"] == "paragraphs"
    assert "<ul>" not in _render_cell(cell, _ESCAPE)


def test_bullets_require_logical_enumeration():
    cell = normalize_cell_structure(
        {"paragraphs": [], "bullets": ["Один очень длинный тезис о процессе производства, "
                              "который сам по себе является связным абзацем",
                              "Второй связный абзац с деталями по настройке"], "source_item_ids": []})
    assert cell["structure_type"] == "paragraphs"


def test_mixed_first_paragraph_rest_bullets_is_normalized():
    cell = normalize_cell_structure(
        {"paragraphs": ["Вступление"], "bullets": ["Тезис один о процессах",
                                     "Тезис два о процессах"], "source_item_ids": []})
    assert cell["structure_type"] == "paragraphs"
    assert not cell["bullets"]


def test_true_enumeration_keeps_ul_li():
    cell = normalize_cell_structure(
        {"paragraphs": ["Рассмотрены следующие варианты:"],
         "bullets": ["Вариант А", "Вариант Б", "Вариант В"], "source_item_ids": []})
    assert cell["structure_type"] in ("paragraphs_with_list", "list")
    assert cell["list_reason"]
    out = _render_cell(cell, _ESCAPE)
    assert "<ul>" in out and "<li>" in out


def test_control_cell_has_five_paragraphs_and_no_list():
    # Control cell about the production dispatcher, "Диспетчирование этапов",
    # status «Начат» and the storehouse must render as five <p> and no list.
    from services.standard_protocol_compactor import normalize_cell_structure as norm
    cell = norm({"paragraphs": [
        "Работа производственного диспетчера.",
        "Диспетчирование этапов производственного процесса.",
        "Статус «Начат».",
        "Обеспечение материалами.",
        "Кладовая для закупок.",
    ], "bullets": [], "source_item_ids": []})
    out = _render_cell(cell, _ESCAPE)
    assert out.count("<p>") == 5
    assert out.count("<ul>") == 0
    assert out.count("<li>") == 0


def test_project_standard_xhtml_remains_valid():
    p = _base_protocol()
    html = ProjectStandardTemplate().render_html(p)
    assert html.count("<p>") >= 1
    assert "<br>" not in html.replace("<br/>", "")


def _load_profiles():
    from services.project_context_resolver import load_profiles
    return load_profiles()
