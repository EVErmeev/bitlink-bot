import re
from datetime import date

from models.protocol import (
    AtomicItem,
    DecisionItem,
    Protocol,
    QuestionItem,
    RiskItem,
    TaskItem,
)
from models.validation import ValidationReport, ValidationStatus
from protocol_templates.base import BaseProtocolTemplate


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

    # ── Helper ───────────────────────────────────────────────────────────

    def _is_template_text(self, llm_output: str) -> bool:
        """Check if llm_output is a mock/template placeholder, not real content."""
        if not llm_output or not llm_output.strip():
            return True
        lower = llm_output.lower()
        mock_markers = [
            "placeholder", "todo", "template", "tbd", "fill me", "заполните",
            "{{", "}}", "mock", "mock_mode",
        ]
        return any(m in lower for m in mock_markers)

    def _extract_summary_from_llm(self, llm_output: str) -> str | None:
        """Try to extract the management_summary section from LLM output."""
        if not llm_output or self._is_template_text(llm_output):
            return None

        patterns = [
            r"(?:Управленческое резюме|Резюме|Management Summary)[\s:]*\n(.+?)(?:\n#|\n\*\*|\Z)",
            r"#+\s*Резюме\s*\n(.+?)(?:\n#|\Z)",
        ]
        for pattern in patterns:
            match = re.search(pattern, llm_output, re.DOTALL | re.IGNORECASE)
            if match:
                text = match.group(1).strip()
                if len(text) > 100:
                    return text

        first_paras = []
        for block in llm_output.split("\n\n"):
            stripped = block.strip()
            if stripped and not stripped.startswith("#") and len(stripped) > 80:
                first_paras.append(stripped)
            if len(first_paras) >= 3:
                break

        if first_paras:
            combined = "\n\n".join(first_paras)
            if len(combined) > 200:
                return combined

        return None

    def _build_summary(self, facts: list[AtomicItem], decisions: list[DecisionItem],
                       questions: list[QuestionItem], risks: list[RiskItem],
                       tasks: list[TaskItem], participants: list[dict],
                       purpose: str, llm_output: str | None = None) -> str:
        """Build a management summary from atomic items."""
        llm_extracted = None
        if llm_output:
            llm_extracted = self._extract_summary_from_llm(llm_output)

        if llm_extracted:
            return llm_extracted

        paragraphs = []

        # Paragraph 1: context and purpose
        para1_parts = []
        if purpose:
            para1_parts.append(f"Цель встречи: {purpose}.")
        if participants:
            names = [p.get("name", "") for p in participants if isinstance(p, dict) and p.get("name")]
            if names:
                para1_parts.append(f"Участники: {', '.join(names)}.")

        if para1_parts:
            paragraphs.append(" ".join(para1_parts))

        # Paragraph 2: what was discussed (from facts)
        if facts:
            fact_summaries = []
            for f in facts[:5]:
                short = f.text[:200].rstrip(".").strip()
                if short:
                    fact_summaries.append(f"- {short}")
            if fact_summaries:
                para2 = "В ходе встречи были рассмотрены следующие вопросы:\n" + "\n".join(fact_summaries)
                if len(facts) > 5:
                    para2 += f"\nВсего зафиксировано {len(facts)} фактов."
                paragraphs.append(para2)
        else:
            paragraphs.append("Обсуждение прошло без фиксации фактов в стенограмме.")

        # Paragraph 3: decisions and outcomes
        if decisions:
            dec_texts = [f"- {d.decision_text[:200]}" for d in decisions[:5]]
            para3 = "Приняты следующие решения:\n" + "\n".join(dec_texts)
            paragraphs.append(para3)

        if questions:
            q_texts = [f"- {q.question_text[:200]}" for q in questions[:5]]
            para_q = "Остаются открытыми вопросы:\n" + "\n".join(q_texts)
            paragraphs.append(para_q)

        if risks:
            r_texts = [f"- {r.risk_text[:200]}" for r in risks[:5]]
            para_r = "Выявлены риски, требующие внимания руководства:\n" + "\n".join(r_texts)
            paragraphs.append(para_r)

        if tasks:
            t_texts = [f"- {t.task_text[:200]}" for t in tasks[:5]]
            para_t = "Поставлены задачи:\n" + "\n".join(t_texts)
            paragraphs.append(para_t)

        if not paragraphs:
            return "Встреча проведена. Материалы зафиксированы. Детальная информация — в приложениях."

        return "\n\n".join(paragraphs)

    def _build_control_points(self, decisions: list[DecisionItem],
                               tasks: list[TaskItem],
                               meeting_date) -> str:
        """Build control points text from decisions and tasks."""
        points = []

        if meeting_date and isinstance(meeting_date, date):
            points.append(f"Дата встречи: {meeting_date.isoformat()} — точка отсчёта.")

        for i, d in enumerate(decisions[:3], 1):
            deadline = d.deadline if d.deadline and d.deadline != "Срок не определён" else "Требует уточнения"
            points.append(f"{i}. Контроль исполнения решения «{d.decision_text[:80]}» — срок: {deadline}.")

        for i, t in enumerate(tasks[:3], len(points) + 1):
            deadline = t.deadline if t.deadline and t.deadline != "Срок не определён" else "Требует уточнения"
            points.append(f"{i}. Контроль задачи «{t.task_text[:80]}» — срок: {deadline}.")

        if not points:
            return "Контрольные точки не определены. Рекомендуется назначить следующую встречу для контроля исполнения."

        return "\n".join(points)

    # ── assemble ─────────────────────────────────────────────────────────

    def assemble(self, protocol: Protocol, atomic_items: list, meeting_metadata: dict) -> Protocol:
        protocol.template_id = self.template_id
        protocol.atomic_items = atomic_items

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

            protocol.protocol_title = meeting_metadata.get("title", protocol.protocol_title)
            protocol.meeting_purpose = meeting_metadata.get("purpose", protocol.meeting_purpose)

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
                    context_and_basis="На основании обсуждения на встрече",
                    agreed_scope="Объём согласован в ходе встречи",
                    boundaries="Границы определены контекстом обсуждения",
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
                    context="Вопрос поднят в ходе встречи",
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
                    reason="Выявлено в ходе встречи",
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
                    basis="Поставлена в ходе встречи",
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

        # --- fill management summary ---
        protocol.management_summary = self._build_summary(
            facts, protocol.decisions, protocol.questions,
            protocol.risks, protocol.tasks, protocol.participants,
            protocol.meeting_purpose,
        )

        # --- fill control points ---
        protocol.control_points = self._build_control_points(
            protocol.decisions, protocol.tasks, protocol.meeting_date,
        )

        # --- key outcomes ---
        outcome_parts = []
        if protocol.decisions:
            outcome_parts.append(f"Принято {len(protocol.decisions)} решений.")
        if protocol.questions:
            outcome_parts.append(f"Зафиксировано {len(protocol.questions)} открытых вопросов.")
        if protocol.risks:
            outcome_parts.append(f"Выявлено {len(protocol.risks)} рисков/ограничений.")
        if protocol.tasks:
            outcome_parts.append(f"Поставлено {len(protocol.tasks)} задач.")

        if outcome_parts:
            protocol.key_outcomes = " ".join(outcome_parts)
        else:
            protocol.key_outcomes = "Встреча проведена. Итоги зафиксированы."

        return protocol

    # ── assemble_from_llm_json ───────────────────────────────────────────

    def assemble_from_llm_json(self, protocol: Protocol, atomic_items: list,
                                llm_data: dict, meeting_metadata: dict) -> Protocol:
        protocol.protocol_title = llm_data.get("protocol_title", protocol.protocol_title or "")
        protocol.meeting_purpose = llm_data.get("purpose", "")
        protocol.management_summary = llm_data.get("management_summary", "")
        protocol.key_outcomes = llm_data.get("key_outcomes", llm_data.get("management_summary", ""))
        protocol.control_points = llm_data.get("control_points", "")
        self._fill_items(protocol, atomic_items)
        return protocol

    def _fill_items(self, protocol: Protocol, atomic_items: list):
        if not protocol.decisions:
            for i, ai in enumerate(a for a in atomic_items if a.item_type == "решение" and a.explicit_agreement):
                protocol.decisions.append(DecisionItem(
                    decision_id=f"d_{i}", source_context_id=ai.source_context_id,
                    decision_text=ai.text, explicit_agreement=ai.explicit_agreement,
                    confidence=ai.confidence, evidence=ai.evidence,
                ))
        if not protocol.questions:
            for i, ai in enumerate(a for a in atomic_items if a.item_type == "вопрос"):
                protocol.questions.append(QuestionItem(
                    question_id=f"q_{i}", source_context_id=ai.source_context_id,
                    question_text=ai.text,
                ))
        if not protocol.risks:
            for i, ai in enumerate(a for a in atomic_items if a.item_type in ("риск", "ограничение", "зависимость")):
                protocol.risks.append(RiskItem(
                    risk_id=f"r_{i}", source_context_id=ai.source_context_id,
                    risk_text=ai.text,
                ))
        if not protocol.tasks:
            for i, ai in enumerate(a for a in atomic_items if a.item_type == "задача" and a.commitment_confirmed):
                protocol.tasks.append(TaskItem(
                    task_id=f"t_{i}", source_context_id=ai.source_context_id,
                    task_text=ai.text, commitment_confirmed=ai.commitment_confirmed,
                ))

    # ── assemble_with_llm_output ─────────────────────────────────────────

    def assemble_with_llm_output(self, protocol: Protocol, atomic_items: list,
                                  llm_output: str, meeting_metadata: dict) -> Protocol:
        """Use LLM output for summary; fall back to assembling from atomic_items."""
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

        facts = []
        for item in atomic_items:
            if not isinstance(item, AtomicItem):
                continue

            if item.item_type == "решение" and item.explicit_agreement and item.confidence >= 0.7:
                decision = DecisionItem(
                    decision_id=item.item_id,
                    source_context_id=item.source_context_id,
                    decision_text=item.text,
                    context_and_basis="На основании обсуждения на встрече",
                    agreed_scope="Объём согласован в ходе встречи",
                    boundaries="Границы определены контекстом обсуждения",
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
                    context="Вопрос поднят в ходе встречи",
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
                    reason="Выявлено в ходе встречи",
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
                    basis="Поставлена в ходе встречи",
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

        protocol.management_summary = self._build_summary(
            facts, protocol.decisions, protocol.questions,
            protocol.risks, protocol.tasks, protocol.participants,
            protocol.meeting_purpose, llm_output,
        )

        protocol.control_points = self._build_control_points(
            protocol.decisions, protocol.tasks, protocol.meeting_date,
        )

        outcome_parts = []
        if protocol.decisions:
            outcome_parts.append(f"Принято {len(protocol.decisions)} решений.")
        if protocol.questions:
            outcome_parts.append(f"Зафиксировано {len(protocol.questions)} открытых вопросов.")
        if protocol.risks:
            outcome_parts.append(f"Выявлено {len(protocol.risks)} рисков/ограничений.")
        if protocol.tasks:
            outcome_parts.append(f"Поставлено {len(protocol.tasks)} задач.")

        if outcome_parts:
            protocol.key_outcomes = " ".join(outcome_parts)
        else:
            protocol.key_outcomes = "Встреча проведена. Итоги зафиксированы."

        return protocol

    # ── validation ───────────────────────────────────────────────────────

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

    # ── render_html ──────────────────────────────────────────────────────

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
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
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
