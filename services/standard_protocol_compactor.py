"""Semantic compression + cell-structuring pass for the standard project protocol.

Turns the canonical-derived grouped view into a compact document:
- long cells are split into semantic paragraphs (CellContent) using cue-based
  (NOT fixed-sentence-count) splitting;
- cross-section repetition is removed (section 5 no longer re-quotes full
  decisions/risks/tasks already present in sections 6-9);
- filler/narration phrases are stripped;
- register coverage and per-section word counts are reported.

The compactor is deterministic and operates purely on the already-verified
canonical view (never on the raw transcript). An optional LLM compression
prompt is provided separately (see ``services/standard_protocol_compaction_prompts.py``).
"""
from __future__ import annotations

import re


# ── text utilities ────────────────────────────────────────────────────

def _norm(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def word_count(value: str) -> int:
    return len(re.findall(r"[^\W\d_]+|\d+(?:[.,]\d+)?", _norm(value)))


_SENT_RE = re.compile(r"(?<=[.!?])\s+(?=[А-ЯЁA-Z0-9])")


def split_sentences(text: str) -> list[str]:
    text = _norm(text)
    if not text:
        return []
    parts = _SENT_RE.split(text)
    return [p.strip() for p in parts if p.strip()]


# Filler / narration phrases that can be removed without losing a fact.
_FILLER_PATTERNS = [
    r"(?:было\s+)?отмечено,\s*что\s*",
    r"участники\s+рассмотрели\s+",
    r"участники\s+обсудили\s+",
    r"в\s+ходе\s+встречи\s+",
    r"в\s+рамках\s+обсуждения\s+",
    r"было\s+рассмотрено,\s*что\s*",
    r"было\s+зафиксировано,\s*что\s*",
    r"следует\s+отметить,\s*что\s*",
    r"на\s+встрече\s+",
    r"ранее\s+обсуждался(?:ся)?\s+вопрос\s+",
]

# Cues that start a new semantic paragraph (fact -> cause -> impact -> decision -> action).
_NEW_PARA_CUES = (
    "причин", "поэтому", "из-за", "вследствие", "следствие",
    "решение", "принято", "согласовано", "утвержд", "решили",
    "необходим", "нужно", "требу", "следует", "задача", "дальней",
    "далее", "следующ", "ожидает", "риск", "если не", "однако",
    "влияние", "влияет", "также важно",
)

# Decision / risk / task markers inside a "what discussed" cell. Such sentences
# are already (or should be) captured in sections 6-9 and must not be re-quoted.
_REGISTER_MARKERS = {
    "decision": ("принято решение", "решили", "договорились", "согласовано:", "утверждено"),
    "risk": ("риск", "если не подтвержд", "зависит от подписан", "есть акт, но нет"),
    "task": ("необходимо", "нужно", "требуется", "следует", "задача", "уточнить", "подготовить"),
}


def strip_fillers(text: str) -> str:
    out = text
    for pat in _FILLER_PATTERNS:
        out = re.sub(pat, "", out, flags=re.IGNORECASE)
    # collapse multiple spaces / stray punctuation left behind
    out = re.sub(r"\s+", " ", out)
    out = re.sub(r"\s+([.,;:!?])", r"\1", out)
    out = re.sub(r"(?<=\S),{2,}", ",", out)
    return out.strip(" ,;:-")


def semantic_paragraphs(text: str) -> list[str]:
    """Split text into semantic paragraphs (NOT by fixed sentence count).

    Breaks when a new object/transition is detected; joins otherwise.
    """
    sentences = split_sentences(text)
    if len(sentences) <= 1:
        return [t for t in sentences if t] or ([_norm(text)] if _norm(text) else [])

    paragraphs: list[str] = []
    current = ""
    for s in sentences:
        head = s[:40].lower()
        starts_new = any(c in head for c in _NEW_PARA_CUES)
        if current and starts_new:
            paragraphs.append(current.strip())
            current = s
        else:
            current = (current + " " if current else "") + s
        if len(current.split()) > 60:
            paragraphs.append(current.strip())
            current = ""
    if current.strip():
        paragraphs.append(current.strip())
    return [p for p in paragraphs if p]


def _clamp_sentences(text: str, max_words: int) -> str:
    """Soft clamp by words (only as a ceiling, never truncating mid-sentence)."""
    if word_count(text) <= max_words:
        return text
    sentences = split_sentences(text)
    out, w = [], 0
    for s in sentences:
        sw = word_count(s)
        if w + sw > max_words and out:
            break
        out.append(s)
        w += sw
    return " ".join(out).strip()


def _fuzzy_similar(a: str, b: str) -> float:
    """Quick token-overlap similarity (0..1) for dedup checks."""
    ta = set(re.findall(r"[а-яёa-z]+", a.lower()))
    tb = set(re.findall(r"[а-яёa-z]+", b.lower()))
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / max(1, min(len(ta), len(tb)))


_STATUS_MAP = {
    "согласовано": "Согласовано", "согласован": "Согласовано",
    "зафиксировано": "Информация зафиксирована", "зафиксирована": "Информация зафиксирована",
    "открыт": "Открыт", "открыто": "Открыт", "не закрыт": "Открыт",
    "требует уточнения": "Требует уточнения", "на уточнении": "Требует уточнения",
    "требует доработки": "Требует доработки",
    "отложено": "Отложено", "отложен": "Отложено",
    "заблокировано": "Заблокировано", "заблокирован": "Заблокировано",
}


def _norm_status(value) -> str:
    s = _norm(value or "")
    if not s:
        return "Информация зафиксирована"
    low = s.lower()
    for key, mapped in _STATUS_MAP.items():
        if key in low:
            return mapped
    return s


# ----------------------------------------------------------------------

def _register_texts(view: dict) -> list[str]:
    """Collect canonical register sentences used for cross-section dedup."""
    texts: list[str] = []
    for d in view.get("decision_groups", []):
        texts.append(d.get("decision_text", ""))
    for r in view.get("risk_groups", []):
        texts.append(r.get("risk_text", "") + " " + r.get("reason", ""))
    for t in view.get("task_groups", []):
        texts.append(t.get("task_text", ""))
    for q in view.get("open_questions", []):
        texts.append(q.get("question_text", ""))
    return [t for t in texts if t]


def _is_register_duplicate(sentence: str, registers: list[str]) -> bool:
    low = sentence.lower()
    for reg in registers:
        if not reg:
            continue
        if len(sentence) > 25 and _fuzzy_similar(sentence, reg) >= 0.65:
            return True
    # explicit decision/risk/task phrasing that must live in its own section
    if any(m in low for m in ("решили:", "принято решение:", "утверждено:")):
        return True
    return False


def compact_topic_what(what: str, registers: list[str], meeting_type: str) -> list[str]:
    """Compress + split a topic "what discussed" cell into semantic paragraphs."""
    text = _norm(what or "")
    if not text:
        return []
    text = strip_fillers(text)
    sentences = split_sentences(text)
    kept = [s for s in sentences if not _is_register_duplicate(s, registers)]
    joined = " ".join(kept).strip() if kept else text
    if word_count(joined) > 150:
        joined = _clamp_sentences(joined, 150)
    return semantic_paragraphs(joined) or ([joined] if _norm(joined) else [])


def _split_cell(text: str, meeting_type: str) -> list[str]:
    text = _norm(text or "")
    if not text:
        return []
    text = strip_fillers(text)
    paras = semantic_paragraphs(text)
    # merge tiny fragments (a paragraph must be a real unit)
    merged: list[str] = []
    for p in paras:
        if word_count(p) < 8 and merged:
            merged[-1] = merged[-1] + " " + p
        else:
            merged.append(p)
    return [p for p in merged if p]


# ----------------------------------------------------------------------

def compact_view(view: dict, meeting_type: str = "internal") -> dict:
    """Return a compacted copy of the standard view with structured cells.

    Each topic group gets ``cell`` = {paragraphs, bullets, source_item_ids}.
    Decisions/risks/tasks keep compact single-cell text plus ``cell`` where long.
    """
    from services.standard_protocol_logger import get_logger
    _log = get_logger("standard.compactor")
    _log.info("compact_view: meeting_type=%s topics=%d before_whole=%d",
              meeting_type, len(view.get("topic_groups", [])), visible_word_count(view))
    registers = _register_texts(view)
    out = dict(view)
    topic_groups = []
    for g in view.get("topic_groups", []):
        g = dict(g)
        what = g.get("what_discussed", "")
        conc = g.get("conclusion", "")
        paras = compact_topic_what(what, registers, meeting_type)
        conc_paras = _split_cell(conc, meeting_type)
        # keep status normalized
        status = _norm_status(g.get("status", ""))
        g["cell"] = {
            "paragraphs": paras,
            "bullets": [],
            "source_item_ids": g.get("source_ids", []),
        }
        g["conclusion_cell"] = {
            "paragraphs": conc_paras,
            "bullets": [],
            "source_item_ids": g.get("source_ids", []),
        }
        g["status"] = status
        # visible single-text keep for metrics/render back-compat
        g["what_discussed"] = "\n".join(paras)
        g["conclusion"] = "\n".join(conc_paras)
        topic_groups.append(g)
    out["topic_groups"] = topic_groups

    # structured cells for decisions / risks / tasks / questions too
    out["decision_groups"] = _attach_cells(view.get("decision_groups", []),
                                           "decision_text", "context_and_basis")
    out["risk_groups"] = _attach_cells(view.get("risk_groups", []),
                                       "risk_text", "reason")
    out["task_groups"] = _attach_cells(view.get("task_groups", []),
                                       "task_text", "expected_result")
    out["open_questions"] = _attach_question_cells(view.get("open_questions", []))

    out["_compaction"] = {
        "applied": True,
        "meeting_type": meeting_type,
    }
    _log.info("compact_view: done whole=%d s5=%d", visible_word_count(out),
              section5_word_count(out))
    return out


def _attach_cells(items, main_key: str, basis_key: str) -> list[dict]:
    res = []
    for it in items:
        it = dict(it)
        main = _split_cell(it.get(main_key, ""), "")
        basis = _split_cell(it.get(basis_key, ""), "")
        it["cell"] = {"paragraphs": main, "bullets": [], "source_item_ids": it.get("source_ids", [])}
        res.append(it)
    return res


def _attach_question_cells(items: list[dict]) -> list[dict]:
    res = []
    for it in items:
        it = dict(it)
        q = _split_cell(it.get("question_text", ""), "")
        det = _split_cell(it.get("what_to_determine", ""), "")
        it["cell"] = {"paragraphs": q + det, "bullets": [], "source_item_ids": it.get("source_ids", [])}
        res.append(it)
    return res


# ----------------------------------------------------------------------
# Metrics

def _cell_visible(cell: dict | None, fallback: str = "") -> str:
    """Rendered cell text (paragraphs+bullets), else the raw fallback field."""
    if cell and (cell.get("paragraphs") or cell.get("bullets")):
        return " ".join(str(p) for p in
                        (cell.get("paragraphs") or []) + (cell.get("bullets") or []))
    return fallback or ""


def visible_word_count(view: dict) -> int:
    def _wc(texts):
        return sum(word_count(t) for t in texts)
    total = 0
    gi = view.get("general_info", {})
    total += _wc([gi.get(k, "") for k in ("client_name", "topic_project",
                                          "meeting_datetime_place", "recording_source")])
    total += _wc([p.get("position", "") + p.get("full_name", "") + p.get("side", "")
                  for p in view.get("participants", [])])
    mc = view.get("meeting_context", {})
    total += _wc([mc.get(k, "") for k in ("goal", "initial_situation", "main_problem",
                                          "expected_result")])
    total += _wc(view.get("key_outcomes", []))
    total += _wc([_cell_visible(g.get("cell"), g.get("what_discussed", "")) +
                  _cell_visible(g.get("conclusion_cell"), g.get("conclusion", "")) +
                  g.get("status", "")
                  for g in view.get("topic_groups", [])])
    total += _wc([_cell_visible(d.get("cell"), d.get("decision_text", "")) +
                  d.get("context_and_basis", "") +
                  d.get("responsible", "") + d.get("deadline", "")
                  for d in view.get("decision_groups", [])])
    total += _wc([_cell_visible(q.get("cell"), q.get("question_text", "")) +
                  q.get("what_to_determine", "") +
                  q.get("responsible", "") + q.get("deadline", "") + q.get("status", "")
                  for q in view.get("open_questions", [])])
    total += _wc([_cell_visible(r.get("cell"), r.get("risk_text", "")) +
                  r.get("reason", "") + r.get("impact", "") +
                  r.get("measures", "") + r.get("responsible", "")
                  for r in view.get("risk_groups", [])])
    total += _wc([_cell_visible(t.get("cell"), t.get("task_text", "")) +
                  t.get("basis", "") + t.get("expected_result", "") +
                  t.get("responsible", "") + t.get("deadline", "") + t.get("status", "")
                  for t in view.get("task_groups", [])])
    return total


def section5_word_count(view: dict) -> int:
    return sum(
        word_count(_cell_visible(g.get("cell"), g.get("what_discussed", "")) +
                   _cell_visible(g.get("conclusion_cell"), g.get("conclusion", "")) +
                   g.get("status", ""))
        for g in view.get("topic_groups", [])
    )


def long_cells(view: dict) -> list[dict]:
    """Unbroken cells: >350 chars but fewer than two semantic blocks.

    A cell that is 700+ chars yet already split into 2+ semantic blocks is
    acceptable (per TASK §13); only UNBROKEN cells are flagged.
    """
    long_ = []
    for idx, g in enumerate(view.get("topic_groups", [])):
        cell = g.get("cell") or {}
        text = " ".join(cell.get("paragraphs", []) + cell.get("bullets", []))
        blocks = len(cell.get("paragraphs", [])) + len(cell.get("bullets", []))
        if len(text) > 350 and blocks < 2:
            long_.append({"section": "topic", "index": idx, "chars": len(text), "blocks": blocks})
    return long_


def semantic_cell_report(view: dict) -> dict:
    report = {}
    groups = view.get("topic_groups", [])
    report["topic_cells"] = [
        {"index": i, "paragraphs": len(g.get("cell", {}).get("paragraphs", [])),
         "bullets": len(g.get("cell", {}).get("bullets", [])),
         "chars": len(" ".join(g.get("cell", {}).get("paragraphs", [])))}
        for i, g in enumerate(groups)
    ]
    report["long_unbroken_cells"] = long_cells(view)
    return report


def duplication_report(view: dict) -> dict:
    """Cross-section duplication: paragraphs repeated verbatim/near-verbatim."""
    fingerprint: dict[str, list[str]] = {}
    for sec in ("key_outcomes",):
        for o in view.get(sec, []):
            for p in semantic_paragraphs(o):
                fingerprint.setdefault(_fp(p), []).append(sec)
    for g in view.get("topic_groups", []):
        for p in g.get("cell", {}).get("paragraphs", []):
            fingerprint.setdefault(_fp(p), []).append("topic")
    dup = {k: v for k, v in fingerprint.items() if len(v) > 1}
    return {
        "duplicate_paragraphs": len(dup),
        "duplicate_groups": dup,
        "semantic_duplication_ratio": min(1.0, len(dup) / max(1, len(fingerprint))),
    }


def _fp(text: str) -> str:
    tokens = re.findall(r"[а-яёa-z\d]+", text.lower())
    return " ".join(tokens[:10])