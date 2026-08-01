import settings
import requests


class TelegramConfigurationError(Exception):
    pass


class TelegramClient:
    def __init__(self, bot_token=None, chat_id=None):
        self.mock_mode = settings.TELEGRAM_MOCK
        self.bot_token = bot_token or settings.TG_BOT_TOKEN
        self.chat_id = chat_id or settings.TG_CHAT_ID
        self.enabled = settings.TELEGRAM_ENABLED

        if self.mock_mode:
            self.enabled = bool(self.bot_token and self.chat_id)
            return

        missing = []
        if not self.bot_token:
            missing.append("TG_BOT_TOKEN")
        if not self.chat_id:
            missing.append("TG_CHAT_ID")
        if missing:
            raise TelegramConfigurationError(
                f"TELEGRAM_MOCK=false, но отсутствуют настройки: {', '.join(missing)}. "
                f"Укажите их в .env или установите TELEGRAM_MOCK=true."
            )

        self.enabled = True

    def check_connection(self) -> bool:
        if self.mock_mode:
            return self.enabled
        try:
            resp = requests.get(
                f"https://api.telegram.org/bot{self.bot_token}/getMe",
                timeout=10,
            )
            return resp.status_code == 200 and resp.json().get("ok", False)
        except Exception:
            return False

    def send_notification(self, protocol_title: str, meeting_date: str,
                          key_result: str, confluence_url: str) -> bool:
        if not self.enabled:
            return False

        message = (
            f"{protocol_title}\n"
            f"Дата: {meeting_date}\n"
            f"Итог: {key_result[:300] if key_result else 'Протокол сформирован'}\n"
            f"Ссылка: {confluence_url}"
        )

        if self.mock_mode:
            print(f"[Mock Telegram] {message}")
            return True

        try:
            resp = requests.post(
                f"https://api.telegram.org/bot{self.bot_token}/sendMessage",
                json={
                    "chat_id": self.chat_id,
                    "text": message,
                    "parse_mode": "Markdown",
                    "disable_web_page_preview": False,
                },
                timeout=15,
            )
            return resp.status_code == 200 and resp.json().get("ok", False)
        except Exception as e:
            print(f"Telegram send failed: {e}")
            return False

    def send_batch_summary(self, summary: str) -> bool:
        if not self.enabled:
            return False

        if self.mock_mode:
            print(f"[Mock Telegram Batch] {summary}")
            return True

        try:
            resp = requests.post(
                f"https://api.telegram.org/bot{self.bot_token}/sendMessage",
                json={
                    "chat_id": self.chat_id,
                    "text": summary,
                    "parse_mode": "Markdown",
                },
                timeout=15,
            )
            return resp.status_code == 200 and resp.json().get("ok", False)
        except Exception as e:
            print(f"Telegram batch summary failed: {e}")
            return False