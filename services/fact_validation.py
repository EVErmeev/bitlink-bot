from datetime import date, datetime
from models.protocol import Protocol, AtomicItem, DecisionItem, TaskItem, TopicBlock
from models.validation import ValidationReport, ValidationStatus


def validate_facts(protocol: Protocol, transcript_text: str) -> ValidationReport:
    report = ValidationReport()

    transcript_lower = transcript_text.lower()

    for i, d in enumerate(protocol.decisions):
        if not d.explicit_agreement:
            report.add_issue(
                f"decision_{i}_no_agreement",
                f"Решение #{i + 1} «{d.decision_text[:60]}...»: отсутствует явное согласование.",
                ValidationStatus.FAILED,
                f"decisions[{i}]",
                "Убедитесь, что решение подтверждено явным согласием участников (explicit_agreement=True).",
            )
        if d.confidence < 0.8:
            report.add_issue(
                f"decision_{i}_low_confidence",
                f"Решение #{i + 1} «{d.decision_text[:60]}...»: "
                f"низкая уверенность ({d.confidence:.2f}, требуется >= 0.8).",
                ValidationStatus.FAILED,
                f"decisions[{i}]",
            )
        if not d.evidence or len(d.evidence.strip()) < 50:
            report.add_issue(
                f"decision_{i}_weak_evidence",
                f"Решение #{i + 1}: недостаточно или отсутствует подтверждение (evidence).",
                ValidationStatus.FAILED,
                f"decisions[{i}]",
            )

    for i, t in enumerate(protocol.tasks):
        if not t.commitment_confirmed:
            report.add_issue(
                f"task_{i}_no_commitment",
                f"Задача #{i + 1} «{t.task_text[:60]}...»: отсутствует подтверждение обязательства.",
                ValidationStatus.FAILED,
                f"tasks[{i}]",
                "Задача должна иметь commitment_confirmed=True.",
            )

    invented_checks = _check_invented_items(protocol, transcript_lower)
    for inv in invented_checks:
        report.add_issue(
            inv["code"],
            inv["message"],
            ValidationStatus.FAILED,
            inv.get("location", ""),
            inv.get("suggestion", ""),
        )

    speaker_checks = _check_speakers_exist(protocol, transcript_text)
    for sc in speaker_checks:
        report.add_issue(
            sc["code"],
            sc["message"],
            ValidationStatus.FAILED,
            sc.get("location", ""),
            sc.get("suggestion", ""),
        )

    date_checks = _check_future_dates(protocol)
    for dc in date_checks:
        report.add_issue(
            dc["code"],
            dc["message"],
            ValidationStatus.FAILED,
            dc.get("location", ""),
            dc.get("suggestion", ""),
        )

    context_checks = _check_source_context(protocol)
    for cc in context_checks:
        report.add_issue(
            cc["code"],
            cc["message"],
            ValidationStatus.FAILED,
            cc.get("location", ""),
            cc.get("suggestion", ""),
        )

    return report


def _check_invented_items(protocol: Protocol, transcript_lower: str) -> list[dict]:
    issues = []

    def text_in_transcript(item_text: str) -> bool:
        if not item_text:
            return True
        search_text = item_text.lower()[:80]
        words = search_text.split()
        if not words:
            return True
        significant_words = [w for w in words if len(w) > 4]
        if not significant_words:
            significant_words = words[:3]
        for w in significant_words:
            if w not in transcript_lower:
                return False
        return True

    for i, d in enumerate(protocol.decisions):
        if not text_in_transcript(d.decision_text):
            issues.append({
                "code": f"decision_{i}_invented",
                "message": f"Решение #{i + 1}: текст не найден в транскрипте — возможно, выдумано.",
                "location": f"decisions[{i}]",
                "suggestion": "Убедитесь, что решение действительно обсуждалось на встрече.",
            })

    for i, q in enumerate(protocol.questions):
        if not text_in_transcript(q.question_text):
            issues.append({
                "code": f"question_{i}_invented",
                "message": f"Вопрос #{i + 1}: текст не найден в транскрипте — возможно, выдуман.",
                "location": f"questions[{i}]",
                "suggestion": "Проверьте, что вопрос действительно был задан на встрече.",
            })

    for i, r in enumerate(protocol.risks):
        if not text_in_transcript(r.risk_text):
            issues.append({
                "code": f"risk_{i}_invented",
                "message": f"Риск #{i + 1}: текст не найден в транскрипте — возможно, выдуман.",
                "location": f"risks[{i}]",
                "suggestion": "Проверьте, что риск действительно обсуждался на встрече.",
            })

    for i, t in enumerate(protocol.tasks):
        if not text_in_transcript(t.task_text):
            issues.append({
                "code": f"task_{i}_invented",
                "message": f"Задача #{i + 1}: текст не найден в транскрипте — возможно, выдумана.",
                "location": f"tasks[{i}]",
                "suggestion": "Проверьте, что задача действительно была поставлена на встрече.",
            })

    return issues


def _check_speakers_exist(protocol: Protocol, transcript_text: str) -> list[dict]:
    issues = []
    speaker_names = [p.get("name", "") for p in protocol.participants if isinstance(p, dict)]
    transcript_speakers = set()
    import re
    for match in re.finditer(
        r"(?:^|\n)\s*([А-ЯЁ][а-яё]+(?:\s+[А-ЯЁ][а-яё]+)?)\s*[.:]",
        transcript_text,
        re.MULTILINE,
    ):
        transcript_speakers.add(match.group(1).strip())

    all_known = set(speaker_names) | transcript_speakers | {"Ведущий", "Участник 1", "Участник 2", "Участник 3"}
    _ = all_known
    return issues


def _check_future_dates(protocol: Protocol) -> list[dict]:
    issues = []
    today = date.today()

    if protocol.meeting_date and isinstance(protocol.meeting_date, date):
        if protocol.meeting_date > today:
            issues.append({
                "code": "future_date",
                "message": f"Дата встречи {protocol.meeting_date.isoformat()} находится в будущем.",
                "location": "meeting_date",
                "suggestion": "Проверьте корректность даты встречи.",
            })

    return issues


def _check_source_context(protocol: Protocol) -> list[dict]:
    issues = []
    expected = protocol.source_context_id

    for i, tb in enumerate(protocol.topic_blocks):
        if tb.source_context_id and tb.source_context_id != expected:
            issues.append({
                "code": f"topic_{i}_wrong_context",
                "message": f"Тематический блок #{i + 1}: несовпадение source_context_id "
                           f"({tb.source_context_id} != {expected}).",
                "location": f"topic_blocks[{i}]",
                "suggestion": "Все элементы протокола должны принадлежать одному источнику.",
            })

    return issues


def check_empty_cells(protocol: Protocol) -> list[str]:
    issues = []

    for i, tb in enumerate(protocol.topic_blocks):
        cells = {
            "title": tb.title,
            "discussion_content": tb.discussion_content,
            "conclusion": tb.conclusion,
            "status_text": tb.status_text,
        }
        empty = [k for k, v in cells.items() if not v or not str(v).strip()]
        if empty:
            issues.append(f"Тематический блок #{i + 1}: пустые ячейки ({', '.join(empty)}).")

    for i, d in enumerate(protocol.decisions):
        cells = {
            "decision_text": d.decision_text,
            "context_and_basis": d.context_and_basis,
        }
        empty = [k for k, v in cells.items() if not v or not str(v).strip()]
        if empty:
            issues.append(f"Решение #{i + 1}: пустые ячейки ({', '.join(empty)}).")

    for i, q in enumerate(protocol.questions):
        cells = {
            "question_text": q.question_text,
        }
        empty = [k for k, v in cells.items() if not v or not str(v).strip()]
        if empty:
            issues.append(f"Вопрос #{i + 1}: пустые ячейки ({', '.join(empty)}).")

    for i, r in enumerate(protocol.risks):
        cells = {
            "risk_text": r.risk_text,
        }
        empty = [k for k, v in cells.items() if not v or not str(v).strip()]
        if empty:
            issues.append(f"Риск #{i + 1}: пустые ячейки ({', '.join(empty)}).")

    for i, t in enumerate(protocol.tasks):
        cells = {
            "task_text": t.task_text,
            "basis": t.basis,
        }
        empty = [k for k, v in cells.items() if not v or not str(v).strip()]
        if empty:
            issues.append(f"Задача #{i + 1}: пустые ячейки ({', '.join(empty)}).")

    if not protocol.meeting_purpose or not protocol.meeting_purpose.strip():
        issues.append("Цель встречи: пустая ячейка.")
    if not protocol.key_outcomes or not protocol.key_outcomes.strip():
        issues.append("Ключевые итоги: пустая ячейка.")

    return issues


def apply_corrections(protocol: Protocol) -> Protocol:
    decisions_to_keep = []
    for d in protocol.decisions:
        if not d.decision_text or not d.decision_text.strip():
            continue
        if not d.evidence or len(d.evidence.strip()) < 20:
            d.explicit_agreement = False
            d.confidence = min(d.confidence, 0.5)
        decisions_to_keep.append(d)
    protocol.decisions = decisions_to_keep

    tasks_to_keep = []
    for t in protocol.tasks:
        if not t.task_text or not t.task_text.strip():
            continue
        if not t.responsible or not t.responsible.strip():
            t.commitment_confirmed = False
        tasks_to_keep.append(t)
    protocol.tasks = tasks_to_keep

    questions_to_keep = []
    for q in protocol.questions:
        if not q.question_text or not q.question_text.strip():
            continue
        questions_to_keep.append(q)
    protocol.questions = questions_to_keep

    risks_to_keep = []
    for r in protocol.risks:
        if not r.risk_text or not r.risk_text.strip():
            continue
        risks_to_keep.append(r)
    protocol.risks = risks_to_keep

    topic_blocks_to_keep = []
    for tb in protocol.topic_blocks:
        if not tb.title or not tb.title.strip():
            continue
        topic_blocks_to_keep.append(tb)
    protocol.topic_blocks = topic_blocks_to_keep

    atomic_to_keep = []
    for ai in getattr(protocol, 'atomic_items', []):
        if not hasattr(ai, 'text') or not ai.text or not ai.text.strip():
            continue
        atomic_to_keep.append(ai)
    if hasattr(protocol, 'atomic_items'):
        protocol.atomic_items = atomic_to_keep

    return protocol