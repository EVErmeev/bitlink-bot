import hashlib
import re
from datetime import date, time
from pathlib import Path

DATE_PATTERNS = [
    (re.compile(r"(\d{4})[_\-.](\d{2})[_\-.](\d{2})[T_ ](\d{2})[_\-.](\d{2})"), True),
    (re.compile(r"(\d{4})[_\-.](\d{2})[_\-.](\d{2})"), False),
]


def extract_date_from_filename(filepath: Path) -> tuple[date | None, time | None]:
    name = filepath.stem
    for pattern, has_time in DATE_PATTERNS:
        match = pattern.search(name)
        if match:
            y, m, d = int(match.group(1)), int(match.group(2)), int(match.group(3))
            meeting_date = date(y, m, d)
            meeting_time = None
            if has_time:
                h, mi = int(match.group(4)), int(match.group(5))
                meeting_time = time(h, mi)
            return meeting_date, meeting_time
    return None, None


def compute_sha256(filepath: Path) -> str:
    sha = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            sha.update(chunk)
    return sha.hexdigest()


def compute_sha256_from_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def count_words(text: str) -> int:
    return len(text.split())


def determine_meeting_date(
    user_date: date | None = None,
    bitlink_metadata: dict | None = None,
    filepath: Path | None = None,
    file_metadata: dict | None = None,
) -> tuple[date | None, time | None]:
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
        d, t = extract_date_from_filename(filepath)
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
