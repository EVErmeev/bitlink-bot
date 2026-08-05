import uuid
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class BatchItem:
    item_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source_type: str = ""
    source_path: Path | None = None
    bitlink_room_id: str | None = None
    bitlink_recording_id: str | None = None
    display_name: str = ""
    file_size_bytes: int | None = None
    duration_seconds: float | None = None
    word_count: int | None = None
    protocol_template: str = "project_detailed"
    protocol_mode: str = "auto"
    parent_page_id: str | None = None
    parent_page_title: str | None = None
    send_telegram: bool = True
    dry_run: bool = False
    source_context_id: str | None = None
    source_sha256: str | None = None
    status: str = "pending"
    status_message: str = ""
    result_url: str | None = None
    debug_directory: Path | None = None
    error_details: str | None = None
    estimated_seconds: float | None = None
    actual_seconds: float | None = None
    client_name: str = ""
    project_name: str = ""

    def to_dict(self) -> dict:
        return {
            "item_id": self.item_id,
            "source_type": self.source_type,
            "source_path": str(self.source_path) if self.source_path else None,
            "bitlink_room_id": self.bitlink_room_id,
            "bitlink_recording_id": self.bitlink_recording_id,
            "display_name": self.display_name,
            "file_size_bytes": self.file_size_bytes,
            "duration_seconds": self.duration_seconds,
            "word_count": self.word_count,
            "protocol_template": self.protocol_template,
            "protocol_mode": self.protocol_mode,
            "parent_page_id": self.parent_page_id,
            "parent_page_title": self.parent_page_title,
            "send_telegram": self.send_telegram,
            "dry_run": self.dry_run,
            "source_context_id": self.source_context_id,
            "source_sha256": self.source_sha256,
            "status": self.status,
            "status_message": self.status_message,
            "result_url": self.result_url,
            "debug_directory": str(self.debug_directory) if self.debug_directory else None,
            "error_details": self.error_details,
            "estimated_seconds": self.estimated_seconds,
            "actual_seconds": self.actual_seconds,
            "client_name": self.client_name,
            "project_name": self.project_name,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "BatchItem":
        item = cls()
        item.item_id = d.get("item_id", str(uuid.uuid4()))
        item.source_type = d.get("source_type", "")
        if d.get("source_path"):
            item.source_path = Path(d["source_path"])
        item.bitlink_room_id = d.get("bitlink_room_id")
        item.bitlink_recording_id = d.get("bitlink_recording_id")
        item.display_name = d.get("display_name", "")
        item.file_size_bytes = d.get("file_size_bytes")
        item.duration_seconds = d.get("duration_seconds")
        item.word_count = d.get("word_count")
        item.protocol_template = d.get("protocol_template", "project_detailed")
        item.protocol_mode = d.get("protocol_mode", "auto")
        item.parent_page_id = d.get("parent_page_id")
        item.parent_page_title = d.get("parent_page_title")
        item.send_telegram = d.get("send_telegram", True)
        item.dry_run = d.get("dry_run", False)
        item.source_context_id = d.get("source_context_id")
        item.source_sha256 = d.get("source_sha256")
        item.status = d.get("status", "pending")
        item.status_message = d.get("status_message", "")
        item.result_url = d.get("result_url")
        if d.get("debug_directory"):
            item.debug_directory = Path(d["debug_directory"])
        item.error_details = d.get("error_details")
        item.estimated_seconds = d.get("estimated_seconds")
        item.actual_seconds = d.get("actual_seconds")
        item.client_name = d.get("client_name", "")
        item.project_name = d.get("project_name", "")
        return item


@dataclass
class BatchRun:
    batch_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    items: list[BatchItem] = field(default_factory=list)
    current_index: int = -1
    status: str = "pending"
    started_at: str | None = None
    completed_at: str | None = None
    stop_after_current: bool = False
    cancel_requested: bool = False

    def to_dict(self) -> dict:
        return {
            "batch_id": self.batch_id,
            "items": [item.to_dict() for item in self.items],
            "current_index": self.current_index,
            "status": self.status,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "stop_after_current": self.stop_after_current,
            "cancel_requested": self.cancel_requested,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "BatchRun":
        run = cls()
        run.batch_id = d.get("batch_id", str(uuid.uuid4()))
        run.items = [BatchItem.from_dict(i) for i in d.get("items", [])]
        run.current_index = d.get("current_index", -1)
        run.status = d.get("status", "pending")
        run.started_at = d.get("started_at")
        run.completed_at = d.get("completed_at")
        run.stop_after_current = d.get("stop_after_current", False)
        run.cancel_requested = d.get("cancel_requested", False)
        return run

    @property
    def total_count(self) -> int:
        return len(self.items)

    @property
    def current_item(self) -> BatchItem | None:
        if 0 <= self.current_index < len(self.items):
            return self.items[self.current_index]
        return None

    @property
    def completed_count(self) -> int:
        return sum(1 for i in self.items if i.status == "completed")

    @property
    def failed_count(self) -> int:
        return sum(1 for i in self.items if i.status == "failed")
