"""
Integration test: generate sample protocols of all four types
and verify key structural requirements.
"""
import json
import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from models.batch import BatchItem
from models.protocol import (
    DecisionItem,
    Protocol,
    QuestionItem,
    RiskItem,
    TaskItem,
    TopicBlock,
)
from protocol_templates.registry import TemplateRegistry


def _make_base_protocol(template_id, ctx="sample_ctx"):
    p = Protocol(protocol_id=f"sample_{template_id}", template_id=template_id, source_context_id=ctx)
    p.meeting_date = date(2026, 7, 24)
    p.protocol_title = f"Протокол встречи — {template_id}"
    p.meeting_purpose = "Демонстрация генерации протоколов разных типов"
    p.meeting_context = "Встреча проектной команды по обсуждению статуса внедрения ERP-системы."
    p.participants = [
        {"name": "Иванов И.И.", "role": "Руководитель проекта"},
        {"name": "Петров П.П.", "role": "Ведущий аналитик"},
        {"name": "Сидоров С.С.", "role": "Технический архитектор"},
    ]
    p.key_outcomes = (
        "1. Согласована архитектура интеграции с внешними системами. "
        "2. Определены риски и меры по их минимизации. "
        "3. Запланированы задачи на следующий этап."
    )
    p.current_state = "Модуль интеграции разработан на 80%, требуется завершить тестирование API-контрактов."

    discussion = (
        "Исходная ситуация: на момент встречи модуль интеграции находится в активной разработке. "
        "Текущее состояние: реализованы основные REST-эндпоинты, проведено юнит-тестирование. "
        "Продемонстрированы механизмы: обмен данными через REST API, обработка ошибок, логирование. "
        "Системы: 1С:ERP Управление предприятием, внешний сервис доставки \"Деловые линии\". "
        "Документы: спецификация API v2.1, протокол интеграционного тестирования. "
        "Роли: разработчик (Иванов), аналитик (Петров), архитектор (Сидоров). "
        "Вопрос заказчика: гарантирует ли текущая архитектура отказоустойчивость при пиковых нагрузках? "
        "Ответ исполнителя: архитектура предусматривает retry-логику и circuit breaker, но требуется нагрузочное тестирование. "
        "Варианты: использовать очередь сообщений RabbitMQ вместо прямых REST-вызовов. "
        "Аргументы: очередь обеспечит гарантированную доставку и снизит связанность систем. "
        "Ограничения: требуется дополнительная инфраструктура и настройка мониторинга. "
        "Зависимости: доступность тестового стенда, согласование с администраторами инфраструктуры. "
        "Пример: аналогичная схема успешно применена в проекте \"Складской учёт\" (2025). "
        "Даты: тестирование интеграции 28-30 июля 2026, приёмка 31 июля. "
        "Сроки: релиз запланирован на 5 августа 2026. "
        "Требуется проверить: совместимость с версией API внешнего сервиса от 01.08.2026. "
        "Перенесено: нагрузочное тестирование перенесено на этап ОПЭ (опытно-промышленная эксплуатация)."
    ) * 4

    conclusion = (
        "Подтверждено: архитектура REST-интеграции согласована всеми участниками. "
        "Согласовано: использование REST API как основного протокола обмена. "
        "Не согласовано: формат сообщений об ошибках требует дополнительного уточнения с командой внешнего сервиса. "
        "Требуется проверка: совместимость версий API после обновления внешнего сервиса. "
        "Действие: завершить интеграционное тестирование до 30.07.2026. "
        "Срок: 30.07.2026, ответственный: Иванов И.И."
    ) * 3

    p.topic_blocks = [
        TopicBlock(
            topic_id="tb_integration",
            title="Архитектура интеграции с внешним сервисом",
            source_context_id=ctx,
            discussion_content=discussion,
            conclusion=conclusion,
            status_text="Требуется проверка",
            status_reason="Не завершено нагрузочное тестирование",
            status_next_action="Провести нагрузочное тестирование на этапе ОПЭ",
            status_responsible="Иванов И.И.",
            status_deadline="15.08.2026",
            order=1,
            word_count=len(discussion.split()),
        ),
        TopicBlock(
            topic_id="tb_budget",
            title="Бюджет этапа интеграции",
            source_context_id=ctx,
            discussion_content=(
                "Исходная ситуация: бюджет этапа был утверждён в размере 3 млн руб. "
                "Текущее состояние: фактические расходы составили 2.4 млн руб. "
                "Выявлена необходимость дополнительного финансирования на нагрузочное тестирование — 300 тыс. руб. "
                "Вопрос заказчика: возможна ли оптимизация затрат за счёт использования внутренних ресурсов?"
            ) * 2,
            conclusion=(
                "Решение не принято: требуется дополнительный анализ затрат. "
                "Ожидается информация от финансового отдела по доступным резервам. "
                "Срок предоставления данных: 28.07.2026, ответственный: Петров П.П."
            ),
            status_text="Ожидается информация",
            status_reason="Не предоставлены данные по резервам бюджета",
            status_next_action="Запросить данные у финансового отдела",
            status_responsible="Петров П.П.",
            status_deadline="28.07.2026",
            order=2,
            word_count=60,
        ),
    ]

    p.decisions = [
        DecisionItem(
            decision_id="d1",
            source_context_id=ctx,
            decision_text="Использовать REST API как основной протокол интеграции",
            context_and_basis="Архитектурное решение, основанное на анализе требований к интеграции",
            agreed_scope="Синхронный обмен данными между 1С:ERP и внешним сервисом доставки",
            boundaries="Только синхронные запросы; асинхронные сценарии будут рассмотрены на этапе ОПЭ",
            responsible="Иванов И.И., Сидоров С.С.",
            deadline="30.07.2026",
            related_topic="Архитектура интеграции с внешним сервисом",
            order=1,
            explicit_agreement=True,
            confidence=0.95,
            evidence='"Согласен, текущая схема REST-интеграции оптимальна" — Сидоров С.С.',
        ),
    ]

    p.questions = [
        QuestionItem(
            question_id="q1",
            source_context_id=ctx,
            question_text="Реалистично ли завершить внедрение до сентября 2026?",
            context="Сроки дорожной карты проекта предполагают завершение внедрения в сентябре 2026",
            known_info="Текущий статус: разработка — 80%, тестирование — запланировано на август",
            to_determine="Оценка трудоёмкости оставшихся задач от команды разработки",
            responsible="Ответственный не определён",
            deadline="Срок не определён",
            next_action="Запросить оценку трудозатрат у команды разработки",
            status="Открыт",
            related_topic="Архитектура интеграции с внешним сервисом",
            order=1,
        ),
        QuestionItem(
            question_id="q2",
            source_context_id=ctx,
            question_text="Какие альтернативные протоколы рассматривались для интеграции?",
            context="Решение использовать REST API требует обоснования перед архитектурным комитетом",
            known_info="Рассматривались SOAP и gRPC как альтернативы",
            to_determine="Сравнительный анализ REST vs gRPC для данного сценария",
            responsible="Сидоров С.С.",
            deadline="27.07.2026",
            next_action="Подготовить краткое сравнение протоколов",
            status="В работе",
            related_topic="Архитектура интеграции с внешним сервисом",
            order=2,
        ),
    ]

    p.risks = [
        RiskItem(
            risk_id="r1",
            source_context_id=ctx,
            risk_type="Риск",
            risk_text="Изменение API внешнего сервиса доставки без предварительного уведомления",
            reason="Внешний сервис находится в активной фазе развития и может менять контракты",
            impact="Нарушение работы интеграции, задержка релиза на 1-2 недели",
            trigger_condition="Выход новой версии API без обратной совместимости",
            measures="Подписка на changelog внешнего сервиса; еженедельная проверка совместимости; mock-тестирование",
            responsible="Сидоров С.С.",
            deadline="Постоянно",
            status="Активен",
            related_topic="Архитектура интеграции с внешним сервисом",
            order=1,
        ),
        RiskItem(
            risk_id="r2",
            source_context_id=ctx,
            risk_type="Зависимость",
            risk_text="Зависимость от доступности тестового стенда внешнего сервиса",
            reason="Интеграционное тестирование требует доступа к sandbox-среде партнёра",
            impact="Невозможность проведения полного цикла интеграционного тестирования",
            trigger_condition="Недоступность sandbox-среды в согласованные даты",
            measures="Согласовать SLA с партнёром; подготовить mock-сервер как резервный вариант",
            responsible="Петров П.П.",
            deadline="28.07.2026",
            status="Активен",
            related_topic="Архитектура интеграции с внешним сервисом",
            order=2,
        ),
    ]

    p.tasks = [
        TaskItem(
            task_id="t1",
            source_context_id=ctx,
            task_text="Завершить интеграционное тестирование модуля",
            basis="Решение встречи от 24.07.2026; требование дорожной карты проекта",
            expected_result="Протокол успешного прохождения интеграционных тестов",
            responsible="Иванов И.И.",
            co_executors="Сидоров С.С.",
            deadline="30.07.2026",
            dependencies="Доступность тестового стенда внешнего сервиса",
            status="В работе",
            related_topic="Архитектура интеграции с внешним сервисом",
            order=1,
            commitment_confirmed=True,
        ),
        TaskItem(
            task_id="t2",
            source_context_id=ctx,
            task_text="Подготовить уточнённый бюджет этапа интеграции",
            basis="Обсуждение на встрече; необходимость дополнительного финансирования",
            expected_result="Смета с обоснованием дополнительных затрат на 300 тыс. руб.",
            responsible="Петров П.П.",
            co_executors="",
            deadline="28.07.2026",
            dependencies="Данные от финансового отдела (ожидаются 27.07.2026)",
            status="Ожидает входных данных",
            related_topic="Бюджет этапа интеграции",
            order=2,
            commitment_confirmed=True,
        ),
    ]

    return p


class TestGenerateAllTemplates:
    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        self.output_dir = tmp_path
        self.registry = TemplateRegistry()

    def test_generate_management_summary(self):
        template = self.registry.get("management_summary")
        protocol = _make_base_protocol("management_summary")
        protocol.management_summary = (
            "Ключевые результаты встречи: согласована архитектура интеграции, "
            "выявлены риски по срокам, определены следующие шаги. "
            "Проект находится в плановых сроках, критических блокеров нет. "
            "В ходе встречи детально рассмотрены вопросы интеграции с внешним сервисом доставки. "
            "Архитектурное решение о применении REST API одобрено всеми участниками проектной команды. "
            "Определены ключевые контрольные точки на ближайший месяц: завершение интеграционного тестирования, "
            "уточнение бюджета этапа, подготовка документации для сдачи модуля в эксплуатацию. "
            "Риски проекта оценены как управляемые при условии соблюдения согласованных сроков. "
            "Основные риски связаны с возможным изменением API внешнего сервиса и зависимостью от доступности "
            "тестового стенда партнёра. Разработаны меры по минимизации: регулярный мониторинг изменений, "
            "использование mock-тестирования, согласование SLA с партнёром. "
            "Бюджет этапа интеграции требует уточнения в связи с необходимостью дополнительного финансирования "
            "нагрузочного тестирования в размере 300 тыс. руб. Финансовому отделу поручено предоставить данные "
            "по доступным резервам до 28 июля. "
            "Команда проекта демонстрирует высокую степень готовности: модуль интеграции разработан на 80 процентов, "
            "проведено юнит-тестирование, реализованы основные REST-эндпоинты. "
            "Следующий крупный этап — опытно-промышленная эксплуатация, запланированная на август 2026 года. "
            "Критических проблем на текущий момент не выявлено. "
            "Рекомендации руководителю проекта: обеспечить контроль сроков интеграционного тестирования, "
            "согласовать формат сообщений об ошибках с командой внешнего сервиса, "
            "провести дополнительный анализ необходимости использования очереди сообщений RabbitMQ "
            "вместо прямых REST-вызовов для повышения отказоустойчивости системы. "
            "Общий статус проекта оценивается как соответствующий дорожной карте. "
            "Следующая статус-встреча запланирована на 31 июля 2026 года для приёмки результатов тестирования. "
            "Дополнительно обсуждены вопросы масштабирования решения на другие модули системы. "
            "Принято решение о поэтапном внедрении с пилотным запуском на одном подразделении. "
            "Определены критерии успешности пилота: стабильность работы в течение двух недель, "
            "отсутствие критических ошибок, положительная обратная связь от пользователей. "
            "Команде поручено подготовить план пилотного внедрения к следующей встрече. "
            "Также обсуждены вопросы обучения персонала работе с новой системой. "
            "Определён график проведения тренингов для ключевых пользователей. "
            "Согласован формат отчётности по статусу проекта для руководства. "
            "Принято решение о еженедельных отчётах с ключевыми метриками выполнения."
        ) * 2
        protocol.control_points = "28.07.2026 — уточнение бюджета; 30.07.2026 — завершение тестирования; 05.08.2026 — релиз."

        html = template.render_html(protocol)
        report = template.validate(protocol)
        render_report = template.validate_render(html, protocol)

        assert report.passed, f"Validation failed: {[i.message for i in report.issues]}"
        assert render_report.passed

        # Save
        (self.output_dir / "management_summary.json").write_text(
            json.dumps(protocol.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8"
        )
        (self.output_dir / "management_summary.html").write_text(html, encoding="utf-8")
        print(f"  [OK] management_summary — saved to {self.output_dir}")

    def test_generate_project_standard(self):
        template = self.registry.get("project_standard")
        protocol = _make_base_protocol("project_standard")
        protocol.process_scheme = (
            "1. Подготовка: сбор требований, анализ API-контрактов, согласование протоколов обмена данными. "
            "2. Интеграционное тестирование: проверка REST-эндпоинтов, обработка ошибок, логирование операций. "
            "3. Приёмка: демонстрация заказчику, подписание акта, передача в промышленную эксплуатацию. "
            "4. Релиз: развёртывание на продуктивной среде, мониторинг, круглосуточная поддержка. "
            "5. Сопровождение: обработка инцидентов, анализ производительности, непрерывная оптимизация. "
            "На каждом этапе предусмотрены контрольные точки и ответственные лица."
        )
        protocol.thematic_sections = [
            {
                "title": "Архитектура интеграции",
                "content": protocol.topic_blocks[0].discussion_content if protocol.topic_blocks else ""
            },
            {
                "title": "Бюджет и финансирование",
                "content": "Вопросы бюджетирования этапа интеграции, анализ фактических расходов и потребности в дополнительном финансировании. "
                           "Рассмотрены варианты оптимизации затрат за счёт использования внутренних ресурсов компании."
            },
            {
                "title": "Управление рисками и качеством",
                "content": "Идентификация и оценка рисков проекта, разработка мер по минимизации и планов реагирования. "
                           "Ключевые риски включают изменения внешних API и зависимость от доступности тестовых сред."
            },
        ]
        protocol.agreed_approaches = (
            "REST API как основной протокол; синхронные запросы для ключевых операций; "
            "использование JSON как формата обмена данными; ретрай-логика с экспоненциальной задержкой; "
            "логирование всех операций интеграции для аудита и отладки; мониторинг доступности внешнего API; "
            "автоматическое восстановление соединения при сбоях; версионирование контрактов для обратной совместимости; "
            "изолированное тестирование каждого компонента перед интеграцией."
        )
        protocol.functional_gaps = (
            "Отсутствует обработка асинхронных сценариев; формат ошибок не согласован; "
            "не реализована поддержка повторной обработки неуспешных запросов; "
            "отсутствует механизм версионирования API-контрактов; нет автоматического переключения "
            "на резервный канал при недоступности основного сервиса; "
            "не реализован механизм пакетной обработки данных при массовых операциях; "
            "отсутствует инструмент мониторинга производительности интеграционных потоков."
        )
        protocol.control_points = (
            "28.07 — бюджет; 30.07 — тестирование; 05.08 — релиз; "
            "15.08 — промежуточный аудит; 01.09 — завершение этапа ОПЭ; "
            "15.09 — подведение итогов пилотного внедрения; 30.09 — финальный отчёт руководству"
        )

        html = template.render_html(protocol)
        report = template.validate(protocol)
        render_report = template.validate_render(html, protocol)

        assert report.passed, f"Validation failed: {[i.message for i in report.issues]}"
        assert render_report.passed

        (self.output_dir / "project_standard.json").write_text(
            json.dumps(protocol.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8"
        )
        (self.output_dir / "project_standard.html").write_text(html, encoding="utf-8")
        print(f"  [OK] project_standard — saved to {self.output_dir}")

    def test_generate_project_detailed(self):
        template = self.registry.get("project_detailed")
        protocol = _make_base_protocol("project_detailed")

        html = template.render_html(protocol)
        report = template.validate(protocol)
        render_report = template.validate_render(html, protocol)

        # The detailed template requires 55% thematic table ratio
        assert report.passed, f"Detailed validation failed: {[i.message for i in report.issues]}"
        assert render_report.passed

        # Verify key structural requirements
        # 1. No removed sections
        for removed in template.REMOVED_SECTIONS:
            assert removed not in html, f"Removed section '{removed}' found!"

        # 2. Thematic table present
        assert "Обсуждение по тематическим блокам" in html

        # 3. All 10 sections present
        for section_name in template.SECTION_NAMES.values():
            assert section_name in html, f"Missing section: {section_name}"

        # 4. No forbidden status codes
        for code in template.FORBIDDEN_STATUS_CODES:
            assert code not in html.lower(), f"Forbidden code '{code}' in HTML"

        # 5. Decisions have explicit_agreement
        for d in protocol.decisions:
            assert d.explicit_agreement, f"Decision without agreement: {d.decision_text}"

        # 6. Tasks have commitment
        for t in protocol.tasks:
            assert t.commitment_confirmed, f"Task without commitment: {t.task_text}"

        (self.output_dir / "project_detailed.json").write_text(
            json.dumps(protocol.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8"
        )
        (self.output_dir / "project_detailed.html").write_text(html, encoding="utf-8")
        print(f"  [OK] project_detailed v3.0 — saved to {self.output_dir}")

    def test_generate_business_process_discovery(self):
        template = self.registry.get("business_process_discovery")
        protocol = _make_base_protocol("business_process_discovery")
        protocol.processes_as_is = (
            "AS-IS: Заказ клиента → Ручная обработка менеджером → "
            "Передача на склад → Отгрузка → Уведомление клиента."
        )
        protocol.roles_description = "Менеджер по продажам, Кладовщик, Логист, Бухгалтер"
        protocol.systems_and_documents = "1С:ERP, 1С:Документооборот, MS Excel (учёт заказов)"
        protocol.process_steps = [
            {"step": 1, "name": "Приём заказа", "role": "Менеджер", "system": "1С:ERP"},
            {"step": 2, "name": "Обработка заказа", "role": "Менеджер", "system": "1С:ERP"},
            {"step": 3, "name": "Передача на склад", "role": "Логист", "system": "1С:ERP"},
        ]
        protocol.problems = [
            {"id": 1, "problem": "Двойной ввод данных в ERP и Excel", "impact": "Потеря времени", "severity": "Высокая"},
        ]
        protocol.requirements = [
            {"id": 1, "requirement": "Автоматическая синхронизация справочника номенклатуры", "priority": "Высокий"},
        ]
        protocol.integration_points = "Интеграция 1С:ERP с внешним сервисом доставки через REST API"

        html = template.render_html(protocol)
        report = template.validate(protocol)
        render_report = template.validate_render(html, protocol)

        assert report.passed, f"Validation failed: {[i.message for i in report.issues]}"
        assert render_report.passed

        (self.output_dir / "business_process_discovery.json").write_text(
            json.dumps(protocol.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8"
        )
        (self.output_dir / "business_process_discovery.html").write_text(html, encoding="utf-8")
        print(f"  [OK] business_process_discovery — saved to {self.output_dir}")


class TestBatchProcessing:
    def test_sequential_processing(self):
        """Items should be processed one at a time (max_concurrency=1)."""
        from services.processing_service import ProcessingService

        processed_order = []

        def cb(stage, pct, item):
            if stage in ("completed", "failed"):
                processed_order.append(item.item_id)

        service = ProcessingService(progress_callback=cb)

        item1 = BatchItem(source_type="unknown", display_name="item1")
        item2 = BatchItem(source_type="unknown", display_name="item2")

        service.process_item(item1)
        service.process_item(item2)

        # Sequential by design of process_item called one at a time
        assert len(processed_order) == 2

    def test_queue_recovery(self, tmp_path):
        """After crash, successful items should not be reprocessed."""
        from services.batch_service import BatchService

        service = BatchService()
        service.create_batch()

        items = [
            BatchItem(item_id="completed_1", status="completed", display_name="done"),
            BatchItem(item_id="failed_1", status="failed", display_name="failed"),
            BatchItem(item_id="pending_1", status="pending", display_name="pending"),
            BatchItem(item_id="processing_1", status="processing", display_name="processing"),
        ]
        service.add_items(items)

        resumable = service.get_resumable_items()
        assert len(resumable) == 1  # only the "processing" item
        assert resumable[0]["display_name"] == "processing"

        pending = service.get_pending_items()
        assert len(pending) == 1  # only "pending" item
        assert pending[0].display_name == "pending"

        # completed and failed should not be in pending or resumable
        pending_ids = {p.item_id for p in pending}
        resumable_ids = {r["item_id"] for r in resumable}
        assert "completed_1" not in pending_ids
        assert "completed_1" not in resumable_ids
        assert "failed_1" not in pending_ids
        assert "failed_1" not in resumable_ids
