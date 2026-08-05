"""Optional LLM semantic-compression prompt for the standard protocol.

The deterministic compactor (``standard_protocol_compactor``) is the default
and is testable. This prompt describes the same semantic-compression pass that
may be applied per-cell by an LLM to reach the 25-35% whole / 30-40% section-5
targets while preserving every fact anchor.
"""
from __future__ import annotations

# Rules are aligned with TASK §6 (two-stage semantic compression) and §9.
COMPRESSION_RULES = (
    "Ты — редактор проектного протокола. Сжимаешь смысловую ячейку без потери фактов.\n"
    "ПРАВИЛА:\n"
    "- Сохраняй числа, суммы, даты, сроки, ответственных, клиентов, проекты и системы.\n"
    "- Удаляй повторы уже названного объекта, хронологию реплик и вводные фразы "
    "«обсуждалось», «было отмечено», «участники рассмотрели».\n"
    "- Убирай повторное объяснение уже сделанного вывода.\n"
    "- Не переноси в этот текст решения/риски/задачи, если они вынесены в реестры.\n"
    "- Не обрезай строку и не заканчивай предложение многоточием из-за лимита.\n"
    "- Разделяй результат на самостоятельные смысловые абзацы: новый объект/проект — "
    "новый абзац; факт→причина→влияние→решение→следующее действие — отдельные абзацы; "
    "однородный перечень — маркированный список.\n"
    "- Ориентир на абзац: 35-75 слов; на ячейку темы: 55-100 слов.\n"
    "- Верни ТОЛЬКО JSON: {\"paragraphs\": [...], \"bullets\": [...]}."
)


def build_compression_user_prompt(section_name: str, text: str, registers: str = "") -> str:
    reg_note = ""
    if registers:
        reg_note = ("\nУже зафиксированы в реестрах (не дублируй в сжатом тексте):\n"
                    + registers + "\n")
    return (
        f"Секция: {section_name}\n"
        f"Исходный текст:\n{text}\n{reg_note}"
    )


def build_compression_system_prompt() -> str:
    return COMPRESSION_RULES