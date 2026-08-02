"""Content normalization utilities for protocol templates."""
import re


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
        # Try JSON array
        if text.startswith("[") and text.endswith("]"):
            try:
                import json
                parsed = json.loads(text)
                if isinstance(parsed, list):
                    return normalize_text_list(parsed)
            except Exception:
                pass
        # Split by numbered items: 1) 2) 3) or 1. 2. 3. or • or -
        parts = re.split(r'(?:^|\n)\s*(?:\d{1,2}[.)]\s*|\•\s*|-\s*)', text)
        items = [p.strip() for p in parts if p.strip()]
        if len(items) >= 2:
            return items
        # Split by newlines
        lines = [l.strip() for l in text.split('\n') if l.strip()]
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
    text = str(value).strip()
    if not text:
        return []
    # Split into sentences
    sentences = re.split(r'(?<=[.!?])\s+(?=[А-ЯA-Z])', text)
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
