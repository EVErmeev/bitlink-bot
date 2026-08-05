"""Extract decisions / questions / risks / tasks from a transcript chunk.

The extractor receives a bounded *chunk* of the transcript and returns
structured candidates with a FULL field schema. It must not silently truncate
the transcript to a fixed prefix — the caller (register pipeline) is
responsible for splitting the full text into chunks so that no part is lost.
"""
from __future__ import annotations

_REGISTER_SCHEMA = {
    "type": "object",
    "properties": {
        "decisions": {"type": "array", "items": {"type": "object"}},
        "questions": {"type": "array", "items": {"type": "object"}},
        "risks": {"type": "array", "items": {"type": "object"}},
        "tasks": {"type": "array", "items": {"type": "object"}},
    },
    "required": ["decisions", "questions", "risks", "tasks"],
}

_PROMPT = """Extract meeting registers from the transcript chunk. Return ONLY valid JSON.

decisions: [{
  "decision_text": "полная подтверждённая формулировка решения без потери смысловых элементов",
  "context_and_basis": "контекст и основание решения",
  "responsible": "ответственный(ые)",
  "deadline": "срок или контрольная точка",
  "evidence": "подтверждение из текста"
}]
questions: [{
  "question_text": "открытый вопрос",
  "context": "контекст вопроса",
  "known_info": "что уже известно",
  "to_determine": "что требуется определить",
  "responsible": "ответственный (если указан в тексте)",
  "deadline": "срок / контрольная точка (если указана)",
  "status": "Открыт"
}]
risks: [{
  "risk_type": "Риск|Ограничение|Зависимость|Блокер|Допущение",
  "risk_text": "риск или ограничение",
  "reason": "причина",
  "impact": "влияние",
  "measures": "стратегия реагирования, если согласована на встрече",
  "responsible": "ответственный (если назначен)",
  "status": "Активен"
}]
tasks: [{
  "task_text": "полная формулировка задачи",
  "basis": "основание / причина задачи",
  "expected_result": "проверяемый ожидаемый результат, если назван",
  "responsible": "ответственный",
  "deadline": "срок",
  "status": "Не начато"
}]

Не выдумывай фактов. Сохраняй полные формулировки: не выбрасывай перечни действий,
причины, сроки, функциональные разрывы и объекты обсуждения.

Transcript chunk:
{chunk}
"""


def _val(obj, key, default=""):
    if hasattr(obj, key):
        return getattr(obj, key, default)
    if isinstance(obj, dict):
        return obj.get(key, default)
    return default


def extract_protocol_registers(transcript: str, topic_blocks: list, participants: list,
                                llm_client) -> dict:
    """Extract register candidates from a transcript chunk via LLM.

    ``transcript`` is expected to be a bounded chunk; the caller handles full
    transcript segmentation. No prefix-only truncation is applied here.
    """
    chunk = transcript or ""
    prompt = _PROMPT.replace("{chunk}", chunk)
    try:
        result, _ = llm_client.generate_json(
            system_prompt="Extract meeting registers: decisions, questions, risks, tasks.",
            user_prompt=prompt,
            json_schema=_REGISTER_SCHEMA,
            temperature=0.1,
        )
        if isinstance(result, dict):
            return {
                "decisions": result.get("decisions") or [],
                "questions": result.get("questions") or [],
                "risks": result.get("risks") or [],
                "tasks": result.get("tasks") or [],
            }
        return {"decisions": [], "questions": [], "risks": [], "tasks": []}
    except Exception:
        return {"decisions": [], "questions": [], "risks": [], "tasks": []}