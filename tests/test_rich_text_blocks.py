import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from services.protocol_content_utils import (
    fill_or,
    fill_required,
    normalize_rich_text_blocks,
    render_rich_text_blocks,
)


class TestRichTextBlocks:
    def test_paragraph_block_normalized(self):
        blocks = normalize_rich_text_blocks([{"type": "paragraph", "text": "Привет мир."}])
        assert blocks[0]["type"] == "paragraph"
        assert "Привет мир" in blocks[0]["text"]

    def test_bullet_list_normalized(self):
        blocks = normalize_rich_text_blocks(
            {"type": "bullet_list", "items": ["а", "б", "в"]}
        )
        assert blocks[0]["type"] == "bullet_list"
        assert blocks[0]["items"] == ["а", "б", "в"]

    def test_plain_string_becomes_blocks(self):
        blocks = normalize_rich_text_blocks("Простой текст в одну мысль.")
        assert blocks and blocks[0]["type"] == "paragraph"

    def test_inline_list_after_colon_becomes_bullets(self):
        text = "Предварительно согласованы две встречи: 4 августа — разбор; 11 августа — закрытие."
        blocks = normalize_rich_text_blocks(text)
        kinds = [b["type"] for b in blocks]
        assert "bullet_list" in kinds

    def test_render_escapes_html(self):
        blocks = [{"type": "paragraph", "text": "<script>alert(1)</script>"}]
        html = render_rich_text_blocks(blocks)
        assert "<script>" not in html
        assert "&lt;script&gt;" in html

    def test_fill_required_defaults_to_assign(self):
        assert fill_required("") == "Требуется назначить"
        assert fill_required("Сергей") == "Сергей"

    def test_fill_or_default(self):
        assert fill_or("", "Не определён") == "Не определён"
        assert fill_or("11.08.2026", "x") == "11.08.2026"