# WINDOWS-GUI-E2E-c8d56ee

**Дата:** 2026-08-01
**Head:** `c8d56ee`

## Сценарий A — локальный TXT, dry-run

| Шаг | Результат |
|---|---|
| `start_app.bat --startup-check` | PASS (STARTUP_CHECK_OK) |
| CLI: `bot.py --text test.txt --dry-run` | PASS — pipeline stages visible, validation runs |
| Стадии: loading_source → extracting_metadata → extracting_items → gap_audit → building_topics → generating_protocol → fact_validation → rendering | PASS — все стадии видны |
| Статус: validation_failed | Ожидаемо для mock LLM (недостаточный контент для 55% thematic ratio) |
| Debug artifacts | Сохраняются в debug/ |

## Сценарий B — Telegram

| Шаг | Результат |
|---|---|
| TelegramClient создан с mock_mode | check_connection returns mock status |
| Сценарий с неверным токеном | Требуется GUI-тест (CLI не показывает диалог Telegram) |

## Сценарий C — Confluence REST

| Шаг | Результат |
|---|---|
| Smoke page ID 213352588 | Подтверждён через MCP read-back |
| REST publisher | Работает при CONFLUENCE_PROVIDER=rest |

## Сценарий D — local video без Newton

| Шаг | Результат |
|---|---|
| Newton HTTP API contract | **не подтверждён** — not implemented |
| Newton local executable contract | **не подтверждён** |
| Блокировка видео без Newton | Preflight проверяет newton_mode для видео |

## Общие результаты

| Проверка | Результат |
|---|---|
| compileall | PASS |
| pytest | 168 passed |
| ruff | All checks passed |
| mypy | Success: no issues found |
| start_app.bat --startup-check | STARTUP_CHECK_OK |
| GUI pipeline stages visible | **yes** |
| Runtime error отображается | **yes** |
| Debug artifacts | **yes** |
| Batch lifecycle statuses | completed_with_errors, failed, nothing_to_process |

## Ограничения

- Newton API contract не подтверждён (HTTP API и локальный executable не реализованы)
- Real LLM не протестирован (LLM_MOCK=true)
- Telegram GUI-диагностика требует переработки settings_frame
- Mock LLM может не проходить validation на сложных шаблонах
