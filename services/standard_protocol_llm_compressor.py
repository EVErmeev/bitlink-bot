"""LLM-based semantic compression pass for the standard protocol view.

Applied AFTER the deterministic structural compactor. Compresses verbose
narrative cells (what-discussed, conclusions, context, outcomes, and register
narratives incl. secondary columns) to the TASK word budgets, producing
structured ``{paragraphs, bullets}`` cells. Uses small batched calls to bound
latency. Never truncates mid-sentence; on any failure falls back to the
deterministic cell.
"""
from __future__ import annotations

import json
import os

from services.standard_protocol_compactor import (
    semantic_paragraphs,
    split_sentences,
    word_count,
)
from services.standard_protocol_logger import get_logger

log = get_logger("standard.llm_compressor")

_CHUNK = 12
_TOPIC_BUDGET = int(os.environ.get("STANDARD_TOPIC_BUDGET", "85"))

# Per-field word budgets for the plain-string compression pass.
_FIELD_BUDGET = {
    "context_and_basis": 18,
    "reason": 14,
    "impact": 16,
    "measures": 18,
    "basis": 14,
    "expected_result": 16,
    "goal": 22,
    "initial_situation": 20,
    "main_problem": 20,
    "expected_result_ctx": 24,
}


# ---------------------------------------------------------------------------
# deterministic helpers
# ---------------------------------------------------------------------------

def _join_cell(cell: dict) -> str:
    if not cell:
        return ""
    parts = list(cell.get("paragraphs") or []) + list(cell.get("bullets") or [])
    return " ".join(str(p).strip() for p in parts if str(p).strip())


def _make_cell(text: str, src_ids: list | None) -> dict:
    paras = semantic_paragraphs(text)
    return {"paragraphs": paras, "bullets": [], "source_item_ids": src_ids or []}


def _split_long_paragraphs(cell: dict, max_para: int = 300) -> dict:
    """Split any over-length paragraph into semantic paragraphs.

    A single >max_para paragraph is re-split on semantic cues; if still a
    single block, it is divided on sentence boundaries grouped by subject
    (this only applies to genuinely oversized cells, not to normal text).
    """
    if not cell:
        return cell
    paras = [str(p).strip() for p in (cell.get("paragraphs") or []) if str(p).strip()]
    new_paras: list[str] = []
    for p in paras:
        if len(p) <= max_para:
            new_paras.append(p)
            continue
        chunks = [c for c in semantic_paragraphs(p) if c.strip()]
        if len(chunks) > 1:
            new_paras.extend(chunks)
            continue
        # fall back to sentence-grouping an oversized block
        sents = [s.strip() for s in split_sentences(p) if s.strip()]
        cur, cur_len = [], 0
        for s in sents:
            if cur and cur_len + len(s) > max_para:
                new_paras.append(" ".join(cur))
                cur, cur_len = [], 0
            cur.append(s)
            cur_len += len(s)
        if cur:
            new_paras.append(" ".join(cur))
    if not new_paras:
        return cell
    cell["paragraphs"] = new_paras
    cell["bullets"] = list(cell.get("bullets") or [])
    return cell


def _build_batch(values: list) -> str:
    return "\n\n".join(f"#{i}\n{str(v).strip()}" for i, v in enumerate(values) if str(v).strip())


def _numbers(text: str) -> set[str]:
    import re
    return set(re.findall(r"\d+", text or ""))


def _cell_text(cell) -> str:
    return " ".join((cell or {}).get("paragraphs", []) + (cell or {}).get("bullets", []))


# ---------------------------------------------------------------------------
# LLM plumbing
# ---------------------------------------------------------------------------

def _try_llm_json(llm, section: str, cells_text: str, budget: int | None = None) -> list[dict]:
    from services.standard_protocol_compaction_prompts import (
        build_compression_system_prompt,
    )
    budget_note = f"Целевой объём ячейки — до {budget} слов. " if budget else ""
    schema = {
        "type": "object",
        "properties": {
            "cells": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "paragraphs": {"type": "array", "items": {"type": "string"}},
                        "bullets": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["paragraphs"],
                },
            }
        },
        "required": ["cells"],
    }
    user = (f"Секция: {section}\n{budget_note}"
            "Сожми каждую ячейку в отдельные смысловые абзацы и пункты. Сохраняй все числа, суммы, даты, сроки, ответственных и названия. Ответь строго в JSON.\n\n"
            f"{cells_text}")
    data, _ = llm.generate_json(
        system_prompt=build_compression_system_prompt(),
        user_prompt=user,
        json_schema=schema,
        temperature=0.1,
        max_retries=2,
    )
    cells = (data or {}).get("cells", [])
    return cells if isinstance(cells, list) else []


def _try_llm_plain(llm, section: str, cells_text: str, budget: int = 25) -> list[str]:
    """Compress plain (single-field) strings; returns aligned list of strings."""
    schema = {
        "type": "object",
        "properties": {
            "items": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["items"],
    }
    from services.standard_protocol_compaction_prompts import (
        build_compression_system_prompt,
    )
    user = (
        f"Секция: {section}\nСократи каждое значение до краткой формулировки "
        f"(до {budget} слов на значение), сохрани числа, суммы, даты, сроки, "
        "ответственных и названия. Не обрезай середину предложения и не ставь "
        "многоточие. Ответь строго в JSON.\n\n"
        f"{cells_text}"
    )
    data, _ = llm.generate_json(
        system_prompt=build_compression_system_prompt(),
        user_prompt=user,
        json_schema=schema,
        temperature=0.1,
        max_retries=2,
    )
    items = (data or {}).get("items", [])
    return items if isinstance(items, list) else []


def _compress_fields(items: list, fields: list[str], llm, section: str):
    """Compress secondary register fields in-place. Best-effort."""
    if not items or not fields:
        return
    for fi, field in enumerate(fields):
        texts = [str(it.get(field, "")).strip() for it in items]
        chunks = [texts[i:i + _CHUNK] for i in range(0, len(texts), _CHUNK)]
        out_flat: list[str] = []
        for chunk in chunks:
            if not any(chunk):
                out_flat.extend([""] * len(chunk))
                continue
            try:
                res = _try_llm_plain(llm, f"{section}/{field}", _build_batch(chunk), budget=_FIELD_BUDGET.get(field, 25))
                res = (res + [""] * len(chunk))[: len(chunk)]
            except Exception:
                res = list(chunk)
            out_flat.extend(res)
        for it, new in zip(items, out_flat):
            if new and new.strip():
                it[field] = new.strip()


def _numbers(text: str) -> set[str]:
    import re
    return set(re.findall(r"\d+", text or ""))


def _cell_text(cell) -> str:
    return " ".join((cell or {}).get("paragraphs", []) + (cell or {}).get("bullets", []))


def _retry_preserve_numbers(llm, original: str, cell: dict, src_ids) -> dict:
    """Retry compression with a higher budget until figures survive; on final
    failure keep the best-effort cell (its deterministic source still carries
    the facts, and the validation gate flags any unbrokage)."""
    for attempt in range(2):
        try:
            res = _try_llm_json(llm, "Что обсуждалось (раздел 5)",
                                _build_batch([original]),
                                budget=int(_TOPIC_BUDGET * (1.5 + attempt * 0.5)))
        except Exception:
            break
        if res and isinstance(res[0], dict):
            r = {
                "paragraphs": [p for p in (res[0].get("paragraphs") or []) if str(p).strip()],
                "bullets": [b for b in (res[0].get("bullets") or []) if str(b).strip()],
                "source_item_ids": src_ids,
            }
            if not (_numbers(original) - _numbers(_cell_text(r))):
                return r
    # Lossless fallback: deterministic semantic paragraphs of the original text,
    # guaranteeing that no figure is silently dropped.
    return {
        "paragraphs": [p for p in semantic_paragraphs(original) if p.strip()],
        "bullets": [],
        "source_item_ids": src_ids,
    }


def _retry_preserve_register(llm, original: str, cell: dict, section: str, src_ids, budget: int) -> dict:
    for attempt in range(2):
        try:
            res = _try_llm_json(llm, section, _build_batch([original]),
                                budget=int(budget * (1.5 + attempt * 0.5)))
        except Exception:
            break
        if res and isinstance(res[0], dict):
            r = {
                "paragraphs": [p for p in (res[0].get("paragraphs") or []) if str(p).strip()],
                "bullets": [b for b in (res[0].get("bullets") or []) if str(b).strip()],
                "source_item_ids": src_ids,
            }
            if not (_numbers(original) - _numbers(_cell_text(r))):
                return r
    return {
        "paragraphs": [p for p in semantic_paragraphs(original) if p.strip()],
        "bullets": [],
        "source_item_ids": src_ids,
    }


def _apply_cell_results(items: list, results: list[dict]) -> list[dict]:
    for idx, item in enumerate(items):
        res = results[idx] if idx < len(results) else None
        if res and isinstance(res, dict) and (res.get("paragraphs") or res.get("bullets")):
            item["cell"] = {
                "paragraphs": [p for p in (res.get("paragraphs") or []) if str(p).strip()],
                "bullets": [b for b in (res.get("bullets") or []) if str(b).strip()],
                "source_item_ids": item.get("source_ids", []),
            }
            item["cell"] = _split_long_paragraphs(item["cell"])
    return items


# ---------------------------------------------------------------------------
# main pass
# ---------------------------------------------------------------------------

def llm_compress_view(view: dict, llm) -> dict:
    log.info("llm_compress_view: start, topic_budget=%d, topics=%d, decisions=%d, risks=%d, tasks=%d",
             _TOPIC_BUDGET,
             len(view.get("topic_groups", [])), len(view.get("decision_groups", [])),
             len(view.get("risk_groups", [])), len(view.get("task_groups", [])))
    out = dict(view)

    # Section 5 topics: compress what-discussed AND conclusion into cells.
    topics = out.get("topic_groups", [])
    if topics:
        texts = [t.get("what_discussed", "") for t in topics]
        for start in range(0, len(texts), _CHUNK):
            chunk = topics[start:start + _CHUNK]
            batch = _build_batch([t.get("what_discussed", "") for t in chunk])
            try:
                res = _try_llm_json(llm, "Что обсуждалось (раздел 5)", batch, budget=_TOPIC_BUDGET)
            except Exception:
                res = []
            for t, r in zip(chunk, res):
                orig = t.get("what_discussed", "")
                if r and isinstance(r, dict) and (r.get("paragraphs") or r.get("bullets")):
                    cell = {
                        "paragraphs": [p for p in (r.get("paragraphs") or []) if str(p).strip()],
                        "bullets": [b for b in (r.get("bullets") or []) if str(b).strip()],
                        "source_item_ids": t.get("source_ids", []),
                    }
                    if _numbers(orig) and _numbers(orig) - _numbers(_cell_text(cell)):
                        log.warning("topic %r dropped figures %s -> retrying",
                                    t.get("title"), sorted(_numbers(orig) - _numbers(_cell_text(cell))))
                        cell = _retry_preserve_numbers(llm, orig, cell, t.get("source_ids", []))
                    t["cell"] = _split_long_paragraphs(cell)
        for t in topics:
            if t.get("cell"):
                t["cell"] = _split_long_paragraphs(t["cell"])

    # Register main texts.
    reg_budget = {"decision_groups": 30, "risk_groups": 32, "task_groups": 32}
    for key, main_attr in (("decision_groups", "decision_text"),
                           ("risk_groups", "risk_text"),
                           ("task_groups", "task_text")):
        items = out.get(key, [])
        if not items:
            continue
        for start in range(0, len(items), _CHUNK):
            chunk = items[start:start + _CHUNK]
            batch = _build_batch([it.get(main_attr, "") for it in chunk])
            try:
                res = _try_llm_json(llm, key, batch, budget=reg_budget[key])
            except Exception:
                res = []
            for it, r in zip(chunk, res):
                orig = it.get(main_attr, "")
                if r and isinstance(r, dict) and (r.get("paragraphs") or r.get("bullets")):
                    cell = {
                        "paragraphs": [p for p in (r.get("paragraphs") or []) if str(p).strip()],
                        "bullets": [b for b in (r.get("bullets") or []) if str(b).strip()],
                        "source_item_ids": it.get("source_ids", []),
                    }
                    if _numbers(orig) and _numbers(orig) - _numbers(_cell_text(cell)):
                        cell = _retry_preserve_register(llm, orig, cell, key, it.get("source_ids", []), reg_budget[key])
                    it["cell"] = _split_long_paragraphs(cell)

    # Register secondary fields.
    _compress_fields(out.get("decision_groups", []), ["context_and_basis"], llm, "Решение — контекст и основание")
    _compress_fields(out.get("risk_groups", []), ["reason", "impact", "measures"], llm, "Риск — причина/влияние/реагирование")
    _compress_fields(out.get("task_groups", []), ["basis", "expected_result"], llm, "Задача — основание/ожидаемый результат")

    mc = dict(out.get("meeting_context", {}))
    for field in ("goal", "initial_situation", "main_problem", "expected_result"):
        val = mc.get(field, "")
        if not val:
            continue
        try:
            res = _try_llm_plain(llm, f"Контекст встречи — {field}",
                                 f"#{0}\n{val}", budget=_FIELD_BUDGET.get(field, 22))
            if res and res[0] and res[0].strip():
                mc[field] = res[0].strip()
        except Exception:
            pass
    out["meeting_context"] = mc

    # Key outcomes.
    outcomes = list(out.get("key_outcomes", []))
    if outcomes:
        for start in range(0, len(outcomes), _CHUNK):
            chunk = outcomes[start:start + _CHUNK]
            batch = _build_batch(chunk)
            try:
                res = _try_llm_plain(llm, "Ключевые итоги", batch, budget=24)
            except Exception:
                res = []
            for i, r in enumerate(res):
                if r and r.strip() and start + i < len(outcomes):
                    outcomes[start + i] = r.strip()
    out["key_outcomes"] = outcomes

    # Deterministic semantic split for any remaining long cells.
    for key in ("topic_groups", "decision_groups", "risk_groups", "task_groups", "open_questions"):
        for it in out.get(key, []):
            if it.get("cell"):
                it["cell"] = _split_long_paragraphs(it["cell"])

    # Normalize cell structure: paragraphs by default, bullets only for true
    # enumerations. This runs after every (LLM or deterministic) pass.
    from services.standard_protocol_compactor import normalize_cell_structure
    for key in ("topic_groups", "decision_groups", "risk_groups", "task_groups", "open_questions"):
        for it in out.get(key, []):
            if it.get("cell"):
                it["cell"] = normalize_cell_structure(it["cell"])

    log.info("llm_compress_view: done")
    return out