from protocol_templates.base import BaseProtocolTemplate
from models.protocol import Protocol, TopicBlock, DecisionItem, QuestionItem, RiskItem, TaskItem
from models.validation import ValidationReport, ValidationStatus


class BusinessProcessDiscoveryTemplate(BaseProtocolTemplate):
    template_id = "business_process_discovery"
    version = "1.0"
    display_name = "Протокол обследования бизнес-процессов"
    description = "Протокол первичного обследования бизнес-процессов AS IS"

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "general_info": {"type": "object"},
                "processes_as_is": {"type": "string"},
                "roles_description": {"type": "string"},
                "systems_and_documents": {"type": "string"},
                "process_steps": {"type": "array"},
                "problems": {"type": "array"},
                "requirements": {"type": "array"},
                "decisions": {"type": "array"},
                "tasks": {"type": "array"},
                "risks": {"type": "array"},
                "questions": {"type": "array"},
                "integration_points": {"type": "string"},
            },
        }

    def get_system_prompt(self) -> str:
        return (
            "Ты — аналитик, составляющий протокол обследования бизнес-процессов. "
            "Твоя задача — зафиксировать процессы AS IS, роли участников, "
            "используемые системы и документы, выявленные проблемы и требования. "
            "Опиши каждый шаг процесса максимально подробно. "
            "Не придумывай то, что не было сказано на встрече."
        )

    def assemble(self, protocol: Protocol, atomic_items: list, meeting_metadata: dict) -> Protocol:
        protocol.atomic_items = atomic_items
        protocol.template_id = self.template_id
        if meeting_metadata:
            protocol.meeting_purpose = meeting_metadata.get("purpose", protocol.meeting_purpose)
        return protocol

    def validate(self, protocol: Protocol) -> ValidationReport:
        report = ValidationReport()
        if not protocol.processes_as_is or len(protocol.processes_as_is.strip()) < 50:
            report.add_issue(
                "processes_empty",
                "Описание бизнес-процессов AS IS отсутствует или слишком короткое",
                ValidationStatus.FAILED,
                "processes_as_is",
            )
        if not protocol.roles_description or len(protocol.roles_description.strip()) < 30:
            report.add_issue(
                "roles_empty",
                "Описание ролей отсутствует или слишком короткое",
                ValidationStatus.FAILED,
                "roles_description",
            )
        report.add_issue("structure_check", "Структура протокола проверена", ValidationStatus.PASSED)
        return report

    def render_html(self, protocol: Protocol) -> str:
        date_str = protocol.meeting_date.isoformat() if protocol.meeting_date else "—"
        return f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<title>{protocol.protocol_title or 'Протокол обследования бизнес-процессов'}</title>
<style>
body {{ font-family: Arial, sans-serif; max-width: 900px; margin: 0 auto; padding: 20px; color: #333; }}
h1 {{ color: #1a237e; border-bottom: 2px solid #1a237e; padding-bottom: 10px; }}
h2 {{ color: #283593; margin-top: 30px; }}
table {{ border-collapse: collapse; width: 100%; margin: 15px 0; }}
th, td {{ border: 1px solid #ccc; padding: 8px 10px; text-align: left; vertical-align: top; }}
th {{ background-color: #e8eaf6; font-weight: bold; }}
</style>
</head>
<body>
<h1>{protocol.protocol_title or 'Протокол обследования бизнес-процессов'}</h1>
<p><strong>Дата встречи:</strong> {date_str}</p>
<h2>Процессы AS IS</h2>
<p>{protocol.processes_as_is or '—'}</p>
<h2>Роли участников</h2>
<p>{protocol.roles_description or '—'}</p>
<h2>Системы и документы</h2>
<p>{protocol.systems_and_documents or '—'}</p>
<h2>Выявленные проблемы</h2>
{"<ul>" + "".join(f"<li>{p}</li>" for p in protocol.problems) + "</ul>" if protocol.problems else "<p>—</p>"}
<h2>Требования</h2>
{"<ul>" + "".join(f"<li>{r}</li>" for r in protocol.requirements) + "</ul>" if protocol.requirements else "<p>—</p>"}
<h2>Задачи</h2>
{"<ul>" + "".join(f"<li>{t.task_text}</li>" for t in protocol.tasks) + "</ul>" if protocol.tasks else "<p>—</p>"}
<h2>Точки интеграции</h2>
<p>{protocol.integration_points or '—'}</p>
</body>
</html>"""

    def validate_render(self, html: str, protocol: Protocol) -> ValidationReport:
        report = ValidationReport()
        checks = {
            "html_tag": "<html",
            "body_tag": "<body",
            "heading": "<h1>",
            "processes_heading": "AS IS",
            "roles_heading": "Рол",
        }
        for code, keyword in checks.items():
            if keyword not in html:
                report.add_issue(code, f"В HTML отсутствует элемент: {keyword}", ValidationStatus.FAILED)
            else:
                report.checks[code] = True
        report.add_issue("render_check", "Валидация рендера завершена", ValidationStatus.PASSED)
        return report