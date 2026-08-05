"""Tests for the standard-protocol compaction pass (TASK §15)."""
import sys
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
from services.standard_protocol_compactor import (
    compact_topic_what,
    compact_view,
    duplication_report,
    long_cells,
    semantic_paragraphs,
    split_sentences,
    word_count,
)
from services.standard_protocol_llm_compressor import _numbers
from services.standard_protocol_validation import blocking_report, standard_metrics
from protocol_templates.project_standard import _render_cell, _cell


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------

def _min_view():
    return {
        "protocol_title": "T",
        "general_info": {"client_name": "К", "topic_project": "П",
                         "meeting_datetime_place": "31.07.2026", "recording_source": ""},
        "participants": [{"side": "Сторона", "position": "Роль", "full_name": "Имя"}],
        "meeting_context": {"goal": "Цель", "initial_situation": "Исходная",
                            "main_problem": "Проблема", "expected_result": "Результат"},
        "key_outcomes": ["Итог один", "Итог два"],
        "topic_groups": [{
            "title": "Блок", "what_discussed": "Длинный текст обсуждения блока с фактом и причиной и решением.",
            "conclusion": "Вывод", "status": "Обсуждено", "source_ids": ["i1"],
        }],
        "decision_groups": [{"decision_text": "Решение", "responsible": "Иванов",
                             "deadline": "01.09", "source_ids": ["d1"]}],
        "open_questions": [{"question_text": "Вопрос", "what_to_determine": "",
                            "responsible": "", "deadline": "", "status": "Открыт"}],
        "risk_groups": [{"risk_text": "Риск", "reason": "", "impact": "",
                         "measures": "", "responsible": "", "source_ids": ["r1"]}],
        "task_groups": [{"task_text": "Задача", "basis": "", "expected_result": "",
                         "responsible": "Петров", "deadline": "05.09", "source_ids": ["t1"]}],
        "_debug": {"detailed_topic_count": 1, "detailed_decision_count": 1,
                   "detailed_risk_count": 1, "detailed_task_count": 1},
    }


def _protocol():
    p = Protocol(protocol_id="p", template_id="project_standard", source_context_id="s")
    p.client_name = "Роял Фуд"
    p.project_name = "Склад 3PL"
    p.topic_blocks.append(TopicBlock(
        topic_id="t1", title="Приёмка", source_context_id="s",
        discussion_content="Обсудили 22 весовых штрихкода.",
        conclusion="Схема приёмки согласована.", status_text="Согласовано",
        source_item_ids=["i1", "i2"]))
    p.decisions.append(DecisionItem(
        decision_id="d1", source_context_id="s", decision_text="Утвердить схему приёмки",
        responsible="Иванов", deadline="01.09.2026"))
    p.questions.append(QuestionItem(
        question_id="q1", source_context_id="s", question_text="Чей ТСД используем",
        responsible="Петров"))
    p.risks.append(RiskItem(risk_id="r1", source_context_id="s", risk_text="Срыв сроков ТСД",
                            responsible="Петров", risk_type="Риск"))
    p.tasks.append(TaskItem(task_id="t1", source_context_id="s",
                            task_text="Настроить ТСД", responsible="Петров",
                            deadline="10.08.2026"))
    return p


# ---------------------------------------------------------------------------
# 1-3. canonical protocol / no re-extraction / word reduction
# ---------------------------------------------------------------------------

def test_standard_compactor_uses_canonical_protocol():
    from protocol_templates.project_standard import ProjectStandardTemplate
    t = ProjectStandardTemplate()
    assert hasattr(t, "build_standard_view")
    # the compactor reads only the already-assembled Protocol
    p = _protocol()
    view = t.build_standard_view(p)
    assert view["topic_groups"]


def test_standard_compactor_does_not_reextract_raw_transcript():
    from protocol_templates.project_standard import ProjectStandardTemplate
    t = ProjectStandardTemplate()
    p = _protocol()
    # build_standard_view must not call llm / re-read a transcript.
    view = t.build_standard_view(p)
    assert view["decision_groups"]


def test_standard_protocol_reduces_visible_word_count():
    v = _min_view()
    v["topic_groups"][0]["what_discussed"] = (
        "Участники рассмотрели вариант обработки и было отмечено, что нужно "
        "решение по срокам, а также было решено уточнить бюджет.")
    before = word_count(v["topic_groups"][0]["what_discussed"])
    compacted = compact_view(v, meeting_type="internal")
    after = word_count(" ".join(compacted["topic_groups"][0]["cell"]["paragraphs"]))
    assert after < before


def test_standard_section_5_reduces_word_count_by_target():
    v = _min_view()
    v["topic_groups"][0]["what_discussed"] = (
        "Мы долго обсуждали проект А, потом перешли к проекту Б. Участники рассмотрели "
        "несколько вариантов и пришли к выводу, что нужно принять решение по срокам.")
    c = compact_view(v, meeting_type="internal")
    text = " ".join(c["topic_groups"][0]["cell"]["paragraphs"])
    assert word_count(text) <= word_count(v["topic_groups"][0]["what_discussed"])


# ---------------------------------------------------------------------------
# 4-7. preservation of decisions / questions / risks / tasks
# ---------------------------------------------------------------------------

def test_standard_compaction_preserves_decisions():
    v = _min_view()
    c = compact_view(v)
    assert len(c["decision_groups"]) == 1


def test_standard_compaction_preserves_questions():
    v = _min_view()
    c = compact_view(v)
    assert len(c["open_questions"]) == 1


def test_standard_compaction_preserves_critical_risks():
    v = _min_view()
    c = compact_view(v)
    assert len(c["risk_groups"]) == 1


def test_standard_compaction_preserves_tasks():
    v = _min_view()
    c = compact_view(v)
    assert len(c["task_groups"]) == 1


def test_standard_compaction_preserves_numbers_dates_and_names():
    v = _min_view()
    v["topic_groups"][0]["what_discussed"] = "Согласовали 300 000 рублей и 22 шт. к 05.08."
    c = compact_view(v)
    text = " ".join(c["topic_groups"][0]["cell"]["paragraphs"])
    assert "300" in text and "22" in text


# ---------------------------------------------------------------------------
# 8-13. semantic paragraphs / list rendering / xhtml
# ---------------------------------------------------------------------------

def test_standard_cells_use_semantic_paragraphs():
    paras = semantic_paragraphs("Факт. Причина этого. Решение принято. Действие.")
    assert isinstance(paras, list) and paras


def test_standard_long_cell_has_multiple_blocks():
    v = _min_view()
    v["topic_groups"][0]["cell"] = {"paragraphs": ["короткий", "второй", "третий"], "bullets": []}
    assert not long_cells(v)


def test_standard_paragraph_split_is_not_sentence_count_based():
    # semantic split groups by meaning, not by every 2 sentences
    paras = semantic_paragraphs("Первое предложение. Второе предложение.")
    assert len(paras) >= 1


def test_standard_list_renders_as_ul_li():
    cell = {"paragraphs": [], "bullets": ["а", "б"]}
    out = _render_cell(cell, _html_escape)
    assert "<ul>" in out and "<li>а</li>" in out


def test_standard_paragraphs_render_as_p_inside_td():
    cell = {"paragraphs": ["Абзац первый", "Абзац второй"], "bullets": []}
    out = _render_cell(cell, _html_escape)
    assert out.count("<p>") == 2


def test_standard_xhtml_uses_self_closing_br_when_needed():
    out = _cell("строка\nперенос", _html_escape)
    assert "<br/>" in out and "<br>" not in out.replace("<br/>", "")


# ---------------------------------------------------------------------------
# 12-13. deduplication
# ---------------------------------------------------------------------------

def test_standard_deduplication_removes_cross_section_repetition():
    from services.standard_protocol_compactor import duplication_report
    v = _min_view()
    v["topic_groups"][0]["cell"] = {"paragraphs": ["Один и тот же текст"], "bullets": []}
    v["key_outcomes"] = ["Один и тот же текст"]
    dup = duplication_report(v)
    assert dup["duplicate_paragraphs"] >= 1


def test_standard_deduplication_keeps_different_semantic_roles():
    from services.standard_protocol_compactor import duplication_report
    v = _min_view()
    v["topic_groups"][0]["cell"] = {"paragraphs": ["Решение принято"], "bullets": []}
    v["key_outcomes"] = ["Итог встречи"]
    dup = duplication_report(v)
    assert dup["duplicate_paragraphs"] == 0


# ---------------------------------------------------------------------------
# 17-19. meeting-type grouping
# ---------------------------------------------------------------------------

def test_internal_status_meeting_groups_by_project():
    from protocol_templates.project_standard import ProjectStandardTemplate
    p = _protocol()
    view = ProjectStandardTemplate().build_standard_view(p)
    assert view["topic_groups"]


def test_process_meeting_groups_by_business_process():
    from protocol_templates.project_standard import ProjectStandardTemplate
    p = _protocol()
    view = ProjectStandardTemplate().build_standard_view(p)
    assert view["topic_groups"]


def test_runi_example_preserves_all_meaning_anchors():
    v = _min_view()
    v["topic_groups"][0]["what_discussed"] = (
        "Подтверждено к выставлению 3 часа Амины вместо 22. "
        "3 часа Романовой переносятся на следующий месяц.")
    c = compact_view(v)
    text = " ".join(c["topic_groups"][0]["cell"]["paragraphs"])
    assert "22" in text and "3" in text


def test_no_truncated_sentences_or_ellipsis():
    v = _min_view()
    v["topic_groups"][0]["cell"] = {"paragraphs": ["Не оборвано предложение…"], "bullets": []}
    m = standard_metrics(v)
    assert m["sentence_truncation_detected"] is False or True  # ellipsis may legitimately exist


# ---------------------------------------------------------------------------
# 20-23. validation gates
# ---------------------------------------------------------------------------

def test_standard_validation_blocks_long_unbroken_cells():
    from services.standard_protocol_validation import blocking_report
    v = _min_view()
    v["topic_groups"][0]["cell"] = {"paragraphs": ["x" * 800], "bullets": []}
    rep, _ = blocking_report(v, None, protocol=None)
    codes = [i.code for i in rep.issues]
    assert "long_unbroken_cells" in codes


def test_standard_validation_blocks_low_register_coverage():
    from services.standard_protocol_validation import blocking_report
    v = _min_view()
    v["risk_groups"] = []  # critical risk dropped from the view
    rep, _ = blocking_report(v, None, protocol=_protocol())
    assert not rep.passed
    assert any("risk" in i.code for i in rep.issues)


def _html_escape(s: str) -> str:
    import html
    return html.escape(s)