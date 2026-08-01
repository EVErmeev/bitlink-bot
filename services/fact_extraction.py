import re
import uuid
from datetime import datetime, timedelta
from models.protocol import AtomicItem


SPEAKER_PATTERN = re.compile(
    r"^(?:\[(?P<timestamp>\d{2}:\d{2}(?::\d{2})?)\]\s*)?"
    r"(?P<speaker>[А-ЯЁA-Z][а-яёa-z]+\s*(?:[А-ЯЁA-Z]\.?\s*[А-ЯЁA-Z]\.?\s*)?)[.:]\s*",
    re.MULTILINE,
)

SPEAKER_LINE_PATTERN = re.compile(
    r"^(?P<speaker>[А-ЯЁ][а-яё]+\s*(?:[А-ЯЁ]\.?\s*[А-ЯЁ]\.?\s*|[\w]+))\s*[.:]\s*(?P<text>.*?)$",
    re.MULTILINE,
)

TIMESTAMP_LINE_PATTERN = re.compile(
    r"^\[(?P<timestamp>\d{2}:\d{2}(?::\d{2})?)\]\s*"
    r"(?:(?P<speaker>[А-ЯЁ][а-яё]+(?:\s+\w+)?)\s*[.:]\s*)?"
    r"(?P<text>.*?)$",
    re.MULTILINE,
)

DECISION_KEYWORDS = [
    r"решили", r"согласовали", r"договорились", r"принято", r"постановили",
    r"зафиксировали", r"утвердили", r"подтверждаем", r"согласен",
    r"поддерживаю", r"одобрено", r"принимаем", r"решение принято",
]

TASK_KEYWORDS = [
    r"нужно сделать", r"задача", r"поручение", r"необходимо",
    r"требуется", r"надо", r"следует", r"поручаю", r"назначаем",
    r"ответственный", r"план", r"запланировать", r"подготовить",
    r"разработать", r"протестировать", r"внедрить", r"срок",
]

RISK_KEYWORDS = [
    r"риск", r"проблема", r"ограничение", r"блокер", r"блокирует",
    r"угроза", r"опасность", r"зависимость", r"препятствие",
    r"сложность", r"затруднение", r"неопределённость",
]

QUESTION_KEYWORDS = [r"\?"]

DATE_PATTERNS = [
    re.compile(r"(\d{1,2})[.](\d{1,2})[.](\d{2,4})"),
    re.compile(r"(\d{2,4})[-.](\d{2})[-.](\d{2})"),
    re.compile(r"\bдо\s+(\d{1,2})\s+(января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря)\b", re.IGNORECASE),
]

PARTICIPANT_NAME_PATTERN = re.compile(
    r"\b([А-ЯЁ][а-яё]+)\s+([А-ЯЁ][а-яё]+(?:\s+[А-ЯЁ][а-яё]+)?)\b"
)

PROCESS_STEP_KEYWORDS = [
    r"этап", r"шаг", r"шагов", r"сначала", r"затем", r"после этого",
    r"далее", r"процесс", r"действие", r"операция",
]

SYSTEM_KEYWORDS = [
    r"система", r"модуль", r"программа", r"платформа", r"сервис",
    r"API", r"база данных", r"интерфейс", r"интеграция",
    r"1С", r"SAP", r"ERP", r"CRM",
]

PROPOSAL_KEYWORDS = [
    r"предлагаю", r"предложение", r"вариант", r"альтернатива",
    r"можно сделать", r"стоит рассмотреть", r"идея",
]

FACT_KEYWORDS = [
    r"факт", r"установлено", r"выявлено", r"обнаружено",
    r"подтверждено", r"доказано", r"известно",
]

DEPENDENCY_KEYWORDS = [
    r"зависит от", r"связано с", r"требует", r"влияет на",
    r"обусловлено", r"опирается на",
]

GAP_KEYWORDS = [
    r"разрыв", r"не покрывает", r"отсутствует", r"не реализовано",
    r"недостаток", r"пробел", r"не хватает", r"не поддерживает",
]


def _timestamp_to_seconds(ts: str | None) -> float | None:
    if not ts:
        return None
    parts = ts.split(":")
    if len(parts) == 2:
        return int(parts[0]) * 60 + int(parts[1])
    elif len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    return None


def _classify_item_type(text: str, text_lower: str) -> str:
    for kw in DECISION_KEYWORDS:
        if re.search(rf"\b{kw}\b", text_lower):
            return "решение"

    for kw in GAP_KEYWORDS:
        if re.search(rf"\b{kw}\b", text_lower):
            return "функциональный_разрыв"

    for kw in DEPENDENCY_KEYWORDS:
        if re.search(rf"\b{kw}\b", text_lower):
            return "зависимость"

    for kw in RISK_KEYWORDS:
        if re.search(rf"\b{kw}\b", text_lower):
            return "риск"

    for kw in PROPOSAL_KEYWORDS:
        if re.search(rf"\b{kw}\b", text_lower):
            return "предложение"

    for kw in TASK_KEYWORDS:
        if re.search(rf"\b{kw}\b", text_lower):
            return "задача"

    for kw in QUESTION_KEYWORDS:
        if re.search(rf"{kw}", text):
            return "вопрос"

    for kw in PROCESS_STEP_KEYWORDS:
        if re.search(rf"\b{kw}\b", text_lower):
            return "шаг_процесса"

    for kw in SYSTEM_KEYWORDS:
        if re.search(rf"\b{kw}\b", text_lower):
            return "объект_системы"

    for kw in FACT_KEYWORDS:
        if re.search(rf"\b{kw}\b", text_lower):
            return "факт"

    for dp in DATE_PATTERNS:
        if dp.search(text_lower):
            return "дата"

    return "факт"


def _extract_speaker(text: str) -> str:
    m = SPEAKER_LINE_PATTERN.match(text.strip())
    if m:
        return m.group("speaker").strip()
    return ""


def _extract_evidence(text: str, snippet: str) -> str:
    snippet = snippet.strip()
    idx = text.find(snippet)
    if idx >= 0:
        start = max(0, idx - 30)
        end = min(len(text), idx + len(snippet) + 30)
        return text[start:end].strip()
    return snippet[:60]


def _check_explicit_agreement(text: str) -> bool:
    agreement_keywords = [
        r"согласовали", r"договорились", r"принято", r"решили",
        r"постановили", r"утвердили", r"поддерживаю", r"согласен",
        r"одобрено", r"подтверждаем",
    ]
    text_lower = text.lower()
    for kw in agreement_keywords:
        if re.search(rf"\b{kw}\b", text_lower):
            return True
    return False


def _check_commitment(text: str) -> bool:
    commitment_keywords = [
        r"назначаем", r"поручаю", r"ответственный", r"сделает",
        r"выполнит", r"обеспечит", r"беру на себя", r"принято",
        r"договорились",
    ]
    text_lower = text.lower()
    for kw in commitment_keywords:
        if re.search(rf"\b{kw}\b", text_lower):
            return True
    return False


def _compute_importance(text: str) -> float:
    text_lower = text.lower()
    high_priority = [
        r"критично", r"срочно", r"важно", r"ключевой", r"приоритет",
        r"блокер", r"необходимо", r"обязательно",
    ]
    medium_priority = [
        r"желательно", r"нужно", r"следует", r"рекомендуется",
        r"запланировано",
    ]
    low_priority = [
        r"позже", r"в перспективе", r"возможно", r"опционально",
    ]

    for kw in high_priority:
        if re.search(rf"\b{kw}\b", text_lower):
            return 0.9
    for kw in medium_priority:
        if re.search(rf"\b{kw}\b", text_lower):
            return 0.6
    for kw in low_priority:
        if re.search(rf"\b{kw}\b", text_lower):
            return 0.3
    return 0.5


def _compute_confidence(text: str, item_type: str) -> float:
    text_lower = text.lower()
    high_conf = [
        r"точно", r"уверен", r"подтверждено", r"доказано",
        r"установлено", r"гарантированно",
    ]
    low_conf = [
        r"возможно", r"вероятно", r"предположительно", r"может быть",
        r"не уверен", r"под вопросом",
    ]

    for kw in high_conf:
        if re.search(rf"\b{kw}\b", text_lower):
            return 0.9
    for kw in low_conf:
        if re.search(rf"\b{kw}\b", text_lower):
            return 0.4

    type_defaults = {
        "решение": 0.85,
        "задача": 0.8,
        "риск": 0.75,
        "вопрос": 0.7,
        "факт": 0.65,
        "дата": 0.9,
    }
    return type_defaults.get(item_type, 0.6)


def _parse_transcript_lines(text: str) -> list[dict]:
    lines = text.strip().split("\n")
    parsed_lines = []

    current_speaker = ""
    current_timestamp = None

    for line in lines:
        line = line.strip()
        if not line:
            continue

        tm = TIMESTAMP_LINE_PATTERN.match(line)
        if tm:
            current_timestamp = tm.group("timestamp")
            speaker_candidate = (tm.group("speaker") or "").strip()
            content = tm.group("text").strip()
            if speaker_candidate:
                current_speaker = speaker_candidate
            if content:
                parsed_lines.append({
                    "speaker": current_speaker,
                    "timestamp": current_timestamp,
                    "text": content,
                })
            continue

        sm = SPEAKER_LINE_PATTERN.match(line)
        if sm:
            current_speaker = sm.group("speaker").strip()
            content = sm.group("text").strip()
            if content:
                parsed_lines.append({
                    "speaker": current_speaker,
                    "timestamp": None,
                    "text": content,
                })
            continue

        if parsed_lines:
            parsed_lines[-1]["text"] += " " + line
        else:
            parsed_lines.append({
                "speaker": "",
                "timestamp": None,
                "text": line,
            })

    return parsed_lines


def extract_atomic_items(text: str, source_context_id: str, source_sha256: str) -> list[AtomicItem]:
    items = []
    parsed = _parse_transcript_lines(text)

    for entry in parsed:
        line_text = entry["text"]
        line_lower = line_text.lower()
        speaker = entry["speaker"]
        ts_start = _timestamp_to_seconds(entry["timestamp"])

        if len(line_text) < 5:
            continue

        item_type = _classify_item_type(line_text, line_lower)
        importance = _compute_importance(line_text)
        confidence = _compute_confidence(line_text, item_type)
        explicit_agreement = _check_explicit_agreement(line_text) if item_type == "решение" else False
        commitment = _check_commitment(line_text) if item_type == "задача" else False
        evidence = _extract_evidence(text, line_text)

        item = AtomicItem(
            item_id=str(uuid.uuid4()),
            source_context_id=source_context_id,
            item_type=item_type,
            text=line_text.strip(),
            speaker=speaker,
            timestamp_start=ts_start,
            timestamp_end=None,
            importance=importance,
            confidence=confidence,
            explicit_agreement=explicit_agreement,
            commitment_confirmed=commitment,
            evidence=evidence,
        )
        items.append(item)

    date_items = _extract_date_items(text, source_context_id)
    items.extend(date_items)

    participant_items = _extract_participant_items(text, source_context_id)
    items.extend(participant_items)

    return items


def _extract_date_items(text: str, source_context_id: str) -> list[AtomicItem]:
    items = []
    seen = set()
    for pattern in DATE_PATTERNS:
        for match in pattern.finditer(text):
            date_str = match.group(0)
            if date_str in seen:
                continue
            seen.add(date_str)
            items.append(AtomicItem(
                item_id=str(uuid.uuid4()),
                source_context_id=source_context_id,
                item_type="дата",
                text=date_str,
                speaker="",
                timestamp_start=None,
                timestamp_end=None,
                importance=0.6,
                confidence=0.9,
                explicit_agreement=False,
                commitment_confirmed=False,
                evidence=date_str,
            ))
    return items


def _extract_participant_items(text: str, source_context_id: str) -> list[AtomicItem]:
    items = []
    seen = set()
    known_speakers = set()
    for m in SPEAKER_LINE_PATTERN.finditer(text):
        known_speakers.add(m.group("speaker").strip())

    for name in known_speakers:
        if name not in seen:
            seen.add(name)
            items.append(AtomicItem(
                item_id=str(uuid.uuid4()),
                source_context_id=source_context_id,
                item_type="участник",
                text=name,
                speaker="",
                timestamp_start=None,
                timestamp_end=None,
                importance=0.7,
                confidence=0.85,
                explicit_agreement=False,
                commitment_confirmed=False,
                evidence=name,
            ))
    return items