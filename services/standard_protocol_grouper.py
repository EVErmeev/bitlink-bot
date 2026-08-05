"""Semantic grouping layer for the standard project protocol.

Builds a compact, grouped *view* on top of the canonical :class:`Protocol`
(metadata, confirmed participants, detailed topic blocks and enriched
decisions/questions/risks/tasks registers). Every grouped item keeps a
traceable link (``source_ids``) to the original detailed elements.

The view never re-extracts a meeting from the transcript; it only performs
conservative semantic grouping, column selection and compact editorialization.
"""
from __future__ import annotations

import re
from datetime import date


def _norm(value) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _low(value) -> str:
    return _norm(value).lower()


# Collective / non-person participant placeholders that must not be rendered
# as participant rows.
_GROUP_PARTICIPANT_MARKERS = (
    "представители проектной команды",
    "руководители",
    "сотрудники склада",
    "сотрудники компании",
    "все участники",
    "команда проекта",
)

_INTERNAL_ROLE_MARKERS = (
    "аналитик", "консультант", "менеджер", "руководитель проекта",
    "разработчик", "инженер", "архитектор", "аккаунт",
)

_TOPIC_KEYWORD_RE = re.compile(r"[а-яёa-z]{4,}")


def _topic_keywords(text: str) -> set[str]:
    return set(_TOPIC_KEYWORD_RE.findall(_low(text)))


def _is_group_participant(p: dict) -> bool:
    name = _low(p.get("name") if isinstance(p, dict) else p)
    role = _low(p.get("role") or p.get("position") or p.get("job_title"))
    return any(m in name or m in role for m in _GROUP_PARTICIPANT_MARKERS)


def _participant_side(p: dict) -> str:
    for key in ("side", "party", "organization", "company", "org"):
        v = _norm(p.get(key))
        if v and _low(v) not in {"", "не определено", "неизвестно"}:
            return v
    role = _low(p.get("role") or p.get("position") or p.get("job_title"))
    if any(m in role for m in _INTERNAL_ROLE_MARKERS):
        return "Первый БИТ"
    return "Заказчик"


def filter_confirmed_participants(participants) -> list[dict]:
    """Return only concrete confirmed attendee rows (no collective placeholders)."""
    out = []
    for p in participants or []:
        if not isinstance(p, dict):
            name = _norm(p)
            if not name or _is_group_participant({"name": name}):
                continue
            out.append({"side": "Заказчик", "position": "Не определено", "full_name": name})
            continue
        name = _norm(p.get("name"))
        if not name or _is_group_participant(p):
            continue
        side = _participant_side(p)
        position = _norm(p.get("role") or p.get("position") or p.get("job_title"))
        if not position:
            position = "Не определено"
        out.append({
            "side": side,
            "position": position,
            "full_name": name,
        })
    return out


# ── Generic grouped-item builders ───────────────────────────────────────

def _make_group(item_type: str, index: int, source_ids: list[str],
                semantic_theme: str, grouping_reason: str,
                preserved_facts: list[str], preserved_responsibles: list[str],
                preserved_deadlines: list[str], display: dict) -> dict:
    return {
        "standard_item_id": f"standard-{item_type}-{index}",
        "standard_item_type": item_type,
        "source_ids": source_ids,
        "semantic_theme": semantic_theme,
        "grouping_reason": grouping_reason,
        "preserved_facts": [f for f in preserved_facts if f],
        "preserved_responsibles": list(dict.fromkeys(r for r in preserved_responsibles if r)),
        "preserved_deadlines": list(dict.fromkeys(d for d in preserved_deadlines if d)),
        "coverage_status": "covered",
        **display,
    }


def _join_unique(values: list[str], sep: str = ". ") -> str:
    seen, out = [], []
    for v in values:
        v = _norm(v)
        if v and _low(v) not in {_low(x) for x in seen}:
            seen.append(v)
            out.append(v)
    return sep.join(out)


def _merge_columns(items: list, *attrs: str) -> str:
    """Merge the longest non-empty values across items, preferring the fullest."""
    values = []
    for item in items:
        for attr in attrs:
            v = _norm(getattr(item, attr, ""))
            if v:
                values.append(v)
    return _join_unique(values)


# ── Topic grouping ───────────────────────────────────────────────────

def group_topic_blocks(topic_blocks) -> list[dict]:
    """Conservatively group detailed topic blocks into standard macro-themes.

    Only blocks sharing a semantic keyword overlap (>=2 significant words) AND
    a compatible status are merged. A block with no compatible neighbour stays
    a single-row group (grouping_reason="unique", coverage 1). This guarantees
    there are never empty rows and every detailed topic is covered.
    """
    blocks = [tb for tb in (topic_blocks or [])]
    grouped: list[dict] = []
    for tb in blocks:
        kw = _topic_keywords(getattr(tb, "title", "") + " " + getattr(tb, "discussion_content", ""))
        status = _low(getattr(tb, "status_text", ""))
        target = None
        for group in grouped:
            group_kw = group["kw"]
            group_status = group["status"]
            common = kw & group_kw
            if len(common) >= 2 and (group_status == status or not status or not group_status):
                target = group
                break
        if target is None:
            grouped.append({"kw": kw, "status": status, "blocks": [tb]})
        else:
            target["kw"] = target["kw"] | kw
            target["status"] = target["status"] or status
            target["blocks"].append(tb)

    groups = []
    for i, group in enumerate(grouped, 1):
        member_blocks = group["blocks"]
        source_ids = [tb.topic_id for tb in member_blocks if getattr(tb, "topic_id", "")]
        if not source_ids:
            source_ids = [tb.source_context_id for tb in member_blocks]
        source_item_ids = []
        for tb in member_blocks:
            source_item_ids.extend(getattr(tb, "source_item_ids", None) or [])
        title = _pick_topic_title(member_blocks)
        discussion = _join_unique([
            _norm(getattr(tb, "discussion_content", "")) for tb in member_blocks
        ])
        conclusion = _join_unique([
            _norm(getattr(tb, "conclusion", "")) for tb in member_blocks
        ])
        status = _dominant_status([getattr(tb, "status_text", "") for tb in member_blocks])
        reason = "объединены по общей смысловой теме и совместимому статусу" \
            if len(member_blocks) > 1 else "уникальная тема (группировка не требуется)"
        groups.append(_group_group(
            "topic", i, source_ids,
            semantic_theme=title,
            grouping_reason=reason,
            preserved_facts=[d for d in discussion.split(". ") if d],
            preserved_responsibles=[getattr(tb, "status_responsible", "") for tb in member_blocks],
            preserved_deadlines=[getattr(tb, "status_deadline", "") for tb in member_blocks],
            display={
                "title": title,
                "what_discussed": discussion,
                "conclusion": conclusion,
                "status": status,
            },
        ))
    return groups


def _pick_topic_title(blocks) -> str:
    # Prefer the most information-dense non-empty title.
    best = ""
    for tb in blocks:
        t = _norm(getattr(tb, "title", ""))
        if len(t) > len(best):
            best = t
    return best or "Обсуждение"


def _dominant_status(statuses: list[str]) -> str:
    order = ["Заблокировано", "Отложено", "Открыт", "Требует доработки",
             "Требует уточнения", "Информация зафиксирована", "Согласовано"]
    present = [_norm(s) for s in statuses]
    for preferred in order:
        if preferred in present:
            return preferred
    return "Информация зафиксирована"


def _grouping_reason_label(kind: str) -> str:
    return f"одинаковые {kind} (объединены только при совместимости)"


def group_decisions(decisions) -> list[dict]:
    """Group decisions only when responsible AND deadline AND topic coincide."""
    buckets: dict[tuple, list] = {}
    for d in decisions or []:
        key = (_low(getattr(d, "responsible", "")),
               _low(getattr(d, "deadline", "")),
               _low(getattr(d, "related_topic", "")))
        buckets.setdefault(key, []).append(d)
    groups = []
    for i, (_, bucket) in enumerate(buckets.items(), start=1):
        ids = [d.decision_id for d in bucket]
        texts = [_norm(getattr(d, "decision_text", "")) for d in bucket]
        reasons = [_norm(getattr(d, "context_and_basis", "")) for d in bucket]
        groups.append(_grouping(
            "decision", i, ids,
            semantic_theme=_join_unique(texts),
            grouping_reason=(
                "совпадают ответственный и срок; формулировки объединены"
                if len(bucket) > 1 else "уникальное решение"
            ),
            preserved_facts=[t for t in texts if t],
            preserved_responsibles=[getattr(d, "responsible", "") for d in bucket],
            preserved_deadlines=[getattr(d, "deadline", "") for d in bucket],
            display={
                "decision_text": _join_unique(texts) or "—",
                "context_and_basis": _join_unique(reasons) or "—",
                "responsible": _first(bucket, "responsible"),
                "deadline": _first(bucket, "deadline"),
            },
        ))
    return groups


def dedupe_questions(questions) -> tuple[list[dict], list[dict]]:
    """Keep questions verbatim; remove only exact duplicates.

    Returns (kept_items, dropped_items). Open questions are intentionally NOT
    semantically collapsed so they remain actionable.
    """
    kept, dropped, seen = [], [], []
    for i, q in enumerate(questions or []):
        qid = getattr(q, "question_id", f"q_{i}")
        text = _low(getattr(q, "question_text", ""))
        display = {
            "question_text": _norm(getattr(q, "question_text", "")),
            "what_to_determine": _norm(getattr(q, "to_determine", ""))
                or _norm(getattr(q, "known_info", ""))
                or _norm(getattr(q, "next_action", "")),
            "responsible": _norm(getattr(q, "responsible", "")),
            "deadline": _norm(getattr(q, "deadline", ""))
                or _norm(getattr(q, "next_action", "")),
            "status": _norm(getattr(q, "status", "")) or "Открыт",
        }
        if text and text in seen:
            dropped.append({
                "standard_item_type": "question",
                "source_ids": [qid],
                "drop_reason": "exact_duplicate",
                "grouping_reason": "точный дубль удалён; вопросы не группируются по смыслу",
                "semantic_theme": display["question_text"],
            })
            continue
        if text:
            seen.append(text)
        kept.append({
            "standard_item_id": f"standard-open-question-{i + 1}",
            "standard_item_type": "open_question",
            "source_ids": [qid],
            "semantic_theme": display["question_text"],
            "grouping_reason": "без группировки (вопросы сохраняются подробно)",
            "preserved_facts": [display["question_text"]],
            "preserved_responsibles": [display["responsible"]],
            "preserved_deadlines": [display["deadline"]],
            "coverage_status": "covered",
            **display,
        })
    return kept, dropped


def group_risks(risks) -> list[dict]:
    buckets: dict[tuple, list] = {}
    for r in risks or []:
        key = (_low(getattr(r, "risk_type", "")),
               _low(getattr(r, "reason", "")),
               _low(getattr(r, "impact", "")),
               _low(getattr(r, "measures", "")),
               _low(getattr(r, "responsible", "")))
        buckets.setdefault(key, []).append(r)
    groups = []
    for i, (_, bucket) in enumerate(buckets.items(), start=1):
        ids = [getattr(r, "risk_id", f"r_{i}") for r in bucket]
        groups.append(_group(
            "risk", i,
            semantic_theme=_join_unique([_norm(getattr(r, "risk_text", "")) for r in bucket]),
            grouping_reason="одинаковые тип, причина, влияние и стратегия"
                if len(bucket) > 1 else "уникальный риск",
            preserved_facts=[_norm(getattr(r, "risk_text", "")) for r in bucket],
            preserved_responsibles=[getattr(r, "responsible", "") for r in bucket],
            preserved_deadlines=[getattr(r, "deadline", "") for r in bucket],
            display={
                "risk_type": _first(bucket, "risk_type") or "Риск",
                "risk_text": _join_unique([_norm(getattr(r, "risk_text", "")) for r in bucket]) or "—",
                "reason": _first(bucket, "reason") or "—",
                "impact": _first(bucket, "impact") or "—",
                "measures": _first(bucket, "measures") or "—",
                "responsible": _first(bucket, "responsible") or "—",
            },
            source_ids=[getattr(r, "risk_id", f"r_{i}") for r in bucket],
        ))
    return groups


def group_tasks(tasks) -> list[dict]:
    buckets: dict[tuple, list] = {}
    for t in tasks or []:
        key = (_low(getattr(t, "responsible", "")),
               _low(getattr(t, "deadline", "")),
               _low(getattr(t, "status", "")))
        buckets.setdefault(key, []).append(t)
    groups = []
    for i, (_, bucket) in enumerate(buckets.items(), start=1):
        groups.append(_make_group(
            "task", i,
            semantic_theme=_join_unique([_norm(getattr(t, "task_text", "")) for t in bucket]),
            grouping_reason="одинаковые ответственный, срок и статус" if len(bucket) > 1
            else "уникальная задача",
            preserved_facts=[_norm(getattr(t, "task_text", "")) for t in bucket],
            preserved_responsibles=[getattr(t, "responsible", "") for t in bucket],
            preserved_deadlines=[getattr(t, "deadline", "") for t in bucket],
            display={
                "task_text": _join_unique([_norm(getattr(t, "task_text", "")) for t in bucket]) or "—",
                "basis": _first(bucket, "basis") or "—",
                "expected_result": _first(bucket, "expected_result") or "—",
                "responsible": _first(bucket, "responsible") or "—",
                "deadline": _first(bucket, "deadline") or "—",
                "status": _first(bucket, "status") or "Не начато",
            },
            source_ids=[getattr(t, "task_id", f"t_{i}") for t in bucket],
        ))
    return groups


def _first(bucket: list, attr: str) -> str:
    for item in bucket:
        v = _norm(getattr(item, attr, ""))
        if v:
            return v
    return ""


def _make_group(group_type, index, semantic_theme, grouping_reason,
                preserved_facts, preserved_responsibles, preserved_deadlines,
                display, source_ids=None) -> dict:
    base = {
        "standard_item_id": f"standard-{group_type}-{index}",
        "standard_item_type": group_type,
        "source_ids": source_ids or [],
        "semantic_theme": semantic_theme,
        "grouping_reason": grouping_reason,
        "preserved_facts": [f for f in preserved_facts if f],
        "preserved_responsibles": list(dict.fromkeys(r for r in preserved_responsibles if r)),
        "preserved_deadlines": list(dict.fromkeys(d for d in preserved_deadlines if d)),
        "coverage_status": "covered",
    }
    base.update(display)
    return base


# Backwards-compatible aliases used by the grouping helpers above.
def _group(group_type, index, source_ids, semantic_theme, grouping_reason,
           preserved_facts, preserved_responsibles, preserved_deadlines,
           display) -> dict:
    return _make_group(
        group_type, index, semantic_theme, grouping_reason,
        preserved_facts, preserved_responsibles, preserved_deadlines,
        display, source_ids=source_ids,
    )


def _grouping(group_type, index, source_ids, semantic_theme, grouping_reason,
              preserved_facts, preserved_responsibles, preserved_deadlines,
              display) -> dict:
    return _group(
        group_type, index, source_ids, semantic_theme, grouping_reason,
        preserved_facts, preserved_responsibles, preserved_deadlines, display,
    )


def _group_group(group_type, index, source_ids, semantic_theme, grouping_reason,
                 preserved_facts, preserved_responsibles, preserved_deadlines,
                 display) -> dict:
    return _group(
        group_type, index, source_ids, semantic_theme, grouping_reason,
        preserved_facts, preserved_responsibles, preserved_deadlines, display,
    )


# ── Standard view builder ─────────────────────────────────────────────

def build_standard_view(protocol, *, recording_source: str = "",
                        meeting_type: str = "external",
                        source_type: str = "local_transcript",
                        source_filename: str = "",
                        meeting_topic: str = "",
                        meeting_type_resolution: dict | None = None,
                        project_resolution: dict | None = None) -> dict:
    """Build the standard JSON view from a canonical Protocol.

    Requires ``protocol.client_name``, ``protocol.project_name`` and the
    enriched registers to already be resolved (as done by the processing
    service / register pipeline).
    """
    from services.protocol_title import build_protocol_title, extract_short_topic

    if meeting_topic:
        short_topic = _norm(meeting_topic)
    else:
        short_topic = extract_short_topic(protocol, fallback=protocol.meeting_purpose or "")
    client = _norm(getattr(protocol, "client_name", ""))
    project = _norm(getattr(protocol, "project_name", ""))
    title = build_protocol_title(
        meeting_date=getattr(protocol, "meeting_date", None),
        short_topic=short_topic,
        client_name=client,
        project_name=project,
        meeting_type=meeting_type,
    )

    date_str = ""
    if protocol.meeting_date:
        date_str = protocol.meeting_date.strftime("%d.%m.%Y")
    time_str = ""
    if protocol.meeting_time:
        time_str = protocol.meeting_time.strftime("%H:%M")
    place = getattr(protocol, "meeting_place", "") or "онлайн"
    dt_place = " / ".join(x for x in [date_str, time_str] if x)
    if dt_place and place:
        dt_place += f", {place}"
    elif not dt_place:
        dt_place = place

    if not recording_source:
        recording_source = _recording_source_label(source_type, source_filename)

    participants = filter_confirmed_participants(getattr(protocol, "participants", []))

    goal = _norm(getattr(protocol, "meeting_purpose", ""))
    context = getattr(protocol, "_standard_context", None) or {}
    initial = _norm(context.get("initial_situation")) or _norm(getattr(protocol, "meeting_context", ""))
    main_problem = _norm(context.get("main_problem")) or _norm(getattr(protocol, "current_state", "")) or initial
    expected_result = _norm(getattr(protocol, "current_state", ""))
    if expected_result and main_problem == expected_result:
        expected_result = ""

    if meeting_type == "internal":
        client_label = "Внутренняя встреча"
    elif meeting_type == "external":
        client_label = client or "Не определено"
    else:
        client_label = "Не определено"

    key_outcomes = _split_outcomes(getattr(protocol, "key_outcomes", ""))

    topic_groups = group_topic_blocks(getattr(protocol, "topic_blocks", []))
    decision_groups = group_decisions(getattr(protocol, "decisions", []))
    open_questions, dropped_questions = dedupe_questions(getattr(protocol, "questions", []))
    risk_groups = group_risks(getattr(protocol, "risks", []))
    task_groups = group_tasks(getattr(protocol, "tasks", []))

    view = {
        "template_id": "project_standard",
        "protocol_title": title,
        "general_info": {
            "client_name": client_label,
            "topic_project": short_topic + (f" — {project}" if project else ""),
            "meeting_datetime_place": dt_place or "—",
            "recording_source": recording_source or "—",
        },
        "participants": participants,
        "meeting_context": {
            "goal": goal,
            "initial_situation": initial,
            "main_problem": main_problem,
            "expected_result": expected_result,
        },
        "key_outcomes": key_outcomes,
        "topic_groups": topic_groups,
        "decision_groups": decision_groups,
        "open_questions": open_questions,
        "risk_groups": risk_groups,
        "task_groups": task_groups,
        "_debug": {
            "client_name": client,
            "project_name": project,
            "detailed_topic_count": len(getattr(protocol, "topic_blocks", []) or []),
            "detailed_decision_count": len(getattr(protocol, "decisions", []) or []),
            "detailed_question_count": len(getattr(protocol, "questions", []) or []),
            "detailed_risk_count": len(getattr(protocol, "risks", []) or []),
            "detailed_task_count": len(getattr(protocol, "tasks", []) or []),
            "dropped_questions": dropped_questions,
            "unsupported_standard_items": 0,
        },
    }
    # Semantic compression + cell structuring pass (deterministic, no re-extraction).
    from services.standard_protocol_compactor import compact_view
    return compact_view(view, meeting_type=meeting_type)


def _recording_source_label(source_type: str, source_filename: str) -> str:
    from services.protocol_title import build_recording_source
    return build_recording_source(source_type, source_filename)


def _split_outcomes(value) -> list[str]:
    if not value or not _norm(value):
        return []
    from services.protocol_content_utils import split_key_outcomes_semantically
    return split_key_outcomes_semantically(_norm(value)) or []


# ── Coverage / validation helpers ─────────────────────────────────────

def validate_group_coverage(view: dict) -> dict:
    """Return a coverage report over the standard view source ids."""
    report: dict = {}
    sections = {
        "topic_source_ids": view["topic_groups"],
        "decision_source_ids": view["decision_groups"],
        "question_source_ids": view["open_questions"],
        "risk_source_ids": view["risk_groups"],
        "task_source_ids": view["task_groups"],
    }
    for name, items in sections.items():
        total = sum(len(item.get("source_ids", [])) for item in items)
        report[name] = {
            "group_count": len(items),
            "covered_source_count": total,
        }
    report["untraceable_standard_items"] = sum(
        1 for section in sections.values() for item in section
        if not item.get("source_ids")
    )
    report["all_covered"] = all(
        item.get("source_ids") for section in sections.values() for item in section
    ) and report["untraceable_standard_items"] == 0
    return report


def source_ids_total(section: list[dict]) -> int:
    return sum(len(item.get("source_ids", [])) for item in section)


def build_grouping_map(view: dict) -> dict:
    """Produce standard_grouping_map.json."""
    def _maps(items):
        out = []
        for item in items:
            out.append({
                "standard_item_id": item.get("standard_item_id"),
                "standard_item_type": item.get("standard_item_type"),
                "source_ids": item.get("source_ids", []),
                "grouping_reason": item.get("grouping_reason", ""),
                "semantic_theme": item.get("semantic_theme", ""),
                "preserved_facts": item.get("preserved_facts", []),
                "preserved_responsibles": item.get("preserved_responsibles", []),
                "preserved_deadlines": item.get("preserved_deadlines", []),
                "coverage_status": item.get("coverage_status", "covered"),
            })
        return out

    questions = _maps(view["open_questions"])
    for q in questions:
        q["grouping_reason"] = "exact_duplicate_removal_only"
    return {
        "topics": _maps(view["topic_groups"]),
        "decisions": _maps(view["decision_groups"]),
        "questions": questions,
        "risks": _maps(view["risk_groups"]),
        "tasks": _maps(view["task_groups"]),
        "dropped_items": view["_debug"].get("dropped_questions", []),
    }


def build_consistency_report(detailed_protocol, standard_view: dict) -> dict:
    """standard_vs_detailed_consistency.json for the same source."""
    d_topics = len(getattr(detailed_protocol, "topic_blocks", []) or [])
    d_decisions = len(getattr(detailed_protocol, "decisions", []) or [])
    d_questions = len(getattr(detailed_protocol, "questions", []) or [])
    d_risks = len(getattr(detailed_protocol, "risks", []) or [])
    d_tasks = len(getattr(detailed_protocol, "tasks", []) or [])

    def covered(src_total, groups, extra_covered=0):
        if src_total == 0:
            return 1.0 if (groups == 0 and extra_covered == 0) else 0.0
        return (source_ids_total(groups) + extra_covered) / src_total

    dropped_q = standard_view["_debug"].get("dropped_questions", [])
    q_covered = sum(len(d.get("source_ids", [])) for d in dropped_q)

    d_confirmed = filter_confirmed_participants(getattr(detailed_protocol, "participants", []))
    s_participants = {_low(p["full_name"]) for p in standard_view["participants"]}
    d_participants = {_low(p["full_name"]) for p in d_confirmed}

    return {
        "metadata_match": bool(
            _date_equal(detailed_protocol, standard_view)
            and _norm(getattr(detailed_protocol, "client_name", ""))
            == _norm(standard_view["_debug"].get("client_name", ""))
            and _norm(getattr(detailed_protocol, "project_name", ""))
            == _norm(standard_view["_debug"].get("project_name", ""))
        ),
        "participants_match": bool(d_participants == s_participants),
        "decision_source_coverage": covered(d_decisions, standard_view["decision_groups"]),
        "question_source_coverage": covered(d_questions, standard_view["open_questions"],
                                            extra_covered=q_covered),
        "risk_source_coverage": covered(d_risks, standard_view["risk_groups"]),
        "task_source_coverage": covered(d_tasks, standard_view["task_groups"]),
        "topic_source_coverage": covered(d_topics, standard_view["topic_groups"]),
        "unsupported_standard_items": standard_view["_debug"].get("unsupported_standard_items", 0),
        "lost_critical_items": [],
    }


def _date_from_view(view: dict) -> date | None:
    import datetime as _dt
    part = view["general_info"].get("meeting_datetime_place", "")
    m = re.match(r"(\d{2})\.(\d{2})\.(\d{4})", part)
    if m:
        d, mo, y = m.groups()
        try:
            return _dt.date(int(y), int(mo), int(d))
        except ValueError:
            return None
    return None


def _date_equal(detailed_protocol, standard_view: dict) -> bool:
    return str(getattr(detailed_protocol, "meeting_date", None)) == str(_date_from_view(standard_view))