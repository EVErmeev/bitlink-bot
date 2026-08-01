import re
from datetime import date

from protocol_templates.base import BaseProtocolTemplate
from models.protocol import Protocol, TopicBlock, DecisionItem, QuestionItem, RiskItem, TaskItem, AtomicItem
from models.validation import ValidationReport, ValidationStatus


class ProjectStandardTemplate(BaseProtocolTemplate):
    template_id = "project_standard"
    version = "1.0"
    display_name = "Проектный протокол"
    description = "Средний вариант для регулярной работы проектной команды (1300-2800 слов, 4-8 страниц)."

    SECTION_NAMES = {
        "general_info": "Общая информация",
        "participants": "Участники",
        "purpose_and_scope": "Цель и границы",
        "key_outcomes": "Ключевые итоги",
        "process_scheme": "Сквозная схема процесса",
        "thematic_sections": "Тематические разделы",
        "agreed_approaches": "Согласованные подходы",
        "functional_gaps": "Функциональные разрывы",
        "decisions": "Решения",
        "questions": "Открытые вопросы",
        "tasks": "Задачи",
        "control_points": "Контрольные точки",
    }

    REQUIRED_SECTIONS = list(SECTION_NAMES.keys())

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "general_info": {
                    "type": "object",
                    "properties": {
                        "meeting_date": {"type": "string", "format": "date"},
                        "protocol_title": {"type": "string"},
                        "meeting_time": {"type": "string"},
                    },
                },
                "participants": {"type": "array"},
                "purpose_and_scope": {"type": "string"},
                "key_outcomes": {"type": "string"},
                "process_scheme": {"type": "string"},
                "thematic_sections": {"type": "array"},
                "agreed_approaches": {"type": "string"},
                "functional_gaps": {"type": "string"},
                "decisions": {"type": "array"},
                "questions": {"type": "array"},
                "tasks": {"type": "array"},
                "control_points": {"type": "string"},
            },
            "required": self.REQUIRED_SECTIONS,
        }

    def get_system_prompt(self) -> str:
        return (
            "Ты — аналитик, составляющий проектный протокол встречи. "
            "Документ среднего уровня детализации для регулярной работы проектной команды.\n\n"
            "ОБЪЁМ: 1300–2800 слов.\n\n"
            "СТРУКТУРА (12 разделов):\n"
            "1. Общая информация — дата, время, название встречи.\n"
            "2. Участники — список с ролями.\n"
            "3. Цель и границы — цель встречи и что входит / не входит в обсуждение.\n"
            "4. Ключевые итоги — основные результаты встречи.\n"
            "5. Сквозная схема процесса — описание процесса от начала до конца.\n"
            "6. Тематические разделы — разбор по функциональным областям.\n"
            "7. Согласованные подходы — что было согласовано, методология, принципы.\n"
            "8. Функциональные разрывы — что не покрывается системой или процессом.\n"
            "9. Решения — таблица принятых решений.\n"
            "10. Открытые вопросы — таблица нерешённых вопросов.\n"
            "11. Задачи — таблица задач с ответственными и сроками.\n"
            "12. Контрольные точки — ключевые вехи.\n\n"
            "ПРАВИЛА:\n"
            "- Только факты из предоставленных данных. Ничего не выдумывай.\n"
            "- Если данных недостаточно — укажи «информация отсутствует».\n"
            "- Используй русский язык.\n"
            "- Все ячейки таблиц должны быть заполнены."
        )

    # ── Helper: topic clustering (shared pattern) ────────────────────────

    def _extract_keywords(self, text: str) -> set[str]:
        words = re.findall(r"[а-яёa-z]{4,}", text.lower())
        return set(words)

    def _cluster_facts(self, facts: list[AtomicItem]) -> dict[str, tuple[set[str], list[AtomicItem]]]:
        topics: dict[str, tuple[set[str], list[AtomicItem]]] = {}
        for fact in facts:
            words = self._extract_keywords(fact.text)
            if not words:
                words = {fact.text[:20].strip() or "обсуждение"}
            matched = False
            for topic_name, (topic_words, items) in topics.items():
                if len(words & topic_words) >= 2:
                    topics[topic_name][0].update(words)
                    topics[topic_name][1].append(fact)
                    matched = True
                    break
            if not matched:
                sorted_words = sorted(words)
                key_words = sorted_words[:3] if len(sorted_words) >= 3 else sorted_words
                key = " ".join(key_words)[:60] or "Обсуждение"
                counter = 1
                unique_key = key
                while unique_key in topics:
                    counter += 1
                    unique_key = f"{key} ({counter})"
                topics[unique_key] = (words, [fact])
        return topics

    # ── Helper: derive title ─────────────────────────────────────────────

    def _derive_topic_title(self, keywords: set[str]) -> str:
        sorted_kw = sorted(keywords, key=len, reverse=True)
        top = sorted_kw[:4]
        topic_prefixes = {
            "интеграц": "Интеграция систем",
            "документооборот": "Документооборот",
            "отчёт": "Отчётность",
            "согласован": "Согласование",
            "процесс": "Бизнес-процесс",
            "рол": "Роли и полномочия",
            "доступ": "Права доступа",
            "справочник": "Справочники и НСИ",
            "архитектур": "Архитектура решения",
            "безопасност": "Безопасность",
            "план": "Планирование",
            "требован": "Требования",
        }
        for kw, prefix in topic_prefixes.items():
            if any(kw in w for w in top):
                others = [w for w in top if kw not in w][:2]
                if others:
                    return f"{prefix}: {', '.join(others)}"
                return prefix
        if top:
            return f"Тема: {' '.join(w.capitalize() for w in top[:3])}"
        return "Обсуждение"

    # ── Helpers ──────────────────────────────────────────────────────────

    def _build_thematic_sections(self, facts: list[AtomicItem],
                                  source_context_id: str) -> list[dict]:
        """Build thematic_sections (list of dicts) from clustered facts."""
        if not facts:
            return []

        clusters = self._cluster_facts(facts)
        sections = []

        for label, (keywords, items) in clusters.items():
            title = self._derive_topic_title(keywords)
            discussion = ". ".join(item.text for item in items)
            speakers = set(item.speaker for item in items if item.speaker)
            speaker_info = f" (докладчики: {', '.join(speakers)})" if speakers else ""

            content = discussion
            if speaker_info:
                content = f"Докладчики: {', '.join(speakers)}. {content}"

            sections.append({
                "title": title,
                "content": content,
                "source_context_id": source_context_id,
            })

        return sections

    def _build_process_scheme(self, facts: list[AtomicItem]) -> str:
        """Build a simple process scheme description from facts."""
        if not facts:
            return "Схема процесса не определена — недостаточно данных."

        steps = []
        for i, f in enumerate(facts[:10], 1):
            steps.append(f"Шаг {i}: {f.text[:150]}")

        return "Описание процесса на основе зафиксированных фактов:\n\n" + "\n".join(steps)

    def _build_agreed_approaches(self, decisions: list[DecisionItem],
                                  facts: list[AtomicItem]) -> str:
        """Build agreed_approaches from decisions and facts."""
        parts = []

        if decisions:
            parts.append("В ходе встречи согласованы следующие подходы:")
            for i, d in enumerate(decisions[:5], 1):
                parts.append(f"{i}. {d.decision_text[:200]}")
        else:
            parts.append("Явно согласованные подходы не зафиксированы.")

        if facts:
            parts.append(f"\nВсего зафиксировано {len(facts)} фактов в рамках обсуждения.")

        return "\n".join(parts)

    def _build_functional_gaps(self, risks: list[RiskItem],
                                questions: list[QuestionItem]) -> str:
        """Build functional_gaps from risks and open questions."""
        parts = []

        if risks:
            parts.append("Выявлены следующие функциональные разрывы и ограничения:")
            for i, r in enumerate(risks[:5], 1):
                parts.append(f"{i}. {r.risk_text[:200]}")
        else:
            parts.append("Явные функциональные разрывы не выявлены на данной встрече.")

        if questions:
            parts.append(f"\nОткрытые вопросы (всего {len(questions)}):")
            for i, q in enumerate(questions[:5], 1):
                parts.append(f"{i}. {q.question_text[:200]}")

        return "\n".join(parts)

    def _build_control_points_text(self, decisions: list[DecisionItem],
                                    tasks: list[TaskItem],
                                    meeting_date) -> str:
        """Build control_points text."""
        points = []

        if meeting_date and isinstance(meeting_date, date):
            points.append(f"Дата встречи: {meeting_date.isoformat()} — точка отсчёта.")

        for i, d in enumerate(decisions[:3], 1):
            deadline = d.deadline if d.deadline and d.deadline != "Срок не определён" else "Требует уточнения"
            points.append(f"{i}. Контроль решения «{d.decision_text[:80]}» — срок: {deadline}.")

        for i, t in enumerate(tasks[:3], len(points) + 1):
            deadline = t.deadline if t.deadline and t.deadline != "Срок не определён" else "Требует уточнения"
            points.append(f"{i}. Контроль задачи «{t.task_text[:80]}» — срок: {deadline}.")

        if not points:
            return "Контрольные точки не определены. Рекомендуется назначить следующую встречу."

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
            protocol.meeting_context = meeting_metadata.get("context", protocol.meeting_context)

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

        # --- fill all 12 sections ---

        # 5. process_scheme
        protocol.process_scheme = self._build_process_scheme(facts)

        # 6. thematic_sections
        src_ctx = protocol.source_context_id or ""
        protocol.thematic_sections = self._build_thematic_sections(facts, src_ctx)

        # Also populate topic_blocks for compatibility
        clusters = self._cluster_facts(facts)
        for i, (label, (keywords, items)) in enumerate(clusters.items(), 1):
            tb = TopicBlock(
                topic_id=f"ps-tb-{i}",
                title=self._derive_topic_title(keywords),
                source_context_id=src_ctx,
                discussion_content=". ".join(item.text for item in items),
                conclusion="Обсуждено, требуется дальнейшая проработка",
                status_text="Обсуждено",
                order=i,
            )
            protocol.topic_blocks.append(tb)

        # 7. agreed_approaches
        protocol.agreed_approaches = self._build_agreed_approaches(
            protocol.decisions, facts,
        )

        # 8. functional_gaps
        protocol.functional_gaps = self._build_functional_gaps(
            protocol.risks, protocol.questions,
        )

        # 12. control_points
        protocol.control_points = self._build_control_points_text(
            protocol.decisions, protocol.tasks, protocol.meeting_date,
        )

        # 4. key_outcomes
        outcome_parts = []
        if protocol.decisions:
            outcome_parts.append(f"Принято {len(protocol.decisions)} решений.")
        if protocol.questions:
            outcome_parts.append(f"Зафиксировано {len(protocol.questions)} открытых вопросов.")
        if protocol.risks:
            outcome_parts.append(f"Выявлено {len(protocol.risks)} рисков/ограничений.")
        if protocol.tasks:
            outcome_parts.append(f"Поставлено {len(protocol.tasks)} задач.")
        if protocol.thematic_sections:
            outcome_parts.append(f"Рассмотрено {len(protocol.thematic_sections)} тематических разделов.")

        if outcome_parts:
            protocol.key_outcomes = " ".join(outcome_parts)
        else:
            protocol.key_outcomes = "Встреча проведена. Итоги зафиксированы."

        return protocol

    # ── assemble_with_llm_output ─────────────────────────────────────────

    def assemble_with_llm_output(self, protocol: Protocol, atomic_items: list,
                                  llm_output: str, meeting_metadata: dict) -> Protocol:
        """Use LLM output content for summary fields when available."""
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
            protocol.meeting_context = meeting_metadata.get("context", protocol.meeting_context)

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

        # Try to extract content from LLM output for specific sections
        if not is_mock:
            for section_name, section_key in [
                ("Сквозная схема процесса", "process_scheme"),
                ("Согласованные подходы", "agreed_approaches"),
                ("Функциональные разрывы", "functional_gaps"),
                ("Контрольные точки", "control_points"),
            ]:
                pattern = rf"(?:{section_name})[\s:]*\n(.+?)(?:\n#|$)"
                match = re.search(pattern, llm_output, re.DOTALL | re.IGNORECASE)
                if match:
                    content = match.group(1).strip()
                    if len(content) > 20:
                        setattr(protocol, section_key, content)

        # Fill missing sections from atomic items (fallback)
        if not protocol.process_scheme or len(protocol.process_scheme.strip()) < 20:
            protocol.process_scheme = self._build_process_scheme(facts)

        if not protocol.thematic_sections:
            src_ctx = protocol.source_context_id or ""
            protocol.thematic_sections = self._build_thematic_sections(facts, src_ctx)

        clusters = self._cluster_facts(facts)
        for i, (label, (keywords, items)) in enumerate(clusters.items(), 1):
            tb = TopicBlock(
                topic_id=f"ps-tb-{i}",
                title=self._derive_topic_title(keywords),
                source_context_id=src_ctx,
                discussion_content=". ".join(item.text for item in items),
                conclusion="Обсуждено, требуется дальнейшая проработка",
                status_text="Обсуждено",
                order=i,
            )
            protocol.topic_blocks.append(tb)

        if not protocol.agreed_approaches or len(protocol.agreed_approaches.strip()) < 20:
            protocol.agreed_approaches = self._build_agreed_approaches(protocol.decisions, facts)

        if not protocol.functional_gaps or len(protocol.functional_gaps.strip()) < 20:
            protocol.functional_gaps = self._build_functional_gaps(protocol.risks, protocol.questions)

        if not protocol.control_points or len(protocol.control_points.strip()) < 20:
            protocol.control_points = self._build_control_points_text(
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
            protocol.meeting_purpose or "",
            protocol.meeting_context or "",
            protocol.key_outcomes or "",
            protocol.process_scheme or "",
            protocol.agreed_approaches or "",
            protocol.functional_gaps or "",
            protocol.control_points or "",
        ]
        for tb in protocol.topic_blocks:
            all_text_parts.append(tb.title)
            all_text_parts.append(tb.discussion_content)
            all_text_parts.append(tb.conclusion)
        for d in protocol.decisions:
            all_text_parts.extend([d.decision_text, d.context_and_basis, d.agreed_scope])
        for q in protocol.questions:
            all_text_parts.extend([q.question_text, q.context, q.known_info, q.to_determine])
        for r in protocol.risks:
            all_text_parts.extend([r.risk_text, r.reason, r.impact])
        for t in protocol.tasks:
            all_text_parts.extend([t.task_text, t.basis, t.expected_result])

        combined_text = " ".join(p for p in all_text_parts if p)
        word_count = len(re.findall(r"\b\w+\b", combined_text))

        if word_count < 1300:
            report.add_issue(
                "word_count_low",
                f"Слишком мало слов: {word_count} (требуется 1300–2800). Добавьте содержание в разделы.",
                ValidationStatus.FAILED,
                "protocol",
                "Расширьте тематические разделы, добавьте контекст решений и описание процесса.",
            )
        elif word_count > 2800:
            report.add_issue(
                "word_count_high",
                f"Слишком много слов: {word_count} (требуется 1300–2800). Сократите текст.",
                ValidationStatus.WARNING,
                "protocol",
            )

        section_checks = {
            "meeting_purpose": (protocol.meeting_purpose or "", "Цель и границы", 10),
            "meeting_context": (protocol.meeting_context or "", "Цель и границы", 10),
            "key_outcomes": (protocol.key_outcomes or "", "Ключевые итоги", 10),
            "process_scheme": (protocol.process_scheme or "", "Сквозная схема процесса", 10),
            "agreed_approaches": (protocol.agreed_approaches or "", "Согласованные подходы", 10),
            "functional_gaps": (protocol.functional_gaps or "", "Функциональные разрывы", 10),
            "control_points": (protocol.control_points or "", "Контрольные точки", 10),
        }

        for key, (content, section_name, min_len) in section_checks.items():
            if not content or len(content.strip()) < min_len:
                report.add_issue(
                    f"{key}_empty",
                    f"Раздел «{section_name}» пуст или недостаточно заполнен.",
                    ValidationStatus.FAILED,
                    key,
                )

        if not protocol.participants:
            report.add_issue("no_participants", "Список участников не заполнен.", ValidationStatus.FAILED, "participants")

        if protocol.meeting_date is not None and isinstance(protocol.meeting_date, date):
            if protocol.meeting_date > date.today():
                report.add_issue(
                    "future_date",
                    f"Дата встречи {protocol.meeting_date} находится в будущем.",
                    ValidationStatus.WARNING,
                    "meeting_date",
                )

        for i, task in enumerate(protocol.tasks):
            row_issues = []
            if not task.task_text.strip():
                row_issues.append("текст задачи")
            if not task.responsible.strip():
                row_issues.append("ответственный")
            if not task.deadline.strip():
                row_issues.append("срок")
            if not task.status.strip():
                row_issues.append("статус")
            if row_issues:
                report.add_issue(
                    f"task_{i}_empty_cells",
                    f"В задаче #{i + 1} не заполнены: {', '.join(row_issues)}.",
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

        for k, q in enumerate(protocol.questions):
            if not q.question_text or len(q.question_text.strip()) < 5:
                report.add_issue(
                    f"question_{k}_empty",
                    f"Вопрос #{k + 1} не заполнен.",
                    ValidationStatus.FAILED,
                    f"questions[{k}]",
                )

        if not report.issues and not report.warnings:
            report.add_issue("all_checks", "Все проверки пройдены", ValidationStatus.PASSED)

        return report

    # ── render_html ──────────────────────────────────────────────────────

    def render_html(self, protocol: Protocol) -> str:
        date_str = protocol.meeting_date.isoformat() if protocol.meeting_date else "—"
        time_str = protocol.meeting_time.strftime("%H:%M") if protocol.meeting_time else "—"

        participants_rows = ""
        for i, p in enumerate(protocol.participants, 1):
            name = p.get("name", "—") if isinstance(p, dict) else str(p)
            role = p.get("role", "—") if isinstance(p, dict) else "—"
            participants_rows += f"<tr><td>{i}</td><td>{name}</td><td>{role}</td></tr>\n"

        decisions_rows = ""
        for i, d in enumerate(protocol.decisions, 1):
            decisions_rows += f"""<tr>
<td>{i}</td>
<td>{d.decision_text or '—'}</td>
<td>{d.context_and_basis or '—'}</td>
<td>{d.responsible or '—'}</td>
<td>{d.deadline or '—'}</td>
</tr>
"""

        questions_rows = ""
        for i, q in enumerate(protocol.questions, 1):
            questions_rows += f"""<tr>
<td>{i}</td>
<td>{q.question_text or '—'}</td>
<td>{q.context or '—'}</td>
<td>{q.responsible or '—'}</td>
<td>{q.status or '—'}</td>
</tr>
"""

        tasks_rows = ""
        for i, t in enumerate(protocol.tasks, 1):
            tasks_rows += f"""<tr>
<td>{i}</td>
<td>{t.task_text or '—'}</td>
<td>{t.expected_result or '—'}</td>
<td>{t.responsible or '—'}</td>
<td>{t.deadline or '—'}</td>
<td>{t.status or '—'}</td>
</tr>
"""

        thematic_html = ""
        for i, tb in enumerate(protocol.topic_blocks, 1):
            thematic_html += f"""<div class="topic-block">
<h3>Тема {i}: {tb.title or '—'}</h3>
<h4>Обсуждение</h4>
<p>{tb.discussion_content.replace(chr(10), '<br>') if tb.discussion_content else '—'}</p>
<h4>Итог / вывод</h4>
<p>{tb.conclusion.replace(chr(10), '<br>') if tb.conclusion else '—'}</p>
<h4>Статус</h4>
<p>{tb.status_text or '—'}</p>
</div>
"""

        if protocol.thematic_sections:
            for i, ts in enumerate(protocol.thematic_sections):
                if isinstance(ts, dict):
                    thematic_html += f"""<div class="topic-block">
<h3>Тематический блок {i + 1}: {ts.get('title', '—')}</h3>
<p>{ts.get('content', '—')}</p>
</div>
"""
                elif isinstance(ts, str):
                    thematic_html += f"""<div class="topic-block">
<h3>Тематический блок {i + 1}</h3>
<p>{ts}</p>
</div>
"""

        html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Проектный протокол — {protocol.protocol_title or 'Встреча'}</title>
<style>
    body {{
        font-family: 'Segoe UI', Arial, sans-serif;
        max-width: 900px;
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
        margin-top: 20px;
    }}
    h4 {{
        color: #546e7a;
        font-size: 14px;
        margin-bottom: 4px;
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
    .topic-block {{
        background: #fafafa;
        border: 1px solid #e0e0e0;
        border-radius: 4px;
        padding: 12px 16px;
        margin: 12px 0;
    }}
    ul {{
        padding-left: 20px;
        margin: 8px 0;
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
<p class="header-meta"><strong>Дата встречи:</strong> {date_str} | <strong>Время:</strong> {time_str}</p>
<p><strong>Название:</strong> {protocol.protocol_title or '—'}</p>

<h2>{self.SECTION_NAMES['participants']}</h2>
<table>
<thead>
<tr><th>№</th><th>Имя</th><th>Роль</th></tr>
</thead>
<tbody>
{participants_rows or '<tr><td colspan="3">Участники не указаны</td></tr>'}
</tbody>
</table>

<h2>{self.SECTION_NAMES['purpose_and_scope']}</h2>
<h3>Цель встречи</h3>
<p>{protocol.meeting_purpose or '—'}</p>
<h3>Исходный контекст</h3>
<p>{protocol.meeting_context or '—'}</p>

<h2>{self.SECTION_NAMES['key_outcomes']}</h2>
<div>{protocol.key_outcomes.replace(chr(10), '<br>') if protocol.key_outcomes else '<p>—</p>'}</div>

<h2>{self.SECTION_NAMES['process_scheme']}</h2>
<div>{protocol.process_scheme.replace(chr(10), '<br>') if protocol.process_scheme else '<p>—</p>'}</div>

<h2>{self.SECTION_NAMES['thematic_sections']}</h2>
{thematic_html or '<p>Тематические разделы отсутствуют</p>'}

<h2>{self.SECTION_NAMES['agreed_approaches']}</h2>
<div>{protocol.agreed_approaches.replace(chr(10), '<br>') if protocol.agreed_approaches else '<p>—</p>'}</div>

<h2>{self.SECTION_NAMES['functional_gaps']}</h2>
<div>{protocol.functional_gaps.replace(chr(10), '<br>') if protocol.functional_gaps else '<p>—</p>'}</div>

<h2>{self.SECTION_NAMES['decisions']}</h2>
<table>
<thead>
<tr>
    <th>№</th>
    <th>Решение</th>
    <th>Контекст и основание</th>
    <th>Ответственный</th>
    <th>Срок</th>
</tr>
</thead>
<tbody>
{decisions_rows or '<tr><td colspan="5">Решения отсутствуют</td></tr>'}
</tbody>
</table>

<h2>{self.SECTION_NAMES['questions']}</h2>
<table>
<thead>
<tr>
    <th>№</th>
    <th>Вопрос</th>
    <th>Контекст</th>
    <th>Ответственный</th>
    <th>Статус</th>
</tr>
</thead>
<tbody>
{questions_rows or '<tr><td colspan="5">Вопросы отсутствуют</td></tr>'}
</tbody>
</table>

<h2>{self.SECTION_NAMES['tasks']}</h2>
<table>
<thead>
<tr>
    <th>№</th>
    <th>Задача</th>
    <th>Ожидаемый результат</th>
    <th>Ответственный</th>
    <th>Срок</th>
    <th>Статус</th>
</tr>
</thead>
<tbody>
{tasks_rows or '<tr><td colspan="6">Задачи отсутствуют</td></tr>'}
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

        table_matches = re.findall(r"<table", html, re.IGNORECASE)
        if len(table_matches) < 3:
            report.add_issue(
                "few_tables",
                f"В HTML найдено {len(table_matches)} таблиц. Ожидается минимум 3 (участники, решения, задачи).",
                ValidationStatus.WARNING,
            )

        for tbl_pattern, tbl_name in [
            (r"<table[^>]*>.*?Решения.*?</table>", "Решения"),
            (r"<table[^>]*>.*?Вопрос.*?</table>", "Вопросы"),
            (r"<table[^>]*>.*?Задача.*?</table>", "Задачи"),
        ]:
            if not re.search(tbl_pattern, html, re.DOTALL | re.IGNORECASE):
                report.add_issue(
                    f"table_{tbl_name}_missing",
                    f"Не найдена таблица «{tbl_name}».",
                    ValidationStatus.WARNING,
                    tbl_name,
                )

        if not report.issues and not report.warnings:
            report.add_issue("render_ok", "Валидация HTML-рендера пройдена", ValidationStatus.PASSED)

        return report