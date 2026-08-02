"""Extract decisions, questions, risks, tasks from transcript via LLM."""


def _val(obj, key, default=""):
    if hasattr(obj, key):
        return getattr(obj, key, default)
    if isinstance(obj, dict):
        return obj.get(key, default)
    return default


def extract_protocol_registers(transcript: str, topic_blocks: list, participants: list,
                                llm_client) -> dict:
    """Run separate LLM pass to extract structured registers."""
    topic_text = ""
    for i, tb in enumerate(topic_blocks):
        title = _val(tb, "title", f"Tema {i}")
        content = _val(tb, "discussion_content", "")
        conclusion = _val(tb, "conclusion", "")
        topic_text += f"\n### {title}\n{content}\nConclusion: {conclusion}\n"

    schema = {
        "type": "object",
        "properties": {
            "decisions": {"type": "array", "items": {"type": "object"}},
            "questions": {"type": "array", "items": {"type": "object"}},
            "risks": {"type": "array", "items": {"type": "object"}},
            "tasks": {"type": "array", "items": {"type": "object"}},
        },
        "required": ["decisions", "questions", "risks", "tasks"],
    }

    prompt = (
        "Extract structured data from this meeting. Return ONLY valid JSON.\n\n"
        "decisions: [{\"decision_text\", \"context_and_basis\", \"responsible\", \"deadline\", \"evidence\"}]\n"
        "questions: [{\"question_text\", \"context\", \"to_determine\", \"status\"=\"Открыт\"}]\n"
        "risks: [{\"risk_type\":\"Риск|Ограничение|Зависимость\", \"risk_text\", \"reason\", \"impact\"}]\n"
        "tasks: [{\"task_text\", \"basis\", \"responsible\", \"deadline\"}]\n\n"
        "Transcript:\n" + transcript[:8000] + "\n\n"
        "Topic blocks:\n" + topic_text[:4000]
    )

    try:
        result, _ = llm_client.generate_json(
            system_prompt="Extract meeting registers: decisions, questions, risks, tasks.",
            user_prompt=prompt,
            json_schema=schema,
            temperature=0.1,
        )
        return result
    except Exception:
        return {"decisions": [], "questions": [], "risks": [], "tasks": []}
