import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from services.protocol_content_utils import split_key_outcomes_semantically

_LONG = (
    "Согласован рабочий алгоритм на ближайшие две недели: заказчик продолжает изучение "
    "документов, Сергей направляет комментарии в чат, а проектная команда фиксирует "
    "уточнения и функциональные разрывы. Ближайшая рабочая встреча предварительно "
    "назначена на 2026-08-04 для разбора обратной связи; на встрече 2026-08-11 "
    "планируется закрыть оставшиеся вопросы по складскому блоку. Зафиксирована "
    "необходимость отдельной проработки по весовым штрихкодам, печати этикеток, "
    "управлению сериями и сверке маркированной продукции с документами ЭДО."
)


class TestKeyOutcomeSemanticSplit:
    def test_long_key_outcome_is_split_semantically(self):
        result = split_key_outcomes_semantically(_LONG)
        assert len(result) >= 3

    def test_key_outcomes_render_as_multiple_li(self):
        from services.protocol_content_utils import render_rich_text_blocks
        result = split_key_outcomes_semantically(_LONG)
        blocks = [{"type": "numbered_list", "items": result}]
        html = render_rich_text_blocks(blocks)
        assert html.count("<li>") >= 3
        assert html.count("<ol>") == 1

    def test_does_not_invent_facts(self):
        result = split_key_outcomes_semantically(_LONG)
        joined = " ".join(result)
        assert "функциональные разрывы" in joined
        assert "2026-08-04" in joined or "04.08" in joined

    def test_empty_returns_empty_list(self):
        assert split_key_outcomes_semantically("") == []
        assert split_key_outcomes_semantically(None) == []