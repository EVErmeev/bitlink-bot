import json
import uuid
from datetime import datetime, date
from pathlib import Path

from models.protocol import Protocol
from models.batch import BatchItem

try:
    import settings
    from meeting_metadata import determine_meeting_date
    from protocol_templates.registry import TemplateRegistry
    from services.source_isolation import (
        generate_source_context_id,
        validate_source_alignment,
        create_provenance,
        create_input_manifest,
    )
    from services.fact_extraction import extract_atomic_items
    from services.fact_validation import validate_facts, apply_corrections
    from services.bitlink_service import BitlinkClient
    from services.transcription_service import TranscriptionClient
    from services.confluence_service import ConfluenceClient
    from services.telegram_service import TelegramClient
    from services.llm_service import LLMClient
    from services.runtime_estimator import RuntimeEstimator
except ImportError:
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    import settings
    from meeting_metadata import determine_meeting_date
    from protocol_templates.registry import TemplateRegistry
    from source_isolation import (
        generate_source_context_id,
        validate_source_alignment,
        create_provenance,
        create_input_manifest,
    )
    from fact_extraction import extract_atomic_items
    from fact_validation import validate_facts, apply_corrections
    from bitlink_service import BitlinkClient
    from transcription_service import TranscriptionClient
    from confluence_service import ConfluenceClient
    from telegram_service import TelegramClient
    from llm_service import LLMClient
    from runtime_estimator import RuntimeEstimator


class ProcessingService:
    PROCESSING_STAGES = [
        "loading_source", "transcribing", "extracting_metadata",
        "extracting_items", "gap_audit", "building_topics",
        "generating_protocol", "fact_validation", "structure_validation",
        "rendering", "publishing_confluence", "sending_telegram",
        "completed",
    ]

    def __init__(self, progress_callback=None):
        self.progress_callback = progress_callback
        self.bitlink = BitlinkClient()
        self.transcription = TranscriptionClient()
        self.confluence = ConfluenceClient()
        self.telegram = TelegramClient()
        self.llm = LLMClient()
        self.templates = TemplateRegistry()
        self.estimator = RuntimeEstimator()

    def process_item(self, item: BatchItem) -> dict:
        start_time = datetime.now()
        result = {"item_id": item.item_id, "success": False, "url": None, "error": None}

        try:
            item.status = "processing"
            self._report_progress("loading_source", 0, item)

            transcript_text = self._load_transcript(item)
            if not transcript_text:
                raise Exception("Failed to obtain transcript")

            if not item.source_sha256:
                from meeting_metadata import compute_sha256_from_bytes
                item.source_sha256 = compute_sha256_from_bytes(transcript_text.encode("utf-8"))

            self._report_progress("extracting_metadata", 15, item)
            meeting_date, meeting_time = determine_meeting_date(
                filepath=item.source_path,
            )

            self._report_progress("extracting_items", 25, item)
            source_ctx_id = item.source_context_id or generate_source_context_id(
                source_path=str(item.source_path) if item.source_path else None,
                bitlink_recording_id=item.bitlink_recording_id,
                source_sha256=item.source_sha256,
            )
            atomic_items = extract_atomic_items(
                transcript_text, source_ctx_id, item.source_sha256 or ""
            )

            self._report_progress("gap_audit", 35, item)

            self._report_progress("building_topics", 45, item)

            self._report_progress("generating_protocol", 55, item)
            template = self.templates.get(item.protocol_template)
            if not template:
                raise Exception(f"Template {item.protocol_template} not found")

            system_prompt = template.get_system_prompt()
            user_prompt = (
                f"Транскрипт встречи:\n\n{transcript_text}\n\n"
                f"Извлечённые факты (atomic items):\n"
                + "\n".join(
                    f"  [{ai.item_type}] {ai.speaker + ': ' if ai.speaker else ''}{ai.text}"
                    for ai in atomic_items[:50]
                )
                + f"\n\nДата встречи: {meeting_date or 'не определена'}\n"
                + f"Название: {item.display_name}\n"
            )

            llm_output = self.llm.generate(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
            )

            protocol = Protocol(
                protocol_id=str(uuid.uuid4()),
                template_id=template.template_id,
                source_context_id=source_ctx_id,
            )
            if meeting_date:
                protocol.meeting_date = meeting_date
            if meeting_time:
                protocol.meeting_time = meeting_time
            protocol.protocol_title = item.display_name or "Протокол встречи"
            protocol.meeting_purpose = "Обсуждение статуса и планов проекта"

            protocol.atomic_items = atomic_items
            protocol = template.assemble_with_llm_output(
                protocol, atomic_items, llm_output,
                {"date": meeting_date, "time": meeting_time, "item": item},
            )

            self._report_progress("fact_validation", 70, item)
            fact_report = validate_facts(protocol, transcript_text)
            protocol = apply_corrections(protocol)

            self._report_progress("fact_validation", 72, item)
            post_correction_fact_report = validate_facts(protocol, transcript_text)
            post_correction_source_report = validate_source_alignment(protocol, source_ctx_id)
            post_correction_struct_report = template.validate(protocol)

            protocol.fact_validation_passed = post_correction_fact_report.passed
            protocol.source_alignment_passed = post_correction_source_report.passed
            protocol.structure_validation_passed = post_correction_struct_report.passed

            self._report_progress("rendering", 85, item)
            html = template.render_html(protocol)

            render_report = template.validate_render(html, protocol)
            protocol.render_validation_passed = render_report.passed

            publishable = (
                protocol.source_alignment_passed
                and protocol.fact_validation_passed
                and protocol.structure_validation_passed
                and protocol.render_validation_passed
            )

            if item.debug_directory:
                self._save_artifacts(item.debug_directory, protocol, html, transcript_text)

            if publishable and not item.dry_run:
                self._report_progress("publishing_confluence", 90, item)
                try:
                    parent_id = item.parent_page_id or settings.CONFLUENCE_PARENT_PAGE_ID
                    page = self.confluence.create_page(
                        title=protocol.protocol_title,
                        storage_html=html,
                        parent_page_id=parent_id,
                    )
                    result["url"] = page.get("url", "")
                    item.result_url = result["url"]

                    if item.send_telegram:
                        self._report_progress("sending_telegram", 95, item)
                        try:
                            self.telegram.send_notification(
                                protocol_title=protocol.protocol_title,
                                meeting_date=(
                                    protocol.meeting_date.isoformat()
                                    if protocol.meeting_date
                                    else "Дата не определена"
                                ),
                                key_result=(
                                    protocol.key_outcomes[:200]
                                    if protocol.key_outcomes
                                    else "Протокол сформирован"
                                ),
                                confluence_url=result["url"],
                            )
                        except Exception as te:
                            print(f"Telegram notification failed: {te}")
                except Exception as ce:
                    if not publishable:
                        raise
                    print(f"Confluence publish failed: {ce}")
                    result["error"] = f"Confluence: {ce}"
            else:
                result["error"] = "Protocol validation failed - publication blocked"

            if publishable and result["url"]:
                item.status = "completed"
                result["success"] = True
            elif publishable and item.dry_run:
                item.status = "completed"
                item.status_message = "Dry-run: протокол сгенерирован, публикация пропущена"
                result["success"] = True
            elif not publishable:
                item.status = "validation_failed"
                item.status_message = "Валидация не пройдена"
                result["success"] = False
            else:
                item.status = "failed"
                result["success"] = False

        except Exception as e:
            item.status = "failed"
            item.error_details = str(e)
            result["error"] = str(e)

        finally:
            elapsed = (datetime.now() - start_time).total_seconds()
            item.actual_seconds = elapsed
            self._report_progress(
                "completed" if result["success"] else "failed", 100, item
            )

        return result

    def republish(self, item: BatchItem) -> dict:
        if not item.debug_directory:
            return {"success": False, "error": "Нет debug-каталога с готовыми артефактами"}

        proto_path = item.debug_directory / "protocol.json"
        html_path = item.debug_directory / "protocol_preview.html"

        if not proto_path.exists() or not html_path.exists():
            return {"success": False, "error": "Готовые артефакты (JSON/HTML) не найдены"}

        try:
            import json
            proto_data = json.loads(proto_path.read_text(encoding="utf-8"))
            html = html_path.read_text(encoding="utf-8")

            if item.dry_run:
                return {"success": True, "url": None, "message": "Dry-run: публикация пропущена"}

            parent_id = item.parent_page_id or settings.CONFLUENCE_PARENT_PAGE_ID
            title = proto_data.get("protocol_title", item.display_name or "Протокол встречи")
            page = self.confluence.create_page(
                title=title,
                storage_html=html,
                parent_page_id=parent_id,
            )
            item.result_url = page.get("url", "")

            if item.send_telegram:
                try:
                    meeting_date = proto_data.get("meeting_date", "")
                    key_outcomes = proto_data.get("key_outcomes", "")[:200]
                    self.telegram.send_notification(
                        protocol_title=title,
                        meeting_date=meeting_date,
                        key_result=key_outcomes or "Протокол сформирован",
                        confluence_url=item.result_url,
                    )
                except Exception as te:
                    print(f"Telegram notification failed: {te}")

            item.status = "completed"
            return {"success": True, "url": item.result_url}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _load_transcript(self, item: BatchItem) -> str:
        if item.source_type == "local_transcript":
            if item.source_path and item.source_path.exists():
                try:
                    with open(item.source_path, "r", encoding="utf-8-sig") as f:
                        return f.read()
                except UnicodeDecodeError:
                    with open(item.source_path, "r", encoding="utf-8") as f:
                        return f.read()

        if item.source_type == "local_video":
            if item.source_path:
                return self.transcription.transcribe_video(
                    item.source_path,
                    item.debug_directory or Path("debug") / item.item_id,
                )

        if item.source_type == "bitlink":
            if item.bitlink_recording_id:
                download_dir = item.debug_directory or Path("debug") / item.item_id
                fpath = self.bitlink.download_recording(
                    item.bitlink_recording_id, download_dir
                )
                if fpath:
                    return fpath.read_text(encoding="utf-8")

        return ""

    def _save_artifacts(self, directory: Path, protocol: Protocol, html: str,
                        transcript: str):
        directory.mkdir(parents=True, exist_ok=True)

        with open(directory / "protocol.json", "w", encoding="utf-8") as f:
            json.dump(protocol.to_dict(), f, indent=2, ensure_ascii=False)

        with open(directory / "protocol_preview.html", "w", encoding="utf-8") as f:
            f.write(html)

        with open(directory / "source_transcript.txt", "w", encoding="utf-8") as f:
            f.write(transcript)

        prov = create_provenance(protocol, protocol.source_context_id, protocol.protocol_id)
        with open(directory / "protocol_provenance.json", "w", encoding="utf-8") as f:
            json.dump(prov, f, indent=2, ensure_ascii=False)

        manifest = create_input_manifest(
            directory, protocol.source_context_id, "",
            "local_transcript", protocol.protocol_id,
        )
        with open(directory / "input_manifest.json", "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)

    def _report_progress(self, stage: str, percent: float, item: BatchItem):
        if self.progress_callback:
            self.progress_callback(stage, percent, item)