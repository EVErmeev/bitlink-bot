import json


def build_topic_registry(protocol) -> dict:
    """Map atomic_items to their topics."""
    registry = {}
    for tb in protocol.topic_blocks:
        registry[tb.topic_id] = {"title": tb.title, "source_item_ids": []}
    return registry


def map_atomic_items_to_topics(protocol, registry) -> dict:
    """Map each atomic item to a topic based on keyword overlap.

    First uses explicit source_item_ids from topic blocks if available,
    then backfills unmapped items by keyword overlap.
    """
    for tb in protocol.topic_blocks:
        if tb.topic_id in registry and hasattr(tb, "source_item_ids") and tb.source_item_ids:
            registry[tb.topic_id]["source_item_ids"] = list(tb.source_item_ids)

    all_mapped = set()
    for r in registry.values():
        all_mapped.update(r["source_item_ids"])

    for ai in getattr(protocol, "atomic_items", []):
        if ai.item_id in all_mapped:
            continue
        best_topic = None
        best_score = 0
        ai_words = set(ai.text.lower().split())
        for tb in protocol.topic_blocks:
            tb_words = set(tb.discussion_content.lower().split())
            common = ai_words & tb_words
            score = len([w for w in common if len(w) > 4])
            if score > best_score and score >= 2:
                best_score = score
                best_topic = tb.topic_id
        if best_topic:
            if best_topic in registry:
                registry[best_topic]["source_item_ids"].append(ai.item_id)
    return registry


def save_coverage_report(coverage_data: dict, output_path):
    """Save topic coverage report as JSON file."""
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(coverage_data, f, indent=2, ensure_ascii=False)


def audit_topic_coverage(protocol) -> dict:
    registry = build_topic_registry(protocol)
    registry = map_atomic_items_to_topics(protocol, registry)

    total = len(getattr(protocol, "atomic_items", []))
    mapped = sum(len(r["source_item_ids"]) for r in registry.values())
    unmapped = []
    mapped_ids = set()
    for r in registry.values():
        mapped_ids.update(r["source_item_ids"])
    for ai in getattr(protocol, "atomic_items", []):
        if ai.item_id not in mapped_ids:
            unmapped.append(ai.item_id)

    high_total = sum(
        1
        for ai in getattr(protocol, "atomic_items", [])
        if getattr(ai, "importance", 0) >= 0.8
    )
    high_mapped = sum(
        1
        for ai in getattr(protocol, "atomic_items", [])
        if getattr(ai, "importance", 0) >= 0.8 and ai.item_id in mapped_ids
    )
    unmapped_high = [
        ai.item_id
        for ai in getattr(protocol, "atomic_items", [])
        if getattr(ai, "importance", 0) >= 0.8 and ai.item_id not in mapped_ids
    ]

    coverage_passed = (
        high_mapped == high_total
        and len(protocol.topic_blocks) > 0
        and len(unmapped_high) == 0
    )

    return {
        "total_atomic_items": total,
        "mapped_atomic_items": mapped,
        "unmapped_atomic_items": unmapped,
        "high_importance_total": high_total,
        "high_importance_mapped": high_mapped,
        "unmapped_high_importance": unmapped_high,
        "topic_count": len(protocol.topic_blocks),
        "coverage_passed": coverage_passed,
    }


def validate_topic_source_alignment(protocol) -> dict:
    """Check all topic blocks have the same source_context_id as protocol."""
    expected = protocol.source_context_id
    foreign = []
    for tb in protocol.topic_blocks:
        if tb.source_context_id and tb.source_context_id != expected:
            foreign.append(tb.topic_id)
    return {"foreign_source_topics": foreign, "alignment_passed": len(foreign) == 0}
