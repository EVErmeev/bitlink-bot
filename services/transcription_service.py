from pathlib import Path
import settings


class TranscriptionConfigurationError(Exception):
    pass


class TranscriptionClient:
    def __init__(self, token=None, base_url=None, newton_path=None):
        self.mock_mode = settings.NEWTON_MOCK
        self.token = token or settings.NEWTON_TOKEN
        self.base_url = base_url or settings.NEWTON_BASE_URL
        self.newton_path = newton_path or settings.NEWTON_PATH

        if not self.mock_mode:
            missing = []
            if not self.token:
                missing.append("NEWTON_TOKEN")
            if not self.base_url:
                missing.append("NEWTON_BASE_URL")
            if missing:
                raise TranscriptionConfigurationError(
                    f"NEWTON_MOCK=false, но отсутствуют настройки: {', '.join(missing)}. "
                    f"Укажите их в .env или установите NEWTON_MOCK=true."
                )

    def check_connection(self) -> bool:
        if self.mock_mode:
            return True
        return bool(self.token and self.base_url)

    def transcribe_video(self, video_path: Path, output_dir: Path) -> str:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        if self.mock_mode:
            name = video_path.stem
            transcript = f"""[Mock transcript from video: {name}]

[00:00] Ведущий: Добрый день, коллеги. Начинаем встречу по обсуждению текущего статуса проекта.
[00:15] Участник 1: У нас есть несколько вопросов, требующих решения.
[00:30] Ведущий: Давайте пройдём по повестке. Первый вопрос — статус разработки модуля интеграции.
[01:00] Участник 2: Модуль готов на 80%, осталось тестирование API-контрактов.
[01:30] Ведущий: Какие риски вы видите?
[02:00] Участник 2: Основной риск — зависимость от внешнего сервиса, который может изменить API.
[02:30] Ведущий: Предлагаю зафиксировать это как риск и запланировать альтернативное решение.
[03:00] Участник 1: Согласен. Также нужно определить ответственного за тестирование.
[03:30] Ведущий: Назначаем Иванова ответственным, срок — до 30 июля.
[04:00] Участник 2: Принято. Следующий вопрос — бюджет на следующий этап.
[04:30] Участник 1: Бюджет требует уточнения, точные цифры предоставлю завтра.
[05:00] Ведущий: Хорошо, ждём информацию. Переходим к задачам.
[05:30] Ведущий: Задача 1 — завершить тестирование модуля до 30.07.2026. Ответственный: Иванов.
[06:00] Ведущий: Задача 2 — подготовить уточнённый бюджет. Ответственный: Петров, срок 28.07.2026.
[06:30] Ведущий: Есть ли ещё вопросы?
[07:00] Участник 1: Вопрос по срокам внедрения — реалистично ли уложиться до сентября?
[07:30] Ведущий: Вопрос остаётся открытым, требуется оценка от команды разработки.
[08:00] Ведущий: Хорошо, на этом завершаем. Спасибо всем.
"""
            tpath = output_dir / f"{name}_transcript.txt"
            tpath.write_text(transcript, encoding="utf-8")
            return transcript
        raise NotImplementedError(
            "Реальная транскрибация через Newton API не реализована. "
            "Используйте NEWTON_MOCK=true для mock-режима."
        )