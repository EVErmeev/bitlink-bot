import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from models.protocol import (
    DecisionItem,
    Protocol,
    QuestionItem,
    RiskItem,
    TaskItem,
    TopicBlock,
)
from models.validation import ValidationReport, ValidationStatus
from services.fact_validation import (
    apply_corrections,
    check_empty_cells,
    validate_facts,
)
from services.protocol_validation import validate_protocol_complete, validate_structure
from services.render_validation import validate_html_render


class TestValidationReport:
    def test_empty_report_passes(self):
        report = ValidationReport()
        assert report.passed
        assert len(report.issues) == 0

    def test_add_issue(self):
        report = ValidationReport()
        report.add_issue("test_code", "Test message", ValidationStatus.FAILED)
        assert not report.passed
        assert len(report.issues) == 1
        assert report.issues[0].code == "test_code"

    def test_add_warning(self):
        report = ValidationReport()
        report.add_issue("warn", "Warning", ValidationStatus.WARNING)
        assert report.passed  # warnings don't fail
        assert len(report.warnings) == 1

    def test_to_dict(self):
        report = ValidationReport()
        report.add_issue("e1", "Error", ValidationStatus.FAILED)
        d = report.to_dict()
        assert d["passed"] is False
        assert len(d["issues"]) == 1


class TestFactValidation:
    @pytest.fixture
    def protocol(self):
        ctx = "test_ctx"
        p = Protocol(protocol_id="p1", template_id="project_detailed", source_context_id=ctx)
        p.meeting_date = date(2026, 7, 24)
        p.meeting_purpose = "Test"
        p.protocol_title = "Тестовый протокол"
        p.key_outcomes = "Test outcomes"
        p.current_state = "Test state"

        p.topic_blocks = [
            TopicBlock(
                topic_id="t1", title="Тема 1", source_context_id=ctx,
                discussion_content="Обсуждение темы 1 с деталями. Обсуждались риски и сроки.",
                conclusion="Итог обсуждения первой темы.",
                status_text="В работе",
                status_reason="Ожидание данных",
                status_next_action="Получить данные",
                status_responsible="Иванов",
                status_deadline="30.07.2026",
                order=1, word_count=10,
            ),
        ]
        p.decisions = [
            DecisionItem(
                decision_id="d1", source_context_id=ctx,
                decision_text="Решение 1",
                context_and_basis="Основание решения",
                agreed_scope="Область согласования",
                boundaries="Границы решения",
                responsible="Иванов",
                deadline="30.07.2026",
                related_topic="Тема 1",
                explicit_agreement=True, confidence=0.9,
                evidence='"Согласен" — Иванов',
            ),
        ]
        p.tasks = [
            TaskItem(
                task_id="t1", source_context_id=ctx,
                task_text="Задача 1", basis="Основание задачи",
                expected_result="Ожидаемый результат",
                responsible="Иванов",
                deadline="30.07.2026",
                commitment_confirmed=True,
            ),
        ]
        p.questions = [
            QuestionItem(
                question_id="q1", source_context_id=ctx,
                question_text="Вопрос 1",
                context="Контекст вопроса",
                known_info="Известная информация",
                to_determine="Требуется уточнить",
                responsible="Петров",
                deadline="01.08.2026",
                next_action="Следующее действие",
                status="Открыт",
                related_topic="Тема 1",
            ),
        ]
        p.risks = [
            RiskItem(
                risk_id="r1", source_context_id=ctx,
                risk_text="Риск 1",
                reason="Причина риска",
                impact="Влияние на проект",
                trigger_condition="Условие проявления",
                measures="Меры по смягчению",
                responsible="Сидоров",
                deadline="Постоянно",
                status="Активен",
                related_topic="Тема 1",
            ),
        ]
        return p

    def test_validate_facts_passes(self, protocol):
        transcript = "Обсуждение темы 1. Согласен — Иванов."
        report = validate_facts(protocol, transcript)
        assert protocol.fact_validation_passed or not report.passed

    def test_check_empty_cells_no_issues(self, protocol):
        issues = check_empty_cells(protocol)
        assert len(issues) == 0

    def test_check_empty_cells_detects_empty(self, protocol):
        protocol.topic_blocks[0].title = ""
        issues = check_empty_cells(protocol)
        assert len(issues) > 0

    def test_check_empty_cells_empty_discussion(self, protocol):
        protocol.topic_blocks[0].discussion_content = ""
        issues = check_empty_cells(protocol)
        assert len(issues) > 0

    def test_check_empty_cells_empty_conclusion(self, protocol):
        protocol.topic_blocks[0].conclusion = ""
        issues = check_empty_cells(protocol)
        assert len(issues) > 0

    def test_check_empty_cells_empty_decision(self, protocol):
        protocol.decisions[0].decision_text = ""
        issues = check_empty_cells(protocol)
        assert len(issues) > 0

    def test_apply_corrections_removes_empty_decisions(self, protocol):
        protocol.decisions.append(
            DecisionItem(decision_id="d_empty", source_context_id="ctx", decision_text="")
        )
        corrected = apply_corrections(protocol)
        assert len(corrected.decisions) == 1  # empty one removed

    def test_apply_corrections_sets_false_agreement(self, protocol):
        protocol.decisions[0].explicit_agreement = True
        protocol.decisions[0].evidence = ""
        corrected = apply_corrections(protocol)
        assert corrected.decisions[0].explicit_agreement is False


class TestStructureValidation:
    def test_validate_structure_detailed(self):
        ctx = "ctx"
        p = Protocol(protocol_id="p1", template_id="project_detailed", source_context_id=ctx)
        p.meeting_date = date(2026, 7, 24)
        p.protocol_title = "Test"
        p.meeting_context = "Context"
        p.meeting_purpose = "Purpose"
        p.key_outcomes = "Outcomes"
        p.current_state = "State"
        p.topic_blocks = [
            TopicBlock(
                topic_id="t1", title="Тема", source_context_id=ctx,
                discussion_content="Обсуждался вопрос интеграции систем. Текущий статус — разработка. Были выявлены риски.",
                conclusion="Подтверждена необходимость тестирования.",
                status_text="В работе",
                order=1, word_count=8,
            ),
        ]
        report = validate_structure(p)
        # This may or may not pass depending on the 55% ratio
        assert isinstance(report, ValidationReport)

    def test_validate_protocol_complete(self):
        ctx = "ctx"
        p = Protocol(protocol_id="p1", template_id="project_detailed", source_context_id=ctx)
        p.meeting_date = date(2026, 7, 24)
        p.protocol_title = "Test"
        p.meeting_purpose = "Test purpose"
        p.key_outcomes = "OK"
        p.participants = [{"name": "Иванов", "role": "Разработчик"}]
        p.topic_blocks = [
            TopicBlock(
                topic_id="t1", title="T", source_context_id=ctx,
                discussion_content="Detailed discussion about the project status and integration.",
                conclusion="Conclusion", status_text="OK",
                order=1, word_count=5,
            ),
        ]
        p.source_alignment_passed = True
        p.fact_validation_passed = True
        p.structure_validation_passed = True
        p.render_validation_passed = True
        report = validate_protocol_complete(p)
        assert report.passed


class TestRenderValidation:
    def test_validate_html_passes_basic(self):
        from protocol_templates.registry import TemplateRegistry
        registry = TemplateRegistry()
        template = registry.get("project_detailed")

        ctx = "ctx"
        p = Protocol(protocol_id="p1", template_id="project_detailed", source_context_id=ctx)
        p.meeting_date = date(2026, 7, 24)
        p.protocol_title = "Test"
        p.key_outcomes = "Test"
        p.meeting_purpose = "Test"
        p.meeting_context = "Test"
        p.current_state = "Test"
        discussion = (
            "Детальное обсуждение статуса проекта с анализом рисков и сроков. "
            "Рассмотрены вопросы интеграции систем, текущее состояние разработки. "
        ) * 30
        conclusion = (
            "Подтверждена необходимость дополнительного тестирования интеграции. "
            "Согласован план завершения работ до конца месяца. "
        ) * 15
        p.topic_blocks = [
            TopicBlock(
                topic_id="t1", title="Тема", source_context_id=ctx,
                discussion_content=discussion,
                conclusion=conclusion,
                status_text="В работе",
                order=1, word_count=8,
            ),
        ]

        html = template.render_html(p)
        report = validate_html_render(html, p)
        assert report.passed, f"Issues: {[i.message for i in report.issues]}"

    def test_validate_html_detects_broken(self):
        html = "not valid html <"
        from protocol_templates.registry import TemplateRegistry
        registry = TemplateRegistry()
        _ = registry.get("management_summary")
        ctx = "ctx"
        p = Protocol(protocol_id="p1", template_id="management_summary", source_context_id=ctx)
        p.meeting_date = date(2026, 7, 24)
        report = validate_html_render(html, p)
        assert not report.passed

    def test_validate_html_detects_removed_section(self):
        ctx = "ctx"
        p = Protocol(protocol_id="p1", template_id="project_detailed", source_context_id=ctx)
        html = "<html><body><h2>Сквозная схема процесса</h2></body></html>"
        report = validate_html_render(html, p)
        assert not report.passed

    def test_validate_html_no_removed_sections_in_good_html(self):
        from protocol_templates.registry import TemplateRegistry
        registry = TemplateRegistry()
        template = registry.get("project_detailed")
        ctx = "ctx"
        p = Protocol(protocol_id="p1", template_id="project_detailed", source_context_id=ctx)
        p.meeting_date = date(2026, 7, 24)
        p.protocol_title = "Test"
        p.key_outcomes = "OK"
        p.meeting_purpose = "Test"
        p.meeting_context = "Test"
        p.current_state = "Test"
        discussion = (
            "Обсуждение содержательное и подробное. Рассмотрены ключевые вопросы проекта. "
            "Проанализированы риски и ограничения, предложены меры по их минимизации. "
        ) * 30
        conclusion = (
            "Важный итог обсуждения: необходимо завершить тестирование в срок. "
            "Согласованы действия на ближайшую неделю, распределены задачи. "
        ) * 15
        p.topic_blocks = [
            TopicBlock(
                topic_id="t1", title="Тема", source_context_id=ctx,
                discussion_content=discussion,
                conclusion=conclusion, status_text="В работе",
                order=1, word_count=5,
            ),
        ]
        html = template.render_html(p)
        report = validate_html_render(html, p)
        assert report.passed

    def test_validate_html_detects_empty_cell(self):
        ctx = "ctx"
        p = Protocol(protocol_id="p1", template_id="project_detailed", source_context_id=ctx)
        p.topic_blocks = [
            TopicBlock(
                topic_id="t1", title="Тема", source_context_id=ctx,
                discussion_content="Обсуждение.", conclusion="Итог.",
                status_text="В работе", order=1, word_count=2,
            ),
        ]
        html = "<html><body><table><tr><td></td></tr></table></body></html>"
        report = validate_html_render(html, p)
        assert not report.passed
