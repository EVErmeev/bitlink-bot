import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from models.protocol import Protocol, TopicBlock
from protocol_templates.project_detailed import ProjectDetailedTemplate
from services.project_context_resolver import resolve_project_context

_CONTROL = (
    "Встреча по складскому контуру на базе 1С и Mobile SMARTS (Клеверенс) с ТСД. "
    "Обсуждались приёмка и размещение, маркированный товар, Data Matrix, "
    "управление доставкой. Роял Фуд — владелец товара."
)


def _protocol():
    p = Protocol(protocol_id="p", template_id="project_detailed", source_context_id="s")
    p.client_name = "Роял Фуд"
    p.project_name = "Склад 3PL"
    p.key_outcomes = "Один итог. Второй итог. Третий итог."
    p.topic_blocks.append(TopicBlock(
        topic_id="1", title="Т", source_context_id="s",
        discussion_content="Текст обсуждения.", conclusion="Вывод.", status_text="Согласовано",
    ))
    return p


class TestProjectDetailedHtmlContract:
    def test_rendered_context_is_not_placeholder(self):
        p = _protocol()
        html = ProjectDetailedTemplate().render_html(p)
        assert "Роял Фуд" in html
        assert "Склад 3PL" in html
        assert "Клиент:</strong> Роял Фуд" in html
        assert "Проект:</strong> Склад 3PL" in html

    def test_resolved_context_reaches_protocol_json(self):
        r = resolve_project_context(_CONTROL, source_filename="f.txt",
                                    known_profiles=None, llm_client=None)
        p = _protocol()
        p.client_name = r.client_name
        p.project_name = r.project_name
        d = p.to_dict()
        assert d["client_name"] == "Роял Фуд"
        assert d["project_name"] == "Склад 3PL"

    def test_resolved_context_reaches_confluence_title(self):
        import inspect
        from services import processing_service
        src = inspect.getsource(processing_service.ProcessingService.process_item)
        # title must be built from protocol client/project (authoritative), not item
        assert "protocol.client_name" in src
        assert "protocol.project_name" in src

    def test_resolved_context_reaches_telegram(self):
        import inspect
        from services import processing_service
        src = inspect.getsource(processing_service.ProcessingService._send_telegram_protocol)
        assert "protocol.client_name" in src
        assert "Клиент:" in src

    def test_render_validates_for_control(self):
        p = _protocol()
        html = ProjectDetailedTemplate().render_html(p)
        report = ProjectDetailedTemplate().validate_render(html, p)
        assert not any(i.code in ("empty_client", "empty_project") for i in report.issues)

    def test_html_has_no_json_array_representation(self):
        p = _protocol()
        html = ProjectDetailedTemplate().render_html(p)
        assert "['" not in html
        assert '{"type"' not in html

    def test_client_project_override_is_authoritative(self):
        # Renderer must use protocol fields; an empty item value must not leak in.
        p = _protocol()
        p.client_name = "Роял Фуд"
        p.project_name = "Склад 3PL"
        html = ProjectDetailedTemplate().render_html(p)
        assert "Роял Фуд" in html