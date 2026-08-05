from services.runtime_config import RuntimeConfig


def build_bitlink_client(config: RuntimeConfig):
    from services.bitlink_service import BitlinkClient
    if config.bitlink_provider == "mock":
        return BitlinkClient()
    if config.bitlink_provider == "disabled":
        return BitlinkClient()
    # Real adapter not implemented — return mock as fallback for now
    return BitlinkClient()


def build_transcription_client(config: RuntimeConfig):
    from services.transcription_service import TranscriptionClient
    if config.transcription_provider == "mock":
        return TranscriptionClient()
    if config.transcription_provider == "disabled":
        raise ValueError("Transcription disabled")
    if config.transcription_provider == "onebit_newton_cli":
        return TranscriptionClient(token=config.onebit_token, cli_path=config.onebit_cli_path)
    raise ValueError(f"Unknown transcription_provider: {config.transcription_provider}")


def build_confluence_client(config: RuntimeConfig):
    from services.confluence_service import ConfluenceClient
    if config.confluence_provider == "mock":
        return ConfluenceClient()
    if not config.confluence_base_url or not config.confluence_token:
        raise ValueError("Confluence real mode requires CONFLUENCE_BASE_URL and CONFLUENCE_TOKEN")
    return ConfluenceClient(base_url=config.confluence_base_url, token=config.confluence_token, space_key=config.confluence_space_key)


def build_telegram_client(config: RuntimeConfig):
    from services.telegram_service import TelegramClient
    if config.telegram_provider == "disabled":
        return TelegramClient(bot_token="", chat_id="")
    if config.telegram_provider == "mock":
        return TelegramClient(bot_token=config.telegram_bot_token, chat_id=config.telegram_chat_id)
    if not config.telegram_bot_token or not config.telegram_chat_id:
        raise ValueError("Telegram real mode requires TG_BOT_TOKEN and TG_CHAT_ID")
    return TelegramClient(bot_token=config.telegram_bot_token, chat_id=config.telegram_chat_id)


def build_llm_client(config: RuntimeConfig):
    from services.llm_service import LLMClient
    return LLMClient(
        mock_mode=(config.llm_provider == "mock"),
        provider_type=config.llm_provider,
        api_url=config.llm_api_url,
        api_key=config.onebit_token or config.llm_api_key,
        model=config.llm_model,
        cli_path=config.onebit_cli_path,
        cli_transport=config.onebit_transport,
        timeout_seconds=config.onebit_timeout_seconds,
    )
