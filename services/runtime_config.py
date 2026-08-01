import os
from dataclasses import dataclass


@dataclass
class RuntimeConfig:
    app_profile: str = "demo"  # demo | local_txt_production | custom
    newton_mode: str = "mock"
    newton_token: str = ""
    newton_base_url: str = ""
    newton_exec_path: str = ""
    llm_mode: str = "mock"
    llm_api_url: str = ""
    llm_api_key: str = ""
    llm_model: str = "gpt-4o"
    confluence_mode: str = "mock"
    confluence_base_url: str = ""
    confluence_token: str = ""
    confluence_space_key: str = ""
    confluence_parent_page_id: str = ""
    confluence_parent_page_title: str = ""
    telegram_mode: str = "disabled"
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    telegram_enabled: bool = False
    telegram_send_batch_summary: bool = True
    bitlink_mode: str = "mock"
    bitlink_email: str = ""
    bitlink_password: str = ""
    bitlink_base_url: str = ""
    protocol_template: str = "project_detailed"
    protocol_mode: str = "auto"
    batch_continue_after_error: bool = True

    @classmethod
    def from_settings(cls):
        import settings
        c = cls()
        c.app_profile = os.getenv("APP_PROFILE", "demo")
        c.newton_mode = "mock" if settings.NEWTON_MOCK else "http_api"
        c.newton_token = settings.NEWTON_TOKEN
        c.newton_base_url = settings.NEWTON_BASE_URL
        c.newton_exec_path = settings.NEWTON_PATH
        c.llm_mode = "mock" if settings.LLM_MOCK else "real"
        c.llm_api_url = settings.LLM_API_URL
        c.llm_api_key = settings.LLM_API_KEY
        c.llm_model = settings.LLM_MODEL
        c.confluence_mode = settings.CONFLUENCE_PROVIDER
        c.confluence_base_url = settings.CONFLUENCE_BASE_URL
        c.confluence_token = settings.CONFLUENCE_TOKEN
        c.confluence_space_key = settings.CONFLUENCE_SPACE_KEY
        c.confluence_parent_page_id = settings.CONFLUENCE_PARENT_PAGE_ID
        c.confluence_parent_page_title = settings.CONFLUENCE_PARENT_PAGE_TITLE
        c.telegram_mode = "mock" if settings.TELEGRAM_MOCK else ("real" if settings.TELEGRAM_ENABLED else "disabled")
        c.telegram_bot_token = settings.TG_BOT_TOKEN
        c.telegram_chat_id = settings.TG_CHAT_ID
        c.telegram_enabled = settings.TELEGRAM_ENABLED
        c.telegram_send_batch_summary = settings.TELEGRAM_SEND_BATCH_SUMMARY
        c.bitlink_mode = "mock" if settings.BITLINK_MOCK else "real"
        c.bitlink_email = settings.BITLINK_EMAIL
        c.bitlink_password = settings.BITLINK_PASSWORD
        c.bitlink_base_url = settings.BITLINK_BASE_URL
        c.protocol_template = settings.PROTOCOL_TEMPLATE
        c.protocol_mode = settings.PROTOCOL_MODE
        c.batch_continue_after_error = settings.BATCH_CONTINUE_AFTER_ERROR
        return c

    def set_profile(self, profile_name: str):
        self.app_profile = profile_name
        if profile_name == "demo":
            self.llm_mode = "mock"
            self.newton_mode = "mock"
            self.bitlink_mode = "mock"
            self.confluence_mode = "mock"
            self.telegram_mode = "disabled"
        elif profile_name == "local_txt_production":
            self.llm_mode = "real"
            self.confluence_mode = "rest"
            self.telegram_mode = "disabled"
            self.newton_mode = "disabled"
            self.bitlink_mode = "disabled"

    def get_effective_services(self, source_type: str) -> dict:
        all_services = {
            "llm": self.llm_mode,
            "newton": self.newton_mode if source_type in ("local_video",) else "not_applicable",
            "bitlink": self.bitlink_mode if source_type in ("bitlink",) else "not_applicable",
            "confluence": self.confluence_mode,
            "telegram": self.telegram_mode,
        }
        return all_services

    def is_demo_for_source(self, source_type: str) -> bool:
        effective = self.get_effective_services(source_type)
        mock_services = [k for k, v in effective.items() if v == "mock" and k not in ("newton", "bitlink")]
        return len(mock_services) > 0

    def is_production_blocked(self, source_type: str) -> bool:
        effective = self.get_effective_services(source_type)
        if self.app_profile == "demo":
            return True
        if effective.get("llm") == "mock":
            return True
        if effective.get("confluence") not in ("disabled", "mock", "rest"):
            return True
        return False

    def get_banner_text(self, source_type: str = "local_transcript") -> str:
        effective = self.get_effective_services(source_type)
        if self.is_demo_for_source(source_type):
            parts = ["DEMO"]
            if effective["llm"] == "mock":
                parts.append("LLM: mock")
            if effective["confluence"] == "mock":
                parts.append("Confluence: mock")
            parts.append("Dry-run forced")
            return " | ".join(parts)
        if self.is_production_blocked(source_type):
            parts = ["PRODUCTION BLOCKED"]
            if effective["llm"] == "mock":
                parts.append("LLM: mock (configure real LLM)")
            if effective["confluence"] not in ("rest", "disabled"):
                parts.append("Confluence: not configured")
            return " | ".join(parts)
        parts = ["PRODUCTION"]
        if effective["llm"] == "real":
            parts.append("LLM: real")
        if effective["confluence"] == "rest":
            parts.append("Confluence: REST")
        elif effective["confluence"] == "disabled":
            parts.append("Confluence: disabled")
        if effective["telegram"] == "real":
            parts.append("Telegram: real")
        return " | ".join(parts)

    def is_demo_mode(self):
        return any([
            self.llm_mode == "mock",
            self.newton_mode == "mock",
            self.confluence_mode == "mock",
            self.telegram_mode == "mock",
            self.bitlink_mode == "mock",
        ])

    def to_safe_dict(self):
        return {
            "app_profile": self.app_profile,
            "newton_mode": self.newton_mode,
            "llm_mode": self.llm_mode, "llm_model": self.llm_model,
            "confluence_mode": self.confluence_mode, "confluence_space_key": self.confluence_space_key,
            "telegram_mode": self.telegram_mode, "telegram_enabled": self.telegram_enabled,
            "bitlink_mode": self.bitlink_mode,
            "protocol_template": self.protocol_template, "protocol_mode": self.protocol_mode,
            "is_demo_mode": self.is_demo_mode(),
        }


_runtime_config = None


def get_runtime_config() -> RuntimeConfig:
    global _runtime_config
    if _runtime_config is None:
        _runtime_config = RuntimeConfig.from_settings()
    return _runtime_config


def reload_runtime_config():
    global _runtime_config
    from dotenv import load_dotenv

    import settings
    load_dotenv(settings.BASE_DIR / ".env", override=True)
    import importlib
    importlib.reload(settings)
    _runtime_config = RuntimeConfig.from_settings()
    return _runtime_config
