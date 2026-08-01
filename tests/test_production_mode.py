import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from services.runtime_config import RuntimeConfig


class TestProductionMode:
    def test_local_txt_ignores_newton_mock_for_demo_status(self):
        c = RuntimeConfig()
        c.llm_mode = "real"
        c.confluence_mode = "rest"
        c.newton_mode = "mock"
        c.bitlink_mode = "mock"
        assert not c.is_demo_for_source("local_transcript")

    def test_local_txt_ignores_bitlink_mock_for_demo_status(self):
        c = RuntimeConfig()
        c.llm_mode = "real"
        c.confluence_mode = "rest"
        c.newton_mode = "mock"
        c.bitlink_mode = "mock"
        assert not c.is_demo_for_source("local_transcript")

    def test_local_txt_real_llm_is_not_demo(self):
        c = RuntimeConfig()
        c.llm_mode = "real"
        c.confluence_mode = "rest"
        assert not c.is_demo_for_source("local_transcript")

    def test_local_txt_mock_llm_is_demo(self):
        c = RuntimeConfig()
        c.llm_mode = "mock"
        assert c.is_demo_for_source("local_transcript")

    def test_empty_queue_banner_uses_selected_profile(self):
        c = RuntimeConfig()
        c.set_profile("local_txt_production")
        banner = c.get_banner_text("local_transcript")
        assert "PRODUCTION" in banner or "BLOCKED" in banner

    def test_production_profile_sets_expected_modes(self):
        c = RuntimeConfig()
        c.set_profile("local_txt_production")
        assert c.llm_mode == "real"
        assert c.newton_mode == "disabled"
        assert c.bitlink_mode == "disabled"

    def test_demo_profile_forces_dry_run(self):
        c = RuntimeConfig()
        c.set_profile("demo")
        assert c.llm_mode == "mock"
        assert c.confluence_mode == "mock"

    def test_get_effective_services_for_local_transcript(self):
        c = RuntimeConfig()
        eff = c.get_effective_services("local_transcript")
        assert eff["newton"] == "not_applicable"
        assert eff["bitlink"] == "not_applicable"

    def test_get_effective_services_for_local_video(self):
        c = RuntimeConfig()
        eff = c.get_effective_services("local_video")
        assert eff["newton"] != "not_applicable"

    def test_mock_llm_never_publishes_real_confluence(self):
        c = RuntimeConfig()
        c.llm_mode = "mock"
        c.confluence_mode = "rest"
        assert c.is_demo_for_source("local_transcript")

    def test_production_readiness_blocks_missing_llm_key(self):
        c = RuntimeConfig()
        c.llm_mode = "real"
        c.confluence_mode = "rest"
        c.llm_api_url = ""
        assert c.is_production_blocked("local_transcript")

    def test_production_readiness_skips_newton_for_local_txt(self):
        c = RuntimeConfig()
        c.llm_mode = "real"
        c.confluence_mode = "rest"
        c.newton_mode = "mock"
        eff = c.get_effective_services("local_transcript")
        assert eff["newton"] == "not_applicable"

    def test_banner_text_demo(self):
        c = RuntimeConfig()
        c.llm_mode = "mock"
        banner = c.get_banner_text("local_transcript")
        assert "DEMO" in banner

    def test_banner_text_production(self):
        c = RuntimeConfig()
        c.app_profile = "local_txt_production"
        c.llm_mode = "real"
        c.llm_api_url = "https://api.example.com"
        c.llm_api_key = "sk-test"
        c.confluence_mode = "rest"
        banner = c.get_banner_text("local_transcript")
        assert "PRODUCTION" in banner
        assert "LLM: real" in banner
