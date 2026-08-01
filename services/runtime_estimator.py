import json
import time
from pathlib import Path
from datetime import datetime, timedelta

HISTORY_FILE = Path(__file__).resolve().parent / "data" / "runtime_history.json"


class RuntimeEstimator:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._history = []
            cls._instance._load()
        return cls._instance

    def _load(self):
        if HISTORY_FILE.exists():
            try:
                with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                    self._history = json.load(f)
            except (json.JSONDecodeError, IOError):
                self._history = []

    def _save(self):
        HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(self._history, f, indent=2, ensure_ascii=False)

    def record(self, source_type: str, template_id: str, mode: str,
               duration_seconds: float | None, word_count: int | None,
               actual_seconds: float, status: str):
        if status in ("failed", "cancelled"):
            return
        entry = {
            "source_type": source_type,
            "template_id": template_id,
            "mode": mode,
            "duration_seconds": duration_seconds,
            "word_count": word_count,
            "actual_seconds": actual_seconds,
            "recorded_at": datetime.now().isoformat(),
        }
        self._history.append(entry)
        self._save()

    def estimate(self, source_type: str, template_id: str, mode: str,
                 duration_seconds: float | None, word_count: int | None) -> tuple[float | None, str]:
        matching = [
            h for h in self._history
            if h["source_type"] == source_type
            and h["template_id"] == template_id
            and h["mode"] == mode
        ]
        if not matching:
            matching = [h for h in self._history if h["source_type"] == source_type]
        if not matching:
            return None, "Оставшееся время: расчёт..."

        avg = sum(h["actual_seconds"] for h in matching) / len(matching)

        if duration_seconds:
            ratio = avg / max(matching[0].get("duration_seconds", 1) or 1, 1)
            estimate = duration_seconds * ratio * 1.5
        elif word_count:
            ratio = avg / max(matching[0].get("word_count", 1) or 1, 1)
            estimate = word_count * ratio * 1.1
        else:
            estimate = avg

        if len(matching) < 3:
            return estimate, f"Предварительная оценка: {_format_time(estimate)}"

        return estimate, f"Примерно осталось: {_format_time(estimate)}"

    def estimate_batch_remaining(self, items: list) -> tuple[float | None, str]:
        total_estimate = 0.0
        for item in items:
            if item.status in ("completed", "failed", "cancelled", "skipped"):
                if item.actual_seconds:
                    total_estimate -= item.actual_seconds
            elif item.estimated_seconds:
                total_estimate += item.estimated_seconds
            else:
                est_tuple = self.estimate(
                    item.source_type, item.protocol_template, item.protocol_mode,
                    item.duration_seconds, item.word_count
                )
                if est_tuple[0]:
                    total_estimate += est_tuple[0]
                    item.estimated_seconds = est_tuple[0]

        if total_estimate <= 0:
            return 0, "Оставшееся время: расчёт..."

        return total_estimate, f"Примерно осталось: {_format_time(total_estimate)}"


def _format_time(seconds: float) -> str:
    td = timedelta(seconds=int(seconds))
    h, remainder = divmod(td.seconds, 3600)
    m, s = divmod(remainder, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"