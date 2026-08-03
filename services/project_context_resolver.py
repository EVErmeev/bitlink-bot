"""Automatic project context resolution for meeting protocols.

Determines `client_name` / `project_name` from the transcript, source
metadata, file name, participants, systems and a registry of known project
profiles. Falls back to an LLM classification only when needed.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

_UNRESOLVED = "Не определено"


@dataclass
class ProjectContextResolution:
    client_name: str = _UNRESOLVED
    project_name: str = _UNRESOLVED
    confidence: str = "unresolved"  # high | medium | low | unresolved
    resolution_method: str = ""
    evidence: list[str] = field(default_factory=list)
    matched_profile_id: str = ""
    alternatives: list[str] = field(default_factory=list)


def _norm(value) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip().lower()


def _count_hits(haystack: str, terms: list[str], cap: int) -> tuple[int, list[str]]:
    hits = 0
    matched = []
    for term in terms:
        t = _norm(term)
        if t and t in haystack:
            hits += 1
            matched.append(term)
            if hits >= cap:
                break
    return hits, matched


def load_profiles(path: str | Path | None = None) -> list[dict]:
    """Load known project profiles from a tracked JSON registry.

    Candidates, first existing wins:
      1. `path` (explicit) if given
      2. tracked `resources/project_profiles.json`
      3. gitignored `data/project_profiles.json` (runtime overrides)
    """
    if path is None:
        base = Path(__file__).resolve().parent.parent
        for candidate in (base / "resources", base / "data"):
            candidate = candidate / "project_profiles.json"
            if candidate.exists():
                path = candidate
                break
        else:
            return []
    path = Path(path)
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    profiles = data.get("profiles", []) if isinstance(data, dict) else data
    return [p for p in profiles if p.get("active", True)]


def _score_profile(profile: dict, haystack: str, participants: list) -> tuple[float, list[str]]:
    """Score a single profile against combined source text."""
    score = 0.0
    evidence: list[str] = []

    client_aliases = profile.get("aliases") or [profile.get("client_name", "")]
    project_aliases = profile.get("project_aliases") or [profile.get("project_name", "")]
    keywords = profile.get("keywords") or []
    systems = profile.get("systems") or []
    profile_participants = profile.get("participants") or []

    n, m = _count_hits(haystack, client_aliases, cap=3)
    if n:
        score += 3.0 * min(n, 2)
        evidence.append(f"найден alias клиента: {m[0]}")

    n, m = _count_hits(haystack, project_aliases, cap=3)
    if n:
        score += 3.0 * min(n, 2)
        evidence.append(f"найден alias проекта: {m[0]}")

    n, m = _count_hits(haystack, keywords, cap=6)
    if n:
        score += 2.0 * min(n, 5)
        evidence.append(f"совпали ключевые термины ({n}): {', '.join(m[:3])}")

    n, m = _count_hits(haystack, systems, cap=4)
    if n:
        score += 2.0 * min(n, 3)
        evidence.append(f"упомянуты системы ({n})")

    if participants:
        names = [_norm(p.get("name") if isinstance(p, dict) else p) for p in participants]
        overlap = [c for c in profile_participants if _norm(c) in names]
        if overlap:
            score += 2.0
            evidence.append(f"совпали участники ({len(overlap)}): {', '.join(overlap[:3])}")

    return score, evidence


def _to_confidence(score: float) -> str:
    if score >= 8.0:
        return "high"
    if score >= 4.0:
        return "medium"
    return "low"


def _resolve_deterministic(
    transcript_text: str,
    source_filename: str,
    source_title: str,
    participants: list,
    known_profiles: list,
) -> ProjectContextResolution | None:
    combined = "\n".join([transcript_text, source_filename, source_title])
    haystack = _norm(combined)
    if not haystack:
        return None

    best: tuple[float, dict, list[str]] | None = None
    for profile in known_profiles:
        score, evidence = _score_profile(profile, haystack, participants)
        if best is None or score > best[0]:
            best = (score, profile, evidence)

    if best is None or best[0] <= 0:
        return None

    score, profile, evidence = best
    confidence = _to_confidence(score)
    if confidence not in ("high", "medium"):
        return ProjectContextResolution(
            confidence=confidence,
            resolution_method="unresolved",
            evidence=evidence,
        )
    return ProjectContextResolution(
        client_name=profile.get("client_name", _UNRESOLVED),
        project_name=profile.get("project_name", _UNRESOLVED),
        confidence=confidence,
        resolution_method="known_profile_match",
        evidence=evidence,
        matched_profile_id=profile.get("profile_id", ""),
    )


def _resolve_with_llm(llm_client, known_profiles: list) -> ProjectContextResolution | None:
    """Optional LLM classification among known profiles (kept lightweight)."""
    try:
        if llm_client is None or not known_profiles:
            return None
        labels = ", ".join(
            f"{p.get('client_name')} / {p.get('project_name')}" for p in known_profiles
        )
        prompt = (
            "По перечню известных проектов выбери один, который соответствует контексту "
            "встречи. Ответь JSON-объектом с ключами profile_id и reason, "
            "или {\"profile_id\": null}, если не уверен. "
            f"Известные проекты: {labels}"
        )
        data, _ = llm_client.generate_json(
            system_prompt=prompt,
            user_prompt="Определи проект по контексту встречи.",
            json_schema={
                "type": "object",
                "properties": {"profile_id": {"type": "string"}, "reason": {"type": "string"}},
            },
            temperature=0.0,
            max_retries=1,
        )
        pid = (data or {}).get("profile_id")
        if not pid:
            return None
        profile = next((p for p in known_profiles if p.get("profile_id") == pid), None)
        if not profile:
            return None
        return ProjectContextResolution(
            client_name=profile.get("client_name", _UNRESOLVED),
            project_name=profile.get("project_name", _UNRESOLVED),
            confidence="medium",
            resolution_method="known_profile_llm_match",
            evidence=["LLM-классификация выбрала профиль"],
            matched_profile_id=pid,
        )
    except Exception:
        return None


def resolve_project_context(
    transcript_text: str,
    source_filename: str = "",
    source_title: str = "",
    source_metadata: dict | None = None,
    participants: list | None = None,
    known_profiles: list | None = None,
    llm_client=None,
) -> ProjectContextResolution:
    """Resolve client/project context for a meeting.

    Priority: source text mentions -> title/file -> registry keywords ->
    participants/systems/terms -> LLM classification among profiles.
    """
    source_metadata = source_metadata or {}
    participants = participants or []
    profiles = known_profiles if known_profiles is not None else load_profiles()

    filename = source_filename or str(source_metadata.get("source_path", ""))
    title = source_title or source_metadata.get("display_name", "")

    resolved = _resolve_deterministic(transcript_text, filename, title, participants, profiles)
    if resolved and resolved.confidence in ("high", "medium"):
        return resolved

    llm_res = _resolve_with_llm(llm_client, profiles)
    if llm_res:
        return llm_res

    if resolved:
        return resolved  # low confidence -> fields = "Не определено"
    return ProjectContextResolution()