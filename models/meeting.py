from dataclasses import dataclass, field
from datetime import date, time
from typing import Optional


@dataclass
class MeetingMetadata:
    meeting_date: Optional[date] = None
    meeting_time: Optional[time] = None
    title: str = ""
    participants: list[dict] = field(default_factory=list)
    source_type: str = ""
    source_path: str = ""
    source_context_id: str = ""

    @property
    def date_str(self) -> str:
        if self.meeting_date:
            return self.meeting_date.isoformat()
        return "Дата не определена"

    @property
    def time_str(self) -> str:
        if self.meeting_time:
            return self.meeting_time.strftime("%H:%M")
        return ""

    @property
    def datetime_display(self) -> str:
        dt = self.date_str
        if self.meeting_time:
            dt += f" {self.time_str}"
        return dt

    def to_dict(self) -> dict:
        return {
            "meeting_date": self.meeting_date.isoformat() if self.meeting_date else None,
            "meeting_time": self.meeting_time.strftime("%H:%M") if self.meeting_time else None,
            "title": self.title,
            "participants": self.participants,
            "source_type": self.source_type,
            "source_path": self.source_path,
            "source_context_id": self.source_context_id,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "MeetingMetadata":
        m = cls()
        if d.get("meeting_date"):
            m.meeting_date = date.fromisoformat(d["meeting_date"])
        if d.get("meeting_time"):
            parts = d["meeting_time"].split(":")
            m.meeting_time = time(int(parts[0]), int(parts[1]))
        m.title = d.get("title", "")
        m.participants = d.get("participants", [])
        m.source_type = d.get("source_type", "")
        m.source_path = d.get("source_path", "")
        m.source_context_id = d.get("source_context_id", "")
        return m