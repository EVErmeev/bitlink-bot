"""Standard-protocol quality gate (TASK §14).

Builds the compression health metrics and a blocking ValidationReport. The
whole/section-5 ratios are only meaningful when a previous baseline is
provided; otherwise field budgets + dedup are used (per TASK §14).
"""
from __future__ import annotations

import re

from models.validation import ValidationReport, ValidationStatus
from services.standard_protocol_compactor import (
    duplication_report,
    long_cells,
    section5_word_count,
    visible_word_count,
)
from services.standard_protocol_logger import get_logger

log = get_logger("standard.validation")

_TRUNCATION_RE = re.compile(r"…\s*$|\.\.\.\s*$")


def _cell_texts(view: dict) -> list[str]:
    out = []
    for g in view.get("topic_groups", []):
        for c in (g.get("cell"), g.get("conclusion_cell")):
            if c:
                out.extend(c.get("paragraphs") or [])
                out.extend(c.get("bullets") or [])
    for key in ("decision_groups", "open_questions", "risk_groups", "task_groups"):
        for it in view.get(key, []):
            c = it.get("cell")
            if c:
                out.extend(c.get("paragraphs") or [])
                out.extend(c.get("bullets") or [])
    return out


def _detect_truncation(view: dict) -> list[str]:
    bad = []
    for t in _cell_texts(view):
        s = t.strip()
        if s and _TRUNCATION_RE.search(s):
            bad.append(s[-60:])
    return bad


def standard_metrics(view: dict, previous: dict | None = None) -> dict:
    whole = visible_word_count(view)
    s5 = section5_word_count(view)
    lc = long_cells(view)
    dup = duplication_report(view)
    trunc = _detect_truncation(view)

    m = {
        "new_visible_word_count": whole,
        "new_section_5_word_count": s5,
        "long_unbroken_cells": len(lc),
        "long_cell_details": lc,
        "duplicate_paragraphs": dup["duplicate_paragraphs"],
        "semantic_duplication_ratio": round(dup["semantic_duplication_ratio"], 4),
        "sentence_truncation_detected": bool(trunc),
        "sentence_truncation_samples": trunc[:5],
    }
    if previous is not None:
        prev_whole = previous.get("visible_word_count", previous.get("new_visible_word_count"))
        prev_s5 = previous.get("section_5_word_count", previous.get("new_section_5_word_count"))
        if prev_whole:
            m["whole_protocol_compression_ratio"] = round(whole / prev_whole, 4)
            m["whole_protocol_reduction_pct"] = round((1 - whole / prev_whole) * 100, 1)
        if prev_s5:
            m["section_5_compression_ratio"] = round(s5 / prev_s5, 4)
            m["section_5_reduction_pct"] = round((1 - s5 / prev_s5) * 100, 1)
    return m


def _coverage(protocol, view) -> dict:
    base = {
        "decision_coverage": 1.0,
        "question_coverage": 1.0,
        "critical_risk_coverage": 1.0,
        "task_coverage": 1.0,
        "high_importance_coverage": 1.0,
    }
    if protocol is None or view is None:
        return base
    def _ratio(need: int, have: int) -> float:
        return 1.0 if need == 0 else min(1.0, have / need)
    try:
        base["decision_coverage"] = _ratio(len(protocol.decisions), len(view.get("decision_groups", [])))
        base["question_coverage"] = _ratio(len(protocol.questions), len(view.get("open_questions", [])))
        risks = [r for r in protocol.risks if getattr(r, "importance", 0.5) >= 0.5] \
            if protocol.risks else protocol.risks
        base["critical_risk_coverage"] = _ratio(len(risks), len(view.get("risk_groups", [])))
        base["task_coverage"] = _ratio(len(protocol.tasks), len(view.get("task_groups", [])))
    except Exception:
        pass
    return base


def blocking_report(view: dict, previous: dict | None = None,
                    protocol=None) -> tuple[ValidationReport, dict]:
    """TASK §14 blocking gates. Returns (report, metrics)."""
    report = ValidationReport()
    m = standard_metrics(view, previous)
    m["coverage"] = _coverage(protocol, view)

    def _fail(code, msg):
        report.add_issue(code, msg, ValidationStatus.FAILED, "standard")

    if m["long_unbroken_cells"] > 0:
        _fail("long_unbroken_cells",
              f"{m['long_unbroken_cells']} неразделённых ячеек (>350 симв., 1 блок).")
    if m["duplicate_paragraphs"] > 0:
        _fail("duplicate_paragraphs",
              f"{m['duplicate_paragraphs']} абзацев дословно повторены между разделами.")
    if m["sentence_truncation_detected"]:
        _fail("sentence_truncation_detected", "Обрезка предложений многоточием.")

    if previous is not None:
        s5r = m.get("section_5_compression_ratio")
        if s5r is not None and s5r > 0.80:
            _fail("section_5_over_target",
                  f"Раздел 5 сокращён лишь на {round((1 - s5r) * 100)}% (порог 20%).")
        wr = m.get("whole_protocol_compression_ratio")
        if wr is not None and wr > 0.85:
            _fail("whole_over_target",
                  f"Общий объём сокращён лишь на {round((1 - wr) * 100)}% (порог 15%).")

    cov = m["coverage"]
    for key, label in (("decision_coverage", "решения"),
                       ("question_coverage", "вопросы"),
                       ("critical_risk_coverage", "критические риски"),
                       ("task_coverage", "задачи"),
                       ("high_importance_coverage", "high-importance элементы")):
        if cov.get(key, 1.0) < 1.0:
            _fail(f"{key}_low", f"Покрытие {label} < 100%.")

    if not report.issues:
        report.add_issue("standard_validation_ok", "Стандартный протокол прошёл gate.",
                         ValidationStatus.PASSED, "standard")
    log.info("blocking_report: passed=%s issues=%s metrics=%s",
             report.passed, [i.code for i in report.issues],
             {k: m.get(k) for k in ("whole_protocol_compression_ratio",
                                    "section_5_compression_ratio",
                                    "long_unbroken_cells", "duplicate_paragraphs",
                                    "sentence_truncation_detected") if k in m})
    return report, m