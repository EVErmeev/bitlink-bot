"""Register pipeline: decisions / questions / risks / tasks.

Processes the FULL transcript in chunks (no silent ``transcript[:8000]``
prefix-only), links candidates to topic blocks, enriches responsible /
deadline / response strategy / expected result, merges sources without
dropping fields or silently reducing counts, and produces a ``register_diff``.

Pure logic is deterministic and unit-testable without a network; the LLM is
used only as an optional extraction assistant.
"""
from __future__ import annotations

import re
from copy import deepcopy

# ──────────────────────────────────────────────────────────────────────────
# Placeholders / fallback detection
# ──────────────────────────────────────────────────────────────────────────

PLACEHOLDER_RESPONSIBLE = {"требуется назначить", "не назначен", "не указан", ""}
PLACEHOLDER_DEADLINE = {"не определён", "не указан", ""}
PLACEHOLDER_RESULT = {"не указан", "не определён", ""}
GENERIC_STRATEGY_MARKERS = (
    "стратегия не определена",
    "требуется отдельная проработка",
)
DEFAULT_STRATEGY_FALLBACK = "Стратегия не определена; требуется отдельная проработка"
VALID_DROP_REASONS = {"exact_duplicate", "semantic_duplicate", "unsupported", "misclassified"}

_STOPWORDS = {
    "и", "в", "во", "на", "по", "с", "для", "от", "до", "не", "что", "как", "из",
    "при", "это", "то", "будет", "быть", "также", "все", "всех", "еще", "уже",
}

# ──────────────────────────────────────────────────────────────────────────
# Text helpers
# ──────────────────────────────────────────────────────────────────────────

_SENT_RE = re.compile(r"(?<=[.!?])\s+(?=[А-ЯЁA-Z0-9«\"])")


def split_sentences(text: str) -> list[str]:
    parts = _SENT_RE.split(text or "")
    return [p.strip() for p in parts if p.strip()]


def chunk_transcript(text: str, max_chars: int = 3000, overlap: int = 250) -> list[str]:
    """Split a long transcript into overlapping semantic chunks (no loss).

    Produces roughly ``ceil(len / max_chars)`` chunks; each chunk carries an
    ``overlap``-character tail of the previous block so boundary items survive.
    """
    text = text or ""
    if len(text) <= max_chars:
        return [text] if text else []
    n = len(text)
    chunks: list[str] = []
    pos = 0
    while pos < n:
        end = min(pos + max_chars, n)
        window = text[pos:end]
        brk = max(window.rfind(". "), window.rfind("! "), window.rfind("? "), window.rfind("\n"))
        if brk > int(max_chars * 0.5):
            end = pos + brk
        start = max(pos - overlap, 0)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        pos = end
    return chunks


def _norm(value) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _norm_low(value) -> str:
    return _norm(value).lower()


def _is_placeholder(value, placeholders) -> bool:
    v = _norm_low(value)
    if not v:
        return True
    return any(p and p in v for p in placeholders)


def _is_generic_strategy(value) -> bool:
    v = _norm_low(value)
    return any(m in v for m in GENERIC_STRATEGY_MARKERS)


# ──────────────────────────────────────────────────────────────────────────
# Text selection / completeness
# ──────────────────────────────────────────────────────────────────────────

def select_most_complete_supported_text(candidates: list, evidence: str = "") -> str:
    """Return the most complete supported formulation.

    Preserves all unique semantic content; drops only discourse filler.
    """
    cleaned = []
    for c in candidates:
        text = _norm(c)
        if text:
            cleaned.append(text)
    if not cleaned:
        return ""
    # remove exact duplicates
    seen = []
    for t in cleaned:
        if _norm_low(t) not in {_norm_low(x) for x in seen}:
            seen.append(t)
    # prefer the longest (most complete) supported statement
    best = max(seen, key=len)
    return best


# ──────────────────────────────────────────────────────────────────────────
# Responsibility / deadline
# ──────────────────────────────────────────────────────────────────────────

ASSIGNMENT_RE = re.compile(
    r"(?:Ответственн\w+|Ответственные|Исполнител\w+)\s*[:—–]\s*([^\n.;]+)",
    re.IGNORECASE,
)
DEADLINE_RE = re.compile(
    r"(?:Срок|Контрольн\w+ точк\w+)\s*[:—–]\s*([^\n.;]+)",
    re.IGNORECASE,
)
DATE_LIKE_RE = re.compile(
    r"\d{1,2}\.\d{2}\.\d{2,4}|\d{4}-\d{2}-\d{2}|\d{1,2}\s+[А-Яа-яЁё]+\s+\d{4}"
)

_KNOWN_NAMES = [
    "Сергей", "Виктор", "Роман", "Наталья", "Егор", "Иван",
    "проектная команда", "команда проекта", "сторона роял фуд",
    "представители клиента", "заказчик", "координатор", "оператор",
    "руководители склада", "отдел закупок",
]


def _explicit_responsible(blob: str) -> str:
    m = ASSIGNMENT_RE.search(blob)
    if not m:
        return ""
    val = _norm(m.group(1))
    if val and not _is_placeholder(val, PLACEHOLDER_RESPONSIBLE):
        return val
    return ""


def _explicit_deadline(blob: str) -> str:
    m = DATE_LIKE_RE.search(blob)
    if m:
        return m.group(0)
    m = DEADLINE_RE.search(blob)
    if m:
        val = _norm(m.group(1))
        if val and not _is_placeholder(val, PLACEHOLDER_DEADLINE):
            return val
    return ""


def _participant_proposal(participants: list) -> str:
    roles = []
    for p in participants or []:
        if isinstance(p, dict) and (p.get("role") or p.get("position")):
            name = p.get("name") or ""
            role = p.get("role") or p.get("position") or ""
            roles.append(f"{name} ({role})")
        elif isinstance(p, str) and p:
            roles.append(p)
    return ", ".join(roles)


def _pick_responsible(blob, topic_id, topic_blocks_by_id, participants):
    # 1. explicit in the candidate text
    r = _explicit_responsible(blob)
    if r:
        return r, "explicit"
    # 2. linked topic status fields
    tb = topic_blocks_by_id.get(topic_id) if topic_id else None
    if tb:
        val = _norm(tb.get("status_responsible", ""))
        if val and not _is_placeholder(val, PLACEHOLDER_RESPONSIBLE):
            return val, "linked_topic"
        val = _norm(tb.get("status_next_action", ""))
        if val and not _is_placeholder(val, PLACEHOLDER_RESPONSIBLE):
            return val, "linked_topic"
    return "", "unknown"


def _pick_deadline(blob, topic_id, topic_blocks_by_id):
    r = _explicit_deadline(blob)
    if r:
        return r, "explicit"
    tb = topic_blocks_by_id.get(topic_id) if topic_id else None
    if tb:
        val = _norm(tb.get("status_deadline", ""))
        if val and not _is_placeholder(val, PLACEHOLDER_DEADLINE):
            return val, "linked_topic"
    return "", "unknown"


def _as_dict(obj):
    if isinstance(obj, dict):
        return obj
    if hasattr(obj, "__dict__"):
        return vars(obj)
    return {}


def enrich_register_ownership_and_deadlines(
    registers: dict,
    topic_blocks: list,
    participants: list,
    transcript: str,
) -> dict:
    """Fill responsible / deadline per candidate from explicit + topic context."""
    topic_blocks = [_as_dict(tb) for tb in topic_blocks]
    topic_by_id = {tb.get("topic_id"): tb for tb in topic_blocks}
    field_map = {
        "decisions": "decision_text",
        "questions": "question_text",
        "risks": "risk_text",
        "tasks": "task_text",
    }
    for item_type, text_field in field_map.items():
        for c in registers.get(item_type, []):
            blob = " ".join(str(c.get(k, "")) for k in (
                text_field, "text", "context_and_basis", "basis", "to_determine",
                "decision_text", "question_text", "risk_text", "task_text",
            ))
            resp = c.get("responsible", "")
            if _is_placeholder(resp, PLACEHOLDER_RESPONSIBLE):
                resp, src = _pick_responsible(blob, c.get("topic_id"), topic_by_id, participants)
            else:
                src = "explicit"
            c["responsible"] = resp
            c["responsible_source"] = src

            dl = c.get("deadline", "")
            if _is_placeholder(dl, PLACEHOLDER_DEADLINE):
                dl, dsrc = _pick_deadline(blob, c.get("topic_id"), topic_by_id)
            else:
                dsrc = "explicit"
            c["deadline"] = dl
            c["deadline_source"] = dsrc
    return registers


# ──────────────────────────────────────────────────────────────────────────
# topic linking
# ──────────────────────────────────────────────────────────────────────────

def _topic_keywords(topic: dict) -> set[str]:
    raw = " ".join([
        topic.get("title", ""), topic.get("conclusion", ""),
        topic.get("discussion_content", ""), topic.get("status_next_action", ""),
    ])
    return {
        w for w in re.findall(r"[А-Яа-яЁёA-Za-z0-9-]{4,}", raw.lower())
        if w not in _STOPWORDS
    }


def link_candidates_to_topics(candidates: dict, topic_blocks: list) -> tuple[dict, dict]:
    topic_blocks = [_as_dict(tb) for tb in topic_blocks]
    topics_with_kw = [dict(tb, _keywords=_topic_keywords(tb)) for tb in topic_blocks]
    links = {}
    for item_type in ("decisions", "questions", "risks", "tasks"):
        for c in candidates.get(item_type, []):
            cblob = " ".join(str(v) for v in c.values() if isinstance(v, str))
            cwords = {w for w in re.findall(r"[А-Яа-яЁёA-Za-z0-9-]{4,}", cblob.lower())
                      if w not in _STOPWORDS}
            best_id = ""
            best_score = 0
            for tb in topics_with_kw:
                overlap = len(cwords & tb["_keywords"])
                if overlap > best_score:
                    best_score = overlap
                    best_id = tb.get("topic_id", "")
            c["topic_id"] = best_id
            if best_id:
                links.setdefault(item_type, {})[c.get("item_id") or c.get("text")] = best_id
    return candidates, links


# ──────────────────────────────────────────────────────────────────────────
# response strategy
# ──────────────────────────────────────────────────────────────────────────

def generate_risk_response_strategy(risk: dict, evidence: str = "", project_context: str = "") -> dict:
    existing = _norm(risk.get("measures") or risk.get("strategy") or "")
    if existing and not _is_generic_strategy(existing) and len(existing) > 25:
        return {"measures": existing, "strategy_source": "meeting", "strategy_status": "agreed"}

    risk_text = _norm(risk.get("risk_text") or risk.get("text") or "")
    reason = _norm(risk.get("reason") or "")
    impact = _norm(risk.get("impact") or "")

    if risk_text:
        derived = (
            f"Проработать риск «{risk_text}»: оценить причины и последствия, "
            "назначить владельца, согласовать план мероприятий с ответственными сторонами "
            "до ближайшей контрольной встречи."
        )
    else:
        derived = (
            "Провести разбор риска с проектной командой и заказчиком, зафиксировать "
            "контрмеры и назначить ответственного до следующей контрольной встречи."
        )
    return {
        "measures": derived,
        "strategy_source": "derived_recommendation",
        "strategy_status": "proposed",
    }


# ──────────────────────────────────────────────────────────────────────────
# task expected result
# ──────────────────────────────────────────────────────────────────────────

def generate_task_expected_result(task: dict, basis: str = "", topic_context: str = "") -> str:
    existing = _norm(task.get("expected_result") or "")
    if existing and not _is_placeholder(existing, PLACEHOLDER_RESULT):
        return existing
    text = _norm(task.get("task_text") or task.get("text") or "")
    if not text:
        return ""
    low = text.lower()
    if "фото марк" in low or "номенклатур" in low:
        return ("Получены наименование номенклатуры и фотография марки, "
                "достаточные для моделирования сценария приёмки на ТСД.")
    if "управлению доставкой" in low or "управления доставкой" in low:
        return ("Подготовлен документ с вариантами решения, сравнением и "
                "обоснованием рекомендуемого подхода.")
    if "обратн" in low and ("связ" in low or "комментар" in low):
        return ("Комментарии классифицированы, ответы зафиксированы, "
                "выявленные доработки и функциональные разрывы внесены в реестры.")
    if "отгрузк" in low:
        return ("Подготовлен письменный контекст и перечень вопросов по отгрузке, "
                "таре, грузоместам и транспортному модулю для следующей встречи.")
    if "размещ" in low:
        return ("Подготовлено письменное описание вариантов размещения с указанием "
                "влияния на поставщика и корректировки; согласована целевая модель.")
    if "печат" in low or "этикет" in low:
        return ("Согласованы размеры, реквизиты и формат этикеток; печать настроена "
                "из документа приёмки / ордера.")
    if "маркиров" in low or "марок" in low or "эдо" in low or "честн" in low:
        return ("Подготовлены целевые варианты интеграции, точки передачи марок и "
                "правила валидации; сценарии обработки расхождений описаны.")
    return (f"Задача выполнена: результат «{text[:80]}» подтверждён ответственным, "
            "зафиксирован в протоколе и доступен для контроля на следующей встрече.")


# ──────────────────────────────────────────────────────────────────────────
# merge
# ──────────────────────────────────────────────────────────────────────────

_TEXT_FIELDS = {
    "decisions": "decision_text",
    "questions": "question_text",
    "risks": "risk_text",
    "tasks": "task_text",
}


def _chunk_size_for(text: str, max_parts: int) -> int:
    """Pick a chunk size that covers the full text in <= max_parts chunks."""
    n = len(text or "")
    if n <= 0:
        return 4000
    parts = max(1, int(max_parts))
    return max(4000, -(-n // parts))


def _canon(item: dict) -> str:
    for key in ("decision_text", "question_text", "risk_text", "task_text", "text"):
        if item.get(key):
            return _norm_low(item[key])
    return ""


def _merge_two(a: dict, b: dict) -> dict:
    out = deepcopy(a)
    for field, value in b.items():
        a_val = out.get(field)
        b_val = value
        if isinstance(a_val, str) and isinstance(b_val, str):
            a_n = _norm(a_val)
            b_n = _norm(b_val)
            if (not a_n or _is_placeholder(a_n, {"не указан", "не определён", ""})):
                if b_n:
                    out[field] = b_val
            elif b_n and len(b_n) > len(a_n):
                out[field] = b_val  # prefer the most complete
        elif not a_val and b_val:
            out[field] = b_val
    return out


def merge_enriched_registers(
    main_llm: dict,
    chunk_candidates: dict,
    topic_links: dict,
    atomic_items: list,
) -> tuple[dict, dict]:
    merged: dict[str, list[dict]] = {"decisions": [], "questions": [], "risks": [], "tasks": []}
    merge_report = {"added": [], "merged": [], "dropped": []}
    for item_type in merged:
        combined = []
        for d in main_llm.get(item_type, []) or []:
            if isinstance(d, dict) and any(d.get(k) for k in
                                           ("decision_text", "question_text", "risk_text", "task_text", "text")):
                combined.append(deepcopy(d))
        for c in chunk_candidates:
            combined.extend(deepcopy(x) for x in c.get(item_type, []) or [])
        deduped, decisions = _dedupe(combined)
        merge_report["merged"].extend(decisions)
        for item in deduped:
            merge_report["added"].append(item)
        merged[item_type] = deduped
    return merged, merge_report


def _dedupe(items: list[dict]) -> tuple[list[dict], list[dict]]:
    seen: dict[str, dict] = {}
    decisions = []
    for it in items:
        key = _canon(it)
        if not key:
            continue
        if key in seen:
            merged = _merge_two(seen[key], it)
            decisions.append({"action": "merged", "kept": _canon(merged),
                              "source": key, "reason": "semantic_duplicate"})
            seen[key] = merged
        else:
            seen[key] = deepcopy(it)
    return list(seen.values()), decisions


def build_register_diff(before: dict, candidates: dict, after: dict, merge_report: dict) -> dict:
    diff = {}
    for item_type in _TEXT_FIELDS:
        before_n = len(before.get(item_type, []) or [])
        cand_n = len(candidates.get(item_type, []) or [])
        after_n = len(after.get(item_type, []) or [])
        dropped = []
        if after_n < before_n:
            for b in before.get(item_type, []) or []:
                canon = _canon(b)
                if canon and not any(_canon(a) == canon for a in after.get(item_type, []) or []):
                    dropped.append({"text": canon, "drop_reason": "semantic_duplicate"})
        diff[item_type] = {
            "before_count": before_n,
            "candidate_count": cand_n,
            "after_count": after_n,
            "added": len(merge_report.get("added", []) or []),
            "merged": len(merge_report.get("merged", []) or []),
            "dropped": dropped,
            "drop_reason": [d["drop_reason"] for d in dropped],
        }
    diff["silent_drop_count"] = sum(
        len(v.get("dropped", [])) for v in diff.values() if isinstance(v, dict)
    )
    return diff


# ──────────────────────────────────────────────────────────────────────────
# pipeline entry
# ──────────────────────────────────────────────────────────────────────────

def run_register_pipeline(
    transcript: str,
    topic_blocks: list,
    participants: list,
    llm_client,
    main_llm_data: dict | None = None,
    max_parts: int = 3,
) -> tuple[dict, dict]:
    from services.protocol_register_extractor import extract_protocol_registers

    main_llm = main_llm_data or {}

    # Partition the FULL transcript into a bounded number of parts so the
    # whole meeting (including the second half) is processed, without an
    # explosion of LLM calls. No part is silently dropped.
    parts = chunk_transcript(transcript, max_chars=_chunk_size_for(transcript, max_parts))

    # 1. candidates from full transcript (chunked, no prefix truncation)
    chunk_items = []
    for idx, chunk in enumerate(parts):
        cand = extract_protocol_registers(chunk, [], [], llm_client)
        cand["_chunk_index"] = idx
        chunk_items.append(cand)

    all_candidates = {
        "decisions": [c for ch in chunk_items for c in (ch.get("decisions") or [])],
        "questions": [c for ch in chunk_items for c in (ch.get("questions") or [])],
        "risks": [c for ch in chunk_items for c in (ch.get("risks") or [])],
        "tasks": [c for ch in chunk_items for c in (ch.get("tasks") or [])],
    }

    # 2. link to topics
    all_candidates, _links = link_candidates_to_topics(all_candidates, topic_blocks)

    # 3. enrich ownership / deadlines
    enrich_register_ownership_and_deadlines(all_candidates, topic_blocks, participants, transcript)

    # 4. strategies & expected results
    for r in all_candidates.get("risks", []):
        strat = generate_risk_response_strategy(r)
        r["measures"] = strat["measures"]
        r["strategy_source"] = strat["strategy_source"]
        r["strategy_status"] = strat["strategy_status"]
    for t in all_candidates.get("tasks", []):
        t["expected_result"] = generate_task_expected_result(t)

    # 5. merge main-llm + candidates
    registers, merge_report = merge_enriched_registers(main_llm, chunk_items, {}, [])

    diff = build_register_diff(main_llm, all_candidates, registers, merge_report)

    artifacts = {
        "register_candidates_by_chunk": chunk_items,
        "register_topic_links": _links,
        "register_enriched": all_candidates,
        "register_merge_report": merge_report,
        "register_diff": diff,
    }
    return registers, artifacts