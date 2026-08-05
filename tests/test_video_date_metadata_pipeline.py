"""Pipeline-level tests for safe meeting-date resolution (TASK В§9, В§11, В§13).

Verifies:
  * the original video filename (not a hash/transcript name) drives date
    resolution;
  * a transcript/hash filename is not treated as the original source;
  * processing continues (no traceback) when the date is unresolved;
  * standard and detailed generation proceed when the date is unresolved.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import services.processing_service as ps
from models.batch import BatchItem
from services.runtime_config import RuntimeConfig

_CONTROL_TRANSCRIPT = (
    "Р’СЃС‚СЂРµС‡Р° РїРѕ Р±Р»РѕРєСѓ СѓРїСЂР°РІР»РµРЅРёСЏ РїСЂРѕРёР·РІРѕРґСЃС‚РІРѕРј. РћР±СЃСѓРґРёР»Рё РґРёСЃРїРµС‚С‡РёСЂРѕРІР°РЅРёРµ "
    "СЌС‚Р°РїРѕРІ, РѕР±РµСЃРїРµС‡РµРЅРёРµ РјР°С‚РµСЂРёР°Р»Р°РјРё Рё СЃРјРµРЅРЅС‹Рµ Р·Р°РґР°РЅРёСЏ. РЎРѕРіР»Р°СЃРѕРІР°Р»Рё РїРѕСЂСЏРґРѕРє "
    "РїРµСЂРµРґР°С‡Рё РјР°С‚РµСЂРёР°Р»РѕРІ РІ РєР»Р°РґРѕРІСѓСЋ."
)


class StubLLM:
    def generate_json(self, system_prompt="", user_prompt="", json_schema=None,
                      temperature=0.1, max_retries=1, **kw):
        required = (json_schema or {}).get("required", [])
        if required == ["decisions", "questions", "risks", "tasks"]:
            return {"decisions": [], "questions": [], "risks": [], "tasks": []}, "{}"
        return dict(_MAIN_LLM), json.dumps(_MAIN_LLM, ensure_ascii=False)


class StubTranscription:
    def transcribe_video(self, path, output_dir=""):
        return _CONTROL_TRANSCRIPT


def _make_local_video_item(tmp, filename):
    dbg = tmp / "debug"
    return BatchItem(
        source_type="local_video",
        source_path=tmp / filename,
        display_name=filename,
        protocol_template="project_standard",
        protocol_mode="auto",
        dry_run=True,
        debug_directory=dbg,
    )


def _service(monkeypatch):
    monkeypatch.setattr(ps.settings, "PROTOCOL_QUALITY_MODE", "off")
    monkeypatch.setattr("services.client_factory.build_llm_client",
                        lambda config: StubTranscriptLLM())
    monkeypatch.setattr("services.client_factory.build_transcription_client",
                        lambda config: StubTranscription())
    cfg = RuntimeConfig(bitlink_provider="disabled",
                        transcription_provider="mock",
                        llm_provider="mock",
                        confluence_provider="mock",
                        telegram_provider="disabled")
    svc = ps.ProcessingService(config=cfg)
    svc.transcription = StubTranscription()
    return svc


def test_original_video_filename_is_used_for_date_resolution(monkeypatch, tmp_path):
    svc = _service(monkeypatch)
    item = _make_local_video_item(tmp_path, "2026_07_24_09_14_30_video.mp4")
    # a video file (content doesn't matter; transcription is stubbed)
    item.source_path.write_bytes(b"0")
    result = svc.process_item(item)
    assert result["success"] is True, result.get("error")
    diag = json.loads((item.debug_directory / "date_resolution_debug.json").read_text(encoding="utf-8"))
    assert diag["meeting_date"] == "2026-07-24"
    assert diag["meeting_time"] == "09:14"
    assert diag["source"] == "filename"
    assert diag["matched_format"] == "YYYY_MM_DD_HH_MM_SS"
    # basename only, no full path leak
    assert "2026_07_24_09_14_30_video.mp4" == diag["filename_basename"]


def test_transcript_hash_filename_is_not_used_as_original_source(monkeypatch, tmp_path):
    # A transcript/hash name carries no date -> date unresolved, no crash.
    svc = _service(monkeypatch)
    item = _make_local_video_item(tmp_path, "local-872b2e3cdd76beb0_transcript.txt")
    item.source_path.write_bytes(b"x")
    result = svc.process_item(item)
    assert result["success"] is True, result.get("error")
    diag = json.loads((item.debug_directory / "date_resolution_debug.json").read_text(encoding="utf-8"))
    assert diag["meeting_date"] is None


def test_standard_generation_continues_when_date_unresolved(monkeypatch, tmp_path):
    svc = _service(monkeypatch)
    item = _make_local_video_item(tmp_path, "простое_имя_без_даты.mp4")
    item.source_path.write_bytes(b"x")
    result = svc.process_item(item)
    assert result["success"] is True, result.get("error")
    diag = json.loads((item.debug_directory / "date_resolution_debug.json").read_text(encoding="utf-8"))
    assert diag["meeting_date"] is None
    # artifacts exist
    assert (item.debug_directory / "protocol_preview.html").exists()


def test_detailed_generation_continues_when_date_unresolved(monkeypatch, tmp_path):
    svc = _service(monkeypatch)
    item = _make_local_video_item(tmp_path, "РЅРµРёР·РІРµСЃС‚РЅРѕРµ_РІРёРґРµРѕ_Р±РµР·_РґР°С‚С‹.mp4")
    item.protocol_template = "project_detailed"
    item.source_path.write_bytes(b"x")
    result = svc.process_item(item)
    assert result["success"] is True, result.get("error")


def test_determine_meeting_date_never_leaks_value_error(monkeypatch, tmp_path):
    svc = _service(monkeypatch)
    item = _make_local_video_item(tmp_path, "31_15_26_10_30_00_video.mp4")
    item.source_path.write_bytes(b"x")
    result = svc.process_item(item)
    # Regression: previously ValueError('month must be in 1..12, not 15')
    assert result["success"] is True, result.get("error")


_MAIN_LLM = {
    "protocol_title": "Р’СЃС‚СЂРµС‡Р° РїРѕ РїСЂРѕРёР·РІРѕРґСЃС‚РІСѓ",
    "general_info": {"meeting_date": "2026-07-31", "meeting_context": "РџСЂРѕРёР·РІРѕРґСЃС‚РІРѕ"},
    "meeting_purpose": "РћР±СЃСѓРґРёС‚СЊ РїСЂРѕРёР·РІРѕРґСЃС‚РІРµРЅРЅС‹Р№ Р±Р»РѕРє.",
    "meeting_context": "РћР±СЃР»РµРґРѕРІР°РЅРёРµ РїСЂРѕРёР·РІРѕРґСЃС‚РІРµРЅРЅРѕРіРѕ Р±Р»РѕРєР°.",
    "key_outcomes": "РЎРѕРіР»Р°СЃРѕРІР°РЅРѕ РґРёСЃРїРµС‚С‡РёСЂРѕРІР°РЅРёРµ СЌС‚Р°РїРѕРІ.",
    "current_state": "РџСЂРѕРґРѕР»Р¶Р°РµС‚СЃСЏ РѕР±СЃР»РµРґРѕРІР°РЅРёРµ.",
    "participants": [{"name": "Р•РІРіРµРЅРёР№", "role": "РђРЅР°Р»РёС‚РёРє"},
                     {"name": "РђР»РµРєСЃР°РЅРґСЂ", "role": "Р”РёСЃРїРµС‚С‡РµСЂ"}],
    "topic_blocks": [{"topic_id": "t1", "title": "Р”РёСЃРїРµС‚С‡РёСЂРѕРІР°РЅРёРµ СЌС‚Р°РїРѕРІ",
                      "discussion_content": "Р Р°СЃСЃРјРѕС‚СЂРµРЅ РїСЂРѕС†РµСЃСЃ РґРёСЃРїРµС‚С‡РµСЂР°.",
                      "conclusion": "РЎРѕРіР»Р°СЃРѕРІР°РЅРѕ.", "status_text": "РЎРѕРіР»Р°СЃРѕРІР°РЅРѕ"}],
    "decisions": [], "questions": [], "risks": [], "tasks": [],
}


class StubTranscriptLLM:
    def generate_json(self, system_prompt="", user_prompt="", json_schema=None,
                      temperature=0.1, max_retries=1, **kw):
        required = (json_schema or {}).get("required", [])
        if required == ["decisions", "questions", "risks", "tasks"]:
            return {"decisions": [], "questions": [], "risks": [], "tasks": []}, "{}"
        return dict(_MAIN_LLM), json.dumps(_MAIN_LLM, ensure_ascii=False)
