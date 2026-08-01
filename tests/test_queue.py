import pytest
import sys
import json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from models.batch import BatchItem, BatchRun
from services.batch_service import BatchService
from services.runtime_estimator import RuntimeEstimator


class TestBatchModels:
    def test_batch_item_defaults(self):
        item = BatchItem()
        assert item.status == "pending"
        assert item.protocol_template == "project_detailed"
        assert item.protocol_mode == "auto"
        assert item.send_telegram is True

    def test_batch_item_to_from_dict(self):
        item = BatchItem(
            source_type="local_transcript",
            source_path=Path("/test/meeting.txt"),
            display_name="meeting.txt",
            protocol_template="management_summary",
            status="pending",
        )
        d = item.to_dict()
        restored = BatchItem.from_dict(d)
        assert restored.source_type == "local_transcript"
        assert restored.display_name == "meeting.txt"
        assert restored.protocol_template == "management_summary"

    def test_batch_item_unique_ids(self):
        items = [BatchItem() for _ in range(5)]
        ids = [i.item_id for i in items]
        assert len(set(ids)) == 5

    def test_batch_run_defaults(self):
        run = BatchRun()
        assert run.status == "pending"
        assert run.current_index == -1
        assert run.total_count == 0

    def test_batch_run_properties(self):
        item1 = BatchItem(status="completed")
        item2 = BatchItem(status="failed")
        item3 = BatchItem(status="pending")
        run = BatchRun(items=[item1, item2, item3])
        assert run.total_count == 3
        assert run.completed_count == 1
        assert run.failed_count == 1
        assert run.current_item is None

    def test_batch_run_current_item(self):
        items = [BatchItem(), BatchItem(), BatchItem()]
        run = BatchRun(items=items, current_index=1)
        assert run.current_item == items[1]

    def test_batch_run_to_from_dict(self):
        items = [BatchItem(display_name="test1"), BatchItem(display_name="test2")]
        run = BatchRun(items=items, current_index=0, status="processing")
        d = run.to_dict()
        restored = BatchRun.from_dict(d)
        assert restored.total_count == 2
        assert restored.current_index == 0
        assert restored.items[0].display_name == "test1"

    def test_batch_item_statuses(self):
        item = BatchItem()
        valid_statuses = ["pending", "validating", "ready", "processing", "completed", "failed", "cancelled", "skipped"]
        for status in valid_statuses:
            item.status = status
            assert item.status == status


class TestBatchService:
    def test_create_batch(self):
        service = BatchService()
        batch = service.create_batch()
        assert batch is not None
        assert batch.total_count == 0
        assert batch.status == "pending"

    def test_add_items(self):
        service = BatchService()
        service.create_batch()
        items = [BatchItem(display_name="test1"), BatchItem(display_name="test2")]
        service.add_items(items)
        assert service.batch_run.total_count == 2

    def test_create_or_add(self):
        service = BatchService()
        items = [BatchItem(display_name="test")]
        batch = service.create_or_add(items)
        assert batch.total_count == 1

    def test_remove_items(self):
        service = BatchService()
        service.create_batch()
        item1 = BatchItem(display_name="keep")
        item2 = BatchItem(display_name="remove")
        service.add_items([item1, item2])
        assert service.batch_run.total_count == 2
        service.remove_items([item2.item_id])
        assert service.batch_run.total_count == 1
        assert service.batch_run.items[0].display_name == "keep"

    def test_remove_multiple_items(self):
        service = BatchService()
        service.create_batch()
        items = [BatchItem() for _ in range(5)]
        service.add_items(items)
        service.remove_items([items[1].item_id, items[3].item_id])
        assert service.batch_run.total_count == 3

    def test_reorder_items(self):
        service = BatchService()
        service.create_batch()
        item1 = BatchItem(display_name="first")
        item2 = BatchItem(display_name="second")
        item3 = BatchItem(display_name="third")
        service.add_items([item1, item2, item3])
        service.reorder_items([item3.item_id, item1.item_id, item2.item_id])
        assert service.batch_run.items[0].display_name == "third"
        assert service.batch_run.items[1].display_name == "first"
        assert service.batch_run.items[2].display_name == "second"

    def test_save_and_load_state(self, tmp_path):
        state_file = tmp_path / "batch_state.json"
        service = BatchService()
        service.create_batch()
        service.add_items([BatchItem(display_name="test_save")])
        service.save_state(state_file)
        assert state_file.exists()

        service2 = BatchService()
        loaded = service2.load_state(state_file)
        assert loaded is not None
        assert loaded.total_count == 1
        assert loaded.items[0].display_name == "test_save"

    def test_load_nonexistent_state(self, tmp_path):
        service = BatchService()
        result = service.load_state(tmp_path / "nonexistent.json")
        assert result is None

    def test_get_pending_items(self):
        service = BatchService()
        service.create_batch()
        items = [
            BatchItem(status="pending"),
            BatchItem(status="completed"),
            BatchItem(status="ready"),
            BatchItem(status="validating"),
        ]
        service.add_items(items)
        pending = service.get_pending_items()
        assert len(pending) == 3  # pending, ready, validating

    def test_get_resumable_items(self):
        service = BatchService()
        service.create_batch()
        items = [
            BatchItem(status="processing", display_name="in_progress"),
            BatchItem(status="completed", display_name="done"),
        ]
        service.add_items(items)
        resumable = service.get_resumable_items()
        assert len(resumable) == 1
        assert resumable[0]["display_name"] == "in_progress"


class TestRuntimeEstimator:
    def test_estimate_no_history(self):
        estimator = RuntimeEstimator()
        estimator._history = []
        est, msg = estimator.estimate("local_transcript", "project_detailed", "auto", None, 1000)
        assert est is None or "расчёт" in msg.lower()

    def test_record_and_estimate(self):
        estimator = RuntimeEstimator()
        estimator._history = []
        estimator.record("local_transcript", "project_detailed", "auto", None, 1000, 30.0, "completed")
        estimator.record("local_transcript", "project_detailed", "auto", None, 1200, 35.0, "completed")
        estimator.record("local_transcript", "project_detailed", "auto", None, 900, 28.0, "completed")
        est, msg = estimator.estimate("local_transcript", "project_detailed", "auto", None, 1000)
        assert est is not None
        assert est > 0

    def test_failed_runs_not_counted(self):
        estimator = RuntimeEstimator()
        estimator._history = []
        estimator.record("local_transcript", "project_detailed", "auto", None, 1000, 999.0, "failed")
        est, msg = estimator.estimate("local_transcript", "project_detailed", "auto", None, 1000)
        assert est is None  # no valid history

    def test_cancelled_runs_not_counted(self):
        estimator = RuntimeEstimator()
        estimator._history = []
        estimator.record("local_transcript", "project_detailed", "auto", None, 1000, 999.0, "cancelled")
        est, msg = estimator.estimate("local_transcript", "project_detailed", "auto", None, 1000)
        assert est is None

    def test_estimate_batch_remaining(self):
        estimator = RuntimeEstimator()
        estimator._history = []
        estimator.record("local_transcript", "project_detailed", "auto", None, 1000, 60.0, "completed")

        items = [
            BatchItem(source_type="local_transcript", protocol_template="project_detailed",
                      protocol_mode="auto", word_count=1000, status="pending"),
            BatchItem(source_type="local_transcript", protocol_template="project_detailed",
                      protocol_mode="auto", word_count=500, status="pending"),
        ]
        total, msg = estimator.estimate_batch_remaining(items)
        assert total is not None
        assert total > 0

    def test_estimate_with_completed_items(self):
        estimator = RuntimeEstimator()
        estimator._history = []
        estimator.record("local_transcript", "project_detailed", "auto", None, 1000, 60.0, "completed")

        items = [
            BatchItem(source_type="local_transcript", protocol_template="project_detailed",
                      protocol_mode="auto", word_count=1000, status="completed", actual_seconds=60.0),
            BatchItem(source_type="local_transcript", protocol_template="project_detailed",
                      protocol_mode="auto", word_count=500, status="pending"),
        ]
        total, msg = estimator.estimate_batch_remaining(items)
        assert total is not None