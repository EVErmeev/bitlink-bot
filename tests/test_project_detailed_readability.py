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
from protocol_templates.project_detailed import ProjectDetailedTemplate


def _build_protocol(**overrides):
    p = Protocol(protocol_id="p", template_id="project_detailed", source_context_id="s")
    p.client_name = "Роял Фуд"
    p.project_name = "Склад 3PL"
    p.key_outcomes = (
        "Согласован рабочий алгоритм на две недели. "
        "Ближайшая встреча назначена на 04.08.2026, на 11.08.2026 закрытие вопросов. "
        "Зафиксирована необходимость доработок по весовым штрихкодам и печати этикеток."
    )
    tb = TopicBlock(
        topic_id="1", title="План работ", source_context_id="s",
        discussion_content=(
            "Егор сообщил об отсутствии критичных изменений. "
            "Наталья остаётся на связи во время отпуска. "
            "Сергей должен проработать остальные участки процессов.\n"
            "Предварительно согласованы две встречи: 4 августа — разбор документации; "
            "11 августа — закрытие вопросов складского блока."
        ),
        conclusion="Принят последовательный порядок работы.",
        status_text="Согласовано",
        status_next_action="Собрать комментарии; подготовить материалы",
        status_responsible="Сергей",
        status_deadline="04.08.2026",
    )
    p.topic_blocks.append(tb)
    for k, v in overrides.items():
        setattr(p, k, v)
    return p


class TestProjectDetailedReadability:
    def test_discussion_renders_paragraphs_and_bullets(self):
        p = _build_protocol()
        html = ProjectDetailedTemplate().render_html(p)
        assert "<p>" in html
        assert "<ul>" in html
        assert "4 августа" in html

    def test_conclusion_uses_rich_text_blocks(self):
        p = _build_protocol()
        html = ProjectDetailedTemplate().render_html(p)
        assert "Принят последовательный порядок работы" in html

    def test_status_uses_structured_rendering(self):
        p = _build_protocol()
        html = ProjectDetailedTemplate().render_html(p)
        assert "Следующее действие:" in html
        assert "Ответственные:" in html
        assert "Срок:" in html
        assert ".." not in html

    def test_current_state_is_split_by_object(self):
        p = _build_protocol()
        p.current_state = [
            {"object": "Приёмка и размещение", "state_blocks": [
                {"type": "paragraph", "text": "Документация прошла первичное изучение."},
                {"type": "bullet_list", "items": ["Сбор замечаний продолжается"]},
            ]},
            {"object": "Управление доставкой", "state": "Рекомендации ожидаются к 11.08.2026."},
        ]
        html = ProjectDetailedTemplate().render_html(p)
        assert "Приёмка и размещение" in html
        assert "Управление доставкой" in html
        assert "<ul>" in html

    def test_current_state_has_no_monolithic_cell(self):
        p = _build_protocol()
        p.current_state = [
            {"object": "Объект", "state": "A" * 800},
        ]
        html = ProjectDetailedTemplate().render_html(p)
        report = ProjectDetailedTemplate().validate_render(html, p)
        assert any(i.code == "monolithic_cell" for i in report.issues)