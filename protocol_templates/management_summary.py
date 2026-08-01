import re
from datetime import date

from protocol_templates.base import BaseProtocolTemplate
from models.protocol import Protocol, TopicBlock, DecisionItem, QuestionItem, RiskItem, TaskItem
from models.validation import ValidationReport, ValidationStatus


class ManagementSummaryTemplate(BaseProtocolTemplate):
    template_id = "management_summary"
    version = "1.0"
    display_name = "Управленческий протокол"
    description = "Документ для руководителя, куратора и проектного комитета (500-1200 слов, 1-3 страницы)."

    SECTION_NAMES = {
        "general_info": "Общая информация",
        "management_summary": "Управленческое резюме",
        "decisions_and_approaches": "Решения и согласованные подходы",
        "critical_gaps_and_risks": "Критические разрывы, риски и блокеры",
        "tasks": "Задачи",
        "control_points": "Контрольные точки",
    }

    REQUIRED_SECTIONS = [
        "general_info",
        "management_summary",
        "decisions_and_approaches",
        "critical_gaps_and_risks",
        "tasks",
        "control_points",
    ]

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "general_info": {
                    "type": "object",
                    "properties": {
                        "meeting_date": {"type": "string", "format": "date"},
                        "protocol_title": {"type": "string"},
                        "participants": {"type": "array"},
                    },
                },
                "management_summary": {"type": "string", "minLength": 500},
                "decisions_and_approaches": {"type": "array"},
                "critical_gaps_and_risks": {"type": "array"},
                "tasks": {"type": "array"},
                "control_points": {"type": "array"},
            },
            "required": self.REQUIRED_SECTIONS,
        }

    def get_system_prompt(self) -> str:
        return (
            "Ты — аналитик, составляющий краткое управленческое резюме встречи. "
            "Твоя задача — создать документ объёмом 500–1200 слов, ориентированный на руководителя, "
            "куратора и проектный комитет.\n\n"
            "СТРУКТУРА ДОКУМЕНТА:\n"
            "1. Общая информация — дата встречи, название, состав участников.\n"
            "2. Управленческое резюме — ключевой итог встречи в 1-2 абзаца: что достигнуто, "
            "какие решения приняты, что остаётся под вопросом.\n"
            "3. Решения и согласованные подходы — перечень принятых решений с указанием "
            "ответственных и сроков.\n"
            "4. Критические разрывы, риски и блокеры — только то, что угрожает срокам, "
            "бюджету или качеству проекта.\n"
            "5. Задачи — конкретные поручения с ответственными и сроками.\n"
            "6. Контрольные точки — ключевые вехи и даты.\n\n"
            "ПРАВИЛА:\n"
            "- Объём: 500–1200 слов.\n"
            "- Никакой стенограммы обсуждения, никакой навигации по интерфейсу, "
            "никаких длинных тематических таблиц.\n"
            "- Только факты из предоставленных данных. Не придумывай информацию.\n"
            "- Если данных недостаточно, укажи «данные отсутствуют».\n"
            "- Пиши на русском языке."
        )

    def assemble(self, protocol: Protocol, atomic_items: list, meeting_metadata: dict) -> Protocol:
        protocol.template_id = self.template_id
        protocol.atomic_items = atomic_items

        if meeting_metadata:
            if "date" in meeting_metadata and not protocol.meeting_date:
                raw_date = meeting_metadata["date"]
                if isinstance(raw_date, str):
                    try:
                        protocol.meeting_date = date.fromisoformat(raw_date)
                    except ValueError:
                        pass
                elif isinstance(raw_date, date):
                    protocol.meeting_date = raw_date

            protocol.protocol_title = meeting_metadata.get("title", protocol.protocol_title)
            protocol.meeting_purpose = meeting_metadata.get("purpose", protocol.meeting_purpose)

            if "participants" in meeting_metadata:
                protocol.participants = meeting_metadata["participants"]

        return protocol

    def validate(self, protocol: Protocol) -> ValidationReport:
        report = ValidationReport()

        all_text_parts = [
            protocol.management_summary,
            protocol.control_points,
            protocol.meeting_purpose or "",
            protocol.key_outcomes or "",
        ]
        for d in protocol.decisions:
            all_text_parts.append(d.decision_text)
            all_text_parts.append(d.context_and_basis)
        for t in protocol.tasks:
            all_text_parts.append(t.task_text)
            all_text_parts.append(t.expected_result)
        for r in protocol.risks:
            all_text_parts.append(r.risk_text)
            all_text_parts.append(r.reason)

        combined_text = " ".join(p for p in all_text_parts if p)
        word_count = len(re.findall(r"\b\w+\b", combined_text))

        if word_count < 500:
            report.add_issue(
                "word_count_low",
                f"Слишком мало слов: {word_count} (требуется 500–1200). Добавьте содержания в управленческое резюме.",
                ValidationStatus.FAILED,
                "management_summary",
                "Расширьте управленческое резюме, добавьте контекст решений и описание рисков.",
            )
        elif word_count > 1200:
            report.add_issue(
                "word_count_high",
                f"Слишком много слов: {word_count} (требуется 500–1200). Сократите текст.",
                ValidationStatus.WARNING,
                "management_summary",
                "Уберите детали обсуждения, оставьте только ключевые выводы.",
            )

        if not protocol.management_summary or len(protocol.management_summary.strip()) < 50:
            report.add_issue(
                "summary_empty",
                "Управленческое резюме отсутствует или слишком короткое (минимум 50 символов).",
                ValidationStatus.FAILED,
                "management_summary",
            )

        if not protocol.control_points or len(str(protocol.control_points).strip()) < 10:
            report.add_issue(
                "control_points_empty",
                "Контрольные точки не заполнены.",
                ValidationStatus.WARNING,
                "control_points",
            )

        if protocol.meeting_date is not None and isinstance(protocol.meeting_date, date):
            if protocol.meeting_date > date.today():
                report.add_issue(
                    "future_date",
                    f"Дата встречи {protocol.meeting_date} находится в будущем.",
                    ValidationStatus.WARNING,
                    "meeting_date",
                )

        for i, task in enumerate(protocol.tasks):
            if not task.responsible or task.responsible.strip() == "":
                report.add_issue(
                    f"task_{i}_no_responsible",
                    f"У задачи '{task.task_text[:50]}...' не указан ответственный.",
                    ValidationStatus.FAILED,
                    f"tasks[{i}]",
                )

        for j, d in enumerate(protocol.decisions):
            if not d.decision_text or len(d.decision_text.strip()) < 10:
                report.add_issue(
                    f"decision_{j}_empty",
                    f"Решение #{j + 1} не заполнено.",
                    ValidationStatus.FAILED,
                    f"decisions[{j}]",
                )

        if not report.issues and not report.warnings:
            report.add_issue("all_checks", "Все проверки пройдены", ValidationStatus.PASSED)

        return report

    def render_html(self, protocol: Protocol) -> str:
        date_str = protocol.meeting_date.isoformat() if protocol.meeting_date else "—"

        decisions_rows = ""
        for i, d in enumerate(protocol.decisions, 1):
            decisions_rows += f"""<tr>
<td>{i}</td>
<td>{d.decision_text or '—'}</td>
<td>{d.responsible or '—'}</td>
<td>{d.deadline or '—'}</td>
</tr>
"""

        tasks_rows = ""
        for i, t in enumerate(protocol.tasks, 1):
            tasks_rows += f"""<tr>
<td>{i}</td>
<td>{t.task_text or '—'}</td>
<td>{t.responsible or '—'}</td>
<td>{t.deadline or '—'}</td>
<td>{t.status or '—'}</td>
</tr>
"""

        risks_rows = ""
        for i, r in enumerate(protocol.risks, 1):
            risks_rows += f"""<tr>
<td>{i}</td>
<td>{r.risk_text or '—'}</td>
<td>{r.reason or '—'}</td>
<td>{r.measures or '—'}</td>
</tr>
"""

        participants_list = ""
        if protocol.participants:
            participants_list = "<ul>" + "".join(
                f"<li>{p.get('name', '—')} — {p.get('role', '—')}</li>"
                for p in protocol.participants
            ) + "</ul>"

        html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Управленческий протокол — {protocol.protocol_title or 'Встреча'}</title>
<style>
    body {{
        font-family: 'Segoe UI', Arial, sans-serif;
        max-width: 800px;
        margin: 30px auto;
        padding: 20px 40px;
        color: #1a1a1a;
        line-height: 1.6;
        background: #fff;
    }}
    h1 {{
        color: #1a237e;
        font-size: 24px;
        border-bottom: 3px solid #1a237e;
        padding-bottom: 12px;
        margin-bottom: 8px;
    }}
    .header-meta {{
        color: #666;
        font-size: 14px;
        margin-bottom: 30px;
    }}
    h2 {{
        color: #283593;
        font-size: 18px;
        margin-top: 32px;
        padding-left: 8px;
        border-left: 4px solid #1a237e;
    }}
    h3 {{
        color: #37474f;
        font-size: 15px;
    }}
    table {{
        border-collapse: collapse;
        width: 100%;
        margin: 12px 0 20px 0;
        font-size: 14px;
    }}
    th, td {{
        border: 1px solid #bdbdbd;
        padding: 8px 12px;
        text-align: left;
        vertical-align: top;
    }}
    th {{
        background-color: #e8eaf6;
        color: #1a237e;
        font-weight: 600;
        white-space: nowrap;
    }}
    tr:nth-child(even) td {{
        background-color: #f5f5f5;
    }}
    ul {{
        padding-left: 20px;
        margin: 8px 0;
    }}
    li {{
        margin: 4px 0;
    }}
    p {{
        margin: 8px 0;
    }}
    .footer {{
        margin-top: 40px;
        padding-top: 12px;
        border-top: 1px solid #ccc;
        font-size: 12px;
        color: #999;
    }}
</style>
</head>
<body>
<h1>{self.SECTION_NAMES['general_info']}</h1>
<p class="header-meta"><strong>Дата встречи:</strong> {date_str}</p>
<p><strong>Название:</strong> {protocol.protocol_title or '—'}</p>
<div>
    <h3>Участники:</h3>
    {participants_list or '<p>—</p>'}
</div>

<h2>{self.SECTION_NAMES['management_summary']}</h2>
<div>{protocol.management_summary.replace(chr(10), '<br>') if protocol.management_summary else '<p>—</p>'}</div>

<h2>{self.SECTION_NAMES['decisions_and_approaches']}</h2>
<table>
<thead>
<tr>
    <th>№</th>
    <th>Решение</th>
    <th>Ответственный</th>
    <th>Срок</th>
</tr>
</thead>
<tbody>
{decisions_rows or '<tr><td colspan="4">Решения отсутствуют</td></tr>'}
</tbody>
</table>

<h2>{self.SECTION_NAMES['critical_gaps_and_risks']}</h2>
<table>
<thead>
<tr>
    <th>№</th>
    <th>Риск / ограничение</th>
    <th>Причина</th>
    <th>Меры</th>
</tr>
</thead>
<tbody>
{risks_rows or '<tr><td colspan="4">Риски отсутствуют</td></tr>'}
</tbody>
</table>

<h2>{self.SECTION_NAMES['tasks']}</h2>
<table>
<thead>
<tr>
    <th>№</th>
    <th>Задача</th>
    <th>Ответственный</th>
    <th>Срок</th>
    <th>Статус</th>
</tr>
</thead>
<tbody>
{tasks_rows or '<tr><td colspan="5">Задачи отсутствуют</td></tr>'}
</tbody>
</table>

<h2>{self.SECTION_NAMES['control_points']}</h2>
<div>{protocol.control_points.replace(chr(10), '<br>') if protocol.control_points else '<p>—</p>'}</div>

<div class="footer">Протокол сгенерирован автоматически. Версия шаблона: {self.template_id} v{self.version}</div>
</body>
</html>"""
        return html

    def validate_render(self, html: str, protocol: Protocol) -> ValidationReport:
        report = ValidationReport()

        if "<html" not in html:
            report.add_issue("no_html_tag", "Отсутствует тег <html>", ValidationStatus.FAILED)
        if "<body" not in html:
            report.add_issue("no_body_tag", "Отсутствует тег <body>", ValidationStatus.FAILED)

        for section_key, section_ru in self.SECTION_NAMES.items():
            if section_ru not in html:
                report.add_issue(
                    f"missing_section_{section_key}",
                    f"В HTML отсутствует секция «{section_ru}».",
                    ValidationStatus.FAILED,
                    section_key,
                )

        table_count = len(re.findall(r"<table", html, re.IGNORECASE))
        if table_count < 2:
            report.add_issue(
                "few_tables",
                f"В HTML найдено только {table_count} таблиц. Ожидается минимум 2.",
                ValidationStatus.WARNING,
            )

        empty_tables = re.findall(r"<tbody>\s*<tr>\s*<td[^>]*colspan=\"\d+\"[^>]*>[^<]+</td>\s*</tr>\s*</tbody>", html)
        if len(empty_tables) > 2:
            report.add_issue(
                "too_many_empty_tables",
                f"Слишком много пустых таблиц: {len(empty_tables)}.",
                ValidationStatus.WARNING,
            )

        if not report.issues and not report.warnings:
            report.add_issue("render_ok", "Валидация HTML-рендера пройдена", ValidationStatus.PASSED)

        return report