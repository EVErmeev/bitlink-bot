import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from models.protocol import (
    DecisionItem,
    Protocol,
    QuestionItem,
    RiskItem,
    TaskItem,
    TopicBlock,
)
from services.source_isolation import (
    create_input_manifest,
    create_provenance,
    generate_source_context_id,
    validate_source_alignment,
)


class TestSourceIsolation:
    def test_generate_unique_ids(self):
        id1 = generate_source_context_id(source_path="/path/to/file1.txt")
        id2 = generate_source_context_id(source_path="/path/to/file2.txt")
        assert id1 != id2
        assert len(id1) == 32

    def test_consistent_id_for_same_path(self):
        id1 = generate_source_context_id(source_path="/same/path.txt")
        id2 = generate_source_context_id(source_path="/same/path.txt")
        assert id1 == id2

    def test_generate_from_bitlink_id(self):
        id1 = generate_source_context_id(bitlink_recording_id="rec_123")
        assert len(id1) == 32

    def test_validate_alignment_all_match(self):
        ctx = "abc123def4567890"
        protocol = Protocol(protocol_id="p1", template_id="test", source_context_id=ctx)
        protocol.topic_blocks = [
            TopicBlock(topic_id="t1", title="Test", source_context_id=ctx),
        ]
        protocol.decisions = [
            DecisionItem(decision_id="d1", source_context_id=ctx),
        ]
        report = validate_source_alignment(protocol, ctx)
        assert report.passed
        assert protocol.source_alignment_passed

    def test_validate_alignment_mismatch_topics(self):
        ctx = "abc123def4567890"
        protocol = Protocol(protocol_id="p1", template_id="test", source_context_id=ctx)
        protocol.topic_blocks = [
            TopicBlock(topic_id="t1", title="Test", source_context_id="DIFFERENT_CTX"),
        ]
        report = validate_source_alignment(protocol, ctx)
        assert not report.passed
        assert len(report.issues) >= 1

    def test_validate_alignment_mismatch_decisions(self):
        ctx = "abc123def4567890"
        protocol = Protocol(protocol_id="p1", template_id="test", source_context_id=ctx)
        protocol.decisions = [
            DecisionItem(decision_id="d1", source_context_id="OTHER"),
        ]
        report = validate_source_alignment(protocol, ctx)
        assert not report.passed

    def test_validate_alignment_mismatch_questions(self):
        ctx = "abc123def4567890"
        protocol = Protocol(protocol_id="p1", template_id="test", source_context_id=ctx)
        protocol.questions = [
            QuestionItem(question_id="q1", source_context_id="DIFF"),
        ]
        report = validate_source_alignment(protocol, ctx)
        assert not report.passed

    def test_validate_alignment_mismatch_risks(self):
        ctx = "abc123def4567890"
        protocol = Protocol(protocol_id="p1", template_id="test", source_context_id=ctx)
        protocol.risks = [
            RiskItem(risk_id="r1", source_context_id="DIFF"),
        ]
        report = validate_source_alignment(protocol, ctx)
        assert not report.passed

    def test_validate_alignment_mismatch_tasks(self):
        ctx = "abc123def4567890"
        protocol = Protocol(protocol_id="p1", template_id="test", source_context_id=ctx)
        protocol.tasks = [
            TaskItem(task_id="t1", source_context_id="DIFF"),
        ]
        report = validate_source_alignment(protocol, ctx)
        assert not report.passed

    def test_create_input_manifest(self):
        manifest = create_input_manifest(
            Path("/test/file.txt"), "ctx123", "sha256abc",
            "local_transcript", "item_001"
        )
        assert Path(manifest["source_path"]) == Path("/test/file.txt")
        assert manifest["source_context_id"] == "ctx123"
        assert manifest["source_sha256"] == "sha256abc"

    def test_create_provenance(self):
        protocol = Protocol(protocol_id="p1", template_id="test", source_context_id="ctx1")
        prov = create_provenance(protocol, "ctx1", "item_id_1")
        assert prov["protocol_id"] == "p1"
        assert prov["source_context_id"] == "ctx1"
        assert prov["item_id"] == "item_id_1"
