import os
from pathlib import Path

from services.newton_cli import build_newton_command
from services.process_runner import (
    classify_auth_error,
    decode_process_output,
    run_process,
)
from services.runtime_config import get_runtime_config


class TranscriptionError(RuntimeError):
    def __init__(self, code="", safe_message="", stage=""):
        self.code = code
        self.safe_message = safe_message
        self.stage = stage
        super().__init__(safe_message)


class TranscriptionClient:
    def __init__(self, token=None, cli_path=None, engine="v3", timeout_seconds=300):
        cfg = get_runtime_config()
        self.token = token or cfg.onebit_token
        self.cli_path = cli_path or cfg.onebit_cli_path
        self.engine = engine
        self.timeout_seconds = timeout_seconds
        self.provider = cfg.transcription_provider
        self.mock_mode = (self.provider == "mock")

    def check_connection(self) -> bool:
        if self.provider == "mock":
            return True
        if self.provider == "disabled":
            return False
        # Don't call CLI during connection check — just check config
        return bool(self.token and self.cli_path)

    def transcribe_video(self, video_path: Path, output_dir: Path) -> str:
        if self.provider == "mock":
            return _mock_transcribe(video_path, output_dir)
        if self.provider == "disabled":
            raise TranscriptionError(code="TRANSCRIPTION_DISABLED", safe_message="Транскрибация отключена")

        if not video_path.exists():
            raise TranscriptionError(code="TRANSCRIPTION_INPUT_NOT_FOUND",
                safe_message=f"Файл не найден: {video_path}")
        if not self.token:
            raise TranscriptionError(code="TRANSCRIPTION_TOKEN_MISSING",
                safe_message="Токен БИТ Ньютон не указан")

        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
out_file = output_dir / f"{video_path.stem}_transcript.txt"
        
        env = os.environ.copy()
        env["NEWTON_TOKEN"] = self.token
        env["PYTHONIOENCODING"] = "utf-8"
        args = build_newton_command(self.cli_path, "transcribe", str(video_path),
                                    "--engine", self.engine, "--output", str(out_file))
        
        r = run_process(args, env=env, timeout_seconds=self.timeout_seconds,
                       secret_values=[self.token] if self.token else None)

        if r.returncode != 0:
            auth_code, auth_msg = classify_auth_error(r.stderr, r.returncode)
            raise TranscriptionError(code=auth_code or "TRANSCRIPTION_FAILED",
                safe_message=auth_msg or f"CLI exit {r.returncode}: {r.stderr[:300]}",
                stage="cli_execution")

        if not out_file.exists() or out_file.stat().st_size == 0:
            raise TranscriptionError(code="TRANSCRIPTION_OUTPUT_EMPTY",
                safe_message="Транскрибация не создала выходной файл")

        raw = out_file.read_bytes()
        text, encoding, _score = decode_process_output(raw, preferred_encoding="auto")
        return text


def _mock_transcribe(video_path: Path, output_dir: Path) -> str:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    name = video_path.stem
    transcript = f"[Mock transcript: {name}]\nВедущий: Добрый день.\nУчастник 1: Обсуждаем проект.\n"
    (output_dir / f"{name}_transcript.txt").write_text(transcript, encoding="utf-8")
    return transcript
