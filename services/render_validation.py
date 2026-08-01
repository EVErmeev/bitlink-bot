import re

from models.protocol import Protocol
from models.validation import ValidationReport, ValidationStatus

REMOVED_SECTIONS_V3 = [
    "Сквозная схема процесса",
    "Согласованные подходы",
    "Рассмотренные варианты",
    "Функциональные разрывы",
    "Контрольные точки",
]

FORBIDDEN_STATUS_CODES = {
    "confirmed", "open", "risk", "in_progress", "closed",
    "pending", "done", "todo", "wip", "new", "resolved",
}

PROJECT_DETAILED_SECTIONS = [
    "Общая информация",
    "Участники",
    "Цель встречи и исходный контекст",
    "Ключевые итоги",
    "Обсуждение по тематическим блокам",
    "Текущее состояние объектов и процессов",
    "Принятые решения",
    "Открытые вопросы",
    "Риски и ограничения",
    "Задачи и следующие шаги",
]

MANAGEMENT_SUMMARY_SECTIONS = [
    "Общая информация",
    "Управленческое резюме",
    "Решения и согласованные подходы",
    "Критические разрывы, риски и блокеры",
    "Задачи",
    "Контрольные точки",
]

PROJECT_STANDARD_SECTIONS = [
    "Общая информация",
    "Участники",
    "Цель и границы",
    "Ключевые итоги",
    "Сквозная схема процесса",
    "Тематические разделы",
    "Согласованные подходы",
    "Функциональные разрывы",
    "Решения",
    "Открытые вопросы",
    "Задачи",
    "Контрольные точки",
]

BUSINESS_PROCESS_SECTIONS = [
    "Процессы AS IS",
    "Роли участников",
    "Системы и документы",
]

TEMPLATE_SECTIONS = {
    "project_detailed": PROJECT_DETAILED_SECTIONS,
    "management_summary": MANAGEMENT_SUMMARY_SECTIONS,
    "project_standard": PROJECT_STANDARD_SECTIONS,
    "business_process_discovery": BUSINESS_PROCESS_SECTIONS,
}


def validate_html_render(html: str, protocol: Protocol) -> ValidationReport:
    report = ValidationReport()

    _check_html_structure(html, report)

    _check_required_sections_in_html(html, protocol, report)

    _check_removed_sections(html, protocol, report)

    _check_empty_table_cells(html, report)

    _check_status_codes_in_html(html, report)

    _check_parseability(html, report)

    _check_thematic_ratio_in_html(html, protocol, report)

    if not report.issues and not report.warnings:
        report.add_issue("render_ok", "Валидация HTML-рендера пройдена", ValidationStatus.PASSED)

    return report


def _check_html_structure(html: str, report: ValidationReport):
    if "<html" not in html:
        report.add_issue("no_html_tag", "Отсутствует тег <html>", ValidationStatus.FAILED)
    if "<head" not in html:
        report.add_issue("no_head_tag", "Отсутствует тег <head>", ValidationStatus.FAILED)
    if "<body" not in html:
        report.add_issue("no_body_tag", "Отсутствует тег <body>", ValidationStatus.FAILED)

    if "<html" in html and "</html>" not in html:
        report.add_issue("unclosed_html", "Тег <html> не закрыт.", ValidationStatus.FAILED)
    if "<body" in html and "</body>" not in html:
        report.add_issue("unclosed_body", "Тег <body> не закрыт.", ValidationStatus.FAILED)

    opened_tables = len(re.findall(r"<table[>\s]", html, re.IGNORECASE))
    closed_tables = len(re.findall(r"</table>", html, re.IGNORECASE))
    if opened_tables != closed_tables:
        report.add_issue(
            "mismatched_table_tags",
            f"Несовпадение количества открывающих ({opened_tables}) "
            f"и закрывающих ({closed_tables}) тегов <table>.",
            ValidationStatus.FAILED,
        )


def _check_required_sections_in_html(html: str, protocol: Protocol, report: ValidationReport):
    template_id = protocol.template_id
    required = TEMPLATE_SECTIONS.get(template_id, PROJECT_DETAILED_SECTIONS)

    for section_name in required:
        if section_name not in html:
            report.add_issue(
                f"missing_section_{_slug(section_name)}",
                f"В HTML отсутствует секция «{section_name}» (требуется для шаблона {template_id}).",
                ValidationStatus.FAILED,
                section_name,
            )

    h2_count = len(re.findall(r"<h2[>\s]", html, re.IGNORECASE))
    if h2_count < 2:
        report.add_issue(
            "too_few_h2",
            f"В HTML найдено только {h2_count} тегов <h2>. Ожидается минимум 2.",
            ValidationStatus.WARNING,
        )


def _check_removed_sections(html: str, protocol: Protocol, report: ValidationReport):
    if protocol.template_id != "project_detailed":
        return

    for removed in REMOVED_SECTIONS_V3:
        pattern = re.compile(
            rf"<h[23][^>]*>\s*{re.escape(removed)}\s*</h[23]>",
            re.IGNORECASE,
        )
        if pattern.search(html):
            report.add_issue(
                f"removed_section_{_slug(removed)}",
                f"В HTML обнаружена удалённая секция «{removed}» "
                f"(должна отсутствовать как отдельный раздел в project_detailed v3).",
                ValidationStatus.FAILED,
                removed,
            )


def _check_empty_table_cells(html: str, report: ValidationReport):
    table_bodies = re.findall(r"<tbody>(.*?)</tbody>", html, re.DOTALL)
    for body_idx, body in enumerate(table_bodies):
        rows = re.findall(r"<tr>(.*?)</tr>", body, re.DOTALL)
        for row_idx, row in enumerate(rows):
            cells = re.findall(r"<td[^>]*>(.*?)</td>", row, re.DOTALL)
            for cell_idx, cell_html in enumerate(cells):
                cell_text = re.sub(r"<[^>]+>", "", cell_html).strip()
                if not cell_text:
                    colspan_match = re.search(
                        r'colspan\s*=\s*["\'](\d+)["\']', row, re.IGNORECASE
                    )
                    if not colspan_match:
                        report.add_issue(
                            f"empty_cell_t{body_idx}_r{row_idx}_c{cell_idx}",
                            f"Пустая ячейка в таблице #{body_idx + 1}, "
                            f"строка #{row_idx + 1}, столбец #{cell_idx + 1}.",
                            ValidationStatus.FAILED,
                        )


def _check_status_codes_in_html(html: str, report: ValidationReport):
    for code in FORBIDDEN_STATUS_CODES:
        pattern = re.compile(
            rf'<td[^>]*>.*?\b{re.escape(code)}\b.*?</td>',
            re.IGNORECASE,
        )
        if pattern.search(html):
            report.add_issue(
                f"status_code_in_html_{code}",
                f"В HTML найден внутренний код статуса «{code}».",
                ValidationStatus.FAILED,
            )


def _check_parseability(html: str, report: ValidationReport):
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        if soup.find("html") is None:
            report.add_issue(
                "bs4_no_html",
                "BeautifulSoup не нашёл тег <html> — возможно, HTML повреждён.",
                ValidationStatus.FAILED,
            )
    except ImportError:
        pass
    except Exception as e:
        report.add_issue(
            "html_parse_error",
            f"Ошибка парсинга HTML: {str(e)[:200]}",
            ValidationStatus.FAILED,
        )


def _check_thematic_ratio_in_html(html: str, protocol: Protocol, report: ValidationReport):
    if protocol.template_id != "project_detailed":
        return

    topic_section_pattern = re.compile(
        r"Обсуждение по тематическим блокам.*?</table>",
        re.DOTALL | re.IGNORECASE,
    )
    topic_match = topic_section_pattern.search(html)
    if topic_match:
        topic_html = topic_match.group()
        topic_words = len(re.findall(r"\b\w+\b", re.sub(r"<[^>]+>", " ", topic_html)))
    else:
        topic_words = 0

    all_text = re.sub(r"<[^>]+>", " ", html)
    all_text = re.sub(r"\s+", " ", all_text).strip()
    total_words = len(re.findall(r"\b\w+\b", all_text))

    if total_words > 0 and topic_words > 0:
        ratio = topic_words / total_words
        if ratio < 0.55:
            report.add_issue(
                "html_thematic_ratio_low",
                f"В HTML тематическая таблица составляет {ratio:.1%} объёма (требуется >=55%). "
                f"Тема: {topic_words} слов, всего: {total_words} слов.",
                ValidationStatus.FAILED,
                "topic_blocks",
            )


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
