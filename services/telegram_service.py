class TelegramClient:
    def __init__(self, bot_token=None, chat_id=None):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.mock_mode = True
        self.enabled = False

    def check_connection(self) -> bool:
        if not self.bot_token or not self.chat_id:
            self.enabled = False
            return False
        self.enabled = self.mock_mode
        return self.mock_mode

    def send_notification(self, protocol_title: str, meeting_date: str,
                          key_result: str, confluence_url: str) -> bool:
        if not self.enabled:
            return False
        message = (
            f"[Mock Telegram] {protocol_title}\n"
            f"Дата: {meeting_date}\n"
            f"Итог: {key_result}\n"
            f"Ссылка: {confluence_url}"
        )
        print(message)
        return True

    def send_batch_summary(self, summary: str) -> bool:
        if not self.enabled:
            return False
        message = f"[Mock Telegram Batch] {summary}"
        print(message)
        return True