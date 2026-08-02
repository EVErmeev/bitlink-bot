import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env", override=False)

DATA_DIR = BASE_DIR / "data"
DEBUG_DIR = BASE_DIR / "debug"


def _str(key: str, default: str = "") -> str:
    return os.getenv(key, default)


def _bool(key: str, default: bool = False) -> bool:
    val = os.getenv(key, str(default)).lower()
    return val in ("1", "true", "yes", "on")


def _float_opt(key: str, default: float | None = None) -> float | None:
    val = os.getenv(key)
    if val is None or val == "":
        return default
    try:
        return float(val)
    except ValueError:
        return default


# ── BIT.Link ──
BITLINK_EMAIL: str = _str("BITLINK_EMAIL")
BITLINK_PASSWORD: str = _str("BITLINK_PASSWORD")
BITLINK_BASE_URL: str = _str("BITLINK_BASE_URL")
BITLINK_MOCK: bool = _bool("BITLINK_MOCK", True)

# ── Newton ──
NEWTON_TOKEN: str = _str("NEWTON_TOKEN")
NEWTON_PATH: str = _str("NEWTON_PATH")
NEWTON_BASE_URL: str = _str("NEWTON_BASE_URL")
NEWTON_MOCK: bool = _bool("NEWTON_MOCK", True)

# ── Confluence ──
CONFLUENCE_PROVIDER: str = _str("CONFLUENCE_PROVIDER", "mock")
CONFLUENCE_MCP_SERVER: str = _str("CONFLUENCE_MCP_SERVER")
CONFLUENCE_MCP_TIMEOUT_SECONDS: int = int(_str("CONFLUENCE_MCP_TIMEOUT_SECONDS", "60"))
CONFLUENCE_TOKEN: str = _str("CONFLUENCE_TOKEN")
CONFLUENCE_BASE_URL: str = _str("CONFLUENCE_BASE_URL")
CONFLUENCE_SPACE_KEY: str = _str("CONFLUENCE_SPACE_KEY")
CONFLUENCE_PARENT_PAGE_ID: str = _str("CONFLUENCE_PARENT_PAGE_ID")
CONFLUENCE_PARENT_PAGE_TITLE: str = _str("CONFLUENCE_PARENT_PAGE_TITLE")
CONFLUENCE_MOCK: bool = _bool("CONFLUENCE_MOCK", True)

# ── Telegram ──
TG_BOT_TOKEN: str = _str("TG_BOT_TOKEN")
TG_CHAT_ID: str = _str("TG_CHAT_ID")
TELEGRAM_ENABLED: bool = _bool("TELEGRAM_ENABLED", False)
TELEGRAM_SEND_BATCH_SUMMARY: bool = _bool("TELEGRAM_SEND_BATCH_SUMMARY", True)
TELEGRAM_MOCK: bool = _bool("TELEGRAM_MOCK", True)

# ── LLM ──
LLM_PROVIDER: str = _str("LLM_PROVIDER", "mock")
LLM_MOCK: bool = _bool("LLM_MOCK", True)
LLM_API_URL: str = _str("LLM_API_URL")
LLM_API_KEY: str = _str("LLM_API_KEY")
LLM_MODEL: str = _str("LLM_MODEL", "gpt-4o")
ONEBIT_CLI_PATH: str = _str("ONEBIT_CLI_PATH", "C:\\Users\\egore\\AppData\\Local\\NewtonCLI\\newton.cmd")
ONEBIT_CLI_TRANSPORT: str = _str("ONEBIT_CLI_TRANSPORT", "native")
ONEBIT_CLI_TIMEOUT_SECONDS: int = int(_str("ONEBIT_CLI_TIMEOUT_SECONDS", "120"))

# ── Protocol ──
PROTOCOL_TEMPLATE: str = _str("PROTOCOL_TEMPLATE", "project_detailed")
PROTOCOL_MODE: str = _str("PROTOCOL_MODE", "auto")
PROTOCOL_QUALITY_MODE: str = _str("PROTOCOL_QUALITY_MODE", "advisory")  # off | advisory | strict
DETAILED_WORD_THRESHOLD: float | None = _float_opt("DETAILED_WORD_THRESHOLD")
DETAILED_DURATION_THRESHOLD: float | None = _float_opt("DETAILED_DURATION_THRESHOLD")
BATCH_CONTINUE_AFTER_ERROR: bool = _bool("BATCH_CONTINUE_AFTER_ERROR", True)

# ── Settings validation ──

def validate_settings(source_type: str) -> list[str]:
    missing = []
    is_live = CONFLUENCE_PROVIDER != "mock"
    if source_type == "bitlink":
        if not BITLINK_BASE_URL and not BITLINK_MOCK:
            missing.append("BITLINK_BASE_URL")
        if not NEWTON_BASE_URL and not NEWTON_MOCK:
            missing.append("NEWTON_BASE_URL")
        if not CONFLUENCE_BASE_URL and is_live:
            missing.append("CONFLUENCE_BASE_URL")
    elif source_type == "local_video":
        if not NEWTON_BASE_URL and not NEWTON_MOCK:
            missing.append("NEWTON_BASE_URL")
        if not CONFLUENCE_BASE_URL and is_live:
            missing.append("CONFLUENCE_BASE_URL")
    elif source_type == "local_transcript":
        if not CONFLUENCE_BASE_URL and is_live:
            missing.append("CONFLUENCE_BASE_URL")
    if source_type in ("bitlink", "local_video", "local_transcript"):
        if not CONFLUENCE_BASE_URL and is_live:
            missing.append("CONFLUENCE_BASE_URL")
    return missing
