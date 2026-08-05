"""Offline E2E driver for TASK-2026-08-05-3A58494 (safe meeting-date parsing).

Runs the date parser over the control/regression/negative cases, produces the
TASK §16 artifacts, and exercises the standard-protocol pipeline with an
unresolved/invalid date to prove no crash and successful generation.

Usage: python tools/e2e_date_parsing.py <out_dir>
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from meeting_metadata import diagnose_date_resolution, extract_date_from_filename


def main(out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)

    control = {
        "2026_07_24_09_14_30_video.mp4": ("2026-07-24", "09:14"),
        "2026_08_05_15_30_45_recording.mp4": ("2026-08-05", "15:30"),
        "31_07_26_14_06_05_recording.mp4": ("2026-07-31", "14:06"),
        "31.07.2026_protocol.docx": ("2026-07-31", None),
        "31_07_2026_protocol.txt": ("2026-07-31", None),
        "2026-07-24-09-14-30.mp4": ("2026-07-24", "09:14"),
        "2026.07.24.09.14.30.mp4": ("2026-07-24", "09:14"),
    }
    cases = []
    for name, expected in control.items():
        d, t = extract_date_from_filename(Path(name))
        actual = (d.isoformat() if d else None,
                  t.strftime("%H:%M") if t else None)
        ok = actual == expected
        cases.append({
            "name": name, "expected": expected, "actual": actual, "ok": ok,
            "diag": diagnose_date_resolution(Path(name)),
        })
    (out_dir / "date_parser_cases.json").write_text(
        json.dumps(cases, ensure_ascii=False, indent=2), encoding="utf-8")

    invalid = [
        "15_15_26_10_30_00_video.mp4",
        "31_15_26_10_30_00_video.mp4",
        "2026_15_31_10_30_00_video.mp4",
        "2026_02_30_10_30_00_video.mp4",
        "2026_08_05_25_30_00_video.mp4",
        "2026_08_05_15_70_00_video.mp4",
        "local-872b2e3cdd76beb0_transcript.txt",
        "meeting_15_30_45_recording.mp4",
        "recording_01_30_15_22_44_99.mp4",
    ]
    inv_cases = []
    for name in invalid:
        d, t = extract_date_from_filename(Path(name))
        diag = diagnose_date_resolution(Path(name))
        inv_cases.append({"name": name, "date": d.isoformat() if d else None,
                          "time": t.strftime("%H:%M") if t else None, "diag": diag})
    (out_dir / "invalid_filename_cases.json").write_text(
        json.dumps(inv_cases, ensure_ascii=False, indent=2), encoding="utf-8")

    # Standard-pipeline run with an invalid-date video -> must not crash.
    run_pipeline(out_dir)

    print("ok_cases:", sum(1 for c in cases if c["ok"]), "/", len(cases))
    print("invalid_never_raise:", all(c["date"] is None for c in inv_cases))
    print("written:", out_dir)


def parse(name):
    from pathlib import Path as P
    return extract_date_from_filename(P(name))


def run_pipeline(out_dir: Path):
    from models.batch import BatchItem
    from services.processing_service import ProcessingService
    from services.runtime_config import RuntimeConfig

    transcript = (
        "Встреча по блоку управления производством. Обсудили диспетчирование "
        "этапов, обеспечение материалами и сменные задания. Согласовали порядок "
        "передачи материалов в кладовую."
    )

    class StubLLM:
        def generate_json(self, system_prompt="", user_prompt="", json_schema=None,
                          temperature=0.1, max_retries=1, **kw):
            required = (json_schema or {}).get("required", [])
            if required == ["decisions", "questions", "risks", "tasks"]:
                return {"decisions": [], "questions": [], "risks": [], "tasks": []}, "{}"
            return dict(_MAIN_LLM), json.dumps(_MAIN_LLM, ensure_ascii=False)

    import services.processing_service as ps
    ps.settings.PROTOCOL_QUALITY_MODE = "off"
    import services.client_factory as cf
    cf.build_llm_client = lambda config: StubLLM()
    cf.build_transcription_client = lambda config: _StubTranscription()

    src = out_dir / "31_15_26_10_30_00_video.mp4"
    src.write_bytes(b"0")
    dbg = out_dir / "debug"
    item = BatchItem(source_type="local_video", source_path=src,
                     display_name="31_15_26_10_30_00_video.mp4",
                     protocol_template="project_standard", protocol_mode="auto",
                     dry_run=True, debug_directory=dbg)
    cfg = RuntimeConfig(bitlink_provider="disabled", transcription_provider="mock",
                        llm_provider="mock", confluence_provider="mock",
                        telegram_provider="disabled")
    svc = ProcessingService(config=cfg)
    result = svc.process_item(item)
    (out_dir / "video_e2e_result.json").write_text(
        json.dumps({"success": result.get("success"), "error": result.get("error")},
                   ensure_ascii=False, indent=2), encoding="utf-8")
    print("pipeline success:", result.get("success"), "error:", result.get("error"))


class _StubTranscription:
    def transcribe_video(self, path, output_dir=""):
        return "Встреча по блоку управления производством. Обсудили диспетчирование этапов."


_MAIN_LLM = {
    "protocol_title": "Встреча по производству",
    "general_info": {"meeting_date": "2026-07-31", "meeting_context": "Производство"},
    "meeting_purpose": "Обсудить производственный блок.",
    "meeting_context": "Обследование производственного блока.",
    "key_outcomes": "Согласовано диспетчирование этапов.",
    "current_state": "Продолжается обследование.",
    "participants": [{"name": "Евгений", "role": "Аналитик"},
                     {"name": "Александр", "role": "Диспетчер"}],
    "topic_blocks": [{"topic_id": "t1", "title": "Диспетчирование этапов",
                      "discussion_content": "Рассмотрен процесс диспетчера.",
                      "conclusion": "Согласовано.", "status_text": "Согласовано"}],
    "decisions": [], "questions": [], "risks": [], "tasks": [],
}


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else r"C:\Users\EVErmeev\AppData\Local\Temp\opencode\e2e_date"
    main(Path(out))