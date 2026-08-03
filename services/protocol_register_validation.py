"""Quality validation and publication-blocking for meeting registers."""
from __future__ import annotations

from services.protocol_register_pipeline import (
    PLACEHOLDER_DEADLINE,
    PLACEHOLDER_RESULT,
    PLACEHOLDER_RESPONSIBLE,
    _is_generic_strategy,
    _is_placeholder,
    _norm,
)


def _coverage(items: list, field: str, placeholders=None) -> float:
    items = items or []
    if not items:
        return 0.0
    placeholders = placeholders or {}
    filled = 0
    for it in items:
        v = _norm(it.get(field, ""))
        if v and not _is_placeholder(v, placeholders):
            filled += 1
    return round(filled / len(items), 4)


def _placeholder_count(decisions, questions, risks, tasks) -> int:
    total = 0
    placeholders = set(PLACEHOLDER_RESPONSIBLE) | set(PLACEHOLDER_DEADLINE) | set(PLACEHOLDER_RESULT)
    placeholders.add("стратегия не определена")
    for group in (decisions, questions, risks, tasks):
        for it in group or []:
            for field in ("responsible", "deadline", "measures", "expected_result",
                          "context_and_basis", "basis"):
                v = _norm(it.get(field, ""))
                if not v or _is_placeholder(v, placeholders) or _is_generic_strategy(v):
                    total += 1
    return total


def build_register_quality_report(registers: dict, diff: dict) -> dict:
    decisions = registers.get("decisions") or []
    questions = registers.get("questions") or []
    risks = registers.get("risks") or []
    tasks = registers.get("tasks") or []

    q_resp = sum(not _is_placeholder(q.get("responsible", ""), PLACEHOLDER_RESPONSIBLE) for q in questions)
    q_dl = sum(not _is_placeholder(q.get("deadline", ""), PLACEHOLDER_DEADLINE) for q in questions)
    r_strat = sum(not _is_generic_strategy(r.get("measures", "")) for r in risks)
    r_resp = sum(not _is_placeholder(r.get("responsible", ""), PLACEHOLDER_RESPONSIBLE) for r in risks)
    t_res = sum(not _is_placeholder(t.get("expected_result", ""), PLACEHOLDER_RESULT) for t in tasks)

    return {
        "decisions_count": len(decisions),
        "questions_count": len(questions),
        "risks_count": len(risks),
        "tasks_count": len(tasks),
        "decision_context_coverage": _coverage(decisions, "context_and_basis"),
        "question_responsible_coverage": round(q_resp / max(len(questions), 1), 4),
        "question_deadline_coverage": round(q_dl / max(len(questions), 1), 4),
        "risk_reason_coverage": _coverage(risks, "reason"),
        "risk_impact_coverage": _coverage(risks, "impact"),
        "risk_strategy_coverage": round(r_strat / max(len(risks), 1), 4),
        "risk_responsible_coverage": round(r_resp / max(len(risks), 1), 4),
        "task_basis_coverage": _coverage(tasks, "basis"),
        "task_expected_result_coverage": round(t_res / max(len(tasks), 1), 4),
        "task_responsible_coverage": _coverage(tasks, "responsible", PLACEHOLDER_RESPONSIBLE),
        "task_deadline_coverage": _coverage(tasks, "deadline", PLACEHOLDER_DEADLINE),
        "generic_placeholder_count": _placeholder_count(decisions, questions, risks, tasks),
        "silent_drop_count": int((diff or {}).get("silent_drop_count", 0)),
    }


def register_quality_blocks(registers: dict) -> list[str]:
    """Return blocking reasons; empty list means the registers pass the gate."""
    questions = registers.get("questions") or []
    risks = registers.get("risks") or []
    tasks = registers.get("tasks") or []

    blocks: list[str] = []

    if questions and all(_is_placeholder(q.get("responsible", ""), PLACEHOLDER_RESPONSIBLE) for q in questions):
        blocks.append("all_question_responsibles_unknown")
    if questions and all(_is_placeholder(q.get("deadline", ""), PLACEHOLDER_DEADLINE) for q in questions):
        blocks.append("all_question_deadlines_unknown")
    if risks and all(_is_generic_strategy(r.get("measures", "")) for r in risks):
        blocks.append("all_risk_strategies_generic")
    if risks and all(_is_placeholder(r.get("responsible", ""), PLACEHOLDER_RESPONSIBLE) for r in risks):
        blocks.append("all_risk_responsibles_unknown")
    if tasks and all(_is_placeholder(t.get("expected_result", ""), PLACEHOLDER_RESULT) for t in tasks):
        blocks.append("all_task_expected_results_empty")
    return blocks


def registers_have_silent_drop(diff: dict) -> bool:
    return int((diff or {}).get("silent_drop_count", 0)) > 0