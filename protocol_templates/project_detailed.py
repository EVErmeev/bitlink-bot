import re
import uuid
from datetime import date

from protocol_templates.base import BaseProtocolTemplate
from models.protocol import Protocol, TopicBlock, DecisionItem, QuestionItem, RiskItem, TaskItem, AtomicItem
from models.validation import ValidationReport, ValidationStatus


class ProjectDetailedTemplate(BaseProtocolTemplate):
    template_id = "project_detailed"
    version = "3.0"
    display_name = "Подробный проектный протокол"
    description = "Максимально наполненный протокол встречи (версия 3.0)."

    SECTION_NAMES = {
        "general_info": "Общая информация",
        "participants": "Участники",
        "purpose_and_context": "Цель встречи и исходный контекст",
        "key_outcomes": "Ключевые итоги",
        "topic_blocks": "Обсуждение по тематическим блокам",
        "current_state": "Текущее состояние объектов и процессов",
        "decisions": "Принятые решения",
        "questions": "Открытые вопросы",
        "risks": "Риски и ограничения",
        "tasks": "Задачи и следующие шаги",
    }

    REQUIRED_SECTIONS = list(SECTION_NAMES.keys())

    REMOVED_SECTIONS = [
        "Сквозная схема процесса",
        "Согласованные подходы",
        "Рассмотренные варианты",
        "Функциональные разрывы",
        "Контрольные точки",
    ]

    RISK_TYPES = {"Риск", "Ограничение", "Зависимость", "Блокер", "Допущение"}

    FORBIDDEN_STATUS_CODES = {"confirmed", "open", "risk", "in_progress", "closed", "pending", "done", "todo"}

    DECISION_FALLBACKS = [
        "решение не принято",
        "вопрос остаётся открытым",
        "требуется проверка",
        "ожидается информация",
        "вариант передан на проработку",
        "вопрос перенесён",
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
                        "meeting_context": {"type": "string"},
                    },
                },
                "participants": {"type": "array"},
                "purpose_and_context": {"type": "string"},
                "key_outcomes": {"type": "string"},
                "topic_blocks": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "topic_id": {"type": "string"},
                            "title": {"type": "string"},
                            "discussion_content": {"type": "string"},
                            "conclusion": {"type": "string"},
                            "status_text": {"type": "string"},
                            "status_reason": {"type": "string"},
                            "status_next_action": {"type": "string"},
                            "status_responsible": {"type": "string"},
                            "status_deadline": {"type": "string"},
                        },
                        "required": ["title", "discussion_content", "conclusion", "status_text"],
                    },
                },
                "current_state": {"type": "string"},
                "decisions": {"type": "array"},
                "questions": {"type": "array"},
                "risks": {"type": "array"},
                "tasks": {"type": "array"},
            },
            "required": self.REQUIRED_SECTIONS,
        }

    def get_system_prompt(self) -> str:
        return (
            "Ты — старший аналитик, составляющий подробный проектный протокол встречи (версия 3.0). "
            "Это максимально наполненный документ для детальной фиксации хода встречи.\n\n"
            "ОБЩИЕ ПРАВИЛА:\n"
            "- Только факты из предоставленных данных источников. Ничего не придумывай.\n"
            "- Используй только подтверждённые данные.\n"
            "- Все ячейки таблиц должны быть заполнены. Пустых ячеек быть не должно.\n"
            "- Отсутствующие данные обозначай явно: «данные отсутствуют», «не указано».\n\n"
            "СТРУКТУРА (10 разделов):\n"
            "1. Общая информация — дата, название, контекст встречи.\n"
            "2. Участники — полный список с ролями.\n"
            "3. Цель встречи и исходный контекст.\n"
            "4. Ключевые итоги — основные результаты.\n"
            "5. ОБСУЖДЕНИЕ ПО ТЕМАТИЧЕСКИМ БЛОКАМ — ГЛАВНЫЙ РАЗДЕЛ (>=55% объёма документа).\n"
            "   Это основная таблица со столбцами: №, Тематический блок, Что обсуждалось, "
            "Итог / вывод, Статус.\n"
            "   Столбец «Что обсуждалось» должен содержать:\n"
            "   - исходную ситуацию, факты, текущее состояние\n"
            "   - продемонстрированные механизмы, системы, документы, роли\n"
            "   - вопросы заказчика, ответы исполнителя\n"
            "   - варианты и аргументы, ограничения и зависимости\n"
            "   - числовые примеры, даты и сроки\n"
            "   - что требуется проверить, что перенесено\n"
            "   Минимум 3 смысловых элемента или 80 слов на тему. 150-500 слов для крупных тем.\n"
            "   Столбец «Итог / вывод» (60-250 слов): что подтверждено, согласовано, "
            "не согласовано, требует проверки, действия, срок, ответственный. Не пустой.\n"
            "   Столбец «Статус»: название статуса, причина, следующее действие, "
            "ответственный, срок. Писать человеческим русским языком, не кодами.\n"
            "6. Текущее состояние объектов и процессов.\n"
            "7. Принятые решения — только решения с explicit_agreement=true, "
            "высокой уверенностью и подтверждениями. Предложения в решения не превращать.\n"
            "8. Открытые вопросы — ВСЕ незакрытые вопросы, включая без ответа, "
            "требующие проверки, запросы данных, перенесённые темы.\n"
            "9. Риски и ограничения — типы: Риск, Ограничение, Зависимость, Блокер, Допущение.\n"
            "10. Задачи и следующие шаги — не придумывать отсутствующие сроки и ответственных.\n\n"
            "ЗАПРЕЩЕНО выделять как отдельные разделы: Сквозная схема процесса, "
            "Согласованные подходы, Рассмотренные варианты, Функциональные разрывы, "
            "Контрольные точки."
        )

    def _build_status_string(self, tb: TopicBlock) -> str:
        parts = []
        if tb.status_text:
            parts.append(tb.status_text)
        if tb.status_reason:
            parts.append(tb.status_reason)
        if tb.status_next_action:
            parts.append(tb.status_next_action)
        resp = tb.status_responsible if tb.status_responsible else "Ответственный не определён"
        dl = tb.status_deadline if tb.status_deadline else "Срок не определён"
        parts.append(f"{resp}, {dl}")
        return ". ".join(parts) if parts else (f"Ответственный не определён, Срок не определён")

    # ── Keyword clustering ──────────────────────────────────────────────

    def _extract_keywords(self, text: str) -> set[str]:
        """Extract significant words (len > 3, only Russian/English letters) from text."""
        words = re.findall(r"[а-яёa-z]{4,}", text.lower())
        return set(words)

    def _cluster_facts(self, facts: list[AtomicItem]) -> dict[str, tuple[set[str], list[AtomicItem]]]:
        """Group fact items by keyword similarity.

        Returns dict: topic_label -> (keyword_set, [AtomicItem, ...])
        """
        topics: dict[str, tuple[set[str], list[AtomicItem]]] = {}

        for fact in facts:
            words = self._extract_keywords(fact.text)
            if not words:
                words = {fact.text[:20].strip() or "обсуждение"}

            matched = False
            for topic_name, (topic_words, items) in topics.items():
                common = words & topic_words
                if len(common) >= 2:
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

    def _derive_topic_title(self, keywords: set[str], topic_label: str,
                            llm_titles: list[str] | None = None) -> str:
        """Derive a human-readable title from keywords or LLM output."""
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
            "загрузк": "Загрузка данных",
            "миграц": "Миграция данных",
            "тестирован": "Тестирование",
            "обучен": "Обучение пользователей",
            "архитектур": "Архитектура решения",
            "безопасност": "Безопасность",
            "план": "Планирование",
            "риск": "Риски",
            "срок": "Сроки проекта",
            "бюджет": "Бюджет",
            "требован": "Требования",
            "прототип": "Прототипирование",
        }

        for kw, prefix in topic_prefixes.items():
            if any(kw in w for w in top):
                if len(top) > 1:
                    other = [w for w in top if kw not in w][:2]
                    return f"{prefix}: {', '.join(other)}"
                return prefix

        if llm_titles and len(llm_titles) > 0:
            idx = len(llm_titles)
            if idx < len(llm_titles):
                return llm_titles[idx]
            return llm_titles[0]

        if top:
            cap_words = [w.capitalize() for w in top[:3]]
            return f"Тема: {' '.join(cap_words)}"

        return topic_label[:60] or "Обсуждение"

    def _build_topic_blocks(self, facts: list[AtomicItem], source_context_id: str,
                            llm_titles: list[str] | None = None) -> list[TopicBlock]:
        """Build multiple TopicBlock instances from clustered facts."""
        if not facts:
            return []

        clusters = self._cluster_facts(facts)
        if not clusters:
            return []

        topic_blocks = []
        order = 0

        for label, (keywords, items) in clusters.items():
            order += 1
            discussion_parts = []
            speakers = set()
            for item in items:
                discussion_parts.append(item.text)
                if item.speaker:
                    speakers.add(item.speaker)

            discussion = ". ".join(discussion_parts)
            speakers_str = ", ".join(speakers) if speakers else "Ответственный не определён"

            conclusion_parts = [f"Обсуждено {len(items)} фактов по теме."]
            if speakers:
                conclusion_parts.append(f"Докладчики: {speakers_str}.")
            conclusion_parts.append("Требуется дальнейший анализ и проработка.")
            conclusion = " ".join(conclusion_parts)

            title = self._derive_topic_title(keywords, label, llm_titles)

            topic_block = TopicBlock(
                topic_id=str(uuid.uuid4()),
                title=title,
                source_context_id=source_context_id or "",
                discussion_content=discussion,
                conclusion=conclusion,
                status_text="Обсуждено",
                status_reason="Информация получена от участников встречи",
                status_next_action="Принять к сведению и проработать",
                status_responsible=speakers_str,
                status_deadline="Срок не определён",
                order=order,
            )
            topic_blocks.append(topic_block)

        return topic_blocks

    # ── Helper: extract LLM topic titles ─────────────────────────────────

    def _extract_llm_topic_titles(self, llm_output: str) -> list[str] | None:
        """Try to extract topic titles from LLM output. Returns None if not found."""
        if not llm_output or not llm_output.strip():
            return None

        titles = []

        LQ = "\u00ab"
        RQ = "\u00bb"
        title_patterns = [
            "(?:" + "Тематический блок" + "|" + "Тема" + r")\s*\d*\s*[" + LQ + r":](.+?)[" + RQ + r":]",
            r"(?:###|##)\s*(.+?)(?:\n|$)",
            r"\*\*(.+?)\*\*",
        ]

        for pattern in title_patterns:
            matches = re.findall(pattern, llm_output, re.IGNORECASE)
            for m in matches:
                clean = m.strip().strip(LQ + RQ + '"')
                if len(clean) > 5 and clean not in titles:
                    titles.append(clean)

        return titles if titles else None

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

        # --- classify items by type ---
        fact_items = []
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
                fact_items.append(item)

        # --- cluster facts into multiple topic blocks ---
        if fact_items:
            src_ctx = protocol.source_context_id or ""
            topic_blocks = self._build_topic_blocks(fact_items, src_ctx)
            for tb in topic_blocks:
                protocol.topic_blocks.append(tb)

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
        if protocol.topic_blocks:
            outcome_parts.append(f"Рассмотрено {len(protocol.topic_blocks)} тематических блоков.")

        if outcome_parts:
            protocol.key_outcomes = " ".join(outcome_parts)
        else:
            protocol.key_outcomes = "Встреча проведена. Итоги зафиксированы."

        # --- current state ---
        if fact_items:
            state_parts = [f"Зафиксировано {len(fact_items)} фактов в {len(protocol.topic_blocks)} тематических блоках."]
            speakers_list = list(set(f.speaker for f in fact_items if f.speaker))
            if speakers_list:
                state_parts.append(f"Докладчики: {', '.join(speakers_list)}.")
            protocol.current_state = " ".join(state_parts)

        # --- word counts ---
        for tb in protocol.topic_blocks:
            tb.word_count = len(re.findall(r"\b\w+\b", tb.discussion_content + " " + tb.conclusion))

        return protocol

    # ── assemble_with_llm_output ─────────────────────────────────────────

    def assemble_with_llm_output(self, protocol: Protocol, atomic_items: list,
                                  llm_output: str, meeting_metadata: dict) -> Protocol:
        """Use LLM output for topic titles, fall back to keyword clustering otherwise."""
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

        llm_titles = self._extract_llm_topic_titles(llm_output)

        fact_items = []
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
                fact_items.append(item)

        if fact_items:
            src_ctx = protocol.source_context_id or ""
            topic_blocks = self._build_topic_blocks(fact_items, src_ctx, llm_titles)
            for tb in topic_blocks:
                protocol.topic_blocks.append(tb)

        outcome_parts = []
        if protocol.decisions:
            outcome_parts.append(f"Принято {len(protocol.decisions)} решений.")
        if protocol.questions:
            outcome_parts.append(f"Зафиксировано {len(protocol.questions)} открытых вопросов.")
        if protocol.risks:
            outcome_parts.append(f"Выявлено {len(protocol.risks)} рисков/ограничений.")
        if protocol.tasks:
            outcome_parts.append(f"Поставлено {len(protocol.tasks)} задач.")
        if protocol.topic_blocks:
            outcome_parts.append(f"Рассмотрено {len(protocol.topic_blocks)} тематических блоков.")

        if outcome_parts:
            protocol.key_outcomes = " ".join(outcome_parts)
        else:
            protocol.key_outcomes = "Встреча проведена. Итоги зафиксированы."

        if fact_items:
            state_parts = [f"Зафиксировано {len(fact_items)} фактов в {len(protocol.topic_blocks)} тематических блоках."]
            speakers_list = list(set(f.speaker for f in fact_items if f.speaker))
            if speakers_list:
                state_parts.append(f"Докладчики: {', '.join(speakers_list)}.")
            protocol.current_state = " ".join(state_parts)

        for tb in protocol.topic_blocks:
            tb.word_count = len(re.findall(r"\b\w+\b", tb.discussion_content + " " + tb.conclusion))

        return protocol

    # ── validation ───────────────────────────────────────────────────────

    def _count_words(self, text: str) -> int:
        if not text:
            return 0
        return len(re.findall(r"\b\w+\b", text))

    def _collect_section_text(self, protocol: Protocol, section_name: str) -> str:
        section_map = {
            "general_info": f"{protocol.protocol_title} {protocol.meeting_context or ''}",
            "participants": " ".join(
                f"{p.get('name', '')} {p.get('role', '')}"
                for p in protocol.participants
                if isinstance(p, dict)
            ),
            "purpose_and_context": f"{protocol.meeting_purpose or ''} {protocol.meeting_context or ''}",
            "key_outcomes": protocol.key_outcomes or "",
            "topic_blocks": " ".join(
                f"{tb.title} {tb.discussion_content} {tb.conclusion} {tb.status_text}"
                for tb in protocol.topic_blocks
            ),
            "current_state": protocol.current_state or "",
            "decisions": " ".join(
                f"{d.decision_text} {d.context_and_basis} {d.agreed_scope} {d.boundaries}"
                for d in protocol.decisions
            ),
            "questions": " ".join(
                f"{q.question_text} {q.context} {q.known_info} {q.to_determine}"
                for q in protocol.questions
            ),
            "risks": " ".join(
                f"{r.risk_text} {r.reason} {r.impact} {r.measures}"
                for r in protocol.risks
            ),
            "tasks": " ".join(
                f"{t.task_text} {t.basis} {t.expected_result}"
                for t in protocol.tasks
            ),
        }
        return section_map.get(section_name, "")

    def validate(self, protocol: Protocol) -> ValidationReport:
        report = ValidationReport()

        section_words = {}
        total_words = 0
        for section_name in self.REQUIRED_SECTIONS:
            text = self._collect_section_text(protocol, section_name)
            wc = self._count_words(text)
            section_words[section_name] = wc
            total_words += wc

        if total_words == 0:
            report.add_issue("empty_protocol", "Протокол полностью пуст.", ValidationStatus.FAILED)
            return report

        if "topic_blocks" in section_words and total_words > 0:
            topic_ratio = section_words["topic_blocks"] / total_words
            if topic_ratio < 0.55:
                report.add_issue(
                    "thematic_ratio_low",
                    f"Тематическая таблица составляет {topic_ratio:.1%} объёма (требуется >=55%). "
                    f"Сейчас: {section_words['topic_blocks']} из {total_words} слов.",
                    ValidationStatus.FAILED,
                    "topic_blocks",
                    "Расширьте столбцы «Что обсуждалось» и «Итог / вывод» в тематической таблице.",
                )
            else:
                report.checks["thematic_ratio_ok"] = True

        for i, tb in enumerate(protocol.topic_blocks):
            if protocol.source_context_id and tb.source_context_id and tb.source_context_id != protocol.source_context_id:
                report.add_issue(
                    f"topic_{i}_source_mismatch",
                    f"Тематический блок #{i + 1} «{tb.title}»: несовпадение source_context_id "
                    f"({tb.source_context_id} != {protocol.source_context_id}).",
                    ValidationStatus.FAILED,
                    f"topic_blocks[{i}].source_context_id",
                )
            if not tb.title or not tb.title.strip():
                report.add_issue(
                    f"topic_{i}_no_title",
                    f"Тематический блок #{i + 1}: отсутствует заголовок.",
                    ValidationStatus.FAILED,
                    f"topic_blocks[{i}].title",
                )
            if not tb.discussion_content or len(tb.discussion_content.strip()) < 80:
                disc_words = self._count_words(tb.discussion_content)
                report.add_issue(
                    f"topic_{i}_discussion_short",
                    f"Тематический блок #{i + 1} «{tb.title}»: столбец «Что обсуждалось» "
                    f"слишком короткий ({disc_words} слов, минимум 80).",
                    ValidationStatus.FAILED,
                    f"topic_blocks[{i}].discussion_content",
                    "Добавьте исходную ситуацию, факты, системы, роли, вопросы, ответы, аргументы.",
                )
            if not tb.conclusion or len(tb.conclusion.strip()) < 60:
                conc_words = self._count_words(tb.conclusion)
                report.add_issue(
                    f"topic_{i}_conclusion_short",
                    f"Тематический блок #{i + 1} «{tb.title}»: столбец «Итог / вывод» "
                    f"слишком короткий ({conc_words} слов, минимум 60).",
                    ValidationStatus.FAILED,
                    f"topic_blocks[{i}].conclusion",
                )

            status_str = self._build_status_string(tb)
            if not status_str.strip():
                report.add_issue(
                    f"topic_{i}_status_empty",
                    f"Тематический блок #{i + 1} «{tb.title}»: столбец «Статус» пуст.",
                    ValidationStatus.FAILED,
                    f"topic_blocks[{i}].status",
                )

            status_lower = status_str.lower()
            for code in self.FORBIDDEN_STATUS_CODES:
                if code == status_lower.strip() or re.search(rf"\b{re.escape(code)}\b", status_lower):
                    report.add_issue(
                        f"topic_{i}_status_code",
                        f"Тематический блок #{i + 1} «{tb.title}»: статус содержит "
                        f"внутренний код «{code}». Используйте человекочитаемый русский текст.",
                        ValidationStatus.FAILED,
                        f"topic_blocks[{i}].status",
                    )
                    break

        for j, d in enumerate(protocol.decisions):
            if not d.explicit_agreement:
                report.add_issue(
                    f"decision_{j}_no_agreement",
                    f"Решение #{j + 1} «{d.decision_text[:60]}...»: "
                    f"отсутствует явное согласование (explicit_agreement=false).",
                    ValidationStatus.FAILED,
                    f"decisions[{j}]",
                )
            if d.confidence < 0.7:
                report.add_issue(
                    f"decision_{j}_low_confidence",
                    f"Решение #{j + 1} «{d.decision_text[:60]}...»: "
                    f"низкая уверенность ({d.confidence:.2f}).",
                    ValidationStatus.FAILED,
                    f"decisions[{j}]",
                )
            if not d.evidence or len(d.evidence.strip()) < 20:
                report.add_issue(
                    f"decision_{j}_no_evidence",
                    f"Решение #{j + 1} «{d.decision_text[:60]}...»: "
                    f"отсутствует или недостаточно подтверждение (evidence).",
                    ValidationStatus.FAILED,
                    f"decisions[{j}]",
                )
            cells = {
                "decision_text": d.decision_text,
                "context_and_basis": d.context_and_basis,
            }
            empty = [k for k, v in cells.items() if not v or not v.strip()]
            if empty:
                report.add_issue(
                    f"decision_{j}_empty_cells",
                    f"Решение #{j + 1}: пустые ячейки: {', '.join(empty)}.",
                    ValidationStatus.FAILED,
                    f"decisions[{j}]",
                )

        for k, q in enumerate(protocol.questions):
            cells = {
                "question_text": q.question_text,
            }
            empty = [key for key, val in cells.items() if not val or not val.strip()]
            if empty:
                report.add_issue(
                    f"question_{k}_empty_cells",
                    f"Вопрос #{k + 1}: пустые ячейки: {', '.join(empty)}.",
                    ValidationStatus.FAILED,
                    f"questions[{k}]",
                )
            status_lower = q.status.lower().strip() if q.status else ""
            for code in self.FORBIDDEN_STATUS_CODES:
                if status_lower == code or re.search(rf"\b{re.escape(code)}\b", status_lower):
                    report.add_issue(
                        f"question_{k}_status_code",
                        f"Вопрос #{k + 1}: статус содержит внутренний код «{code}».",
                        ValidationStatus.FAILED,
                        f"questions[{k}].status",
                    )
                    break

        for m, r in enumerate(protocol.risks):
            if r.risk_type and r.risk_type not in self.RISK_TYPES:
                report.add_issue(
                    f"risk_{m}_bad_type",
                    f"Риск #{m + 1}: недопустимый тип «{r.risk_type}». "
                    f"Допустимые: {', '.join(sorted(self.RISK_TYPES))}.",
                    ValidationStatus.FAILED,
                    f"risks[{m}].risk_type",
                )
            cells = {
                "risk_text": r.risk_text,
            }
            empty = [key for key, val in cells.items() if not val or not val.strip()]
            if empty:
                report.add_issue(
                    f"risk_{m}_empty_cells",
                    f"Риск #{m + 1}: пустые ячейки: {', '.join(empty)}.",
                    ValidationStatus.FAILED,
                    f"risks[{m}]",
                )

        for n, t in enumerate(protocol.tasks):
            if not t.commitment_confirmed:
                report.add_issue(
                    f"task_{n}_no_commitment",
                    f"Задача #{n + 1} «{t.task_text[:60]}...»: "
                    f"отсутствует подтверждение обязательства (commitment_confirmed=false).",
                    ValidationStatus.FAILED,
                    f"tasks[{n}]",
                )
            cells = {
                "task_text": t.task_text,
                "basis": t.basis,
            }
            empty = [key for key, val in cells.items() if not val or not val.strip()]
            if empty:
                report.add_issue(
                    f"task_{n}_empty_cells",
                    f"Задача #{n + 1}: пустые ячейки: {', '.join(empty)}.",
                    ValidationStatus.FAILED,
                    f"tasks[{n}]",
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

        atomic_ids = {a.item_id for a in protocol.atomic_items if isinstance(a, AtomicItem)}
        for d in protocol.decisions:
            if d.source_context_id and d.source_context_id not in atomic_ids:
                report.add_issue(
                    f"decision_{d.decision_id}_mixed_source",
                    f"Решение «{d.decision_text[:50]}...» ссылается на несуществующий источник.",
                    ValidationStatus.WARNING,
                    f"decisions.{d.decision_id}",
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

        topic_rows = ""
        for i, tb in enumerate(protocol.topic_blocks, 1):
            status_str = self._build_status_string(tb)
            discussion = tb.discussion_content.replace(chr(10), "<br>") if tb.discussion_content else "—"
            conclusion = tb.conclusion.replace(chr(10), "<br>") if tb.conclusion else "—"
            topic_rows += f"""<tr>
<td class=\"num\">{i}</td>
<td class=\"topic-title\">{tb.title or '—'}</td>
<td class=\"discussion\">{discussion}</td>
<td class=\"conclusion\">{conclusion}</td>
<td class=\"status\">{status_str}</td>
</tr>
"""

        decisions_rows = ""
        for i, d in enumerate(protocol.decisions, 1):
            decisions_rows += f"""<tr>
<td class=\"num\">{i}</td>
<td>{d.decision_text or '—'}</td>
<td>{d.context_and_basis or '—'}</td>
<td>{d.agreed_scope or '—'}</td>
<td>{d.boundaries or '—'}</td>
<td>{d.responsible or '—'}</td>
<td>{d.deadline or '—'}</td>
<td>{d.related_topic or '—'}</td>
</tr>
"""

        questions_rows = ""
        for i, q in enumerate(protocol.questions, 1):
            questions_rows += f"""<tr>
<td class=\"num\">{i}</td>
<td>{q.question_text or '—'}</td>
<td>{q.context or '—'}</td>
<td>{q.known_info or '—'}</td>
<td>{q.to_determine or '—'}</td>
<td>{q.responsible or '—'}</td>
<td>{q.deadline or '—'}</td>
<td>{q.next_action or '—'}</td>
<td>{q.status or '—'}</td>
<td>{q.related_topic or '—'}</td>
</tr>
"""

        risks_rows = ""
        for i, r in enumerate(protocol.risks, 1):
            risks_rows += f"""<tr>
<td class=\"num\">{i}</td>
<td>{r.risk_type or '—'}</td>
<td>{r.risk_text or '—'}</td>
<td>{r.reason or '—'}</td>
<td>{r.impact or '—'}</td>
<td>{r.trigger_condition or '—'}</td>
<td>{r.measures or '—'}</td>
<td>{r.responsible or '—'}</td>
<td>{r.deadline or '—'}</td>
<td>{r.status or '—'}</td>
<td>{r.related_topic or '—'}</td>
</tr>
"""

        tasks_rows = ""
        for i, t in enumerate(protocol.tasks, 1):
            tasks_rows += f"""<tr>
<td class=\"num\">{i}</td>
<td>{t.task_text or '—'}</td>
<td>{t.basis or '—'}</td>
<td>{t.expected_result or '—'}</td>
<td>{t.responsible or '—'}</td>
<td>{t.co_executors or '—'}</td>
<td>{t.deadline or '—'}</td>
<td>{t.dependencies or '—'}</td>
<td>{t.status or '—'}</td>
<td>{t.related_topic or '—'}</td>
</tr>
"""

        html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Подробный проектный протокол — {protocol.protocol_title or 'Встреча'}</title>
<style>
    * {{ box-sizing: border-box; }}
    body {{
        font-family: 'Segoe UI', Arial, sans-serif;
        max-width: 1100px;
        margin: 30px auto;
        padding: 20px 40px;
        color: #1a1a1a;
        line-height: 1.6;
        background: #fff;
    }}
    h1 {{
        color: #1a237e;
        font-size: 26px;
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
        font-size: 20px;
        margin-top: 36px;
        padding-left: 10px;
        border-left: 4px solid #1a237e;
    }}
    h3 {{
        color: #37474f;
        font-size: 16px;
        margin-top: 20px;
    }}
    table {{
        border-collapse: collapse;
        width: 100%;
        margin: 16px 0 24px 0;
        font-size: 13px;
        page-break-inside: avoid;
    }}
    th, td {{
        border: 1px solid #b0bec5;
        padding: 10px 14px;
        text-align: left;
        vertical-align: top;
    }}
    th {{
        background-color: #1a237e;
        color: #ffffff;
        font-weight: 600;
        white-space: nowrap;
        font-size: 13px;
    }}
    tr:nth-child(even) td {{
        background-color: #f5f5f5;
    }}
    td.num {{
        text-align: center;
        width: 40px;
        white-space: nowrap;
    }}
    td.topic-title {{
        font-weight: 600;
        min-width: 140px;
    }}
    td.discussion {{
        min-width: 250px;
    }}
    td.conclusion {{
        min-width: 200px;
    }}
    td.status {{
        min-width: 160px;
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
    .section-content {{
        margin: 8px 0 16px 0;
    }}
    .footer {{
        margin-top: 40px;
        padding-top: 12px;
        border-top: 1px solid #bdbdbd;
        font-size: 12px;
        color: #999;
    }}
    @media print {{
        body {{ margin: 0; padding: 15px; font-size: 12px; }}
        h1 {{ font-size: 20px; }}
        h2 {{ font-size: 16px; }}
        table {{ font-size: 11px; }}
        th, td {{ padding: 6px 8px; }}
    }}
    @media (max-width: 768px) {{
        body {{ padding: 10px; }}
        table {{ font-size: 12px; }}
        th, td {{ padding: 6px 8px; }}
    }}
</style>
</head>
<body>

<h1>{self.SECTION_NAMES['general_info']}</h1>
<p class="header-meta"><strong>Дата встречи:</strong> {date_str} | <strong>Время:</strong> {time_str}</p>
<p><strong>Название протокола:</strong> {protocol.protocol_title or '—'}</p>
<div class="section-content">{protocol.meeting_context.replace(chr(10), '<br>') if protocol.meeting_context else '<p>—</p>'}</div>

<h2>{self.SECTION_NAMES['participants']}</h2>
<table>
<thead>
<tr><th>№</th><th>Имя</th><th>Роль</th></tr>
</thead>
<tbody>
{participants_rows or '<tr><td colspan="3">Участники не указаны</td></tr>'}
</tbody>
</table>

<h2>{self.SECTION_NAMES['purpose_and_context']}</h2>
<h3>Цель встречи</h3>
<div class="section-content">{protocol.meeting_purpose.replace(chr(10), '<br>') if protocol.meeting_purpose else '<p>—</p>'}</div>
<h3>Исходный контекст</h3>
<div class="section-content">{protocol.meeting_context.replace(chr(10), '<br>') if protocol.meeting_context else '<p>—</p>'}</div>

<h2>{self.SECTION_NAMES['key_outcomes']}</h2>
<div class="section-content">{protocol.key_outcomes.replace(chr(10), '<br>') if protocol.key_outcomes else '<p>—</p>'}</div>

<h2>{self.SECTION_NAMES['topic_blocks']}</h2>
<table class="topic-table">
<thead>
<tr>
    <th>№</th>
    <th>Тематический блок</th>
    <th>Что обсуждалось</th>
    <th>Итог / вывод</th>
    <th>Статус</th>
</tr>
</thead>
<tbody>
{topic_rows or '<tr><td colspan="5">Тематические блоки отсутствуют</td></tr>'}
</tbody>
</table>

<h2>{self.SECTION_NAMES['current_state']}</h2>
<div class="section-content">{protocol.current_state.replace(chr(10), '<br>') if protocol.current_state else '<p>—</p>'}</div>

<h2>{self.SECTION_NAMES['decisions']}</h2>
<table>
<thead>
<tr>
    <th>№</th>
    <th>Решение</th>
    <th>Контекст и основание</th>
    <th>Что согласовано</th>
    <th>Границы решения</th>
    <th>Ответственные / участники</th>
    <th>Срок</th>
    <th>Связанная тема</th>
</tr>
</thead>
<tbody>
{decisions_rows or '<tr><td colspan="8">Решения отсутствуют</td></tr>'}
</tbody>
</table>

<h2>{self.SECTION_NAMES['questions']}</h2>
<table>
<thead>
<tr>
    <th>№</th>
    <th>Вопрос</th>
    <th>Контекст</th>
    <th>Что известно</th>
    <th>Что определить / получить</th>
    <th>Ответственный</th>
    <th>Срок</th>
    <th>Следующее действие</th>
    <th>Статус</th>
    <th>Связанная тема</th>
</tr>
</thead>
<tbody>
{questions_rows or '<tr><td colspan="10">Вопросы отсутствуют</td></tr>'}
</tbody>
</table>

<h2>{self.SECTION_NAMES['risks']}</h2>
<table>
<thead>
<tr>
    <th>№</th>
    <th>Тип</th>
    <th>Риск / ограничение</th>
    <th>Причина</th>
    <th>Влияние</th>
    <th>Условие проявления</th>
    <th>Меры</th>
    <th>Ответственный</th>
    <th>Срок</th>
    <th>Статус</th>
    <th>Связанная тема</th>
</tr>
</thead>
<tbody>
{risks_rows or '<tr><td colspan="11">Риски отсутствуют</td></tr>'}
</tbody>
</table>

<h2>{self.SECTION_NAMES['tasks']}</h2>
<table>
<thead>
<tr>
    <th>№</th>
    <th>Задача</th>
    <th>Основание</th>
    <th>Ожидаемый результат</th>
    <th>Ответственный</th>
    <th>Соисполнители</th>
    <th>Срок</th>
    <th>Зависимости</th>
    <th>Статус</th>
    <th>Связанная тема</th>
</tr>
</thead>
<tbody>
{tasks_rows or '<tr><td colspan="10">Задачи отсутствуют</td></tr>'}
</tbody>
</table>

<div class="footer">Протокол сгенерирован автоматически. Шаблон: {self.template_id} v{self.version}</div>
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

        for removed_name in self.REMOVED_SECTIONS:
            if removed_name in html:
                pattern = re.compile(
                    rf"<h[23][^>]*>\s*{re.escape(removed_name)}\s*</h[23]>",
                    re.IGNORECASE,
                )
                if pattern.search(html):
                    report.add_issue(
                        f"removed_section_{removed_name}",
                        f"В HTML обнаружена удалённая секция «{removed_name}» "
                        f"(должна отсутствовать как отдельный раздел).",
                        ValidationStatus.FAILED,
                        removed_name,
                    )

        for code in self.FORBIDDEN_STATUS_CODES:
            pattern = re.compile(
                rf'<td[^>]*>.*?\b{re.escape(code)}\b.*?</td>',
                re.IGNORECASE,
            )
            if pattern.search(html):
                report.add_issue(
                    f"status_code_found_{code}",
                    f"В HTML найден внутренний код статуса «{code}».",
                    ValidationStatus.FAILED,
                )

        topic_table_pattern = re.compile(
            r"Обсуждение по тематическим блокам.*?</table>",
            re.DOTALL | re.IGNORECASE,
        )
        topic_table_match = topic_table_pattern.search(html)
        if topic_table_match:
            topic_section_html = topic_table_match.group()
            topic_section_words = self._count_words(topic_section_html)
        else:
            topic_section_words = 0

        all_text = re.sub(r"<[^>]+>", " ", html)
        all_text = re.sub(r"\s+", " ", all_text).strip()
        total_html_words = self._count_words(all_text)

        if total_html_words > 0 and topic_section_words > 0:
            topic_ratio = topic_section_words / total_html_words
            if topic_ratio < 0.55:
                report.add_issue(
                    "html_thematic_ratio_low",
                    f"В HTML тематическая таблица составляет {topic_ratio:.1%} объёма (требуется >=55%). "
                    f"Тема: {topic_section_words} слов, всего: {total_html_words} слов.",
                    ValidationStatus.FAILED,
                    "topic_blocks",
                )

        table_bodies = re.findall(r"<tbody>(.*?)</tbody>", html, re.DOTALL)
        for body_idx, body in enumerate(table_bodies):
            rows = re.findall(r"<tr>(.*?)</tr>", body, re.DOTALL)
            for row_idx, row in enumerate(rows):
                cells = re.findall(r"<td[^>]*>(.*?)</td>", row, re.DOTALL)
                for cell_idx, cell in enumerate(cells):
                    cell_text = re.sub(r"<[^>]+>", "", cell).strip()
                    if not cell_text:
                        colspan_match = re.search(r'colspan\s*=\s*["\'](\d+)["\']', row, re.IGNORECASE)
                        if not colspan_match:
                            report.add_issue(
                                f"empty_cell_tbody{body_idx}_row{row_idx}_cell{cell_idx}",
                                f"Пустая ячейка в таблице #{body_idx + 1}, строка #{row_idx + 1}, "
                                f"столбец #{cell_idx + 1}.",
                                ValidationStatus.FAILED,
                            )

        if not report.issues and not report.warnings:
            report.add_issue("render_ok", "Валидация HTML-рендера пройдена", ValidationStatus.PASSED)

        return report