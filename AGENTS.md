# AGENTS.md — Постоянные правила проекта bitlink-bot

## Репозиторий и PR

- Репозиторий: `EVErmeev/bitlink-bot`
- Рабочая ветка: `fix/audit-e7cc95f`
- Draft PR: https://github.com/EVErmeev/bitlink-bot/pull/1
- **PR #1 всегда остаётся Draft**
- **Merge не выполнять**
- **`accepted` не устанавливать**

## Перед началом работы

1. Проверить remote headRefOid через `gh pr view 1 --json headRefOid`
2. Прочитать `docs/opencode/manifest.json`
3. Изучить последний HANDOFF-файл в `docs/opencode/`
4. Прочитать `docs/opencode/START-NEXT-SESSION.md`
5. Сравнить локальный и remote head — при расхождении изучить diff

## Правила разработки

1. Каждая итерация имеет отдельный TASK и VALIDATION файл в `docs/opencode/tasks/` и `docs/opencode/validations/`
2. Не переходить к другим задачам без завершения текущей
3. `pytest -q` не заменяет Windows GUI E2E через `start_app.bat`
4. Не считать задачу выполненной только по unit-тестам
5. Реальный результат подтверждается Confluence URL и Telegram message ID
6. Не менять код рабочего pipeline без подтверждённого дефекта

## Запуск

- Приложение запускается через `call start_app.bat`
- `start_app.bat --startup-check` — проверка импортов без GUI

## Безопасность

- Секреты (токены, пароли, API keys) **запрещено** выводить в:
  - логи;
  - отчёты;
  - validation-файлы;
  - manifest;
  - git diff;
  - ответы OpenCode.

## Обязательные проверки перед commit

```bash
python -m compileall .
pytest -q
ruff check .
mypy . --ignore-missing-imports
call start_app.bat --startup-check
```

## Статусы задач

- `OPEN` — не исправлено
- `IN_PROGRESS` — в работе
- `FIXED` — исправлено
- `PARTIALLY_FIXED` — частично исправлено
- `NOT_FIXED` — не исправлено
- `NOT_VERIFIABLE` — невозможно проверить
- `REGRESSION` — регресс
- `USER_ACTION_REQUIRED` — требуется действие пользователя

## Ключевые файлы

| Файл | Назначение |
|---|---|
| `start_app.bat` | Точка входа GUI |
| `app.py` | GUI приложение |
| `bot.py` / `cli.py` | CLI |
| `settings.py` | Конфигурация из .env |
| `services/processing_service.py` | Основной пайплайн обработки |
| `services/llm_providers.py` | Провайдеры LLM (Mock, OpenAI, OneBit Newton CLI) |
| `services/transcription_service.py` | Транскрибация через Newton CLI |
| `services/confluence_service.py` | Публикация в Confluence (REST) |
| `services/telegram_service.py` | Уведомления Telegram |
| `services/process_runner.py` | Безопасный subprocess runner |
| `services/json_response_parser.py` | Парсинг и repair JSON |
| `services/protocol_register_extractor.py` | LLM extraction pass реестров |
| `protocol_templates/project_detailed.py` | Шаблон v3.0 |
| `protocol_templates/management_summary.py` | Управленческий протокол |
| `ui/source_queue_frame.py` | Окно очереди обработки |
| `ui/settings_frame.py` | Страница настроек |
| `docs/opencode/manifest.json` | Точка входа служебного контура |