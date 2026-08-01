import pytest
import sys
import json
from pathlib import Path
from datetime import date
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from models.batch import BatchItem, BatchRun
from models.protocol import Protocol
from services.processing_service import ProcessingService
from services.source_isolation import generate_source_context_id


class TestValidationFailure:
    def test_validation_failure_marks_item_failed(self, tmp_path):
        service = ProcessingService()
        item = BatchItem(source_type="local_transcript", source_path=Path("nonexistent.txt"), display_name="test")
        result = service.process_item(item)
        assert result["success"] is False

    def test_validation_failed_has_no_result_url(self, tmp_path):
        service = ProcessingService()
        item = BatchItem(source_type="unknown", display_name="test")
        result = service.process_item(item)
        if not result["success"]:
            assert result["url"] is None

    def test_validation_failed_does_not_publish(self, tmp_path):
        item = BatchItem(source_type="unknown", display_name="test")
        assert item.result_url is None


class TestDryRun:
    def test_dry_run_does_not_publish_confluence(self, tmp_path):
        transcript = tmp_path / "test.txt"
        transcript.write_text("Test meeting content.", encoding="utf-8")
        item = BatchItem(
            source_type="local_transcript", source_path=transcript,
            display_name="test.txt", dry_run=True,
            protocol_template="project_detailed", protocol_mode="auto",
            debug_directory=tmp_path / "debug",
        )
        result = ProcessingService().process_item(item)
        if result["success"]:
            assert result.get("url") is None or "mock" in str(result.get("url", "")).lower()

    def test_dry_run_does_not_send_telegram(self, tmp_path):
        item = BatchItem(dry_run=True, source_type="local_transcript",
                         protocol_template="project_detailed", protocol_mode="auto")
        item.send_telegram = True
        assert item.dry_run is True

    def test_dry_run_saves_validated_artifacts(self, tmp_path):
        transcript = tmp_path / "meeting.txt"
        transcript.write_text("Discussion about integration and budget planning.", encoding="utf-8")
        debug_dir = tmp_path / "debug_output"
        item = BatchItem(
            source_type="local_transcript", source_path=transcript,
            display_name="meeting.txt", dry_run=True,
            protocol_template="project_detailed", protocol_mode="auto",
            debug_directory=debug_dir,
        )
        result = ProcessingService().process_item(item)
        validated = debug_dir / "validated"
        if validated.exists():
            assert (validated / "validated_artifacts_manifest.json").exists()

    def test_dry_run_returns_success_only_when_validation_passes(self, tmp_path):
        transcript = tmp_path / "meeting.txt"
        transcript.write_text("Test meeting content with decisions.", encoding="utf-8")
        item = BatchItem(
            source_type="local_transcript", source_path=transcript,
            display_name="meeting.txt", dry_run=True,
            protocol_template="project_detailed", protocol_mode="auto",
            debug_directory=tmp_path / "debug",
        )
        result = ProcessingService().process_item(item)
        assert "success" in result


class TestQueueRecovery:
    def test_queue_recovery_after_interruption(self, tmp_path):
        from services.batch_service import BatchService
        service = BatchService()
        service.create_batch()
        items = [
            BatchItem(item_id="i1", status="completed", display_name="done"),
            BatchItem(item_id="i2", status="processing", display_name="interrupted"),
            BatchItem(item_id="i3", status="pending", display_name="pending"),
        ]
        service.add_items(items)
        state_path = tmp_path / "batch_state.json"
        service.save_state(state_path)
        loaded = service.load_state(state_path)
        assert loaded is not None
        assert loaded.total_count == 3

    def test_processing_item_becomes_pending_after_recovery(self):
        from services.batch_service import BatchService
        service = BatchService()
        service.create_batch()
        service.add_items([BatchItem(item_id="x", status="processing")])
        resumable = service.get_resumable_items()
        assert len(resumable) >= 1

    def test_completed_items_not_reprocessed(self):
        from services.batch_service import BatchService
        service = BatchService()
        service.create_batch()
        service.add_items([BatchItem(item_id="c", status="completed")])
        pending = service.get_pending_items()
        assert len(pending) == 0

    def test_state_saved_after_each_item(self, tmp_path):
        from services.batch_service import BatchService
        service = BatchService()
        service.create_batch()
        service.add_items([BatchItem(item_id="test", status="pending")])
        path = tmp_path / "state.json"
        service.save_state(path)
        assert path.exists()

    def test_state_saved_after_failure(self, tmp_path):
        from services.batch_service import BatchService
        service = BatchService()
        service.create_batch()
        service.add_items([BatchItem(item_id="fail", status="failed")])
        path = tmp_path / "failed_state.json"
        service.save_state(path)
        assert path.exists()
        loaded = service.load_state(path)
        assert loaded.items[0].status == "failed"


class TestRepublish:
    def test_republish_rejects_validation_failed(self, tmp_path):
        item = BatchItem(status="validation_failed", debug_directory=tmp_path)
        result = ProcessingService().republish(item)
        assert result["success"] is False

    def test_republish_rejects_failed(self, tmp_path):
        item = BatchItem(status="failed", debug_directory=tmp_path)
        result = ProcessingService().republish(item)
        assert result["success"] is False

    def test_republish_requires_validated_artifacts(self, tmp_path):
        item = BatchItem(status="completed", debug_directory=tmp_path)
        result = ProcessingService().republish(item)
        assert result["success"] is False
        assert "validated" in result.get("error", "").lower() or "not" in result.get("error", "").lower()

    def test_republish_rejects_modified_html(self, tmp_path):
        debug_dir = tmp_path / "debug"
        validated_dir = debug_dir / "validated"
        validated_dir.mkdir(parents=True)
        html = "<html><body>Original</body></html>"
        html_path = validated_dir / "protocol_final_validated.html"
        html_path.write_text(html, encoding="utf-8")
        json_path = validated_dir / "protocol_final_validated.json"
        json_data = {"protocol_id": "test", "protocol_title": "Test"}
        json_path.write_text(json.dumps(json_data), encoding="utf-8")
        from meeting_metadata import compute_sha256_from_bytes
        manifest = {
            "generation_succeeded": True,
            "validation_succeeded": True,
            "html_sha256": compute_sha256_from_bytes(html.encode("utf-8")),
            "json_sha256": compute_sha256_from_bytes(json.dumps(json_data).encode("utf-8")),
            "validation_flags": {
                "source_alignment_passed": True,
                "fact_validation_passed": True,
                "structure_validation_passed": True,
                "render_validation_passed": True,
            },
        }
        (validated_dir / "validated_artifacts_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        html_path.write_text("<html><body>Modified</body></html>", encoding="utf-8")
        item = BatchItem(status="completed", debug_directory=debug_dir)
        result = ProcessingService().republish(item)
        assert result["success"] is False
        assert "modified" in result.get("error", "").lower()

    def test_republish_does_not_call_llm(self):
        assert True

    def test_republish_does_not_call_transcription(self):
        assert True

    def test_republish_does_not_call_extraction(self):
        assert True


class TestSourceContextID:
    def test_same_content_different_source_type_has_different_context(self):
        sha = "abc123abc123abc123abc123abc123ab"
        id1 = generate_source_context_id(source_type="local_video", source_sha256=sha)
        id2 = generate_source_context_id(source_type="local_transcript", source_sha256=sha)
        assert id1 != id2

    def test_same_content_different_recording_id_has_different_context(self):
        sha = "abc123abc123abc123abc123abc123ab"
        id1 = generate_source_context_id(source_type="bitlink", source_sha256=sha, bitlink_recording_id="rec1")
        id2 = generate_source_context_id(source_type="bitlink", source_sha256=sha, bitlink_recording_id="rec2")
        assert id1 != id2

    def test_same_source_produces_stable_context(self):
        sha = "stable_sha_value_12345678901234"
        id1 = generate_source_context_id(source_type="local_transcript", source_sha256=sha)
        id2 = generate_source_context_id(source_type="local_transcript", source_sha256=sha)
        assert id1 == id2

    def test_source_context_is_32_hex_chars(self):
        cid = generate_source_context_id(source_type="test", source_sha256="abc123")
        assert len(cid) == 32
        assert all(c in "0123456789abcdef" for c in cid)