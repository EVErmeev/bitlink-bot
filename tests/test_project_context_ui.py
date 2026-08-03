import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


class TestProjectContextUI:
    def test_local_transcript_page_has_no_client_input(self):
        import inspect
        from ui.local_transcript_frame import LocalTranscriptFrame
        src = inspect.getsource(LocalTranscriptFrame)
        assert "client_name_var" not in src
        assert "Клиент:" not in src

    def test_local_transcript_page_has_no_project_input(self):
        import inspect
        from ui.local_transcript_frame import LocalTranscriptFrame
        src = inspect.getsource(LocalTranscriptFrame)
        assert "project_name_var" not in src
        assert "Проект:" not in src

    def test_generation_does_not_require_manual_client_project(self):
        # BatchItem may be created without client/project; they default to empty.
        from models.batch import BatchItem
        item = BatchItem(source_type="local_transcript", display_name="t.txt")
        assert item.client_name == ""
        assert item.project_name == ""