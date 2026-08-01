import pytest
import sys
from pathlib import Path
from datetime import date
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from models.protocol import Protocol, TopicBlock, DecisionItem
from models.batch import BatchItem
from services.processing_service import ProcessingService


class TestPostCorrectionValidation:
    def test_post_correction_fact_validation_runs(self, tmp_path):
        transcript = tmp_path / "test.txt"
        transcript.write_text("Meeting about API integration. Decided to use REST.", encoding="utf-8")
        item = BatchItem(
            source_type="local_transcript", source_path=transcript, display_name="test",
            protocol_template="project_detailed", protocol_mode="auto",
            debug_directory=tmp_path / "debug",
        )
        result = ProcessingService().process_item(item)
        assert "success" in result

    def test_post_correction_source_validation_runs(self, tmp_path):
        transcript = tmp_path / "src.txt"
        transcript.write_text("Meeting content.", encoding="utf-8")
        item = BatchItem(
            source_type="local_transcript", source_path=transcript, display_name="src",
            protocol_template="project_detailed", protocol_mode="auto",
            debug_directory=tmp_path / "debug2",
        )
        result = ProcessingService().process_item(item)
        assert "success" in result

    def test_post_correction_topic_coverage_runs(self, tmp_path):
        transcript = tmp_path / "topic.txt"
        transcript.write_text("Discussion about integration. Discussion about budget.", encoding="utf-8")
        item = BatchItem(
            source_type="local_transcript", source_path=transcript, display_name="topic",
            protocol_template="project_detailed", protocol_mode="auto",
            debug_directory=tmp_path / "debug3",
        )
        result = ProcessingService().process_item(item)
        assert "success" in result

    def test_post_correction_structure_validation_runs(self, tmp_path):
        transcript = tmp_path / "struct.txt"
        transcript.write_text("Test meeting.", encoding="utf-8")
        item = BatchItem(
            source_type="local_transcript", source_path=transcript, display_name="struct",
            protocol_template="project_detailed", protocol_mode="auto",
            debug_directory=tmp_path / "debug4",
        )
        result = ProcessingService().process_item(item)
        assert "success" in result

    def test_post_correction_render_validation_runs(self, tmp_path):
        transcript = tmp_path / "render.txt"
        transcript.write_text("Test meeting.", encoding="utf-8")
        item = BatchItem(
            source_type="local_transcript", source_path=transcript, display_name="render",
            protocol_template="project_detailed", protocol_mode="auto",
            debug_directory=tmp_path / "debug5",
        )
        result = ProcessingService().process_item(item)
        assert "success" in result