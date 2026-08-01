# bitlink-bot — Генератор протоколов встреч

Приложение для формирования протоколов встреч из записей БИТ.Link, локальных видео и локальных расшифровок, с публикацией в Confluence и уведомлениями в Telegram.

## Возможности

- **Три источника**: БИТ.Link, локальное видео (`.mp4`, `.webm`, `.m4v`), локальные расшифровки (`.txt`, `.md`)
- **Четыре шаблона протоколов**: Управленческий, Проектный, Подробный проектный (v3.0), Обследование бизнес-процессов
- **Пакетная обработка**: очередь из нескольких источников с независимыми настройками
- **Прогресс и ETA**: «Протокол X из Y», общий/текущий прогресс, оставшееся время
- **Изоляция источников**: уникальный `source_context_id` и SHA-256 для каждого файла, запрет смешения
- **Валидация**: фактологическая, структурная, HTML — публикация только при 4 пройденных проверках
- **Confluence**: выбор родительской страницы, создание с ancestors
- **Telegram**: уведомления после публикации, опциональная пакетная сводка
- **Восстановление очереди**: автосохранение `batch_state.json`, возобновление после сбоя
- **Повторная публикация**: без повторной генерации (транскрибации и LLM)
- **GUI** (Tkinter + ttk) и **CLI**

## Установка

### Требования
- Windows 10/11
- Python 3.11+
- Установленные библиотеки из `requirements.txt`

### Быстрый старт

```bash
# 1. Клонировать / скопировать репозиторий
cd D:\OpenCode\bitlink-bot

# 2. Установить зависимости
py -3 -m pip install -r requirements.txt

# 3. Настроить (опционально — по умолчанию mock-режим)
copy .env.example .env
# отредактировать .env

# 4. Запустить GUI
start_app.bat

# Или CLI
py -3 bot.py --text "meeting.txt"
```

## Запуск

### GUI
```bash
start_app.bat
# или
py -3 app.py
```

### CLI
```bash
# Обработка локальной расшифровки
py -3 bot.py --text "path/to/meeting.txt"

# Обработка локального видео
py -3 bot.py --local "path/to/meeting.mp4"

# Dry-run (без публикации)
py -3 bot.py --text "meeting.txt" --dry-run

# Указание шаблона и режима
py -3 bot.py --text "meeting.txt" --protocol-template management_summary --protocol-mode brief

# Интерактивная настройка
py -3 bot.py --setup

# Наблюдение за директорией
py -3 bot.py --watch
```

## Настройка (.env)

См. `.env.example` — все интеграции опциональны. При отсутствии настроек используется mock-режим.

| Блок | Обязателен для |
|---|---|
| БИТ.Link | источника БИТ.Link |
| Newton | БИТ.Link и локального видео |
| Confluence | всех источников |
| Telegram | опционально (ошибка не отменяет публикацию) |

## Шаблоны протоколов

| ID | Название | Объём |
|---|---|---|
| `management_summary` | Управленческий протокол | 500–1 200 слов |
| `project_standard` | Проектный протокол | 1 300–2 800 слов |
| `project_detailed` | Подробный проектный протокол | версия 3.0 |
| `business_process_discovery` | Обследование бизнес-процессов | |

### Подробный проектный протокол (v3.0)

10 разделов. Основной раздел — тематическая таблица (≥55% объёма):

| № | Тематический блок | Что обсуждалось | Итог / вывод | Статус |
|---|---|---|---|---|

**Не выводятся** отдельными разделами: сквозная схема процесса, согласованные подходы, рассмотренные варианты, функциональные разрывы, контрольные точки — их сведения встроены в тематические блоки и реестры.

## Структура проекта

```
bitlink-bot/
├── app.py                     # Точка входа GUI
├── bot.py                     # Главная точка входа (GUI/CLI)
├── cli.py                     # CLI
├── settings.py                # Конфигурация из .env
├── meeting_metadata.py        # Определение даты встречи, SHA-256
├── start_app.bat              # Запуск GUI
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
├── ui/                        # Графический интерфейс (Tkinter)
│   ├── main_window.py
│   ├── main_menu_frame.py
│   ├── bitlink_frame.py
│   ├── local_video_frame.py
│   ├── local_transcript_frame.py
│   ├── source_queue_frame.py  # Очередь + прогресс
│   ├── settings_frame.py
│   ├── confluence_parent_dialog.py
│   ├── progress_frame.py
│   └── result_frame.py
├── services/                  # Сервисы
│   ├── batch_service.py       # Управление очередью
│   ├── processing_service.py  # Конвейер обработки
│   ├── bitlink_service.py     # Адаптер БИТ.Link (mock)
│   ├── transcription_service.py # Адаптер Newton (mock)
│   ├── confluence_service.py  # Адаптер Confluence (mock)
│   ├── telegram_service.py    # Адаптер Telegram (mock)
│   ├── runtime_estimator.py   # Оценка оставшегося времени
│   ├── source_isolation.py    # Изоляция источников
│   ├── fact_extraction.py     # Извлечение атомарных элементов
│   ├── fact_validation.py     # Фактологическая проверка
│   ├── protocol_validation.py # Структурная проверка
│   └── render_validation.py   # Проверка HTML-рендера
├── protocol_templates/        # Шаблоны протоколов
│   ├── base.py
│   ├── registry.py
│   ├── management_summary.py
│   ├── project_standard.py
│   ├── project_detailed.py    # v3.0 — самый объёмный
│   └── business_process_discovery.py
├── models/                    # Модели данных
│   ├── batch.py
│   ├── meeting.py
│   ├── protocol.py
│   └── validation.py
├── data/                      # Данные времени выполнения
└── tests/                     # Тесты (130 тестов)
```

## Тестирование

```bash
py -3 -m pytest tests/ -v
```

Покрытие: 130 тестов в 7 файлах:
- `test_meeting_metadata.py` — даты, SHA-256, подсчёт слов
- `test_queue.py` — модели очереди, batch-сервис, оценка времени
- `test_source_isolation.py` — изоляция источников, провенанс
- `test_templates.py` — реестр, подробный протокол v3.0
- `test_services.py` — BIT.Link, Newton, Confluence, Telegram, факты, конвейер
- `test_validation.py` — фактологическая, структурная, HTML-валидация
- `test_integration.py` — генерация 4 шаблонов, восстановление очереди

## Интеграции (mock-режим)

Все внешние интеграции реализованы в режиме mock (по умолчанию):
- **БИТ.Link**: возвращает тестовые комнаты и записи, создаёт placeholder-транскрипты
- **Newton**: возвращает модельный транскрипт встречи
- **Confluence**: возвращает тестовые страницы, создаёт mock-страницы
- **Telegram**: выводит сообщения в консоль

Для подключения реальных сервисов заполните соответствующие поля в `.env`.

## Лицензия

Внутренний инструмент. Все права защищены.