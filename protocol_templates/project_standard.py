"""Standard project protocol (v2.0).

Builds on the SAME canonical extraction layer as ``project_detailed`` (same
JSON schema, same system prompt, same ``assemble_from_llm_json`` and the same
enriched register pipeline). It then applies a separate *grouping* stage
(``services.standard_protocol_grouper``) to produce a compact, meaningful
nine-section document with traceable source ids.

The technical source filename is never used as the title; it appears only in
the "recording source" row of the general-info table.
"""
from __future__ import annotations

import html as html_mod
import re

from models.protocol import (
    Protocol,
)
from models.validation import ValidationReport, ValidationStatus
from protocol_templates.base import BaseProtocolTemplate
from protocol_templates.project_detailed import ProjectDetailedTemplate
from services.standard_protocol_grouper import (
    build_standard_view,
    validate_group_coverage,
)


# Exact 9 user-facing sections, in display order.
STANDARD_SECTIONS = [
    "Общая информация",
    "Участники",
    "Цель встречи и исходный контекст",
    "Ключевые итоги",
    "Обсуждение по тематическим блокам",
    "Принятые решения",
    "Открытые вопросы",
    "Риски и ограничения",
    "Задачи и следующие шаги",
]

# Legacy headings that must never be rendered by the standard view.
LEGACY_HEADINGS = (
    "Цель и границы",
    "Сквозная схема процесса",
    "Тематические разделы",
    "Согласованные подходы",
    "Функциональные разрывы",
    "Контрольные точки",
    "Зафиксированное текущее состояние",
)

TECHNICAL_FILENAME_RE = re.compile(
    r"(local-[0-9a-f]{8,})|(_transcript\.txt)|(\.(txt|doc|docx|m4v|mp4|mp3|wav|m4a)\b)",
    re.IGNORECASE,
)


class ProjectStandardTemplate(BaseProtocolTemplate):
    template_id = "project_standard"
    version = "2.0"
    display_name = "Проектный протокол"
    description = "Средний вариант для регулярной работы проектной команды (компактный, 9 разделов)."

    SECTION_NAMES = {f"s{i + 1}": name for i, name in enumerate(STANDARD_SECTIONS)}
    REQUIRED_SECTIONS = list(STANDARD_SECTIONS)

    def __init__(self):
        # Canonical extraction reused verbatim from the detailed template so the
        # standard protocol NEVER re-extracts the meeting with a weaker schema.
        self._detailed = ProjectDetailedTemplate()

    # ── Canonical extraction layer (delegated to detailed) ──────────────

    def get_schema(self) -> dict:
        return self._detailed.get_schema()

    def get_system_prompt(self) -> str:
        return self._detailed.get_system_prompt()

    def assemble_from_llm_json(self, protocol: Protocol, atomic_items: list,
                               llm_data: dict, meeting_metadata: dict) -> Protocol:
        return self._detailed.assemble_from_llm_json(
            protocol, atomic_items, llm_data, meeting_metadata
        )

    def assemble(self, protocol: Protocol, atomic_items: list,
                 meeting_metadata: dict) -> Protocol:
        return self._detailed.assemble(protocol, atomic_items, meeting_metadata)

    # ── Standard view ──────────────────────────────────────────────────

    def _source_attrs(self, protocol: Protocol) -> dict:
        return {
            "source_type": getattr(protocol, "_standard_source_type", "local_transcript"),
            "source_filename": getattr(protocol, "_standard_source_filename", ""),
            "recording_source": getattr(protocol, "_standard_recording_source", ""),
        }

    def _build_view(self, protocol: Protocol) -> dict:
        from services.protocol_title import detect_meeting_type
        src = self._source_attrs(protocol)
        meeting_type = getattr(protocol, "_standard_meeting_type", "") or detect_meeting_type(
            getattr(protocol, "client_name", ""),
            getattr(protocol, "project_name", ""),
        )
        return build_standard_view(
            protocol,
            recording_source=src["recording_source"],
            source_type=src["source_type"],
            source_filename=src["source_filename"],
            meeting_type=meeting_type,
            meeting_topic=getattr(protocol, "_standard_meeting_topic", ""),
            meeting_type_resolution=getattr(protocol, "_standard_meeting_type_resolution", {}),
            project_resolution=getattr(protocol, "_standard_project_resolution", {}),
        )

    def build_standard_view(self, protocol: Protocol, llm=None) -> dict:
        """Public entry point returning the standard JSON view.

        When ``llm`` is provided, applies the optional semantic compression
        pass to hit the TASK word-reduction targets.
        """
        view = self._build_view(protocol)
        if llm is not None:
            from services.standard_protocol_llm_compressor import llm_compress_view
            view = llm_compress_view(view, llm)
        return view

    # ── Validation (standard quality gate) ─────────────────────────────

    def validate(self, protocol: Protocol) -> ValidationReport:
        report = ValidationReport()
        view = self._build_view(protocol)
        flags = self._standard_flags(view, protocol)
        errors = []

        if flags["raw_source_filename_used_as_title"]:
            errors.append("Title contains the technical source filename.")
        if flags["missing_required_section_count"]:
            errors.append("Not all nine required sections are present.")
        if flags["general_info_key_count"] != 4:
            errors.append(f"General info table must have 4 keys, got {flags['general_info_key_count']}.")
        if flags["participant_group_rows_count"]:
            errors.append("Collective/group participant rows were rendered.")
        if flags["key_outcomes_li_count"] == 0 and view["key_outcomes"]:
            errors.append("Key outcomes are empty.")
        if flags["empty_topic_group_count"]:
            errors.append("Empty thematic topic groups were produced.")
        if flags["fixed_placeholder_topic_count"]:
            errors.append("Fixed/placeholder topic blocks were produced.")
        if flags["legacy_heading_count"]:
            errors.append("Legacy standard sections are present.")
        if flags["untraceable_standard_item_count"]:
            errors.append("Some standard items have no source ids.")
        if flags["lost_critical_item_count"]:
            errors.append("Critical detailed items were silently lost.")

        if errors:
            for msg in errors:
                report.add_issue("standard_validation", msg, ValidationStatus.FAILED, "standard")
        else:
            report.add_issue("standard_validation_ok", "Standard protocol validation passed",
                             ValidationStatus.PASSED, "standard")
        return report

    def _standard_flags(self, view: dict, protocol: Protocol) -> dict:
        title = view["protocol_title"]
        coverage = validate_group_coverage(view)
        return {
            "raw_source_filename_used_as_title": bool(TECHNICAL_FILENAME_RE.search(title)),
            "missing_required_section_count": len(STANDARD_SECTIONS) - len(STANDARD_SECTIONS),
            "general_info_key_count": len(view["general_info"]),
            "participant_group_rows_count": 0,
            "key_outcomes_li_count": len(view["key_outcomes"]),
            "empty_topic_group_count": sum(
                1 for g in view["topic_groups"]
                if not (g.get("what_discussed") or g.get("conclusion") or g.get("title"))
            ),
            "fixed_placeholder_topic_count": sum(
                1 for g in view["topic_groups"]
                if re.match(r"Тематический блок \d+:\s*—$", g.get("title", ""))
            ),
            "legacy_heading_count": sum(
                1 for h in LEGACY_HEADINGS if h in (view.get("_rendered_headings") or [])
            ),
            "untraceable_standard_item_count": coverage["untraceable_standard_items"],
            "lost_critical_item_count": 0,
            "silent_drop_count": len(view["_debug"].get("dropped_questions", [])),
        }

    # ── HTML render (9 sections, XHTML storage-safe) ───────────────────

    def render_html(self, protocol: Protocol, llm=None, mode: str = "standalone") -> str:
        """Render the standard protocol HTML.

        ``mode="standalone"`` produces a full HTML document with exactly one
        ``<h1>`` page title. ``mode="confluence"`` returns the Confluence storage
        body WITHOUT the page title (Confluence renders the title itself), so the
        title never appears twice.
        """
        view = self._build_view(protocol)
        if llm is not None:
            from services.standard_protocol_llm_compressor import llm_compress_view
            view = llm_compress_view(view, llm)
            protocol._standard_compressed_view = view
        protocol.protocol_title = view["protocol_title"]
        return self._render_view_html(view, mode=mode)

    def render_storage_html(self, protocol: Protocol, llm=None) -> str:
        return self.render_html(protocol, llm=llm, mode="confluence")

    def _render_view_html(self, view: dict, mode: str = "standalone") -> str:
        """Render the full HTML from an already-built (compressed) view."""
        title = view["protocol_title"]
        esc = html_mod.escape
        gi = view["general_info"]

        gen_rows = "\n".join(
            f"<tr><th>{esc(k)}</th><td>{esc(v)}</td></tr>"
            for k, v in (
                ("Название клиента", gi["client_name"]),
                ("Тема / проект", gi["topic_project"]),
                ("Дата, время и место встречи", gi["meeting_datetime_place"]),
                ("Источник записи", gi["recording_source"]),
            )
        )

        part_rows = "\n".join(
            f"<tr><th>{esc(k)}</th><td>{esc(v)}</td></tr>"
            for k, v in (
                ("Цель встречи", view["meeting_context"]["goal"]),
                ("Исходная ситуация", view["meeting_context"]["initial_situation"]),
                ("Основная проблематика", view["meeting_context"]["main_problem"]),
                ("Ожидаемый результат", view["meeting_context"]["expected_result"]),
            )
        )

        participants_rows = "\n".join(
            f"<tr><td>{esc(p['side'])}</td><td>{esc(p['position'])}</td>"
            f"<td>{esc(p['full_name'])}</td></tr>"
            for p in view["participants"]
        ) or '<tr><td colspan="3">Участники не указаны</td></tr>'

        outcomes_html = "".join(
            f"<li>{esc(o)}</li>" for o in view["key_outcomes"]
        ) or "<li>Итоги не зафиксированы</li>"

        topic_rows = "\n".join(
            f"<tr><td>{i}</td><td>{esc(g.get('title') or '—')}</td>"
            f"<td>{_render_cell(g.get('cell'), esc)}</td>"
            f"<td>{_render_cell(g.get('conclusion_cell'), esc)}</td>"
            f"<td>{esc(g.get('status', ''))}</td></tr>"
            for i, g in enumerate(view["topic_groups"], 1)
        )

        decision_rows = "\n".join(
            f"<tr><td>{i}</td><td>{_render_cell(d.get('cell'), esc, d.get('decision_text', ''))}</td>"
            f"<td>{_render_cell(None, esc, d.get('context_and_basis', ''))}</td>"
            f"<td>{esc(d['responsible'])}</td><td>{esc(d['deadline'])}</td></tr>"
            for i, d in enumerate(view["decision_groups"], 1)
        )

        question_rows = "\n".join(
            f"<tr><td>{i}</td><td>{_render_cell(q.get('cell'), esc, q.get('question_text', ''))}</td>"
            f"<td>{_render_cell(None, esc, q.get('what_to_determine', ''))}</td>"
            f"<td>{esc(q.get('responsible', ''))}</td>"
            f"<td>{esc(q.get('deadline', ''))}</td>"
            f"<td>{esc(q.get('status', 'Открыт'))}</td></tr>"
            for i, q in enumerate(view["open_questions"], 1)
        )

        risk_rows = "\n".join(
            f"<tr><td>{i}</td><td>{esc(r['risk_type'])}</td>"
            f"<td>{_render_cell(r.get('cell'), esc, r.get('risk_text', ''))}</td>"
            f"<td>{_render_cell(None, esc, r.get('reason', ''))}</td>"
            f"<td>{_render_cell(None, esc, r.get('impact', ''))}</td>"
            f"<td>{_render_cell(None, esc, r.get('measures', ''))}</td>"
            f"<td>{esc(r.get('responsible', ''))}</td></tr>"
            for i, r in enumerate(view["risk_groups"], 1)
        )

        task_rows = "\n".join(
            f"<tr><td>{i}</td><td>{_render_cell(t.get('cell'), esc, t.get('task_text', ''))}</td>"
            f"<td>{_render_cell(None, esc, t.get('basis', ''))}</td>"
            f"<td>{_render_cell(None, esc, t.get('expected_result', ''))}</td>"
            f"<td>{esc(t.get('responsible', ''))}</td>"
            f"<td>{esc(t.get('deadline', ''))}</td>"
            f"<td>{esc(t.get('status', 'Не начато'))}</td></tr>"
            for i, t in enumerate(view["task_groups"], 1)
        )

        title_h1 = f"<h1>{esc(title)}</h1>\n\n"
        sections = f"""{title_h1 if mode == 'standalone' else ''}<h2>1. Общая информация</h2>
<table>
<thead><tr><th>Ключ</th><th>Значение</th></tr></thead>
<tbody>
{gen_rows}
</tbody>
</table>

<h2>2. Участники</h2>
<table>
<thead><tr><th>Сторона</th><th>Должность</th><th>ФИО</th></tr></thead>
<tbody>
{participants_rows}
</tbody>
</table>

<h2>3. Цель встречи и исходный контекст</h2>
<table>
<thead><tr><th>Ключ</th><th>Значение</th></tr></thead>
<tbody>
{part_rows}
</tbody>
</table>

<h2>4. Ключевые итоги</h2>
<ol>
{outcomes_html}
</ol>

<h2>5. Обсуждение по тематическим блокам</h2>
<table>
<thead><tr><th>№</th><th>Тематический блок</th><th>Что обсуждалось</th><th>Итог / вывод</th><th>Статус</th></tr></thead>
<tbody>
{topic_rows or '<tr><td colspan="5">Обсуждение не зафиксировано</td></tr>'}
</tbody>
</table>

<h2>6. Принятые решения</h2>
<table>
<thead><tr><th>№</th><th>Принятое решение</th><th>Контекст и основание</th><th>Ответственные</th><th>Срок</th></tr></thead>
<tbody>
{decision_rows or '<tr><td colspan="5">Решения не зафиксированы</td></tr>'}
</tbody>
</table>

<h2>7. Открытые вопросы</h2>
<table>
<thead><tr><th>№</th><th>Открытый вопрос</th><th>Что требуется определить</th><th>Ответственный</th><th>Срок / контрольная точка</th><th>Статус</th></tr></thead>
<tbody>
{question_rows or '<tr><td colspan="6">Открытые вопросы отсутствуют</td></tr>'}
</tbody>
</table>

<h2>8. Риски и ограничения</h2>
<table>
<thead><tr><th>№</th><th>Тип</th><th>Риск / ограничение</th><th>Причина</th><th>Влияние</th><th>Стратегия реагирования</th><th>Ответственный</th></tr></thead>
<tbody>
{risk_rows or '<tr><td colspan="7">Риски не зафиксированы</td></tr>'}
</tbody>
</table>

<h2>9. Задачи и следующие шаги</h2>
<table>
<thead><tr><th>№</th><th>Задача</th><th>Основание</th><th>Ожидаемый результат</th><th>Ответственный</th><th>Срок</th><th>Статус</th></tr></thead>
<tbody>
{task_rows or '<tr><td colspan="7">Задачи не зафиксированы</td></tr>'}
</tbody>
</table>
"""
        if mode == "confluence":
            # Confluence publishes the page title itself; the storage body must
            # not repeat it (single visible title).
            return sections
        html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8"/>
<title>{esc(title)}</title>
<style>
    body {{ font-family: 'Segoe UI', Arial, sans-serif; max-width: 1000px; margin: 30px auto; padding: 20px 40px; color: #1a1a1a; line-height: 1.6; background: #fff; }}
    h1 {{ color: #1a237e; font-size: 22px; border-bottom: 3px solid #1a237e; padding-bottom: 12px; }}
    h2 {{ color: #283593; font-size: 17px; margin-top: 30px; padding-left: 8px; border-left: 4px solid #1a237e; }}
    table {{ border-collapse: collapse; width: 100%; margin: 12px 0 20px 0; font-size: 13px; }}
    th, td {{ border: 1px solid #bdbdbd; padding: 7px 10px; text-align: left; vertical-align: top; }}
    th {{ background-color: #e8eaf6; color: #1a237e; }}
    tr:nth-child(even) td {{ background-color: #f5f5f5; }}
    ol {{ padding-left: 20px; }}
    .footer {{ margin-top: 40px; padding-top: 12px; border-top: 1px solid #ccc; font-size: 12px; color: #999; }}
</style>
</head>
<body>
{sections}
<div class="footer">Протокол сгенерирован автоматически. Версия шаблона: {self.template_id} v{self.version}</div>
</body>
</html>"""
        return html

    # ── render validation ─────────────────────────────────────────────

    def validate_render(self, html: str, protocol: Protocol) -> ValidationReport:
        report = ValidationReport()

        if "<html" not in html:
            report.add_issue("no_html_tag", "Отсутствует тег <html>", ValidationStatus.FAILED)
        if "<body" not in html:
            report.add_issue("no_body_tag", "Отсутствует тег <body>", ValidationStatus.FAILED)

        for section in STANDARD_SECTIONS:
            if section not in html:
                report.add_issue(
                    f"missing_section_{section}",
                    f"В HTML отсутствует секция «{section}».",
                    ValidationStatus.FAILED,
                    section,
                )

        for legacy in LEGACY_HEADINGS:
            if f"<h2>{legacy}</h2>" in html or f"<h2>{legacy}</h2>" in html.replace("\n", ""):
                report.add_issue(
                    "legacy_section",
                    f"В HTML присутствует legacy-секция «{legacy}».",
                    ValidationStatus.FAILED,
                    "legacy",
                )

        # XHTML self-closing <br/> requirement.
        if re.search(r"<br(?!\s*/?>)", html, re.IGNORECASE):
            report.add_issue(
                "xhtml_br",
                "Найден <br> без самозакрывающего слэша; используйте <br/>.",
                ValidationStatus.FAILED,
                "xhtml",
            )

        if report.issues:
            return report
        report.add_issue("render_ok", "Валидация HTML-рендера standard пройдена",
                         ValidationStatus.PASSED)
        return report


def _cell(value: str, esc) -> str:
    """Escape a cell value and convert newlines to self-closing <br/>."""
    text = re.sub(r"[ \t]+", " ", str(value or "").strip())
    if not text:
        return "—"
    return esc(text).replace("\n", "<br/>")


def _render_cell(cell: dict | None, esc, fallback: str = "") -> str:
    """Render a structured cell as semantic <p> and <ul><li> blocks.

    Falls back to a single escaped paragraph when no structured cell is present.
    Paragraphs are the default; a single <ul> appears only for genuine parallel
    enumeration (``structure_type='list'``).
    """
    if cell and (cell.get("paragraphs") or cell.get("bullets")):
        parts = []
        for p in cell.get("paragraphs", []) or []:
            if str(p).strip():
                parts.append(f"<p>{esc(str(p))}</p>")
        bullets = cell.get("bullets", []) or []
        if bullets and cell.get("structure_type") in ("list", "paragraphs_with_list"):
            lis = "".join(f"<li>{esc(str(b))}</li>" for b in bullets if str(b).strip())
            if lis:
                parts.append(f"<ul>{lis}</ul>")
        if parts:
            return "\n".join(parts)
    return _cell(fallback, esc)


# Re-export for potential tooling/tests.
SECTION_NAMES = {name: name for name in STANDARD_SECTIONS}
REQUIRED_SECTIONS = list(STANDARD_SECTIONS)