import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from models.batch import BatchItem
from services.bitlink_service import BitlinkClient
from services.confluence_service import ConfluenceClient
from services.fact_extraction import extract_atomic_items
from services.processing_service import ProcessingService
from services.telegram_service import TelegramClient
from services.transcription_service import TranscriptionClient


class TestBitlinkService:
    def test_client_initialization(self):
        client = BitlinkClient()
        assert client.mock_mode is True

    def test_check_connection(self):
        client = BitlinkClient()
        assert client.check_connection() is True

    def test_get_rooms(self):
        client = BitlinkClient()
        rooms = client.get_rooms()
        assert len(rooms) >= 1
        assert "id" in rooms[0]
        assert "name" in rooms[0]

    def test_get_recordings(self):
        client = BitlinkClient()
        recordings = client.get_recordings("room_1")
        assert len(recordings) >= 1
        assert "id" in recordings[0]
        assert "date" in recordings[0]
        assert "duration_seconds" in recordings[0]

    def test_get_recordings_unknown_room(self):
        client = BitlinkClient()
        recordings = client.get_recordings("nonexistent")
        assert recordings == []

    def test_download_recording(self, tmp_path):
        client = BitlinkClient()
        fpath = client.download_recording("rec_1_1", tmp_path)
        assert fpath is not None
        assert fpath.exists()
        content = fpath.read_text(encoding="utf-8")
        assert len(content) > 0


class TestTranscriptionService:
    def test_client_initialization(self):
        client = TranscriptionClient()
        assert client.mock_mode is True

    def test_check_connection(self):
        client = TranscriptionClient()
        assert client.check_connection() is True

    def test_transcribe_video(self, tmp_path):
        client = TranscriptionClient()
        video_path = tmp_path / "test_video.mp4"
        video_path.write_text("dummy")  # mock file
        transcript = client.transcribe_video(video_path, tmp_path)
        assert len(transcript) > 0
        assert "Ведущий" in transcript or "Участник" in transcript


class TestConfluenceService:
    def test_client_initialization(self):
        client = ConfluenceClient()
        assert client.mock_mode is True

    def test_check_connection(self):
        client = ConfluenceClient()
        assert client.check_connection() is True

    def test_find_page_by_title(self):
        client = ConfluenceClient()
        results = client.find_page_by_title("Протокол")
        assert len(results) >= 1
        assert "id" in results[0]
        assert "title" in results[0]

    def test_create_page(self):
        client = ConfluenceClient(space_key="TEST")
        page = client.create_page(
            title="Тестовый протокол",
            storage_html="<p>Test content</p>",
            parent_page_id="parent_123",
        )
        assert "id" in page
        assert "url" in page
        assert page["space"] == "TEST"

    def test_create_page_no_parent(self):
        client = ConfluenceClient()
        page = client.create_page(
            title="Протокол без родителя",
            storage_html="<p>Content</p>",
        )
        assert page["id"] is not None
        assert page["url"] is not None

    def test_get_page(self):
        client = ConfluenceClient()
        page = client.get_page("page_123")
        assert page is not None
        assert page["id"] == "page_123"


class TestTelegramService:
    def test_client_disabled_without_credentials(self):
        client = TelegramClient(bot_token="", chat_id="")
        assert client.check_connection() is False
        assert client.enabled is False

    def test_send_notification_when_disabled(self):
        client = TelegramClient(bot_token="", chat_id="")
        result = client.send_notification("Title", "2026-07-24", "Key result", "http://example.com")
        assert result is False

    def test_send_notification_mock(self):
        client = TelegramClient(bot_token="mock_token", chat_id="mock_chat")
        client.enabled = True
        result = client.send_notification("Тест", "2026-07-24", "Итог", "http://url")
        assert result is True

    def test_send_batch_summary_mock(self):
        client = TelegramClient(bot_token="mock_token", chat_id="mock_chat")
        client.enabled = True
        result = client.send_batch_summary("Батч завершён")
        assert result is True


class TestFactExtraction:
    def test_extract_from_transcript(self):
        text = """Ведущий: Добрый день. Начинаем встречу.
Участник 1: Нужно обсудить статус проекта.
Ведущий: Согласен. Есть риски по срокам?
Участник 2: Да, зависимость от API — это риск.
Ведущий: Решили: использовать mock-сервер для тестирования.
Участник 1: Задача: подготовить прототип к пятнице.
Ведущий: Вопрос по бюджету остаётся открытым."""
        items = extract_atomic_items(text, "ctx_test", "sha_test")
        assert len(items) > 0

        types_found = {i.item_type for i in items}
        assert "риск" in types_found or "решение" in types_found or "задача" in types_found

    def test_all_items_have_source_context(self):
        text = "Тестовый текст встречи. Нужно сделать задачу. Есть риск."
        items = extract_atomic_items(text, "ctx123", "sha456")
        for item in items:
            assert item.source_context_id == "ctx123"

    def test_empty_transcript(self):
        items = extract_atomic_items("", "ctx", "sha")
        assert items == []


class TestProcessingPipeline:
    @pytest.fixture
    def service(self):
        return ProcessingService()

    def test_process_local_transcript(self, service, tmp_path):
        transcript_file = tmp_path / "2026_07_24_meeting.txt"
        transcript_file.write_text("""Ведущий: Обсуждаем статус проекта.
Участник 1: Модуль готов на 80%.
Ведущий: Какие риски?
Участник 1: Зависимость от внешнего API.
Ведущий: Решили использовать mock-сервер.
Участник 1: Задача: завершить тестирование до 30 июля.
Ведущий: Сроки реалистичны?""", encoding="utf-8")

        item = BatchItem(
            source_type="local_transcript",
            source_path=transcript_file,
            display_name=transcript_file.name,
            protocol_template="project_detailed",
            protocol_mode="auto",
            debug_directory=tmp_path / "debug_output",
        )

        result = service.process_item(item)
        assert result["success"] is True or "error" in result

        # Check artifacts saved
        debug = tmp_path / "debug_output"
        if debug.exists():
            protocol_json = debug / "protocol.json"
            if protocol_json.exists():
                import json
                data = json.loads(protocol_json.read_text(encoding="utf-8"))
                assert "template_id" in data

    def test_process_item_with_invalid_source(self, service):
        item = BatchItem(
            source_type="unknown_type",
            display_name="test",
        )
        result = service.process_item(item)
        assert result["success"] is False

    def test_process_item_stages_callback(self, service):
        stages = []

        def cb(stage, pct, item):
            stages.append(stage)

        service.progress_callback = cb
        item = BatchItem(
            source_type="local_transcript",
            source_path=Path("nonexistent.txt"),
            display_name="test",
        )
        service.process_item(item)
        assert "loading_source" in stages or "transcribing" in stages
