"""Safe meeting-date/time extraction from local file names.

Design guarantees (TASK-2026-08-05-3A58494):
  * four-digit-year formats are checked before two-digit-year formats;
  * every pattern uses strict numeric boundaries (a lookbehind ``(?<!\\d)`` and
    a lookahead ``(?!\\d)``) so a candidate is never a suffix of a longer
    number (e.g. ``26_07_24...`` inside ``2026_07_24...``);
  * ``date()``/``time()`` remain the final calendar validation and any
    ``ValueError`` is caught inside the parser;
  * an invalid candidate is rejected and the parser moves to the next format;
  * no day/month guessing and no replacement of an invalid date with today's
    date;
  * ``extract_date_from_filename`` always returns ``(date|None, time|None)``
    and never raises for a user-supplied name.
"""
from __future__ import annotations

import hashlib
import re
from datetime import date, time

# ── explicit, boundary-safe formats ──────────────────────────────────────
# Four-digit-year formats (with seconds optional) come FIRST.

# YYYY_MM_DD_HH_MM_SS / YYYY-MM-DD-HH-MM-SS / YYYY.MM.DD.HH.MM.SS / YYYY_MM_DD_HH_MM
_PATTERN_YYYY_MM_DD_TIME = re.compile(
    r"(?<!\d)(\d{4})[_\-.](\d{2})[_\-.](\d{2})"
    r"[T_ \-.](\d{2})[_\-.](\d{2})(?:[_\-.](\d{2}))?(?!\d)"
)
# YYYY_MM_DD / YYYY-MM-DD / YYYY.MM.DD
_PATTERN_YYYY_MM_DD = re.compile(
    r"(?<!\d)(\d{4})[_\-.](\d{2})[_\-.](\d{2})(?!\d)"
)
# DD.MM.YYYY / DD_MM_YYYY / DD-MM-YYYY
_PATTERN_DD_MM_YYYY = re.compile(
    r"(?<!\d)(\d{2})[_\-.](\d{2})[_\-.](\d{4})(?!\d)"
)
# DD_MM_YY_HH_MM_SS / DD-MM-YY-HH-MM-SS (two-digit year) — LAST.
_PATTERN_DD_MM_YY_TIME = re.compile(
    r"(?<!\d)(\d{2})[_\-.](\d{2})[_\-.](\d{2})"
    r"[_\-.](\d{2})[_\-.](\d{2})(?:[_\-.](\d{2}))?(?!\d)"
)

# Ordered: four-digit first, date-only last. "has_time" formats are checked
# before their date-only siblings so an invalid time rejects the candidate
# instead of silently degrading to a date.
_DATE_FORMATS = [
    ("YYYY_MM_DD_HH_MM_SS", _PATTERN_YYYY_MM_DD_TIME, True),
    ("DD_MM_YY_HH_MM_SS", _PATTERN_DD_MM_YY_TIME, True),
]
_DATE_ONLY_FORMATS = [
    ("YYYY_MM_DD", _PATTERN_YYYY_MM_DD, False),
    ("DD_MM_YYYY", _PATTERN_DD_MM_YYYY, False),
]


def _to_yyyy(yy: int) -> int:
    if yy <= 79:
        return 2000 + yy
    return 1900 + yy


def _safe_build_datetime_candidate(
    *,
    year: int,
    month: int,
    day: int,
    hour: int | None = None,
    minute: int | None = None,
    second: int | None = None,
) -> tuple[date | None, time | None]:
    """Final calendar validation. Returns (None, None) instead of raising.

    ``second`` is validated but intentionally NOT returned: the protocol title
    shows hour:minute only (e.g. ``09:14``), matching the control expectation.
    """
    try:
        d = date(year, month, day)
    except (ValueError, OverflowError, TypeError):
        return None, None
    if hour is None and minute is None:
        return d, None
    # Validate hour/minute (and second if present) even though seconds are
    # not returned.
    try:
        time(hour or 0, minute or 0, second or 0)
    except (ValueError, OverflowError, TypeError):
        return None, None
    return d, time(hour or 0, minute or 0)


def _match_into(name: str) -> tuple[date | None, time | None, str, int]:
    """Try every format on ``name`` (stem, no extension).

    Returns (date, time, matched_format, invalid_candidates_count).
    ``invalid_candidates_count`` counts regex hits that failed calendar
    validation (i.e. were rejected, not just skipped).

    Time formats are checked first: if a time pattern matched but the datetime
    is invalid, the candidate is fully rejected (no silent date-only fallback
    that would hide an invalid time).
    """
    invalid = 0

    # Phase 1: full datetime formats (four-digit then two-digit year).
    for fmt, pattern, _has_time in _DATE_FORMATS:
        match = pattern.search(name)
        if not match:
            continue
        if fmt == "DD_MM_YY_HH_MM_SS":
            dd = int(match.group(1))
            mm = int(match.group(2))
            yy = _to_yyyy(int(match.group(3)))
            h = int(match.group(4))
            mi = int(match.group(5))
            s = int(match.group(6)) if match.lastindex and match.group(6) else None
        else:  # YYYY_MM_DD_HH_MM_SS
            yy = int(match.group(1))
            mm = int(match.group(2))
            dd = int(match.group(3))
            h = int(match.group(4))
            mi = int(match.group(5))
            s = int(match.group(6)) if match.lastindex and match.group(6) else None
        d, t = _safe_build_datetime_candidate(year=yy, month=mm, day=dd,
                                              hour=h, minute=mi, second=s)
        if d is not None:
            return d, t, fmt, invalid
        invalid += 1
        # A time format matched but the candidate is invalid -> reject entirely
        # (do not reduce to a date-only value, which would be silently wrong).
        return None, None, "", invalid

    # Phase 2: date-only formats.
    for fmt, pattern, _has_time in _DATE_ONLY_FORMATS:
        match = pattern.search(name)
        if not match:
            continue
        if fmt == "DD_MM_YYYY":
            dd = int(match.group(1))
            mm = int(match.group(2))
            yy = int(match.group(3))
        else:  # YYYY_MM_DD
            yy = int(match.group(1))
            mm = int(match.group(2))
            dd = int(match.group(3))
        d, t = _safe_build_datetime_candidate(year=yy, month=mm, day=dd)
        if d is not None:
            return d, t, fmt, invalid
        invalid += 1
    return None, None, "", invalid


def extract_date_from_filename(filepath) -> tuple[date | None, time | None]:
    """Return (date|None, time|None) from a file path/name. Never raises."""
    name = getattr(filepath, "stem", None)
    if name is None:
        name = str(filepath)
        # strip a trailing extension for a raw string
        name = re.sub(r"\.[A-Za-z0-9]{1,5}$", "", name)
    d, t, _fmt, _invalid = _match_into(str(name))
    return d, t


def compute_sha256(filepath):
    sha = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            sha.update(chunk)
    return sha.hexdigest()


def compute_sha256_from_bytes(data):
    return hashlib.sha256(data).hexdigest()


def count_words(text):
    return len(text.split())


def determine_meeting_date(
    user_date=None,
    bitlink_metadata=None,
    filepath=None,
    file_metadata=None,
):
    """Priority: user_date -> bitlink_metadata -> valid filename -> file_metadata -> None.

    A filename that yields an invalid/unresolved date is ignored so the caller
    can fall back to ``file_metadata``.
    """
    if user_date:
        return user_date, None

    if bitlink_metadata:
        bitlink_date = bitlink_metadata.get("date")
        if bitlink_date:
            if isinstance(bitlink_date, str):
                try:
                    return date.fromisoformat(bitlink_date), None
                except ValueError:
                    pass
            elif isinstance(bitlink_date, date):
                return bitlink_date, None

    if filepath:
        try:
            d, t = extract_date_from_filename(filepath)
        except Exception:
            d, t = None, None
        if d:
            return d, t

    if file_metadata:
        meta_date = file_metadata.get("date")
        if meta_date:
            if isinstance(meta_date, str):
                try:
                    return date.fromisoformat(meta_date), None
                except ValueError:
                    pass
            elif isinstance(meta_date, date):
                return meta_date, None

    return None, None


def diagnose_date_resolution(filepath, file_metadata=None) -> dict:
    """Safe diagnostics object (TASK §12). Never raises for a user name."""
    name = getattr(filepath, "name", None) or str(filepath)
    stem = getattr(filepath, "stem", None)
    stem = str(stem) if stem else name
    d, t, matched_fmt, invalid = _match_into(stem)
    fallback_used = d is None
    source = "filename" if d else ("metadata" if file_metadata and file_metadata.get("date") else "none")
    return {
        "meeting_date": d.isoformat() if d else None,
        "meeting_time": (t.strftime("%H:%M") if t else None),
        "source": source,
        "matched_format": matched_fmt or None,
        "filename_basename": name,
        "invalid_candidates_count": invalid,
        "fallback_used": fallback_used,
    }
