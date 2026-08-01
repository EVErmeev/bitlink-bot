from services.runtime_config import RuntimeConfig


def build_bitlink_client(config: RuntimeConfig):
    from services.bitlink_service import BitlinkClient
    if config.bitlink_mode == "mock":
        return BitlinkClient()
    if not config.bitlink_base_url or not config.bitlink_email:
        raise ValueError("BIT.Link real mode requires BITLINK_BASE_URL and BITLINK_EMAIL")
    return BitlinkClient(base_url=config.bitlink_base_url, email=config.bitlink_email, password=config.bitlink_password)


def build_transcription_client(config: RuntimeConfig):
    from services.transcription_service import TranscriptionClient
    if config.newton_mode == "mock":
        return TranscriptionClient()
    if config.newton_mode == "disabled":
        raise ValueError("Newton disabled - cannot transcribe")
    if config.newton_mode == "http_api":
        raise ValueError("Newton HTTP API contract not confirmed - real transcription unavailable")
    raise ValueError(f"Unknown newton_mode: {config.newton_mode}")


def build_confluence_client(config: RuntimeConfig):
    from services.confluence_service import ConfluenceClient
    if config.confluence_mode == "mock":
        return ConfluenceClient()
    if not config.confluence_base_url or not config.confluence_token:
        raise ValueError("Confluence real mode requires CONFLUENCE_BASE_URL and CONFLUENCE_TOKEN")
    return ConfluenceClient(base_url=config.confluence_base_url, token=config.confluence_token, space_key=config.confluence_space_key)


def build_telegram_client(config: RuntimeConfig):
    from services.telegram_service import TelegramClient
    if config.telegram_mode == "disabled":
        return TelegramClient(bot_token="", chat_id="")
    if config.telegram_mode == "mock":
        return TelegramClient(bot_token=config.telegram_bot_token, chat_id=config.telegram_chat_id)
    if not config.telegram_bot_token or not config.telegram_chat_id:
        raise ValueError("Telegram real mode requires TG_BOT_TOKEN and TG_CHAT_ID")
    return TelegramClient(bot_token=config.telegram_bot_token, chat_id=config.telegram_chat_id)


def build_llm_client(config: RuntimeConfig):
    from services.llm_service import LLMClient
    if config.llm_mode == "mock":
        return LLMClient(mock_mode=True)
    if not config.llm_api_url or not config.llm_api_key:
        raise ValueError("LLM real mode requires LLM_API_URL and LLM_API_KEY")
    return LLMClient(api_url=config.llm_api_url, api_key=config.llm_api_key,
                     model=config.llm_model, mock_mode=False)
