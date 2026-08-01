import pytest
import sys
from pathlib import Path
from datetime import date

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from models.protocol import (
    Protocol, TopicBlock, DecisionItem, QuestionItem, RiskItem, TaskItem
)
from models.validation import ValidationReport, ValidationStatus
from protocol_templates.registry import TemplateRegistry


class TestTemplateRegistry:
    def test_all_four_templates_registered(self):
        registry = TemplateRegistry()
        templates = registry.list_templates()
        ids = [t["id"] for t in templates]
        assert "management_summary" in ids
        assert "project_standard" in ids
        assert "project_detailed" in ids
        assert "business_process_discovery" in ids

    def test_get_template(self):
        registry = TemplateRegistry()
        t = registry.get("project_detailed")
        assert t is not None
        assert t.template_id == "project_detailed"
        assert t.version == "3.0"

    def test_get_nonexistent(self):
        registry = TemplateRegistry()
        assert registry.get("nonexistent") is None


class TestProjectDetailedTemplate:
    @pytest.fixture
    def template(self):
        registry = TemplateRegistry()
        return registry.get("project_detailed")

    @pytest.fixture
    def valid_protocol(self):
        ctx = "test_source_ctx_01"
        p = Protocol(
            protocol_id="test_proto_1",
            template_id="project_detailed",
            source_context_id=ctx,
        )
        p.meeting_date = date(2026, 7, 24)
        p.protocol_title = "Тестовый протокол"
        p.meeting_context = "Обсуждение статуса проекта"
        p.meeting_purpose = "Статус-встреча по проекту ERP"
        p.participants = [
            {"name": "Иванов И.И.", "role": "Руководитель проекта"},
            {"name": "Петров П.П.", "role": "Аналитик"},
        ]
        p.key_outcomes = "Обсуждены основные вопросы интеграции. Приняты решения по срокам."
        p.current_state = "Модуль интеграции готов на 80%"

        # Large topic block (well over 55% of content)
        discussion = (
            "Исходная ситуация: модуль интеграции находится в разработке. "
            "Текущее состояние: завершено 80% работ по API-контрактам. "
            "Продемонстрированы механизмы обмена данными через REST API. "
            "Системы: 1С:ERP, внешний сервис доставки. Роли: разработчик, аналитик. "
            "Вопрос заказчика: когда будет готово тестирование? "
            "Ответ исполнителя: к 30 июля при отсутствии блокеров. "
            "Варианты: использовать mock-сервер для тестирования. "
            "Аргументы: это позволит не зависеть от внешнего API. "
            "Ограничения: требуется настройка тестового окружения. "
            "Зависимости: доступность стенда разработки. "
            "Пример: аналогичный подход использовался в проекте X. "
            "Даты: тестирование 28-30 июля, приёмка 31 июля. "
            "Сроки: релиз запланирован на 5 августа. "
            "Требуется проверить: совместимость версий API. "
            "Перенесено: нагрузочное тестирование на следующий этап."
        ) * 6

        conclusion = (
            "Подтверждено: архитектура интеграции согласована. "
            "Согласовано: использование REST API для обмена. "
            "Не согласовано: формат ошибок требует уточнения. "
            "Требуется проверка: совместимость версий. "
            "Действие: завершить тестирование до 30 июля. "
            "Ответственный: Иванов. Срок: 30.07.2026."
        ) * 2

        p.topic_blocks = [
            TopicBlock(
                topic_id="tb1",
                title="Интеграция с внешним сервисом",
                source_context_id=ctx,
                discussion_content=discussion,
                conclusion=conclusion,
                status_text="Требуется проверка",
                status_reason="Не все тесты пройдены",
                status_next_action="Завершить тестирование",
                status_responsible="Иванов",
                status_deadline="30.07.2026",
                order=1,
                word_count=len(discussion.split()),
            ),
            TopicBlock(
                topic_id="tb2",
                title="Бюджет следующего этапа",
                source_context_id=ctx,
                discussion_content="Обсуждался бюджет на следующий этап. Цифры требуют уточнения. "
                                   "Текущий бюджет: 5 млн руб. Планируемый: 7 млн руб.",
                conclusion="Требуется уточнение бюджета. Ответственный: Петров. Срок: 28.07.2026.",
                status_text="Ожидается информация",
                status_reason="Цифры не предоставлены",
                status_next_action="Предоставить уточнённый бюджет",
                status_responsible="Петров",
                status_deadline="28.07.2026",
                order=2,
                word_count=30,
            ),
        ]

        p.decisions = [
            DecisionItem(
                decision_id="d1",
                source_context_id=ctx,
                decision_text="Использовать REST API для интеграции",
                context_and_basis="Архитектурное решение",
                agreed_scope="Обмен данными между 1С и внешним сервисом",
                boundaries="Только синхронные запросы",
                responsible="Иванов",
                deadline="30.07.2026",
                related_topic="Интеграция с внешним сервисом",
                order=1,
                explicit_agreement=True,
                confidence=0.9,
                evidence="\"Согласен, используем REST API\" — Иванов",
            ),
        ]

        p.questions = [
            QuestionItem(
                question_id="q1",
                source_context_id=ctx,
                question_text="Сроки внедрения до сентября — реалистично?",
                context="Обсуждение roadmap",
                known_info="Текущий план: сентябрь 2026",
                to_determine="Оценка от команды разработки",
                responsible="Ответственный не определён",
                deadline="Срок не определён",
                next_action="Запросить оценку",
                status="Открыт",
                related_topic="Интеграция с внешним сервисом",
                order=1,
            ),
        ]

        p.risks = [
            RiskItem(
                risk_id="r1",
                source_context_id=ctx,
                risk_type="Риск",
                risk_text="Задержка из-за изменения API внешнего сервиса",
                reason="Внешний сервис может изменить API",
                impact="Срыв сроков интеграции",
                trigger_condition="Обновление внешнего сервиса без уведомления",
                measures="Мониторинг изменений, mock-тестирование",
                responsible="Иванов",
                deadline="Постоянно",
                status="Активен",
                related_topic="Интеграция с внешним сервисом",
                order=1,
            ),
        ]

        p.tasks = [
            TaskItem(
                task_id="t1",
                source_context_id=ctx,
                task_text="Завершить тестирование модуля интеграции",
                basis="Решение встречи",
                expected_result="Модуль готов к приёмке",
                responsible="Иванов",
                co_executors="",
                deadline="30.07.2026",
                dependencies="Доступность стенда",
                status="В работе",
                related_topic="Интеграция с внешним сервисом",
                order=1,
                commitment_confirmed=True,
            ),
        ]

        return p

    def test_schema(self, template):
        schema = template.get_schema()
        assert schema["type"] == "object"
        assert "topic_blocks" in schema["properties"]

    def test_no_removed_sections_in_structure(self, template):
        """Five sections must NOT be separate sections in v3.0."""
        assert "process_scheme" not in template.REQUIRED_SECTIONS
        assert "agreed_approaches" not in template.REQUIRED_SECTIONS
        assert "functional_gaps" not in template.REQUIRED_SECTIONS
        assert "control_points" not in template.REQUIRED_SECTIONS
        assert "considered_options" not in template.REQUIRED_SECTIONS
        assert len(template.REMOVED_SECTIONS) == 5

    def test_validate_passes_for_valid_protocol(self, template, valid_protocol):
        report = template.validate(valid_protocol)
        assert report.passed, f"Issues: {[i.message for i in report.issues]}"

    def test_validate_empty_topic_cells(self, template, valid_protocol):
        valid_protocol.topic_blocks[0].discussion_content = ""
        report = template.validate(valid_protocol)
        assert not report.passed

    def test_validate_empty_conclusion(self, template, valid_protocol):
        valid_protocol.topic_blocks[0].conclusion = ""
        report = template.validate(valid_protocol)
        assert not report.passed

    def test_validate_forbidden_status_code(self, template, valid_protocol):
        valid_protocol.topic_blocks[0].status_text = "confirmed"
        report = template.validate(valid_protocol)
        assert not report.passed

    def test_validate_decision_no_agreement(self, template, valid_protocol):
        valid_protocol.decisions[0].explicit_agreement = False
        report = template.validate(valid_protocol)
        assert not report.passed

    def test_validate_decision_no_evidence(self, template, valid_protocol):
        valid_protocol.decisions[0].evidence = ""
        report = template.validate(valid_protocol)
        assert not report.passed

    def test_validate_empty_task_cells(self, template, valid_protocol):
        valid_protocol.tasks[0].task_text = ""
        report = template.validate(valid_protocol)
        assert not report.passed

    def test_validate_date_mismatch(self, template, valid_protocol):
        valid_protocol.meeting_date = date(2026, 1, 1)
        # Protocol was for July 24, now set to Jan 1 - should still pass
        # because date validation checks consistency, but only one date
        report = template.validate(valid_protocol)
        assert report.passed  # date itself is valid

    def test_validate_source_mismatch_in_topics(self, template, valid_protocol):
        valid_protocol.topic_blocks[0].source_context_id = "DIFFERENT"
        report = template.validate(valid_protocol)
        assert not report.passed

    def test_validate_wrong_risk_type(self, template, valid_protocol):
        valid_protocol.risks[0].risk_type = "НедопустимыйТип"
        report = template.validate(valid_protocol)
        assert not report.passed

    def test_thematic_table_ratio_below_55(self, template, valid_protocol):
        # Make topic blocks tiny, add large other content
        valid_protocol.topic_blocks[0].discussion_content = "Короткое обсуждение."
        valid_protocol.topic_blocks[0].conclusion = "Короткий итог."
        valid_protocol.current_state = "Очень много текста о текущем состоянии. " * 50
        report = template.validate(valid_protocol)
        assert not report.passed

    def test_render_html(self, template, valid_protocol):
        html = template.render_html(valid_protocol)
        assert "<html" in html or "<!DOCTYPE" in html or "<div" in html
        assert "Общая информация" in html
        assert "Обсуждение по тематическим блокам" in html

    def test_render_html_no_removed_sections(self, template, valid_protocol):
        html = template.render_html(valid_protocol)
        for removed in template.REMOVED_SECTIONS:
            assert removed not in html, f"Removed section '{removed}' found in HTML"

    def test_validate_render_passes(self, template, valid_protocol):
        html = template.render_html(valid_protocol)
        report = template.validate_render(html, valid_protocol)
        assert report.passed, f"Issues: {[i.message for i in report.issues]}"

    def test_validate_render_detects_removed_section(self, template, valid_protocol):
        html = "<html><body><h2>Сквозная схема процесса</h2></body></html>"
        report = template.validate_render(html, valid_protocol)
        assert not report.passed

    def test_validate_render_detects_forbidden_code(self, template, valid_protocol):
        html = template.render_html(valid_protocol)
        # Inject forbidden code
        html = html.replace("Требуется проверка", "confirmed")
        report = template.validate_render(html, valid_protocol)
        assert not report.passed

    def test_questions_table_in_render(self, template, valid_protocol):
        html = template.render_html(valid_protocol)
        assert "Открытые вопросы" in html
        assert "Сроки внедрения" in html

    def test_decisions_only_confirmed(self, template, valid_protocol):
        # Add a non-confirmed decision - should be caught
        valid_protocol.decisions.append(DecisionItem(
            decision_id="d2", source_context_id=valid_protocol.source_context_id,
            decision_text="Гипотетическое решение",
            explicit_agreement=False, confidence=0.3, evidence="",
        ))
        report = template.validate(valid_protocol)
        assert not report.passed

    def test_all_questions_included(self, template, valid_protocol):
        # Add open question without responsible/deadline
        valid_protocol.questions.append(QuestionItem(
            question_id="q2", source_context_id=valid_protocol.source_context_id,
            question_text="Вопрос без ответственного",
            responsible="", deadline="",
        ))
        report = template.validate(valid_protocol)
        # Still valid - questions without responsible are allowed
        assert report.passed

    def test_task_without_commitment(self, template, valid_protocol):
        valid_protocol.tasks[0].commitment_confirmed = False
        report = template.validate(valid_protocol)
        assert not report.passed

    def test_assemble_creates_content(self, template):
        from models.protocol import AtomicItem
        atomic = [
            AtomicItem(
                item_id="a1", source_context_id="ctx", item_type="факт",
                text="Система готова на 80%", speaker="Иванов", confidence=0.9,
            ),
            AtomicItem(
                item_id="a2", source_context_id="ctx", item_type="решение",
                text="Использовать REST API", speaker="Иванов",
                explicit_agreement=True, confidence=0.95,
                evidence="\"Согласен\" — Петров",
            ),
            AtomicItem(
                item_id="a3", source_context_id="ctx", item_type="задача",
                text="Завершить тестирование до 30.07", speaker="Иванов",
                commitment_confirmed=True, confidence=0.9,
            ),
            AtomicItem(
                item_id="a4", source_context_id="ctx", item_type="риск",
                text="Зависимость от внешнего API", speaker="Петров", confidence=0.8,
            ),
            AtomicItem(
                item_id="a5", source_context_id="ctx", item_type="вопрос",
                text="Сроки реалистичны?", speaker="Иванов", confidence=0.7,
            ),
        ]
        proto = Protocol(protocol_id="p_test", template_id="project_detailed", source_context_id="ctx")
        proto.meeting_date = date(2026, 7, 24)
        proto = template.assemble(proto, atomic, {"date": date(2026, 7, 24)})
        assert len(proto.topic_blocks) > 0
        assert len(proto.decisions) > 0
        assert len(proto.questions) > 0
        assert len(proto.risks) > 0
        assert len(proto.tasks) > 0