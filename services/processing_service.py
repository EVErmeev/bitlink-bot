import json
import uuid
from datetime import datetime
from pathlib import Path

from models.batch import BatchItem
from models.protocol import Protocol

try:
    import settings
    from meeting_metadata import determine_meeting_date
    from protocol_templates.registry import TemplateRegistry
    from services.fact_extraction import extract_atomic_items
    from services.runtime_estimator import RuntimeEstimator
    from services.source_isolation import (
        create_input_manifest,
        create_provenance,
        generate_source_context_id,
    )
except ImportError:
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from fact_extraction import extract_atomic_items  # type: ignore[no-redef]
    from runtime_estimator import RuntimeEstimator  # type: ignore[no-redef]
    from source_isolation import (  # type: ignore[no-redef]
        create_input_manifest,
        create_provenance,
        generate_source_context_id,
    )

    import settings
    from meeting_metadata import determine_meeting_date
    from protocol_templates.registry import TemplateRegistry


class ProcessingService:
    PROCESSING_STAGES = [
        "loading_source", "transcribing", "extracting_metadata",
        "extracting_items", "gap_audit", "building_topics",
        "generating_protocol", "fact_validation", "structure_validation",
        "rendering", "publishing_confluence", "sending_telegram",
        "completed",
    ]

    def __init__(self, progress_callback=None, config=None):
        self.progress_callback = progress_callback
        if config is None:
            from services.runtime_config import get_runtime_config
            config = get_runtime_config()
        from services.client_factory import (
            build_bitlink_client,
            build_confluence_client,
            build_llm_client,
            build_telegram_client,
            build_transcription_client,
        )
        self.bitlink = build_bitlink_client(config)
        self.transcription = build_transcription_client(config)
        self.confluence = build_confluence_client(config)
        self.telegram = build_telegram_client(config)
        self.llm = build_llm_client(config)
        self.templates = TemplateRegistry()
        self.estimator = RuntimeEstimator()
        self.config = config

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
                source_type=item.source_type,
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
            json_schema = template.get_schema()

            user_prompt = (
                f"Транскрипт встречи:\n\n{transcript_text}\n\n"
                f"Дата встречи: {meeting_date or 'не определена'}\n"
                f"Название: {item.display_name}\n"
            )

            try:
                llm_data, llm_raw = self.llm.generate_json(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    json_schema=json_schema,
                    temperature=0.1,
                    max_retries=3,
                )
            except Exception as e:
                item.status = "failed"
                item.error_details = f"LLM generation failed: {e}"
                result["error"] = str(e)
                return result

            protocol = Protocol(
                protocol_id=str(uuid.uuid4()),
                template_id=template.template_id,
                source_context_id=source_ctx_id,
            )
            if meeting_date: protocol.meeting_date = meeting_date
            if meeting_time: protocol.meeting_time = meeting_time
            protocol.protocol_title = item.display_name or "Протокол встречи"

            protocol = template.assemble_from_llm_json(protocol, atomic_items, llm_data,
                {"date": meeting_date, "time": meeting_time, "item": item})

            # Stage: rendering (technical)
            self._report_progress("rendering", 85, item)
            try:
                html = template.render_html(protocol)
                if not html or "<html" not in html.lower() and "<body" not in html.lower():
                    raise Exception("HTML render produced invalid output")
            except Exception as e:
                item.status = "failed"
                item.error_details = f"HTML generation failed: {e}"
                result["error"] = str(e)
                return result

            # TECHNICAL SUCCESS — always save artifacts
            if item.debug_directory:
                self._save_artifacts(item.debug_directory, protocol, html, transcript_text, item, llm_raw, llm_data)

            # Quality checks (based on mode)
            quality_mode = settings.PROTOCOL_QUALITY_MODE
            warnings = []
            if quality_mode != "off":
                struct_report = template.validate(protocol)
                render_report = template.validate_render(html, protocol)

                for issue in getattr(struct_report, 'issues', []):
                    warnings.append(f"[structure] {issue.message}")
                for issue in getattr(render_report, 'issues', []):
                    warnings.append(f"[render] {issue.message}")

                if item.debug_directory:
                    import json as _json
                    qr = {"mode": quality_mode, "warnings": warnings, "struct_passed": struct_report.passed if hasattr(struct_report, 'passed') else None}
                    with open(item.debug_directory / "quality_report.json", "w", encoding="utf-8") as f:
                        _json.dump(qr, f, indent=2, ensure_ascii=False)

            if quality_mode == "strict" and warnings:
                item.status = "validation_failed"
                item.error_details = "Quality gate failed:\n" + "\n".join(warnings[:5])
                result["success"] = False
                result["error"] = "Quality gate failed"
            else:
                # Advisory or off — protocol succeeds
                item.status = "completed_with_warnings" if warnings else "completed"
                if warnings:
                    item.status_message = f"Протокол сформирован с {len(warnings)} предупреждениями качества"
                result["success"] = True

                # Publish if not dry-run
                if not item.dry_run:
                    self._report_progress("publishing_confluence", 90, item)
                    try:
                        parent_id = item.parent_page_id or settings.CONFLUENCE_PARENT_PAGE_ID
                        page = self.confluence.create_page(
                            title=protocol.protocol_title,
                            storage_html=html,
                            parent_page_id=parent_id,
                        )
                        result["url"] = page.get("url", "")
                        item.result_url = str(result["url"])

                        if item.send_telegram:
                            self._report_progress("sending_telegram", 95, item)
                            try:
                                self.telegram.send_notification(
                                    protocol_title=protocol.protocol_title,
                                    meeting_date=protocol.meeting_date.isoformat() if protocol.meeting_date else "",
                                    key_result=(protocol.key_outcomes or "")[:200],
                                    confluence_url=result["url"],
                                )
                            except Exception as te:
                                print(f"Telegram: {te}")
                    except Exception as ce:
                        item.status_message = (item.status_message or "") + f" | Confluence: {ce}"

                if item.dry_run:
                    item.status_message = (item.status_message or "") + " (dry-run)"

            return result

        except Exception as e:
            item.status = "failed"
            import traceback
            tb = traceback.format_exc()
            item.error_details = f"{type(e).__name__}: {e}\n\n{tb[-1000:]}"
            result["error"] = str(e)

            # Save runtime error log
            try:
                from pathlib import Path
                log_dir = Path("debug") / "runtime_errors"
                log_dir.mkdir(parents=True, exist_ok=True)
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                log_path = log_dir / f"error_{ts}_{item.item_id[:8]}.log"
                with open(log_path, "w", encoding="utf-8") as lf:
                    lf.write(f"Stage: {getattr(self, '_current_stage', 'unknown')}\n")
                    lf.write(f"Item: {item.display_name}\n")
                    lf.write(f"Source: {item.source_type}\n")
                    lf.write(f"Error: {e}\n\n{tb}")
                if item.debug_directory:
                    item.debug_directory.mkdir(parents=True, exist_ok=True)
                    with open(item.debug_directory / "runtime_error.log", "w", encoding="utf-8") as lf:
                        lf.write(tb)
            except Exception:
                pass

        finally:
            elapsed = (datetime.now() - start_time).total_seconds()
            item.actual_seconds = elapsed
            self._report_progress(
                "completed" if result["success"] else "failed", 100, item
            )

        return result

    def republish(self, item: BatchItem) -> dict:
        if not item.debug_directory:
            return {"success": False, "error": "No debug directory"}

        validated_dir = item.debug_directory / "validated"
        manifest_path = validated_dir / "validated_artifacts_manifest.json"
        json_path = validated_dir / "protocol_final_validated.json"
        html_path = validated_dir / "protocol_final_validated.html"

        if not manifest_path.exists():
            return {"success": False, "error": "No validated_artifacts_manifest.json — protocol was not validated"}
        if not json_path.exists() or not html_path.exists():
            return {"success": False, "error": "Missing validated artifacts (JSON/HTML)"}

        import json as json_mod

        from meeting_metadata import compute_sha256_from_bytes

        manifest = json_mod.loads(manifest_path.read_text(encoding="utf-8"))
        if not manifest.get("validation_succeeded"):
            return {"success": False, "error": "Protocol did not pass validation — republish rejected"}
        if not manifest.get("generation_succeeded"):
            return {"success": False, "error": "Protocol generation was not successful — republish rejected"}

        html_content = html_path.read_text(encoding="utf-8")
        json_content_bytes = json_path.read_bytes()

        html_sha = compute_sha256_from_bytes(html_content.encode("utf-8"))
        json_sha = compute_sha256_from_bytes(json_content_bytes)

        if html_sha != manifest.get("html_sha256"):
            return {"success": False, "error": "HTML was modified after validation — republish rejected"}
        if json_sha != manifest.get("json_sha256"):
            return {"success": False, "error": "JSON was modified after validation — republish rejected"}

        validation_flags = manifest.get("validation_flags", {})
        for flag_name in ["source_alignment_passed", "fact_validation_passed",
                          "structure_validation_passed", "render_validation_passed"]:
            if not validation_flags.get(flag_name, False):
                return {"success": False, "error": f"Validation flag {flag_name} is False — republish rejected"}

        if item.dry_run:
            return {"success": True, "url": None, "message": "Dry-run: publishing skipped"}

        proto_data = json_mod.loads(json_content_bytes.decode("utf-8"))
        parent_id = item.parent_page_id or settings.CONFLUENCE_PARENT_PAGE_ID
        title = proto_data.get("protocol_title", item.display_name or "Protocol")
        page = self.confluence.create_page(
            title=title, storage_html=html_content, parent_page_id=parent_id
        )
        item.result_url = page.get("url", "")

        if item.send_telegram:
            try:
                self.telegram.send_notification(
                    protocol_title=title,
                    meeting_date=proto_data.get("meeting_date", ""),
                    key_result=(proto_data.get("key_outcomes", "") or "")[:200],
                    confluence_url=item.result_url,
                )
            except Exception as te:
                print(f"Telegram notification failed: {te}")

        item.status = "completed"
        return {"success": True, "url": item.result_url}

    def _load_transcript(self, item: BatchItem) -> str:
        if item.source_type == "local_transcript":
            if item.source_path and item.source_path.exists():
                try:
                    with open(item.source_path, encoding="utf-8-sig") as f:
                        return f.read()
                except UnicodeDecodeError:
                    with open(item.source_path, encoding="utf-8") as f:
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
                        transcript: str, item: BatchItem, llm_raw: str = "", llm_data: dict | None = None):
        directory.mkdir(parents=True, exist_ok=True)

        with open(directory / "protocol.json", "w", encoding="utf-8") as f:
            json.dump(protocol.to_dict(), f, indent=2, ensure_ascii=False)

        with open(directory / "protocol_preview.html", "w", encoding="utf-8") as f:
            f.write(html)

        with open(directory / "source_transcript.txt", "w", encoding="utf-8") as f:
            f.write(transcript)

        if llm_raw:
            with open(directory / "llm_raw_response.txt", "w", encoding="utf-8") as f:
                f.write(llm_raw)

        if llm_data is not None:
            with open(directory / "llm_parsed_response.json", "w", encoding="utf-8") as f:
                json.dump(llm_data, f, indent=2, ensure_ascii=False)

        prov = create_provenance(protocol, protocol.source_context_id, protocol.protocol_id)
        with open(directory / "protocol_provenance.json", "w", encoding="utf-8") as f:
            json.dump(prov, f, indent=2, ensure_ascii=False)

        manifest = create_input_manifest(
            source_path=str(item.source_path) if item.source_path else None,
            source_context_id=protocol.source_context_id,
            source_sha256=item.source_sha256 or "",
            source_type=item.source_type,
            item_id=item.item_id,
        )
        manifest["protocol_id"] = protocol.protocol_id
        manifest["template_id"] = protocol.template_id
        manifest["protocol_mode"] = item.protocol_mode
        manifest["word_count"] = item.word_count
        manifest["file_size_bytes"] = item.file_size_bytes
        manifest["duration_seconds"] = item.duration_seconds
        manifest["external_source_id"] = item.bitlink_recording_id
        with open(directory / "input_manifest.json", "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)

    def _report_progress(self, stage: str, percent: float, item: BatchItem):
        if self.progress_callback:
            self.progress_callback(stage, percent, item)
