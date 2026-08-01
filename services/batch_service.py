import json
from pathlib import Path

from models.batch import BatchItem, BatchRun

try:
    from services.runtime_estimator import RuntimeEstimator
except ImportError:
    from runtime_estimator import RuntimeEstimator  # type: ignore[no-redef]


class BatchService:
    def __init__(self):
        self.batch_run = None
        self.estimator = RuntimeEstimator()

    def create_batch(self) -> BatchRun:
        self.batch_run = BatchRun()
        return self.batch_run

    def create_or_add(self, items: list[BatchItem]) -> BatchRun:
        if not self.batch_run:
            self.create_batch()
        self.batch_run.items.extend(items)
        return self.batch_run

    def add_items(self, items: list[BatchItem]):
        if not self.batch_run:
            self.create_batch()
        self.batch_run.items.extend(items)

    def remove_items(self, item_ids: list[str]):
        if not self.batch_run:
            return
        self.batch_run.items = [i for i in self.batch_run.items if i.item_id not in item_ids]

    def reorder_items(self, item_ids_ordered: list[str]):
        if not self.batch_run:
            return
        order_map = {iid: idx for idx, iid in enumerate(item_ids_ordered)}
        self.batch_run.items.sort(key=lambda x: order_map.get(x.item_id, 9999))

    def save_state(self, filepath: Path):
        if self.batch_run:
            filepath.parent.mkdir(parents=True, exist_ok=True)
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(self.batch_run.to_dict(), f, indent=2, ensure_ascii=False)

    def load_state(self, filepath: Path) -> BatchRun | None:
        if not filepath.exists():
            return None
        with open(filepath, encoding="utf-8") as f:
            data = json.load(f)
        self.batch_run = BatchRun.from_dict(data)
        return self.batch_run

    def get_pending_items(self) -> list[BatchItem]:
        if not self.batch_run:
            return []
        return [
            i for i in self.batch_run.items
            if i.status in ("pending", "validating", "ready")
        ]

    def get_resumable_items(self) -> list[dict]:
        if not self.batch_run:
            return []
        result = []
        for item in self.batch_run.items:
            if item.status == "processing":
                result.append({
                    "item_id": item.item_id,
                    "display_name": item.display_name,
                    "status": item.status,
                })
        return result

    def normalize_after_recovery(self):
        """Convert 'processing' items to 'pending' for recovery."""
        if not self.batch_run:
            return
        for item in self.batch_run.items:
            if item.status == "processing":
                item.status = "pending"
                item.status_message = "Recovered after interruption"
            elif item.status == "validation_failed":
                pass
            elif item.status == "failed":
                pass

    def archive_state(self, state_path):
        import shutil
        from datetime import datetime
        if state_path.exists():
            archive_name = state_path.with_name(f"batch_state_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
            shutil.move(str(state_path), str(archive_name))
