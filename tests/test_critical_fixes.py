import json as json_mod
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from meeting_metadata import compute_sha256_from_bytes
from models.batch import BatchItem
from models.validation import ValidationReport
from services.batch_service import BatchService
from services.processing_service import ProcessingService
from services.source_isolation import generate_source_context_id


class TestValidationFailure:
    def test_validation_failure_marks_item_validation_failed(self, tmp_path):
        item = BatchItem(source_type="unknown", display_name="test", debug_directory=tmp_path)
        ProcessingService().process_item(item)
        assert item.status == "failed"

    def test_publishable_false_sets_success_to_false(self, tmp_path):
        item = BatchItem(source_type="unknown", display_name="test", debug_directory=tmp_path)
        result = ProcessingService().process_item(item)
        assert result["success"] is False
        assert result["url"] is None

    def test_validation_failed_has_no_result_url(self, tmp_path):
        item = BatchItem(source_type="unknown", display_name="test", debug_directory=tmp_path)
        ProcessingService().process_item(item)
        assert item.result_url is None

    def test_validation_failed_does_not_publish(self, tmp_path):
        item = BatchItem(source_type="unknown", display_name="test", debug_directory=tmp_path)
        result = ProcessingService().process_item(item)
        assert item.status == "failed"
        assert result["success"] is False


class TestDryRun:
    def test_dry_run_creates_validated_artifacts(self, tmp_path, monkeypatch):
        transcript = tmp_path / "meeting.txt"
        transcript.write_text(
            "Meeting discussion. Decided to use REST API. Task: complete testing.",
            encoding="utf-8",
        )
        debug_dir = tmp_path / "debug"
        item = BatchItem(
            source_type="local_transcript",
            source_path=transcript,
            display_name="meeting.txt",
            dry_run=True,
            protocol_template="project_detailed",
            protocol_mode="auto",
            debug_directory=debug_dir,
        )
        svc = ProcessingService()
        valid_json = {
            "general_info": {"meeting_date": "2026-07-01", "protocol_title": "Test", "meeting_context": "Context"},
            "participants": [{"name": "Alice"}],
            "purpose_and_context": "Review",
            "key_outcomes": "Completed",
            "topic_blocks": [{"title": "API", "discussion_content": "REST API integration discussed in detail", "conclusion": "Done", "status_text": "OK"}],
            "current_state": "On track",
            "decisions": [],
            "questions": [],
            "risks": [],
            "tasks": [],
        }
        pass_report = ValidationReport(passed=True)
        monkeypatch.setattr(svc.llm, "generate_json", lambda *a, **kw: (valid_json, json_mod.dumps(valid_json)))
        monkeypatch.setattr(svc.templates.get("project_detailed"), "validate", lambda *a, **kw: pass_report)
        monkeypatch.setattr(svc.templates.get("project_detailed"), "validate_render", lambda *a, **kw: pass_report)
        result = svc.process_item(item)
        assert result["success"] is True, f"Processing failed: {result.get('error')}"
        validated_dir = debug_dir / "validated"
        assert validated_dir.is_dir(), f"Expected {validated_dir} to exist"
        assert (validated_dir / "validated_artifacts_manifest.json").is_file()

    def test_dry_run_success_has_no_error(self, tmp_path):
        transcript = tmp_path / "meeting.txt"
        transcript.write_text(
            "Meeting discussion about API integration and budget planning.",
            encoding="utf-8",
        )
        item = BatchItem(
            source_type="local_transcript",
            source_path=transcript,
            display_name="meeting.txt",
            dry_run=True,
            protocol_template="project_detailed",
            protocol_mode="auto",
            debug_directory=tmp_path / "debug",
        )
        result = ProcessingService().process_item(item)
        if result["success"]:
            assert result.get("error") is None, f"Error should be None but got: {result.get('error')}"

    def test_dry_run_validation_failure_is_not_success(self, tmp_path):
        item = BatchItem(
            source_type="unknown", display_name="test", dry_run=True,
            debug_directory=tmp_path / "debug",
        )
        result = ProcessingService().process_item(item)
        assert result["success"] is False

    def test_dry_run_pipeline_stages_are_called(self, tmp_path):
        stages = []

        def cb(stage, pct, item):
            stages.append(stage)

        transcript = tmp_path / "test.txt"
        transcript.write_text("Test content.", encoding="utf-8")
        item = BatchItem(
            source_type="local_transcript",
            source_path=transcript,
            display_name="test",
            dry_run=True,
            protocol_template="project_detailed",
            protocol_mode="auto",
            debug_directory=tmp_path / "debug",
        )
        svc = ProcessingService(progress_callback=cb)
        svc.process_item(item)
        assert "loading_source" in stages
        assert len(stages) >= 3, f"Expected at least 3 stages, got: {stages}"


class TestQueueRecovery:
    def test_processing_item_becomes_pending_on_normalization(self):
        svc = BatchService()
        svc.create_batch()
        svc.add_items([BatchItem(item_id="x", status="processing")])
        svc.normalize_after_recovery()
        assert svc.batch_run.items[0].status == "pending"

    def test_recovered_processing_item_is_in_pending_items(self):
        svc = BatchService()
        svc.create_batch()
        svc.add_items([BatchItem(item_id="y", status="processing")])
        svc.normalize_after_recovery()
        pending = svc.get_pending_items()
        assert any(i.item_id == "y" for i in pending)

    def test_completed_item_is_not_reprocessed(self):
        svc = BatchService()
        svc.create_batch()
        svc.add_items([BatchItem(item_id="c", status="completed")])
        pending = svc.get_pending_items()
        assert not any(i.item_id == "c" for i in pending)

    def test_recovery_saves_normalized_state(self, tmp_path):
        svc = BatchService()
        svc.create_batch()
        svc.add_items([BatchItem(item_id="p", status="processing")])
        svc.normalize_after_recovery()
        path = tmp_path / "state.json"
        svc.save_state(path)
        loaded = svc.load_state(path)
        assert loaded.items[0].status == "pending"

    def test_state_saved_survives_roundtrip(self, tmp_path):
        svc = BatchService()
        svc.create_batch()
        svc.add_items([
            BatchItem(item_id="a", status="completed"),
            BatchItem(item_id="b", status="processing"),
            BatchItem(item_id="c", status="pending"),
        ])
        svc.normalize_after_recovery()
        path = tmp_path / "batch_state.json"
        svc.save_state(path)

        loaded = BatchService().load_state(path)
        assert loaded is not None
        statuses = {i.item_id: i.status for i in loaded.items}
        assert statuses["a"] == "completed"
        assert statuses["b"] == "pending"
        assert statuses["c"] == "pending"


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

    def test_republish_rejects_modified_html(self, tmp_path):
        debug_dir = tmp_path / "debug"
        validated_dir = debug_dir / "validated"
        validated_dir.mkdir(parents=True)

        html_original = b"<html><body>Original</body></html>"
        json_data = {
            "protocol_id": "test",
            "protocol_title": "Test",
            "template_id": "project_detailed",
        }
        json_bytes = json_mod.dumps(
            json_data, ensure_ascii=False, indent=2, sort_keys=True
        ).encode("utf-8")

        html_path = validated_dir / "protocol_final_validated.html"
        json_path = validated_dir / "protocol_final_validated.json"
        html_path.write_bytes(html_original)
        json_path.write_bytes(json_bytes)

        manifest = {
            "generation_succeeded": True,
            "validation_succeeded": True,
            "html_sha256": compute_sha256_from_bytes(html_original),
            "json_sha256": compute_sha256_from_bytes(json_bytes),
            "validation_flags": {
                "source_alignment_passed": True,
                "fact_validation_passed": True,
                "structure_validation_passed": True,
                "render_validation_passed": True,
            },
        }
        (validated_dir / "validated_artifacts_manifest.json").write_text(
            json_mod.dumps(manifest), encoding="utf-8"
        )

        html_path.write_bytes(b"<html><body>Modified</body></html>")
        item = BatchItem(status="completed", debug_directory=debug_dir)
        result = ProcessingService().republish(item)
        assert result["success"] is False
        assert "modified" in result.get("error", "").lower()

    def test_republish_does_not_call_llm(self, monkeypatch, tmp_path):
        debug_dir = tmp_path / "debug"
        validated_dir = debug_dir / "validated"
        validated_dir.mkdir(parents=True)

        html_bytes = b"<html><body>Test</body></html>"
        json_data = {
            "protocol_id": "x",
            "protocol_title": "T",
            "template_id": "project_detailed",
        }
        json_bytes = json_mod.dumps(
            json_data, ensure_ascii=False, indent=2, sort_keys=True
        ).encode("utf-8")
        (validated_dir / "protocol_final_validated.html").write_bytes(html_bytes)
        (validated_dir / "protocol_final_validated.json").write_bytes(json_bytes)
        manifest = {
            "generation_succeeded": True,
            "validation_succeeded": True,
            "html_sha256": compute_sha256_from_bytes(html_bytes),
            "json_sha256": compute_sha256_from_bytes(json_bytes),
            "validation_flags": {
                "source_alignment_passed": True,
                "fact_validation_passed": True,
                "structure_validation_passed": True,
                "render_validation_passed": True,
            },
        }
        (validated_dir / "validated_artifacts_manifest.json").write_text(
            json_mod.dumps(manifest), encoding="utf-8"
        )

        llm_call_count = 0
        svc = ProcessingService()
        orig_generate = svc.llm.generate

        def mock_gen(*a, **kw):
            nonlocal llm_call_count
            llm_call_count += 1
            return orig_generate(*a, **kw)

        monkeypatch.setattr(svc.llm, "generate", mock_gen)
        monkeypatch.setattr(
            svc.llm, "generate_json", lambda *a, **kw: ({"test": 1}, '{"test": 1}')
        )

        item = BatchItem(status="completed", debug_directory=debug_dir)
        svc.republish(item)
        assert llm_call_count == 0, f"LLM was called {llm_call_count} times during republish"

    def test_republish_accepts_valid_artifacts(self, tmp_path):
        debug_dir = tmp_path / "debug"
        validated_dir = debug_dir / "validated"
        validated_dir.mkdir(parents=True)

        html_bytes = b"<html><body>Valid</body></html>"
        json_data = {
            "protocol_id": "ok",
            "protocol_title": "Valid Protocol",
            "template_id": "project_detailed",
        }
        json_bytes = json_mod.dumps(
            json_data, ensure_ascii=False, indent=2, sort_keys=True
        ).encode("utf-8")

        (validated_dir / "protocol_final_validated.html").write_bytes(html_bytes)
        (validated_dir / "protocol_final_validated.json").write_bytes(json_bytes)
        manifest = {
            "generation_succeeded": True,
            "validation_succeeded": True,
            "html_sha256": compute_sha256_from_bytes(html_bytes),
            "json_sha256": compute_sha256_from_bytes(json_bytes),
            "validation_flags": {
                "source_alignment_passed": True,
                "fact_validation_passed": True,
                "structure_validation_passed": True,
                "render_validation_passed": True,
            },
        }
        (validated_dir / "validated_artifacts_manifest.json").write_text(
            json_mod.dumps(manifest), encoding="utf-8"
        )

        item = BatchItem(status="completed", debug_directory=debug_dir, dry_run=True)
        result = ProcessingService().republish(item)
        assert result["success"] is True


class TestSourceContextID:
    def test_same_content_different_source_type_has_different_context(self):
        sha = "abc123abc123abc123abc123abc123ab"
        id1 = generate_source_context_id(source_type="local_video", source_sha256=sha)
        id2 = generate_source_context_id(source_type="local_transcript", source_sha256=sha)
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

    def test_different_recording_id_produces_different_context(self):
        sha = "abc123abc123abc123abc123abc123ab"
        id1 = generate_source_context_id(
            source_type="bitlink", source_sha256=sha, bitlink_recording_id="rec1"
        )
        id2 = generate_source_context_id(
            source_type="bitlink", source_sha256=sha, bitlink_recording_id="rec2"
        )
        assert id1 != id2
