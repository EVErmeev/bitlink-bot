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

            self._report_progress("extracting_metadata", 15, item)
            meeting_date, meeting_time = determine_meeting_date(
                filepath=item.source_path,
            )

            self._report_progress("extracting_items", 25, item)
            source_ctx_id = item.source_context_id or generate_source_context_id(
                str(item.source_path) if item.source_path else item.bitlink_recording_id
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

            protocol = template.assemble(protocol, atomic_items, {
                "date": meeting_date,
                "time": meeting_time,
                "item": item,
            })

            self._report_progress("fact_validation", 70, item)
            fact_report = validate_facts(protocol, transcript_text)
            protocol = apply_corrections(protocol)
            protocol.fact_validation_passed = fact_report.passed

            source_report = validate_source_alignment(protocol, source_ctx_id)
            protocol.source_alignment_passed = source_report.passed

            self._report_progress("structure_validation", 80, item)
            struct_report = template.validate(protocol)
            protocol.structure_validation_passed = struct_report.passed

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

            if publishable:
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

            item.status = "completed" if (result["url"] or not publishable) else "failed"
            result["success"] = item.status == "completed"

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