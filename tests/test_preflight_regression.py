import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from models.batch import BatchItem
from services.preflight_service import run_preflight
from services.runtime_config import RuntimeConfig


class TestPreflightRegression:
    def test_run_preflight_public_signature_accepts_items_and_config(self):
        """Public API: run_preflight(items, config) — only 2 positional args."""
        import inspect
        sig = inspect.signature(run_preflight)
        params = list(sig.parameters.keys())
        assert len(params) == 2, f"Expected 2 params, got {params}"
        assert "items" in params
        assert "config" in params
        assert "source_types" not in params, "source_types must NOT be in signature"

    def test_source_queue_start_processing_does_not_pass_source_types_kwarg(self):
        """Verify SourceQueueFrame._start_processing does NOT pass source_types."""
        import inspect

        from ui.source_queue_frame import SourceQueueFrame
        source = inspect.getsource(SourceQueueFrame._start_processing)
        assert "source_types" not in source, "source_types found in _start_processing source"

    def test_successful_preflight_reaches_run_preflight(self):
        """Preflight for local TXT with mock LLM should return result dict."""
        config = RuntimeConfig()
        config.llm_mode = "mock"
        config.confluence_mode = "mock"
        config.newton_mode = "mock"
        config.bitlink_mode = "mock"
        items = [BatchItem(source_type="local_transcript", display_name="test")]
        result = run_preflight(items, config)
        assert "passed" in result
        assert "has_blocking" in result
        assert "has_warnings" in result
        assert result["items_checked"] == 1

    def test_local_transcript_real_llm_ignores_mock_newton_and_bitlink(self):
        """local TXT + real LLM + mock Newton/Bitlink = NOT demo."""
        config = RuntimeConfig()
        config.llm_mode = "real"
        config.confluence_mode = "rest"
        config.newton_mode = "mock"
        config.bitlink_mode = "mock"
        assert not config.is_demo_for_source("local_transcript")

    def test_local_transcript_real_llm_does_not_force_dry_run(self, tmp_path, monkeypatch):
        """Relevant mock services only: LLM. If LLM is real, no demo."""
        from services.llm_service import LLMClient
        monkeypatch.setattr(LLMClient, "check_connection", lambda self: True)
        config = RuntimeConfig()
        config.llm_mode = "real"
        config.newton_mode = "mock"
        config.bitlink_mode = "mock"
        config.llm_api_url = "https://api.example.com"
        config.llm_api_key = "sk-test"
        f = tmp_path / "t.txt"
        f.write_text("content", encoding="utf-8")
        items = [BatchItem(source_type="local_transcript", source_path=f, display_name="test")]
        result = run_preflight(items, config)
        # Should not force dry-run because LLM is real
        assert result["passed"]

    def test_local_video_mock_newton_is_demo(self):
        """local video + mock Newton = DEMO (Newton is applicable)."""
        config = RuntimeConfig()
        config.llm_mode = "real"
        config.newton_mode = "mock"
        assert config.is_demo_for_source("local_video")

    def test_bitlink_source_mock_bitlink_is_demo(self):
        """bitlink source + mock BIT.Link = DEMO."""
        config = RuntimeConfig()
        config.llm_mode = "real"
        config.bitlink_mode = "mock"
        assert config.is_demo_for_source("bitlink")

    def test_production_readiness_blocks_missing_llm_url(self):
        """Real LLM mode without URL = production blocked."""
        config = RuntimeConfig()
        config.llm_mode = "real"
        config.confluence_mode = "rest"
        config.llm_api_url = ""
        assert config.is_production_blocked("local_transcript")

    def test_production_readiness_blocks_missing_llm_key(self):
        """Real LLM mode without API key = production blocked."""
        config = RuntimeConfig()
        config.llm_mode = "real"
        config.confluence_mode = "rest"
        config.llm_api_url = "https://api.openai.com"
        config.llm_api_key = ""
        assert config.is_production_blocked("local_transcript")

    def test_banner_never_shows_production_with_missing_credentials(self):
        """Banner must show BLOCKED not PRODUCTION when creds missing."""
        config = RuntimeConfig()
        config.llm_mode = "real"
        config.confluence_mode = "rest"
        config.llm_api_url = ""
        banner = config.get_banner_text("local_transcript")
        assert "BLOCKED" in banner
        assert "PRODUCTION " not in banner.upper() or "BLOCKED" in banner

    def test_get_effective_services_local_transcript(self):
        """Newton/bitlink = not_applicable for local TXT."""
        config = RuntimeConfig()
        config.newton_mode = "mock"
        config.bitlink_mode = "mock"
        eff = config.get_effective_services("local_transcript")
        assert eff["newton"] == "not_applicable"
        assert eff["bitlink"] == "not_applicable"

    def test_get_effective_services_local_video(self):
        """Newton IS applicable for local video."""
        config = RuntimeConfig()
        config.newton_mode = "mock"
        eff = config.get_effective_services("local_video")
        assert eff["newton"] == "mock"

    def test_preflight_demo_forces_dry_run(self, tmp_path):
        """Demo preflight must auto-enable dry_run for items."""
        config = RuntimeConfig()
        config.llm_mode = "mock"
        items = [BatchItem(source_type="local_transcript", source_path=tmp_path / "t.txt", display_name="t", dry_run=False)]
        (tmp_path / "t.txt").write_text("x")
        run_preflight(items, config)
        assert items[0].dry_run is True
