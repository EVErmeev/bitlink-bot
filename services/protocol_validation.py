import re
from datetime import date

from models.protocol import Protocol, TopicBlock
from models.validation import ValidationReport, ValidationStatus

try:
    from services.fact_validation import check_empty_cells, validate_facts
    from services.render_validation import validate_html_render  # noqa: F401
    from services.source_isolation import validate_source_alignment
except ImportError:
    from fact_validation import (  # type: ignore[no-redef]
        check_empty_cells,
        validate_facts,
    )
    from source_isolation import validate_source_alignment  # type: ignore[no-redef]


SECTION_WORD_COUNTS = {
    "project_detailed": {
        "topic_blocks": 0.55,
    },
}


FORBIDDEN_STATUS_CODES = {
    "confirmed", "open", "risk", "in_progress", "closed",
    "pending", "done", "todo", "wip", "new", "resolved",
}


def validate_structure(protocol: Protocol) -> ValidationReport:
    report = ValidationReport()

    _check_required_sections(protocol, report)

    _check_thematic_ratio(protocol, report)

    _check_status_codes(protocol, report)

    _check_date_consistency(protocol, report)

    _check_empty_tables(protocol, report)

    if not report.issues and not report.warnings:
        report.add_issue("structure_ok", "Структура протокола валидна.", ValidationStatus.PASSED)

    return report


def _check_required_sections(protocol: Protocol, report: ValidationReport):
    if not protocol.protocol_id:
        report.add_issue("no_protocol_id", "Отсутствует protocol_id.", ValidationStatus.FAILED)
    if not protocol.template_id:
        report.add_issue("no_template_id", "Отсутствует template_id.", ValidationStatus.FAILED)
    if not protocol.source_context_id:
        report.add_issue("no_source_context", "Отсутствует source_context_id.", ValidationStatus.FAILED,
                         suggestion="Каждый протокол должен иметь уникальный source_context_id.")

    if not protocol.protocol_title or not protocol.protocol_title.strip():
        report.add_issue("no_title", "Название протокола не заполнено.", ValidationStatus.FAILED, "protocol_title")

    if not protocol.participants:
        report.add_issue("no_participants", "Список участников не заполнен.", ValidationStatus.FAILED, "participants")


def _check_thematic_ratio(protocol: Protocol, report: ValidationReport):
    if protocol.template_id != "project_detailed":
        return

    topic_words = 0
    for tb in protocol.topic_blocks:
        content = f"{tb.title or ''} {tb.discussion_content or ''} {tb.conclusion or ''} {tb.status_text or ''}"
        topic_words += len(re.findall(r"\b\w+\b", content))

    all_text_parts = [
        protocol.protocol_title or "",
        protocol.meeting_purpose or "",
        protocol.meeting_context or "",
        protocol.key_outcomes or "",
        protocol.current_state or "",
    ]
    for d in protocol.decisions:
        all_text_parts.append(d.decision_text or "")
        all_text_parts.append(d.context_and_basis or "")
        all_text_parts.append(d.agreed_scope or "")
    for q in protocol.questions:
        all_text_parts.append(q.question_text or "")
        all_text_parts.append(q.context or "")
    for r in protocol.risks:
        all_text_parts.append(r.risk_text or "")
        all_text_parts.append(r.reason or "")
    for t in protocol.tasks:
        all_text_parts.append(t.task_text or "")
        all_text_parts.append(t.expected_result or "")

    total_words = topic_words + sum(len(re.findall(r"\b\w+\b", p)) for p in all_text_parts)

    if total_words > 0:
        ratio = topic_words / total_words
        if ratio < 0.55:
            report.add_issue(
                "thematic_ratio_low",
                f"Тематическая таблица составляет {ratio:.1%} объёма (требуется >=55%). "
                f"Тема: {topic_words} слов, всего: {total_words} слов.",
                ValidationStatus.FAILED,
                "topic_blocks",
                "Расширьте столбцы «Что обсуждалось» и «Итог / вывод» в тематической таблице.",
            )


def _check_status_codes(protocol: Protocol, report: ValidationReport):
    for i, tb in enumerate(protocol.topic_blocks):
        status_str = _collect_status_text(tb)
        status_lower = status_str.lower()
        for code in FORBIDDEN_STATUS_CODES:
            if re.search(rf"\b{re.escape(code)}\b", status_lower):
                report.add_issue(
                    f"topic_{i}_status_code",
                    f"Тематический блок #{i + 1}: статус содержит внутренний код «{code}».",
                    ValidationStatus.FAILED,
                    f"topic_blocks[{i}]",
                )
                break

    for i, q in enumerate(protocol.questions):
        if q.status:
            status_lower = q.status.lower().strip()
            for code in FORBIDDEN_STATUS_CODES:
                if status_lower == code or re.search(rf"\b{re.escape(code)}\b", status_lower):
                    report.add_issue(
                        f"question_{i}_status_code",
                        f"Вопрос #{i + 1}: статус содержит внутренний код «{code}».",
                        ValidationStatus.FAILED,
                        f"questions[{i}].status",
                    )
                    break

    for i, t in enumerate(protocol.tasks):
        if t.status:
            status_lower = t.status.lower().strip()
            for code in FORBIDDEN_STATUS_CODES:
                if status_lower == code:
                    report.add_issue(
                        f"task_{i}_status_code",
                        f"Задача #{i + 1}: статус содержит внутренний код «{code}».",
                        ValidationStatus.FAILED,
                        f"tasks[{i}].status",
                    )
                    break

    for i, r in enumerate(protocol.risks):
        if r.status:
            status_lower = r.status.lower().strip()
            for code in FORBIDDEN_STATUS_CODES:
                if status_lower == code:
                    report.add_issue(
                        f"risk_{i}_status_code",
                        f"Риск #{i + 1}: статус содержит внутренний код «{code}».",
                        ValidationStatus.FAILED,
                        f"risks[{i}].status",
                    )
                    break


def _collect_status_text(tb: TopicBlock) -> str:
    parts = []
    if tb.status_text:
        parts.append(tb.status_text)
    if tb.status_reason:
        parts.append(tb.status_reason)
    if tb.status_next_action:
        parts.append(tb.status_next_action)
    return " ".join(parts)


def _check_date_consistency(protocol: Protocol, report: ValidationReport):
    meeting_date = protocol.meeting_date

    if meeting_date and isinstance(meeting_date, date):
        if meeting_date > date.today():
            report.add_issue(
                "future_meeting_date",
                f"Дата встречи {meeting_date.isoformat()} находится в будущем.",
                ValidationStatus.WARNING,
                "meeting_date",
            )


def _check_empty_tables(protocol: Protocol, report: ValidationReport):
    empty_cells = check_empty_cells(protocol)
    for ec in empty_cells:
        report.add_issue("empty_cell", ec, ValidationStatus.FAILED)


def validate_protocol_complete(protocol: Protocol) -> ValidationReport:
    combined = ValidationReport()

    source_report = validate_source_alignment(protocol, protocol.source_context_id)
    _merge_report(combined, source_report)

    fact_report = validate_facts(protocol, "")
    _merge_report(combined, fact_report)

    structure_report = validate_structure(protocol)
    _merge_report(combined, structure_report)

    if not combined.issues and not combined.warnings:
        combined.add_issue("overall_ok", "Все проверки протокола пройдены успешно.", ValidationStatus.PASSED)

    return combined


def _merge_report(target: ValidationReport, source: ValidationReport):
    for issue in source.issues:
        target.add_issue(issue.code, issue.message, issue.severity, issue.location, issue.suggestion)
    for warning in source.warnings:
        target.add_issue(warning.code, warning.message, warning.severity, warning.location, warning.suggestion)
    for check_name, check_result in source.checks.items():
        target.checks[check_name] = check_result
