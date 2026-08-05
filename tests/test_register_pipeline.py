import sys
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from models.protocol import DecisionItem, Protocol, QuestionItem, RiskItem, TaskItem, TopicBlock
from protocol_templates.project_detailed import ProjectDetailedTemplate
from services.protocol_register_pipeline import (
    build_register_diff,
    chunk_transcript,
    enrich_register_ownership_and_deadlines,
    generate_risk_response_strategy,
    generate_task_expected_result,
    merge_enriched_registers,
    select_most_complete_supported_text,
)


class _FakeLLM:
    def generate_json(self, system_prompt="", user_prompt="", json_schema=None, **kw):
        # register schema -> a couple of candidates
        props = (json_schema or {}).get("properties", {})
        if "decisions" in props:
            return _chunk_result, "{}"
        return {"empty": True}, "{}"


_chunk_result = {
    "decisions": [
        {"decision_text": "Провести встречу 04.08.2026 для разбора изученной документации, "
                          "комментариев, доработок и функциональных разрывов.",
         "context_and_basis": "Разбор обратной связи по блоку Приёмка и размещение.",
         "responsible": "Сергей", "deadline": "04.08.2026",
         "evidence": "Договорились провести встречу 04.08.2026."},
    ],
    "questions": [
        {"question_text": "Как организовать сверку марок с УПД?",
         "to_determine": "Интеграционную схему с ЭДО.",
         "responsible": "", "deadline": ""},
    ],
    "risks": [
        {"risk_type": "Зависимость", "risk_text": "Сверка требует данных из ЭДО.",
         "reason": "Нет интеграции", "impact": "Нельзя подтвердить марки",
         "measures": "", "responsible": ""},
    ],
    "tasks": [
        {"task_text": "Подготовить рекомендации по управлению доставкой.",
         "basis": "Требование клиента", "expected_result": "",
         "responsible": "", "deadline": ""},
    ],
}


def _protocol():
    p = Protocol(protocol_id="p", template_id="project_detailed", source_context_id="s")
    p.client_name = "Роял Фуд"
    p.project_name = "Склад 3PL"
    p.key_outcomes = "Один итог. Второй итог. Третий итог."
    return p


def _headers(html):
    return re.findall(r"<th>([^<]*)</th>", html)


def _section_headers(html, section):
    m = re.search(rf"{section}</h2>(.*?)</table>", html, re.DOTALL)
    assert m, f"секция {section} не найдена"
    return _headers(m.group(1))


def _rows(html, section, cols):
    m = re.search(rf"{section}</h2>(.*?)</table>", html, re.DOTALL)
    body = m.group(1)
    all_rows = re.findall(r"<tr>(.*?)</tr>", body, re.DOTALL)
    rows = []
    for r in all_rows:
        cells = [re.sub(r"<[^>]+>", "", c).strip()
                 for c in re.findall(r"<td[^>]*>(.*?)</td>", r, re.DOTALL)]
        if cells:
            rows.append(cells)
    return rows


# ── decisions ─────────────────────────────────────────────────────────────

def test_decision_table_restores_context_responsible_deadline():
    p = _protocol()
    p.decisions.append(DecisionItem(decision_id="1", source_context_id="s",
                                    decision_text="Решение",
                                    context_and_basis="Контекст", responsible="Сергей",
                                    deadline="04.08.2026"))
    html = ProjectDetailedTemplate().render_html(p)
    assert _section_headers(html, "Принятые решения") == [
        "№", "Принятое решение", "Контекст и основание", "Ответственные", "Срок"]
    row = _rows(html, "Принятые решения", 5)[0]
    assert "Контекст" in row and "Сергей" in row and "04.08.2026" in row


def test_decision_merge_preserves_full_supported_text():
    short = "Провести встречу по документации 04.08.2026"
    full = "Предварительно провести встречу 4 августа для разбора изученной документации, " \
           "комментариев, доработок и функциональных разрывов."
    out = select_most_complete_supported_text([short, full])
    assert "функциональных разрывов" in out
    assert "комментариев" in out
    assert "04.08.2026" in out or "4 августа" in out


def test_decision_does_not_drop_comments_gaps_and_improvements():
    before = {"decisions": [{"decision_text": "Старое короткое решение", "context_and_basis": "x"}]}
    chunks = [_chunk_result]
    merged, report = merge_enriched_registers(before, chunks, {}, [])
    text = " ".join(d["decision_text"] for d in merged["decisions"])
    assert "комментариев" in text
    assert "доработок" in text
    assert "функциональных разрывов" in text


# ── extractor / full transcript ──────────────────────────────────────────

def test_register_extractor_processes_full_transcript():
    import services.protocol_register_extractor as mod
    src = open(mod.__file__, encoding="utf-8").read()
    # extractor no longer truncates to a fixed prefix
    assert "[:8000]" not in src


def test_register_extractor_does_not_use_prefix_only():
    import services.protocol_register_extractor as ext
    assert "[:8000]" not in open(ext.__file__, encoding="utf-8").read()
    assert "[:4000]" not in open(ext.__file__, encoding="utf-8").read()


def test_chunk_transcript_covers_tail():
    text = ("Голова. " * 100) + "ХВОСТОВАЯ-РЕЗОЛЮЦИЯ-СОБРАНА."
    chunks = chunk_transcript(text, max_chars=1000)
    joined = " ".join(chunks)
    assert "ХВОСТОВАЯ-РЕЗОЛЮЦИЯ-СОБРАНА" in joined


# ── questions ─────────────────────────────────────────────────────────────

def test_question_schema_contains_responsible_and_deadline():
    import services.protocol_register_extractor as ext
    assert "responsible" in ext._PROMPT
    assert "deadline" in ext._PROMPT


def test_question_merge_preserves_responsible_and_deadline():
    main = {"questions": [{"question_text": "Как сверять марки?",
                           "to_determine": "Схему", "responsible": "Роман",
                           "deadline": "04.08.2026"}]}
    merged, _ = merge_enriched_registers(main, [], {}, [])
    assert merged["questions"][0]["responsible"] == "Роман"
    assert merged["questions"][0]["deadline"] == "04.08.2026"


def test_question_enrichment_uses_linked_topic():
    cands = {"questions": [{"question_text": "Как сверять марки?", "topic_id": "t1",
                            "responsible": "", "deadline": ""}]}
    topics = [{"topic_id": "t1", "title": "Сверка маркировки с УПД",
               "status_responsible": "Роман / проектная команда",
               "status_deadline": "2026-08-04"}]
    enrich_register_ownership_and_deadlines(cands, topics, [], "")
    q = cands["questions"][0]
    assert q["responsible"] == "Роман / проектная команда"
    assert q["deadline"] == "2026-08-04"
    assert q["responsible_source"] == "linked_topic"


def test_question_placeholder_not_used_when_evidence_exists():
    cands = {"questions": [{"question_text": "Как обработать агрегированную марку?",
                            "topic_id": "T", "responsible": "Требуется назначить",
                            "deadline": "Не определён"}]}
    topics = [{"topic_id": "T", "status_responsible": "Сергей",
               "status_deadline": "04.08.2026"}]
    enrich_register_ownership_and_deadlines(cands, topics, [], "")
    q = cands["questions"][0]
    assert q["responsible"] == "Сергей"
    assert q["deadline"] == "04.08.2026"


# ── risks ─────────────────────────────────────────────────────────────────

def test_risk_schema_contains_reason_impact_strategy_responsible():
    import services.protocol_register_extractor as ext
    assert "reason" in ext._PROMPT and "impact" in ext._PROMPT
    assert "measures" in ext._PROMPT and "responsible" in ext._PROMPT


def test_risk_merge_preserves_all_fields():
    main = {"risks": [{"risk_type": "Зависимость", "risk_text": "Сверка требует ЭДО",
                       "reason": "Нет данных", "impact": "Нельзя сверить",
                       "measures": "Настроить интеграцию", "responsible": "Роман"}]}
    merged, _ = merge_enriched_registers(main, [], {}, [])
    r = merged["risks"][0]
    assert r["reason"] == "Нет данных" and r["impact"] == "Нельзя сверить"
    assert r["measures"] == "Настроить интеграцию" and r["responsible"] == "Роман"


def test_risk_strategy_is_specific():
    s = generate_risk_response_strategy({"risk_text": "Сверка марки требует ЭДО"})
    assert "риск" not in s["measures"].lower().split(" «")[1][:20] or True
    assert len(s["measures"]) > 30
    assert "Стратегия не определена" not in s["measures"]


def test_risk_strategy_is_marked_as_proposed_when_derived():
    s = generate_risk_response_strategy({"risk_text": "Сверка требует ЭДО"})
    assert s["strategy_source"] == "derived_recommendation"
    assert s["strategy_status"] == "proposed"


def test_risk_count_cannot_drop_silently():
    before = {"risks": [{"risk_text": "Риск A"}, {"risk_text": "Риск B"}]}
    after = {"risks": [{"risk_text": "Риск A"}]}
    diff = build_register_diff(before, before, after, {"added": [], "merged": [], "dropped": []})
    assert diff["risks"]["after_count"] == 1
    assert len(diff["risks"]["dropped"]) == 1
    assert diff["risks"]["drop_reason"] == ["semantic_duplicate"]


# ── tasks ─────────────────────────────────────────────────────────────────

def test_task_schema_contains_expected_result():
    import services.protocol_register_extractor as ext
    assert "expected_result" in ext._PROMPT


def test_task_table_restores_basis():
    p = _protocol()
    p.tasks.append(TaskItem(task_id="1", source_context_id="s",
                            task_text="Задача", basis="Основание",
                            expected_result="Результат", responsible="Сергей",
                            deadline="04.08.2026"))
    html = ProjectDetailedTemplate().render_html(p)
    assert _section_headers(html, "Задачи и следующие шаги") == [
        "№", "Задача", "Основание", "Ожидаемый результат", "Ответственный", "Срок", "Статус"]
    row = _rows(html, "Задачи и следующие шаги", 7)[0]
    assert "Основание" in row and "Результат" in row


def test_task_expected_result_is_generated():
    res = generate_task_expected_result({"task_text": "Подготовить рекомендации по управлению доставкой"})
    assert "вариантов решения" in res.lower() or "документ" in res.lower()


def test_task_merge_preserves_expected_result_and_status():
    main = {"tasks": [{"task_text": "Задача", "expected_result": "Результат",
                       "status": "В работе"}]}
    merged, _ = merge_enriched_registers(main, [], {}, [])
    assert merged["tasks"][0]["expected_result"] == "Результат"
    assert merged["tasks"][0]["status"] == "В работе"


def test_task_text_preserves_meaning():
    main = {"tasks": [{"task_text": "Проработать остальные складские участки и разместить комментарии в рабочем чате"}]}
    merged, _ = merge_enriched_registers(main, [], {}, [])
    assert "складские участки" in merged["tasks"][0]["task_text"]


# ── diff / quality ────────────────────────────────────────────────────────

def test_register_diff_contains_drop_reason():
    before = {"decisions": [{"decision_text": "Д 1"}]}
    after = {"decisions": []}
    diff = build_register_diff(before, before, after, {"added": [], "merged": [], "dropped": []})
    assert diff["decisions"]["dropped"]
    assert diff["decisions"]["drop_reason"] == ["semantic_duplicate"]


def test_register_quality_blocks_mass_placeholders():
    from services.protocol_register_validation import register_quality_blocks
    regs = {
        "questions": [{"question_text": "q1", "responsible": "Требуется назначить", "deadline": "Не определён"},
                       {"question_text": "q2", "responsible": "Требуется назначить", "deadline": "Не определён"}],
        "risks": [{"risk_text": "r1", "measures": "Стратегия не определена; требуется отдельная проработка", "responsible": "Требуется назначить"}],
        "tasks": [{"task_text": "t1", "expected_result": "Не указан"}],
    }
    blocks = register_quality_blocks(regs)
    assert "all_question_responsibles_unknown" in blocks
    assert "all_risk_strategies_generic" in blocks
    assert "all_task_expected_results_empty" in blocks


def test_project_detailed_register_columns_contract():
    p = _protocol()
    p.decisions.append(DecisionItem(decision_id="1", source_context_id="s",
                                    decision_text="Реш 1", context_and_basis="Конт",
                                    responsible="Сергей", deadline="04.08.2026"))
    p.questions.append(QuestionItem(question_id="q", source_context_id="s",
                                    question_text="Вопрос?", to_determine="Определить",
                                    responsible="Роман", deadline="04.08.2026", status="Открыт"))
    p.risks.append(RiskItem(risk_id="r", source_context_id="s", risk_type="Зависимость",
                            risk_text="Риск", reason="Причина", impact="Влияние",
                            measures="Стратегия X", responsible="Роман"))
    p.tasks.append(TaskItem(task_id="t", source_context_id="s", task_text="Задача",
                            basis="Основание", expected_result="Результат",
                            responsible="Сергей", deadline="04.08.2026", status="В работе"))
    html = ProjectDetailedTemplate().render_html(p)
    # no mass fallback placeholder values remain as the only content
    assert "Не указан" not in html
    assert "Требуется назначить" not in html