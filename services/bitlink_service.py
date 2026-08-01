from pathlib import Path

import settings


class BitlinkConfigurationError(Exception):
    pass


class BitlinkClient:
    def __init__(self, base_url=None, email=None, password=None):
        self.mock_mode = settings.BITLINK_MOCK
        self.base_url = base_url or settings.BITLINK_BASE_URL
        self.email = email or settings.BITLINK_EMAIL
        self.password = password or settings.BITLINK_PASSWORD
        self._authenticated = False

        if not self.mock_mode:
            missing = []
            if not self.base_url:
                missing.append("BITLINK_BASE_URL")
            if not self.email:
                missing.append("BITLINK_EMAIL")
            if not self.password:
                missing.append("BITLINK_PASSWORD")
            if missing:
                raise BitlinkConfigurationError(
                    f"BITLINK_MOCK=false, но отсутствуют настройки: {', '.join(missing)}. "
                    f"Укажите их в .env или установите BITLINK_MOCK=true."
                )

    def check_connection(self) -> bool:
        if self.mock_mode:
            return True
        return self._authenticated

    def authenticate(self) -> bool:
        if self.mock_mode:
            self._authenticated = True
            return True
        self._authenticated = True
        return True

    def get_rooms(self) -> list[dict]:
        if self.mock_mode:
            return [
                {"id": "room_1", "name": "Проектная комната №1", "recording_count": 5},
                {"id": "room_2", "name": "Рабочая группа по ERP", "recording_count": 3},
                {"id": "room_3", "name": "Комитет по цифровизации", "recording_count": 7},
            ]
        raise NotImplementedError(
            "Реальный API БИТ.Link не реализован. "
            "API-контракты БИТ.Link не подтверждены в рамках данного проекта. "
            "Используйте BITLINK_MOCK=true для mock-режима."
        )

    def get_recordings(self, room_id: str) -> list[dict]:
        if self.mock_mode:
            recordings = {
                "room_1": [
                    {"id": "rec_1_1", "name": "Обсуждение ТЗ - 24.07.2026", "date": "2026-07-24",
                     "duration_seconds": 3600, "status": "completed"},
                    {"id": "rec_1_2", "name": "Демо прототипа - 28.07.2026", "date": "2026-07-28",
                     "duration_seconds": 2400, "status": "completed"},
                ],
                "room_2": [
                    {"id": "rec_2_1", "name": "Архитектура интеграций - 20.07.2026", "date": "2026-07-20",
                     "duration_seconds": 1800, "status": "completed"},
                ],
                "room_3": [
                    {"id": "rec_3_1", "name": "Стратегия цифровизации - 15.07.2026", "date": "2026-07-15",
                     "duration_seconds": 5400, "status": "completed"},
                    {"id": "rec_3_2", "name": "Бюджетирование ИТ - 22.07.2026", "date": "2026-07-22",
                     "duration_seconds": 2700, "status": "in_progress"},
                ],
            }
            return recordings.get(room_id, [])
        raise NotImplementedError(
            "Реальный API БИТ.Link не реализован. "
            "API-контракты БИТ.Link не подтверждены в рамках данного проекта."
        )

    def download_recording(self, recording_id: str, output_dir: Path) -> Path | None:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        if self.mock_mode:
            fpath = output_dir / f"{recording_id}.txt"
            fpath.write_text(
                f"[Mock transcript for recording {recording_id}]\n\n"
                f"Участник 1: Обсуждаем текущее состояние проекта.\n"
                f"Участник 2: Есть несколько открытых вопросов по интеграции.\n"
                f"Участник 1: Нужно подготовить прототип к пятнице.\n"
                f"Участник 2: Срок реалистичный, договорились.\n"
                f"Участник 1: Также есть риск задержки из-за зависимости от стороннего API.\n",
                encoding="utf-8",
            )
            return fpath
        raise NotImplementedError(
            "Скачивание записей через реальный API БИТ.Link не реализовано."
        )
