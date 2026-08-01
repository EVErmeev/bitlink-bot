import pytest
import sys
from pathlib import Path
from datetime import date
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from models.protocol import Protocol, TopicBlock, AtomicItem
from services.topic_coverage import (
    build_topic_registry, map_atomic_items_to_topics,
    audit_topic_coverage, validate_topic_source_alignment,
)


class TestTopicCoverage:
    @pytest.fixture
    def protocol_with_topics(self):
        ctx = "test_ctx_123"
        p = Protocol(protocol_id="p1", template_id="project_detailed", source_context_id=ctx)
        p.meeting_date = date(2026, 7, 24)
        p.topic_blocks = [
            TopicBlock(topic_id="t1", title="Integration", source_context_id=ctx,
                       discussion_content="Discussing REST API integration with external service", order=1),
            TopicBlock(topic_id="t2", title="Budget", source_context_id=ctx,
                       discussion_content="Budget planning for next phase", order=2),
        ]
        p.atomic_items = [
            AtomicItem(item_id="a1", source_context_id=ctx, item_type="факт",
                       text="REST API integration architecture discussed", importance=0.9),
            AtomicItem(item_id="a2", source_context_id=ctx, item_type="факт",
                       text="Budget requires clarification", importance=0.4),
            AtomicItem(item_id="a3", source_context_id=ctx, item_type="риск",
                       text="Dependency on external API is a risk", importance=0.85),
        ]
        return p

    def test_project_detailed_creates_multiple_topics(self, protocol_with_topics):
        assert len(protocol_with_topics.topic_blocks) >= 2

    def test_all_high_importance_items_are_mapped(self, protocol_with_topics):
        coverage = audit_topic_coverage(protocol_with_topics)
        assert coverage["coverage_passed"] is True
        assert coverage["high_importance_mapped"] == coverage["high_importance_total"]

    def test_unmapped_high_importance_blocks_publication(self):
        ctx = "ctx"
        p = Protocol(protocol_id="p2", template_id="project_detailed", source_context_id=ctx)
        p.topic_blocks = [
            TopicBlock(topic_id="t1", title="Other", source_context_id=ctx,
                       discussion_content="Something else completely", order=1),
        ]
        p.atomic_items = [
            AtomicItem(item_id="a1", source_context_id=ctx, item_type="факт",
                       text="Critical security vulnerability found", importance=0.95),
        ]
        coverage = audit_topic_coverage(p)
        assert coverage["coverage_passed"] is False
        assert len(coverage["unmapped_high_importance"]) >= 1

    def test_topic_registry_contains_source_item_ids(self, protocol_with_topics):
        registry = build_topic_registry(protocol_with_topics)
        registry = map_atomic_items_to_topics(protocol_with_topics, registry)
        total_mapped = sum(len(r["source_item_ids"]) for r in registry.values())
        assert total_mapped > 0

    def test_foreign_source_item_blocks_publication(self):
        ctx = "original_ctx"
        p = Protocol(protocol_id="p3", template_id="project_detailed", source_context_id=ctx)
        p.topic_blocks = [
            TopicBlock(topic_id="t1", title="Topic", source_context_id="DIFFERENT_CTX", order=1),
        ]
        result = validate_topic_source_alignment(p)
        assert result["alignment_passed"] is False
        assert len(result["foreign_source_topics"]) >= 1