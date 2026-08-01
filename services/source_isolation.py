import hashlib
import uuid
from pathlib import Path
from models.validation import ValidationReport, ValidationStatus


def generate_source_context_id(source_path: str | None = None,
                               bitlink_recording_id: str | None = None,
                               source_sha256: str | None = None) -> str:
    if source_sha256:
        return source_sha256[:16]
    seed = source_path or bitlink_recording_id or str(uuid.uuid4())
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]


def validate_source_alignment(protocol, expected_source_context_id: str) -> ValidationReport:
    report = ValidationReport()

    mismatches = []
    for tb in protocol.topic_blocks:
        if tb.source_context_id and tb.source_context_id != expected_source_context_id:
            mismatches.append(f"TopicBlock {tb.topic_id}: {tb.source_context_id} != {expected_source_context_id}")

    for d in protocol.decisions:
        if d.source_context_id and d.source_context_id != expected_source_context_id:
            mismatches.append(f"Decision {d.decision_id}: {d.source_context_id} != {expected_source_context_id}")

    for q in protocol.questions:
        if q.source_context_id and q.source_context_id != expected_source_context_id:
            mismatches.append(f"Question {q.question_id}: {q.source_context_id} != {expected_source_context_id}")

    for r in protocol.risks:
        if r.source_context_id and r.source_context_id != expected_source_context_id:
            mismatches.append(f"Risk {r.risk_id}: {r.source_context_id} != {expected_source_context_id}")

    for t in protocol.tasks:
        if t.source_context_id and t.source_context_id != expected_source_context_id:
            mismatches.append(f"Task {t.task_id}: {t.source_context_id} != {expected_source_context_id}")

    for ai in getattr(protocol, 'atomic_items', []):
        if ai.source_context_id and ai.source_context_id != expected_source_context_id:
            mismatches.append(f"AtomicItem {ai.item_id}: {ai.source_context_id} != {expected_source_context_id}")

    if mismatches:
        for m in mismatches:
            report.add_issue("source_mismatch", m, ValidationStatus.FAILED, "source_alignment")
    else:
        protocol.source_alignment_passed = True

    return report


def create_input_manifest(source_path: Path, source_context_id: str, source_sha256: str,
                          source_type: str, item_id: str) -> dict:
    return {
        "source_path": str(source_path),
        "source_context_id": source_context_id,
        "source_sha256": source_sha256,
        "source_type": source_type,
        "item_id": item_id,
    }


def create_provenance(protocol, source_context_id: str, item_id: str) -> dict:
    return {
        "protocol_id": protocol.protocol_id,
        "source_context_id": source_context_id,
        "item_id": item_id,
        "template_id": protocol.template_id,
        "sections_generated": [s for s in dir(protocol) if not s.startswith("_")],
    }