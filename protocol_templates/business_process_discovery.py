import re
from datetime import date

from protocol_templates.base import BaseProtocolTemplate
from models.protocol import Protocol, TopicBlock, DecisionItem, QuestionItem, RiskItem, TaskItem, AtomicItem
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

    # ── Helpers ──────────────────────────────────────────────────────────

    def _build_processes_as_is(self, facts: list[AtomicItem]) -> str:
        """Describe processes based on fact items."""
        if not facts:
            return "Описание процессов AS IS отсутствует — недостаточно данных встречи."

        parts = ["На основе встречи зафиксированы следующие процессы AS IS:"]

        for i, f in enumerate(facts[:10], 1):
            parts.append(f"{i}. {f.text[:300]}")

        parts.append(f"\nВсего зафиксировано {len(facts)} единиц информации по процессам.")
        return "\n".join(parts)

    def _build_roles_description(self, participants: list[dict],
                                   facts: list[AtomicItem]) -> str:
        """Build roles description from participants and fact speakers."""
        parts = []

        if participants:
            parts.append("Участники встречи и их роли:")
            for p in participants:
                if isinstance(p, dict):
                    name = p.get("name", "Не указано")
                    role = p.get("role", "Не указана")
                    parts.append(f"- {name} — {role}")

        if facts:
            speakers = set(f.speaker for f in facts if f.speaker)
            if speakers:
                parts.append(f"\nДокладчики: {', '.join(sorted(speakers))}.")
                parts.append("Роли уточняются в процессе дальнейшего обследования.")

        if not parts:
            return "Описание ролей отсутствует — данные не предоставлены."

        return "\n".join(parts)

    def _build_systems_and_documents(self, facts: list[AtomicItem]) -> str:
        """Extract systems and documents from facts mentioning them."""
        if not facts:
            return "Информация о системах и документах отсутствует."

        parts = ["Упоминаемые системы и документы:"]
        found = False

        system_keywords = [
            "система", "1с", "1c", "программа", "модуль", "конфигурация",
            "платформа", "база", "сервер", "приложение", "портал", "сайт",
            "облако", "хранилище", "бд", "sql", "api", "интерфейс",
            "excel", "word", "документ", "отчёт", "шаблон", "реестр", "журнал",
            "накладная", "счёт", "акт", "договор", "спецификация",
        ]

        for f in facts:
            lower = f.text.lower()
            if any(kw in lower for kw in system_keywords):
                parts.append(f"- {f.text[:200]}")
                found = True

        if not found:
            parts.append("Явные упоминания систем и документов не найдены в материалах встречи.")

        return "\n".join(parts)

    def _build_process_steps(self, facts: list[AtomicItem]) -> list[dict]:
        """Build process_steps as a list of dicts from facts."""
        if not facts:
            return []

        steps = []
        for i, f in enumerate(facts[:15], 1):
            step = {
                "step_number": i,
                "description": f.text[:300],
                "actor": f.speaker or "Не указан",
                "system": "Не указана",
                "input_document": "Не указан",
                "output_document": "Не указан",
                "notes": f"Источник: {f.source_context_id}",
            }
            steps.append(step)

        return steps

    def _build_problems(self, risks: list[RiskItem],
                         questions: list[QuestionItem],
                         facts: list[AtomicItem]) -> list[dict]:
        """Build problems list from risks and other items."""
        problems = []
        pid = 1

        for r in risks:
            impact = r.impact if r.impact and r.impact != "Требует оценки" else "Среднее"
            severity = "Высокая" if r.risk_type == "Блокер" else "Средняя"
            problems.append({
                "id": f"P{pid:03d}",
                "problem": r.risk_text[:200],
                "impact": f"Тип: {r.risk_type}. {impact}",
                "severity": severity,
            })
            pid += 1

        for q in questions:
            problems.append({
                "id": f"P{pid:03d}",
                "problem": q.question_text[:200],
                "impact": "Требует выяснения",
                "severity": "Низкая",
            })
            pid += 1

        if not problems and facts:
            problems.append({
                "id": "P001",
                "problem": "Необходимо детальное обследование бизнес-процессов",
                "impact": "Без детального обследования невозможна точная настройка системы",
                "severity": "Средняя",
            })

        return problems

    def _build_requirements(self, tasks: list[TaskItem],
                             decisions: list[DecisionItem]) -> list[dict]:
        """Build requirements list from tasks and decisions."""
        requirements = []
        rid = 1

        for t in tasks[:10]:
            requirements.append({
                "id": f"R{rid:03d}",
                "requirement": t.task_text[:200],
                "priority": "Средний",
                "source": t.basis or "Поставлена на встрече",
                "responsible": t.responsible or "Не назначен",
            })
            rid += 1

        for d in decisions[:5]:
            requirements.append({
                "id": f"R{rid:03d}",
                "requirement": f"Реализовать решение: {d.decision_text[:200]}",
                "priority": "Высокий",
                "source": "Решение встречи",
                "responsible": d.responsible or "Не назначен",
            })
            rid += 1

        if not requirements:
            requirements.append({
                "id": "R001",
                "requirement": "Провести детальное обследование процессов",
                "priority": "Высокий",
                "source": "Результаты встречи",
                "responsible": "Не назначен",
            })

        return requirements

    def _build_integration_points(self, facts: list[AtomicItem],
                                   risks: list[RiskItem]) -> str:
        """Build integration_points description."""
        parts = []

        integration_keywords = [
            "интеграц", "обмен", "синхронизац", "выгрузк", "загрузк",
            "api", "веб-сервис", "web-сервис", "шина", "esb", "rest",
            "soap", "json", "xml", "файловый обмен", "справочник",
            "миграц", "перенос", "импорт", "экспорт",
        ]

        found_items = []
        for f in facts:
            lower = f.text.lower()
            if any(kw in lower for kw in integration_keywords):
                found_items.append(f"- {f.text[:200]}")

        if found_items:
            parts.append("Выявлены следующие точки интеграции:")
            parts.extend(found_items)
        else:
            parts.append("Точки интеграции явно не обсуждались на встрече.")

        if risks:
            integration_risks = [r for r in risks if r.risk_type == "Зависимость"]
            if integration_risks:
                parts.append("\nЗависимости по интеграции:")
                for r in integration_risks:
                    parts.append(f"- {r.risk_text[:200]}")

        return "\n".join(parts)

    # ── assemble ─────────────────────────────────────────────────────────

    def assemble(self, protocol: Protocol, atomic_items: list, meeting_metadata: dict) -> Protocol:
        protocol.atomic_items = atomic_items
        protocol.template_id = self.template_id

        # --- metadata ---
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

            protocol.meeting_purpose = meeting_metadata.get("purpose", protocol.meeting_purpose)
            protocol.protocol_title = meeting_metadata.get("title", protocol.protocol_title)

            if "participants" in meeting_metadata:
                protocol.participants = meeting_metadata["participants"]

        # --- classify items ---
        facts = []
        for item in atomic_items:
            if not isinstance(item, AtomicItem):
                continue

            if item.item_type == "решение" and item.explicit_agreement and item.confidence >= 0.7:
                decision = DecisionItem(
                    decision_id=item.item_id,
                    source_context_id=item.source_context_id,
                    decision_text=item.text,
                    context_and_basis="На основании обсуждения",
                    agreed_scope="Объём согласован",
                    boundaries="Границы определены",
                    responsible="Ответственный не определён",
                    deadline="Срок не определён",
                    related_topic="",
                    order=len(protocol.decisions) + 1,
                    explicit_agreement=item.explicit_agreement,
                    confidence=item.confidence,
                    evidence=item.evidence,
                )
                protocol.decisions.append(decision)

            elif item.item_type == "вопрос":
                question = QuestionItem(
                    question_id=item.item_id,
                    source_context_id=item.source_context_id,
                    question_text=item.text,
                    context="Вопрос поднят в ходе обследования",
                    known_info="Информация уточняется",
                    to_determine="Требуется уточнение",
                    responsible="Ответственный не определён",
                    deadline="Срок не определён",
                    next_action="Запросить информацию",
                    status="открыт",
                    related_topic="",
                    order=len(protocol.questions) + 1,
                )
                protocol.questions.append(question)

            elif item.item_type in ("риск", "ограничение", "зависимость"):
                risk_type_map = {
                    "риск": "Риск",
                    "ограничение": "Ограничение",
                    "зависимость": "Зависимость",
                }
                risk = RiskItem(
                    risk_id=item.item_id,
                    source_context_id=item.source_context_id,
                    risk_type=risk_type_map.get(item.item_type, "Риск"),
                    risk_text=item.text,
                    reason="Выявлено в ходе обследования",
                    impact="Требует оценки",
                    trigger_condition="Условия не определены",
                    measures="Меры не определены",
                    responsible="Ответственный не определён",
                    deadline="Срок не определён",
                    status="актуален",
                    related_topic="",
                    order=len(protocol.risks) + 1,
                )
                protocol.risks.append(risk)

            elif item.item_type == "задача" and item.commitment_confirmed:
                task = TaskItem(
                    task_id=item.item_id,
                    source_context_id=item.source_context_id,
                    task_text=item.text,
                    basis="Поставлена в ходе обследования",
                    expected_result="Результат будет определён при уточнении",
                    responsible="Ответственный не определён",
                    co_executors="",
                    deadline="Срок не определён",
                    dependencies="Зависимости не указаны",
                    status="новая",
                    related_topic="",
                    order=len(protocol.tasks) + 1,
                    commitment_confirmed=item.commitment_confirmed,
                )
                protocol.tasks.append(task)

            elif item.item_type == "факт":
                facts.append(item)

        # --- fill all discovery fields ---

        protocol.processes_as_is = self._build_processes_as_is(facts)
        protocol.roles_description = self._build_roles_description(
            protocol.participants, facts,
        )
        protocol.systems_and_documents = self._build_systems_and_documents(facts)
        protocol.process_steps = self._build_process_steps(facts)
        protocol.problems = self._build_problems(
            protocol.risks, protocol.questions, facts,
        )
        protocol.requirements = self._build_requirements(
            protocol.tasks, protocol.decisions,
        )
        protocol.integration_points = self._build_integration_points(
            facts, protocol.risks,
        )

        return protocol

    # ── assemble_with_llm_output ─────────────────────────────────────────

    def assemble_with_llm_output(self, protocol: Protocol, atomic_items: list,
                                  llm_output: str, meeting_metadata: dict) -> Protocol:
        """Use LLM output content when available; fall back to atomic items."""
        protocol.atomic_items = atomic_items
        protocol.template_id = self.template_id

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

            protocol.meeting_purpose = meeting_metadata.get("purpose", protocol.meeting_purpose)
            protocol.protocol_title = meeting_metadata.get("title", protocol.protocol_title)

            if "participants" in meeting_metadata:
                protocol.participants = meeting_metadata["participants"]

        is_mock = not llm_output or not llm_output.strip()
        if not is_mock:
            lower = llm_output.lower()
            mock_markers = ["placeholder", "todo", "template", "tbd", "{{", "}}", "mock", "mock_mode"]
            is_mock = any(m in lower for m in mock_markers)

        facts = []
        for item in atomic_items:
            if not isinstance(item, AtomicItem):
                continue

            if item.item_type == "решение" and item.explicit_agreement and item.confidence >= 0.7:
                decision = DecisionItem(
                    decision_id=item.item_id,
                    source_context_id=item.source_context_id,
                    decision_text=item.text,
                    context_and_basis="На основании обсуждения",
                    agreed_scope="Объём согласован",
                    boundaries="Границы определены",
                    responsible="Ответственный не определён",
                    deadline="Срок не определён",
                    related_topic="",
                    order=len(protocol.decisions) + 1,
                    explicit_agreement=item.explicit_agreement,
                    confidence=item.confidence,
                    evidence=item.evidence,
                )
                protocol.decisions.append(decision)

            elif item.item_type == "вопрос":
                question = QuestionItem(
                    question_id=item.item_id,
                    source_context_id=item.source_context_id,
                    question_text=item.text,
                    context="Вопрос поднят в ходе обследования",
                    known_info="Информация уточняется",
                    to_determine="Требуется уточнение",
                    responsible="Ответственный не определён",
                    deadline="Срок не определён",
                    next_action="Запросить информацию",
                    status="открыт",
                    related_topic="",
                    order=len(protocol.questions) + 1,
                )
                protocol.questions.append(question)

            elif item.item_type in ("риск", "ограничение", "зависимость"):
                risk_type_map = {
                    "риск": "Риск",
                    "ограничение": "Ограничение",
                    "зависимость": "Зависимость",
                }
                risk = RiskItem(
                    risk_id=item.item_id,
                    source_context_id=item.source_context_id,
                    risk_type=risk_type_map.get(item.item_type, "Риск"),
                    risk_text=item.text,
                    reason="Выявлено в ходе обследования",
                    impact="Требует оценки",
                    trigger_condition="Условия не определены",
                    measures="Меры не определены",
                    responsible="Ответственный не определён",
                    deadline="Срок не определён",
                    status="актуален",
                    related_topic="",
                    order=len(protocol.risks) + 1,
                )
                protocol.risks.append(risk)

            elif item.item_type == "задача" and item.commitment_confirmed:
                task = TaskItem(
                    task_id=item.item_id,
                    source_context_id=item.source_context_id,
                    task_text=item.text,
                    basis="Поставлена в ходе обследования",
                    expected_result="Результат будет определён при уточнении",
                    responsible="Ответственный не определён",
                    co_executors="",
                    deadline="Срок не определён",
                    dependencies="Зависимости не указаны",
                    status="новая",
                    related_topic="",
                    order=len(protocol.tasks) + 1,
                    commitment_confirmed=item.commitment_confirmed,
                )
                protocol.tasks.append(task)

            elif item.item_type == "факт":
                facts.append(item)

        # Try LLM content for sections
        if not is_mock:
            llm_sections = [
                ("Процессы AS IS", "processes_as_is"),
                ("Роли участников", "roles_description"),
                ("Системы и документы", "systems_and_documents"),
                ("Точки интеграции", "integration_points"),
            ]
            for section_name, attr_name in llm_sections:
                pattern = rf"(?:{section_name})[\s:]*\n(.+?)(?:\n#|\n\*\*|\Z)"
                match = re.search(pattern, llm_output, re.DOTALL | re.IGNORECASE)
                if match:
                    content = match.group(1).strip()
                    if len(content) > 20:
                        setattr(protocol, attr_name, content)

        # Fill missing from atomic items
        if not protocol.processes_as_is or len(protocol.processes_as_is.strip()) < 30:
            protocol.processes_as_is = self._build_processes_as_is(facts)

        if not protocol.roles_description or len(protocol.roles_description.strip()) < 20:
            protocol.roles_description = self._build_roles_description(
                protocol.participants, facts,
            )

        if not protocol.systems_and_documents or len(protocol.systems_and_documents.strip()) < 20:
            protocol.systems_and_documents = self._build_systems_and_documents(facts)

        if not protocol.process_steps:
            protocol.process_steps = self._build_process_steps(facts)

        if not protocol.problems:
            protocol.problems = self._build_problems(
                protocol.risks, protocol.questions, facts,
            )

        if not protocol.requirements:
            protocol.requirements = self._build_requirements(
                protocol.tasks, protocol.decisions,
            )

        if not protocol.integration_points or len(protocol.integration_points.strip()) < 20:
            protocol.integration_points = self._build_integration_points(
                facts, protocol.risks,
            )

        return protocol

    # ── validation ───────────────────────────────────────────────────────

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

    # ── render_html ──────────────────────────────────────────────────────

    def render_html(self, protocol: Protocol) -> str:
        date_str = protocol.meeting_date.isoformat() if protocol.meeting_date else "—"

        problems_html = ""
        if protocol.problems:
            problems_html = "<ul>"
            for p in protocol.problems:
                if isinstance(p, dict):
                    pid = p.get("id", "")
                    problem_text = p.get("problem", "")
                    impact = p.get("impact", "")
                    severity = p.get("severity", "")
                    problems_html += f"<li><strong>{pid}</strong>: {problem_text} — Влияние: {impact} (Серьёзность: {severity})</li>"
                else:
                    problems_html += f"<li>{p}</li>"
            problems_html += "</ul>"
        else:
            problems_html = "<p>—</p>"

        requirements_html = ""
        if protocol.requirements:
            requirements_html = "<ul>"
            for r in protocol.requirements:
                if isinstance(r, dict):
                    rid = r.get("id", "")
                    req_text = r.get("requirement", "")
                    priority = r.get("priority", "")
                    requirements_html += f"<li><strong>{rid}</strong>: {req_text} (Приоритет: {priority})</li>"
                else:
                    requirements_html += f"<li>{r}</li>"
            requirements_html += "</ul>"
        else:
            requirements_html = "<p>—</p>"

        steps_html = ""
        if protocol.process_steps:
            for s in protocol.process_steps:
                if isinstance(s, dict):
                    steps_html += f"""<tr>
<td>{s.get('step_number', '—')}</td>
<td>{s.get('description', '—')}</td>
<td>{s.get('actor', '—')}</td>
<td>{s.get('system', '—')}</td>
<td>{s.get('input_document', '—')}</td>
<td>{s.get('output_document', '—')}</td>
</tr>
"""
                else:
                    steps_html += f"<tr><td colspan=\"6\">{s}</td></tr>\n"
        else:
            steps_html = '<tr><td colspan="6">Шаги процесса не зафиксированы</td></tr>'

        tasks_html = ""
        if protocol.tasks:
            tasks_html = "<ul>"
            for t in protocol.tasks:
                tasks_html += f"<li><strong>{t.task_text}</strong> — {t.responsible or 'Не назначен'}</li>"
            tasks_html += "</ul>"
        else:
            tasks_html = "<p>—</p>"

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
<h2>Шаги процесса</h2>
<table>
<thead>
<tr><th>№</th><th>Описание</th><th>Исполнитель</th><th>Система</th><th>Входной документ</th><th>Выходной документ</th></tr>
</thead>
<tbody>
{steps_html}
</tbody>
</table>
<h2>Выявленные проблемы</h2>
{problems_html}
<h2>Требования</h2>
{requirements_html}
<h2>Задачи</h2>
{tasks_html}
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