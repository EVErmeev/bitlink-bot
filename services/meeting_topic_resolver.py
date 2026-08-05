"""Meeting-topic resolver: a short subject noun-phrase for the standard title.

The meeting purpose is NOT used directly as the topic. Priority:
  1. explicit ``meeting_topic`` (metadata);
  2. a short title derived from the source name/title;
  3. LLM short-topic extraction;
  4. first thematic topic block title;
  5. ``meeting_purpose`` only after conversion into a short subject phrase.
"""
from __future__ import annotations

import re

_PLACEHOLDERS = {"не определено", "неизвестно", "не указано", "нет", "", "без темы"}
_DATE_RE = re.compile(r"\b\d{1,2}\.\d{2}\.\d{2,4}\b")
_TECH_RE = re.compile(r"(local-[0-9a-f]{8,})|(_transcript\.txt)|(\.(txt|doc|docx))\b", re.I)


def _norm(value) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _valid(value: str) -> bool:
    v = _norm(value)
    if not v or v.lower() in _PLACEHOLDERS:
        return False
    if _TECH_RE.search(v):
        return False
    if "цель встречи" in v.lower() or "целью встречи" in v.lower():
        return False
    return True


def _shorten(value: str, max_len: int = 120) -> str:
    v = _norm(value)
    if len(v) <= max_len:
        return v
    cut = v.find(". ")
    if 0 < cut <= max_len:
        v = v[:cut].strip(" .")
    if len(v) > max_len:
        v = v[: max_len - 1].rstrip() + "…"
    return v


def _from_source(filename: str, title: str) -> str:
    """Derive a topic noun-phrase from the source name/title.

    Handles the control shape:
        ... 31.07.2026. УралДронЗавод + Первый БИТ — демонстрация процессов блока «Производство»
    → "Демонстрация процессов блока «Производство»"
    """
    text = _norm(title or filename)
    # cut any technical extension
    text = _TECH_RE.sub("", text).strip(" .-_")
    # remove a date token
    text = _DATE_RE.sub("", text).strip(" .-–—")
    # remove leading "Протокол ..." / "Протокол встречи ..."
    text = re.sub(r"^\s*Протокол(:\s*(встречи|внутренней\s+встречи|стандартной\s+встречи))?\s*", "", text)
    # take the part after a separator "—", "-", ":"
    for sep in (" — ", "—", " – ", " - "):
        if sep in text:
            text = text.split(sep, 1)[-1].strip()
            break
    # drop a leading client "X + Первый БИТ" segment
    m = re.match(r"^(.+?)(?:\s*\+\s*)(первый\s*бит|первыйбит)\b", text, re.I)
    if m:
        text = text[m.end():].strip(" .-–—")
    else:
        m2 = re.match(r"^(Первый\s*Бит|ПервыйБит)\s*\+\s*(.+)$", text, re.I)
        if m2:
            text = m2.group(2).strip()
    return _shorten(_capitalize(text))


def _capitalize(value: str) -> str:
    v = _norm(value)
    if not v:
        return v
    return v[0].upper() + v[1:]


def resolve_meeting_topic(
    meeting_topic: str = "",
    source_filename: str = "",
    source_title: str = "",
    topic_blocks: list | None = None,
    meeting_purpose: str = "",
    llm=None,
) -> str:
    """Return a short meeting topic (noun phrase, <=120 chars)."""
    if _valid(meeting_topic):
        return _shorten(meeting_topic)

    derived = _from_source(source_filename, source_title)
    if _valid(derived):
        return derived

    if llm is not None:
        try:
            topic = _llm_short_topic(llm, meeting_purpose, source_title,
                                     topic_blocks or [])
            if _valid(topic):
                return _shorten(topic)
        except Exception:
            pass

    for tb in (topic_blocks or []):
        title = _norm(getattr(tb, "title", "")) if not isinstance(tb, dict) else _norm(tb.get("title", ""))
        if _valid(title):
            return _shorten(title)

    if _valid(meeting_purpose):
        return _shorten(meeting_purpose)

    return "Анализ прошедшей встречи"


def _llm_short_topic(llm, purpose: str, title: str, blocks: list) -> str:
    schema = {
        "type": "object",
        "properties": {"topic": {"type": "string"}},
        "required": ["topic"],
    }
    block_titles = []
    for tb in blocks[:8]:
        t = _norm(getattr(tb, "title", None)) if not isinstance(tb, dict) else _norm(tb.get("title", ""))
        if t:
            block_titles.append(t)
    user = (
        "Составь короткую предметную тему встречи (именная конструкция, 4-12 слов, без даты, "
        "города, длительности, имени файла и без фразы «Цель встречи —»). Не повторяй цель. "
        f"Название: {title}\nЦель: {meeting_purpose}\nТемы: {'; '.join(block_titles)}"
    )
    data, _ = llm.generate_json(
        system_prompt="Ты определяешь краткую тему протокола встречи.",
        user_prompt=user,
        json_schema=schema,
        temperature=0.0,
        max_retries=1,
    )
    return (data or {}).get("topic", "")