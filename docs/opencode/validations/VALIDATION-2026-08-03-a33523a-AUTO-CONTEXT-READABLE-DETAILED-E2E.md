# VALIDATION-2026-08-03-a33523a-AUTO-CONTEXT-READABLE-DETAILED-E2E

Задача: TASK-2026-08-03-D4F346B-AUTO-CONTEXT-AND-READABLE-DETAILED-PROTOCOL

Ветка: `fix/audit-e7cc95f`
PR: https://github.com/EVErmeev/bitlink-bot/pull/1 (остаётся Draft, merge не выполнялся)
Проверенный коммит реализации: `a33523a`
Базовый независимо проверенный remote head: `3732397c649fe4c4277c087c5b8a1799e22222be`

## 1. Что сделано

- Автоматическое определение клиента и проекта `services/project_context_resolver.py`
  (источники: текст расшифровки → metadata/title → имя файла → реестр → участники/системы/термины →
  опциональная LLM-классификация). Результат: `ProjectContextResolution`.
- Реестр профилей в tracked-файле `resources/project_profiles.json` (НЕ hardcode в Python;
  профиль `royal-food-3pl` = Роял Фуд / Склад 3PL). `data/` в .gitignore, поэтому реестр вынесен
  в `resources/`; resolver читает `resources/` первым, `data/` — как runtime-переопределение.
- Единая модель смыслового форматирования в `services/protocol_content_utils.py`:
  `RichTextBlock` (paragraph / bullet_list / numbered_list), `normalize_rich_text_blocks`,
  `render_rich_text_blocks`, `split_key_outcomes_semantically` (только деление, без новых фактов).
- Интеграция в pipeline `services/processing_service.py`:
  контекст резолвится ДО LLM-генерации, значения authoritative, передаются в prompt, `Protocol`,
  `protocol.json`, `pipeline_result.json`, HTML, Confluence title, Telegram;
  пишется артефакт `project_context_resolution.json` (с `mkdir` до записи — исправлена ошибка
  FileNotFoundError при отсутствующей debug-директории).
- Рендер `protocol_templates/project_detailed.py`: RichTextBlock для discussion/conclusion/status/
  current_state, структурированный статус (label/next/responsible/deadline без `..`), текущее
  состояние таблицей `№ | Объект | Текущее состояние`, ключевые итоги `<ol>` ≥3 `<li>`,
  упрощённые видимые таблицы, `validate_render` (непустые client/project, ≥3 `<li>`, нет `..`,
  нет монолитных ячеек >700 симв, нет удалённых колонок, нет Python/JSON-представлений).
- Удалены ручные поля «Клиент»/«Проект» со страницы локальных расшифровок
  (`ui/local_transcript_frame.py`) без скрытого обязательного требования.

## 2. Контрольный результат

Для контрольной расшифровки (Роял Фуд / Склад 3PL) авторезолвер даёт:

```json
{
  "client_name": "Роял Фуд",
  "project_name": "Склад 3PL",
  "confidence": "high",
  "resolution_method": "known_profile_match",
  "matched_profile_id": "royal-food-3pl"
}
```

- Клиент/Проект в `protocol.json` и HTML — «Роял Фуд» / «Склад 3PL», не `—`, не `Не определено`.
- Ключевые итоги — отдельные `<li>` внутри одного `<ol>` (не один `<li>`).
- Тематические ячейки делятся на абзацы/списки, нет монолитных ячеек >700 симв без структуры.
- Статус структурный (label / следующее действие / ответственные / срок), нет `..`.
- В видимых таблицах только целевые колонки; удалённые служебные колонки отсутствуют в HTML.

## 3. Тесты (все зелёные, `assert True` запрещён)

```text
39 passed
```

- tests/test_project_context_resolver.py — разрешение, evidence, low→«Не определено», реестр из файла, НЕ hardcode.
- tests/test_project_context_ui.py — удаление ручных полей Клиент/Проект.
- tests/test_key_outcome_semantic_split.py — semantic split ≥3, рендер ≥3 `<li>`, не придумывает факты.
- tests/test_rich_text_blocks.py — модель/рендер RichTextBlock.
- tests/test_project_detailed_readability.py — читаемость ячеек, отсутствие монолитных ячеек.
- tests/test_project_detailed_visible_columns.py — целевые колонки таблиц, удалённые колонки отсутствуют.
- tests/test_project_detailed_html_contract.py — клиент/проект в HTML/JSON/Confluence title/Telegram.
- tests/test_e2e_pipeline_auto_context.py — headless E2E всего конвейера на контрольном тексте:
  resolver → protocol.json → HTML (≥3 `<li>`).

## 3. Проверки окружения

- `python -m compileall services protocol_templates models ui tests` — OK (exit 0).
- `python app.py --startup-check` — `STARTUP_CHECK_OK` (4 шаблона, schema валидны, Confluence-соединение OK).
- Полный `pytest -q` полного набора не запускался целиком: `test_services` с живым `.env` делает
  сетевые вызовы и зависает; поэтому проверялся точечный набор новых тестов (39 passed).
- `ruff check .` и `mypy .` — недоступны в окружении (`python -m ruff`/`python -m mypy` не установлены).

## 4. Реальный Windows E2E

Headless E2E выполнен автоматически (см. `tests/test_e2e_pipeline_auto_context.py`).
Полный GUI-прогон через `call start_app.bat` требует интерактивного выбора контрольной расшифровки
пользователем в tkinter-окне — этот шаг автоматически не воспроизводится в данной среде и остаётся
за пользователем:
```text
cd /d D:\OpenCode\bitlink-bot
call start_app.bat
```
Ожидаемо: Клиент «Роял Фуд», Проект «Склад 3PL», без ручного ввода.

## 5. Известные ограничения

- `ruff` и `mypy` не установлены — статические проверки не выполнены.
- Реальный GUI-прогон (выбор файла в окне) требует ручного действия пользователя.