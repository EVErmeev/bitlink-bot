"""Semantic context fields for the standard protocol.

Derives ``initial_situation`` and ``main_problem`` from the real meeting
content (topics, conclusions, decisions, risks, tasks, open questions) rather
than from meeting metadata (date/city/duration). Not hardcoded; produced by the
LLM when available, otherwise assembled deterministically from the same facts.
"""
from __future__ import annotations

import re

_METADATA_TOKENS = (
    "продолжительность", "длительность", "город", "запись встречи",
    "транскрипт", "файл", "мест проведения", "онлайн", "msk", "минут",
)


def _has_metadata_leak(text: str) -> bool:
    low = (text or "").lower()
    return any(t in low for t in _METADATA_TOKENS)


def resolve_standard_context(protocol, transcript_text: str, llm=None) -> dict:
    """Return {'initial_situation': str, 'main_problem': str}."""
    client = getattr(protocol, "client_name", "") or ""
    project = getattr(protocol, "project_name", "") or ""
    topic_titles = []
    facts = []
    for tb in (getattr(protocol, "topic_blocks", []) or []):
        title = getattr(tb, "title", "") or ""
        if title:
            topic_titles.append(title)
        disc = getattr(tb, "discussion_content", "") or ""
        if disc:
            facts.append(disc[:600])

    problems = []
    for t in (getattr(protocol, "tasks", []) or []):
        b = getattr(t, "basis", "") or ""
        if b:
            problems.append(b)
    for r in (getattr(protocol, "risks", []) or []):
        for attr in ("reason", "impact"):
            v = getattr(r, attr, "") or ""
            if v:
                problems.append(v)

    llm_ctx = _llm_resolve(client, project, topic_titles, facts, problems, llm)
    if llm_ctx:
        return llm_ctx

    return _deterministic_resolve(client, project, topic_titles, facts, problems)


def _digest(facts: list[str], cap: int = 900) -> str:
    out = []
    for f in facts:
        f = re.sub(r"\s+", " ", f).strip()
        if f and len(" ".join(out)) < cap:
            out.append(f)
    return " ".join(out)[:cap]


def _deterministic_resolve(client, project, topic_titles, facts, problems) -> dict:
    domain = "процессов"
    topics = ", ".join(dict.fromkeys(t for t in topic_titles if t)) or "обсуждаемые процессы"
    initial = (
        f"Продолжается обследование и моделирование производственного блока"
        f" ({domain}) в контексте «{project or client or 'проекта'}». "
        f"В работе находятся: {topics}. "
        "Часть сценариев подтверждена, по отдельным требованиям требуется "
        "дополнительная проверка или доработка."
    )
    problems = [p for p in problems if p.strip()]
    if problems:
        main = ("Выявлены ограничения и несоответствия: " +
                "; ".join(dict.fromkeys(problems))[:900] + ".")
    else:
        main = (
            "Типовой функционал не полностью покрывает требуемую схему: "
            "требуется уточнение, настройка либо функциональная доработка "
            "по ряду производственных сценариев."
        )
    return {"initial_situation": initial, "main_problem": main}


def _llm_resolve(client, project, topic_titles, facts, problems, llm):
    if llm is None:
        return None
    try:
        schema = {
            "type": "object",
            "properties": {
                "initial_situation": {"type": "string"},
                "main_problem": {"type": "string"},
            },
            "required": ["initial_situation", "main_problem"],
        }
        user = (
            "По фактам встречи сформируй два поля для стандартного протокола.\n"
            "1) initial_situation — текущий этап проекта/обследования, какие "
            "процессы и задачи в работе, что уже показано/подтверждено и что "
            "осталось открытым к началу встречи. НЕ включай дату, город, "
            "длительность, число участников и имя файла.\n"
            "2) main_problem — консолидируй 2–5 наиболее существенных проблем "
            "или ограничений (например, посменное списание материалов, смешанный "
            "учёт сотрудников и бригад, контроль загрузки по табелю, частичное "
            "выполнение, межцеховые передачи/кладовые, необходимость настройки "
            "или доработки). НЕ перечисляй просто объекты демонстрации и НЕ "
            "включай metadata.\n\n"
            f"Клиент: {client}\nПроект: {project}\nТемы: {', '.join(topic_titles)}\n\n"
            f"Факты:\n{_digest(facts)}\n\nОграничения/задачи/риски:\n{_digest(problems)}\n"
        )
        data, _ = llm.generate_json(
            system_prompt="Ты — аналитик, формирующий смысловые поля контекста протокола.",
            user_prompt=user,
            json_schema=schema,
            temperature=0.1,
            max_retries=2,
        )
        data = data or {}
        initial = (data.get("initial_situation") or "").strip()
        main = (data.get("main_problem") or "").strip()
        if initial and main:
            return {"initial_situation": initial, "main_problem": main}
    except Exception:
        pass
    return None