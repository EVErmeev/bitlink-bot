"""Meeting-type resolution: external | internal | unresolved.

An unresolved client is NOT treated as internal. The type is decided from
evidence (filename/title with two parties, participant sides split between
Первый БИТ and another organisation, a matched known client profile, or an
explicit customer/contractor separation in the text).
"""
from __future__ import annotations

import re

FIRST_BIT_NAMES = ("первый бит", "первыйбит", "1бит", "1с бит", "первыйbit")

_UNRESOLVED = "Не определено"


def _norm(value) -> str:
    return re.sub(r"\s+", " ", str(value or "")).lower().strip()


def _has_second_party(filename: str, title: str, transcript: str) -> bool:
    hay = " ".join([filename, title, transcript[:3000]])
    low = _norm(hay)
    # two parties separated by '+': one of them is Первый БИТ
    plus_patterns = [
        r"[\wА-Яа-яЁё]+\s*\+\s*первый\s*бит",
        r"первый\s*бит\s*\+\s*[\wА-Яа-яЁё]+",
    ]
    for pat in plus_patterns:
        if re.search(pat, low):
            return True
    return False


def _participant_sides(participants: list) -> list[str]:
    sides = []
    for p in participants or []:
        if not isinstance(p, dict):
            continue
        side = p.get("side") or p.get("organization") or p.get("company") or ""
        if side:
            sides.append(side)
    return sides


def _sides_split(p_side: list[str], transcript: str, filename: str, title: str) -> bool:
    if not p_side:
        return False
    side_text = " ".join(p_side)
    has_fb = any(_norm(name) in _norm(side_text) for name in FIRST_BIT_NAMES)
    has_other = bool(p_side) and not all(
        any(_norm(name) in _norm(s) for name in FIRST_BIT_NAMES) for s in p_side)
    return has_fb and has_other


def _explicit_customer_separation(transcript: str, filename: str, title: str) -> bool:
    low = " ".join([_norm(transcript), _norm(filename), _norm(title)])
    patterns = [
        r"встреча\s+с\s+клиентом",
        r"заказчик", r"исполнитель", r"подрядчик",
        r"со\s+стороны\s+заказчика", r"со\s+стороны\s+исполнителя",
    ]
    return any(re.search(p, low) for p in patterns)


def resolve_meeting_type(
    transcript_text: str = "",
    source_filename: str = "",
    source_title: str = "",
    participants: list | None = None,
    client_name: str = "",
    project_name: str = "",
    known_profile_id: str = "",
) -> tuple[str, str, list[str]]:
    """Return (meeting_type, confidence, evidence).

    meeting_type ∈ {external, internal, unresolved}.
    """
    evidence: list[str] = []
    transcript = transcript_text or ""
    filename = source_filename or ""
    title = source_title or ""

    p_side = _participant_sides(participants)

    # strong: two parties, one of them Первый БИТ
    if _has_second_party(filename, title, transcript):
        evidence.append("в названии/файле две стороны, одна из них — Первый БИТ")
        return "external", "high", evidence

    # strong: participants split across Первый БИТ and another organisation
    if _sides_split(p_side, transcript, filename, title):
        evidence.append("участники распределены между Первым БИТ и другой организацией")
        return "external", "high", evidence

    # strong: known client profile resolved (client is not Первый БИТ)
    if client_name and _norm(client_name) != _norm(_UNRESOLVED) and \
            not any(_norm(name) in _norm(client_name) for name in FIRST_BIT_NAMES):
        evidence.append(f"найден профиль клиента: {client_name}")
        return "external", "high", evidence

    if known_profile_id:
        evidence.append(f"сопоставлен известный профиль: {known_profile_id}")
        return "external", "medium", evidence

    # internal only when every participant belongs to Первый БИТ (or no other party)
    if p_side and p_side and not any(
            not any(_norm(name) in _norm(s) for name in FIRST_BIT_NAMES) for s in p_side):
        evidence.append("все участники относятся к Первому БИТ")
        return "internal", "medium", evidence

    if _explicit_customer_separation(transcript, filename, title):
        evidence.append("в тексте явно разделены заказчик и исполнитель")
        return "external", "medium", evidence

    # fall back to the resolved client when it is a real non-Первый-БИТ client
    if client_name and _norm(client_name) != _norm(_UNRESOLVED) and \
            not any(_norm(name) in _norm(client_name) for name in FIRST_BIT_NAMES):
        evidence.append(f"клиент определён как {client_name}")
        return "external", "medium", evidence

    return "unresolved", "low", evidence