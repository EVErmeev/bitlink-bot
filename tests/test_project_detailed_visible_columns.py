import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from models.protocol import (
    DecisionItem,
    Protocol,
    QuestionItem,
    RiskItem,
    TaskItem,
    TopicBlock,
)
from protocol_templates.project_detailed import ProjectDetailedTemplate


def _build_protocol():
    p = Protocol(protocol_id="p", template_id="project_detailed", source_context_id="s")
    p.client_name = "Роял Фуд"
    p.project_name = "Склад 3PL"
    p.key_outcomes = "Один итог. Второй итог. Третий итог."
    p.topic_blocks.append(TopicBlock(
        topic_id="1", title="Т", source_context_id="s",
        discussion_content="Абзац один. Абзац два.", conclusion="Вывод.",
        status_text="Согласовано",
    ))
    p.decisions.append(DecisionItem(decision_id="1", source_context_id="s",
                                    decision_text="Решение 1",
                                    context_and_basis="основание", boundaries="границы",
                                    related_topic="тема"))
    p.questions.append(QuestionItem(question_id="q", source_context_id="s",
                                    question_text="Вопрос?", to_determine="Определить",
                                    status="Открыт"))
    p.risks.append(RiskItem(risk_id="r", source_context_id="s", risk_type="Риск",
                            risk_text="Риск", measures="Проверить"))
    p.tasks.append(TaskItem(task_id="t", source_context_id="s", task_text="Задача",
                            expected_result="Результат", responsible="Команда",
                            deadline="11.08", status="В работе",
                            co_executors="x", dependencies="y"))
    return p


def _headers(html):
    return re.findall(r"<th>([^<]*)</th>", html)


class TestVisibleColumns:
    def test_decisions_table_has_only_expected_columns(self):
        html = ProjectDetailedTemplate().render_html(_build_protocol())
        sec = re.search(r"Принятые решения</h2>(.*?)</table>", html, re.DOTALL)
        assert sec, "секция решений не найдена"
        assert _headers(sec.group(1)) == ["№", "Принятое решение"]

    def test_questions_table_has_only_expected_columns(self):
        html = ProjectDetailedTemplate().render_html(_build_protocol())
        sec = re.search(r"Открытые вопросы</h2>(.*?)</table>", html, re.DOTALL)
        assert _headers(sec.group(1)) == [
            "№", "Открытый вопрос", "Что требуется определить",
            "Ответственный", "Срок / контрольная точка", "Статус",
        ]

    def test_risks_table_has_response_strategy(self):
        html = ProjectDetailedTemplate().render_html(_build_protocol())
        sec = re.search(r"Риски и ограничения</h2>(.*?)</table>", html, re.DOTALL)
        headers = _headers(sec.group(1))
        assert "Стратегия реагирования" in headers
        assert headers == ["№", "Тип", "Риск / ограничение", "Стратегия реагирования", "Ответственный"]

    def test_tasks_table_has_expected_result_and_status(self):
        html = ProjectDetailedTemplate().render_html(_build_protocol())
        sec = re.search(r"Задачи и следующие шаги</h2>(.*?)</table>", html, re.DOTALL)
        assert _headers(sec.group(1)) == [
            "№", "Задача", "Ожидаемый результат", "Ответственный", "Срок", "Статус",
        ]

    def test_removed_columns_are_absent_from_html(self):
        html = ProjectDetailedTemplate().render_html(_build_protocol())
        for col in ("Соисполнители", "Зависимости", "Связанная тема",
                    "Контекст и основание", "Границы решения", "Что известно",
                    "Следующее действие", "Условие проявления", "Меры"):
            assert col not in html, f"лишняя колонка осталась: {col}"

    def test_visible_tables_have_no_empty_cells(self):
        p = _build_protocol()
        html = ProjectDetailedTemplate().render_html(p)
        report = ProjectDetailedTemplate().validate_render(html, p)
        assert not any(i.code.startswith("empty_cell") for i in report.issues)

    def test_old_protocol_json_is_backward_compatible(self):
        from models.protocol import Protocol as P
        d = {"protocol_id": "x", "template_id": "project_detailed", "source_context_id": "s",
             "client_name": "Роял Фуд", "project_name": "Склад 3PL",
             "topic_blocks": [{"topic_id": "1", "title": "Т", "source_context_id": "s",
                               "discussion_content": "Текст обсуждения.", "conclusion": "Вывод.",
                               "status_text": "Согласовано"}],
             "decisions": [], "questions": [], "risks": [], "tasks": []}
        p = P.from_dict(d)
        assert p.client_name == "Роял Фуд"
        assert p.project_name == "Склад 3PL"
        html = ProjectDetailedTemplate().render_html(p)
        assert "<html" in html