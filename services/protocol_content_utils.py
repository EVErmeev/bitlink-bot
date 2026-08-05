"""Content normalization utilities for protocol templates."""
import re


def _norm_text(value) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _split_sentences(text: str) -> list[str]:
    text = _norm_text(text)
    if not text:
        return []
    parts = re.split(r"(?<=[.!?])\s+(?=[А-ЯA-Z])", text)
    return [p.strip() for p in parts if p.strip()]


def normalize_text_list(value) -> list[str]:
    """Normalize various formats into a clean list of strings."""
    if value is None:
        return []
    if isinstance(value, list):
        items = []
        for v in value:
            if isinstance(v, dict):
                items.append(str(v.get("text", v.get("value", str(v)))))
            elif isinstance(v, str):
                items.append(v.strip())
        return [i for i in items if i]
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        if text.startswith("[") and text.endswith("]"):
            try:
                import json
                parsed = json.loads(text)
                if isinstance(parsed, list):
                    return normalize_text_list(parsed)
            except Exception:
                pass
        parts = re.split(r"(?:^|\n)\s*(?:\d{1,2}[.)]\s*|\u2022\s*|-\s*)", text)
        items = [p.strip() for p in parts if p.strip()]
        if len(items) >= 2:
            return items
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        if len(lines) >= 2:
            return lines
        return [text]
    return []


def normalize_paragraphs(value, max_per_paragraph=3) -> list[str]:
    """Split long text into paragraphs by sentence boundaries."""
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    text = _norm_text(value)
    if not text:
        return []
    sentences = _split_sentences(text)
    if len(sentences) <= 1:
        return [text]
    paragraphs = []
    current = ""
    for s in sentences:
        if current and len(current) + len(s) > 600:
            paragraphs.append(current.strip())
            current = s
        else:
            current += " " + s if current else s
    if current.strip():
        paragraphs.append(current.strip())
    return paragraphs if paragraphs else [text]


# ── RichTextBlock model ──────────────────────────────────────────────
# A block is a dict: {"type": "paragraph", "text": "..."}
#                   | {"type": "bullet_list", "items": [...]}
#                   | {"type": "numbered_list", "items": [...]}

_BLOCK_TYPES = {"paragraph", "bullet_list", "numbered_list"}


def _clean_block(block: dict) -> dict:
    btype = block.get("type")
    if btype == "paragraph":
        return {"type": "paragraph", "text": _norm_text(block.get("text", ""))}
    items = normalize_text_list(block.get("items", []))
    return {"type": btype, "items": items}


def _is_list_detected(text: str):
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    bullet = re.compile(r"^[\s\u2013\u2022-]\s+(.+)$")
    bullet_idx = [i for i, ln in enumerate(lines) if bullet.match(ln)]
    if len(bullet_idx) >= 2 and bullet_idx[0] >= 1:
        intro = " ".join(lines[:bullet_idx[0]]).strip()
        items = [lines[i] for i in bullet_idx]
        return intro, items
    return None, None


def _split_inline_list(text: str):
    """Split 'intro: item1; item2' into (intro, [items]) when >=2 items present."""
    m = re.match(r"^(.*?):\s+(.+)$", text)
    if not m:
        return None, None
    intro = m.group(1).strip()
    rest = m.group(2).strip()
    items = [x.strip() for x in re.split(r"[;]", rest) if x.strip()]
    if len(items) < 2:
        return None, None
    return intro, items


def _split_text_to_blocks(text: str) -> list[dict]:
    text = _norm_text(text)
    if not text:
        return []
    intro, items = _is_list_detected(text)
    if items:
        blocks = []
        if intro:
            blocks.append({"type": "paragraph", "text": intro})
        blocks.append({"type": "bullet_list", "items": items})
        return blocks
    sentences = _split_sentences(text)
    paragraphs = []
    cur = ""
    for s in sentences:
        if cur and len(cur) + len(s) > 420:
            paragraphs.append(cur)
            cur = s
        else:
            cur += (" " if cur else "") + s
    if cur.strip():
        paragraphs.append(cur.strip())
    blocks = []
    for para in paragraphs:
        intro2, items2 = _split_inline_list(para)
        if items2:
            if intro2:
                blocks.append({"type": "paragraph", "text": intro2})
            blocks.append({"type": "bullet_list", "items": items2})
        else:
            blocks.append({"type": "paragraph", "text": para})
    return blocks


def normalize_rich_text_blocks(value) -> list[dict]:
    """Normalize a value into a list of RichTextBlock dicts."""
    if value is None:
        return []
    if isinstance(value, list):
        blocks = []
        for v in value:
            if isinstance(v, dict) and v.get("type") in _BLOCK_TYPES:
                blocks.append(_clean_block(v))
            elif isinstance(v, str) and v.strip():
                blocks.extend(_split_text_to_blocks(v))
        return blocks
    if isinstance(value, dict) and value.get("type") in _BLOCK_TYPES:
        return [_clean_block(value)]
    if isinstance(value, str) and value.strip():
        return _split_text_to_blocks(value)
    return []


def render_rich_text_blocks(blocks) -> str:
    """Render a list of RichTextBlock dicts into safe HTML."""
    import html as html_mod
    out = []
    for block in blocks or []:
        if not isinstance(block, dict):
            out.append(f"<p>{html_mod.escape(_norm_text(str(block)))}</p>")
            continue
        btype = block.get("type")
        if btype == "paragraph":
            out.append(f"<p>{html_mod.escape(_norm_text(block.get('text', '')))}</p>")
        elif btype in ("bullet_list", "numbered_list"):
            items = normalize_text_list(block.get("items", []))
            lis = "".join(f"<li>{html_mod.escape(i)}</li>" for i in items)
            tag = "ol" if btype == "numbered_list" else "ul"
            if lis:
                out.append(f"<{tag}>{lis}</{tag}>")
    return "\n".join(o for o in out if o)


# ── Semantic key outcomes split ────────────────────────────────────

_OUTCOME_MARKERS = (
    "согласован", "согласовано", "зафиксирован", "зафиксирована", "зафиксировано",
    "назначена", "назначен", "принят", "принято", "утверждён", "определён",
    "предусмотрено", "запланировано", "договорились", "ближайшая", "достигнуто",
    "проведена", "запущена", "обеспечен",
)


def _balance_split(text: str, count: int) -> list[str]:
    sents = _split_sentences(text)
    if len(sents) <= 1:
        return [text]
    if len(sents) < count:
        return sents
    per = max(1, len(sents) // count)
    groups = []
    for i in range(0, len(sents), per):
        chunk = " ".join(sents[i:i + per]).strip()
        if chunk:
            groups.append(chunk)
    return groups if groups else [text]


def split_key_outcomes_semantically(text: str) -> list[str]:
    """Split a long key-outcomes string into independent semantic items.

    Only re-segments the given text; never invents facts. Uses marker-based
    splitting first, then falls back to balanced sentence grouping into 3+ items.
    """
    if not text or not str(text).strip():
        return []
    text = _norm_text(str(text))

    numbered = normalize_text_list(text)
    if len(numbered) >= 3:
        return numbered

    sentences = _split_sentences(text)
    groups: list[str] = []
    current = ""
    for s in sentences:
        head = s[:60].lower()
        starts_new = any(head.startswith(m) for m in _OUTCOME_MARKERS)
        if current and (starts_new or len(current) > 450):
            groups.append(current.strip())
            current = s
        else:
            current += (" " if current else "") + s
    if current.strip():
        groups.append(current.strip())

    if len(groups) < 3:
        joined = " ".join(groups) if groups else text
        return _balance_split(joined, 3)
    return groups


# ── Table cell fill helpers ───────────────────────────────────────

def fill_required(value) -> str:
    """Return a non-empty visible cell value."""
    v = _norm_text(value)
    return v if v else "Требуется назначить"


def fill_or(value, default: str) -> str:
    v = _norm_text(value)
    return v if v else default