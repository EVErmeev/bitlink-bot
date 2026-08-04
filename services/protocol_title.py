"""Shared protocol title builder.

Used by ``project_standard`` and usable by ``project_detailed`` to produce a
single consistent, contentful document title. The technical source filename is
never placed in the title; it is allowed only in the "recording source" row of
the general info table.
"""
from __future__ import annotations

import re
from datetime import date


PLACEHOLDER_CLIENT = {"", "не определено", "неизвестно", "не указано", "нет"}

# Phrases that never constitute a meaningful topic.
_FORBIDDEN_TOPIC_FRAGMENTS = (
    "рабочая встреча",
    "обсуждение вопросов",
    "встреча с клиентом",
    "проектный протокол встречи 3.0",
    "проектный протокол",
)

# Technical artifacts that must never leak into a title.
_TECHNICAL_RE = re.compile(
    r"(local-[0-9a-f]{8,})|(_transcript\.txt)|(\.(txt|doc|docx|m4v|mp4|mp3|wav|m4a)\b)|"
    r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})",
    re.IGNORECASE,
)


def _norm(value) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _looks_placeholder_topic(value: str) -> bool:
    low = value.lower()
    return (
        not value
        or low in ("не определено", "неизвестно", "не указано", "нет")
        or any(frag in low for frag in _FORBIDDEN_TOPIC_FRAGMENTS)
        or bool(_TECHNICAL_RE.search(value))
    )


def extract_short_topic(protocol, fallback: str = "") -> str:
    """Return a meaningful short topic (<=140 chars) from a canonical Protocol.

    Priority:
      1. meeting_purpose (a real sentence describing the meeting subject).
      2. protocol.protocol_title (the LLM short topic) if it is contentful.
      3. first non-empty topic block title.
      4. ``fallback``.
    """
    candidates: list[str] = []

    purpose = _norm(getattr(protocol, "meeting_purpose", ""))
    if purpose and not _looks_placeholder_topic(purpose):
        candidates.append(purpose)

    title = _norm(getattr(protocol, "protocol_title", ""))
    if title and not _looks_placeholder_topic(title):
        candidates.append(title)

    for tb in getattr(protocol, "topic_blocks", []) or []:
        tb_title = _norm(getattr(tb, "title", ""))
        if tb_title and not _looks_placeholder_topic(tb_title):
            candidates.append(tb_title)
            break

    for cand in candidates:
        # Take first sentence or a bounded chunk.
        short = cand
        cut = short.find(". ")
        if 0 < cut <= 140:
            short = short[:cut].strip(" .")
        if len(short) > 140:
            short = short[:139].rstrip() + "…"
        if not _looks_placeholder_topic(short):
            return short

    fb = _norm(fallback)
    if fb and not _looks_placeholder_topic(fb):
        return fb[:140].rstrip() if len(fb) > 140 else fb

    return "Анализ прошедшей встречи"


def detect_meeting_type(client_name: str, project_name: str = "") -> str:
    """Return 'internal' or 'external' based on resolved context."""
    client = _norm(client_name)
    if not client or client.lower() in {
        "не определено", "неизвестно", "внутренняя встреча", "внутренняя"
    }:
        return "internal"
    return "external"


def _normalize(value) -> str:
    return _norm(value)


def format_meeting_date(d: date | None) -> str:
    if d is None:
        return ""
    return d.strftime("%d.%m.%Y")


def build_protocol_title(
    meeting_date: date | None = None,
    short_topic: str = "",
    client_name: str = "",
    project_name: str = "",
    meeting_type: str = "external",
) -> str:
    """Build the single final title shared across HTML/Confluence/Telegram."""
    client = _normalize(client_name)
    project = _normalize(project_name)
    topic = _norm(short_topic)
    date_str = format(meeting_date.strftime("%d.%m.%Y")) if meeting_date else ""

    is_internal = meeting_type == "internal"

    if is_internal:
        prefix = "Протокол внутренней встречи"
        if date_str:
            return f"{prefix} от {date_str}. {topic}" if topic else f"{prefix} от {date_str}"
        return f"{prefix}. {topic}" if topic else prefix

    # external
    head = "Протокол встречи"
    if date_str:
        head = f"{head} от {date_str}."

    if topic:
        head = f"{head} {topic}"
    else:
        head = f"{head}"

    suffix_parts: list[str] = []
    if client and client.lower() not in PLACEHOLDER_CLIENT:
        if project and project.lower() not in PLACEHOLDER_CLIENT:
            suffix_parts.append(f"{client}, {project}")
        else:
            suffix_parts.append(client)
    if suffix_parts:
        head += " — " + ", ".join(suffix_parts)

    if head == "Протокол встречи от ":
        return "Протокол встречи"
    return head


def build_recording_source(source_type: str = "local_transcript",
                           source_filename: str = "") -> str:
    """Human-readable recording source line (technical filename allowed here)."""
    name = _norm(source_filename)
    if source_type == "bitlink":
        return f"БИТ.Link — запись встречи{(' (' + name + ')') if name else ''}"
    if name:
        return f"Локальная расшифровка: {name}"
    return "Локальная расшифровка"