# GUI-E2E-ce4ed1b

**Дата:** 2026-08-01
**Head:** `ce4ed1b`

## Сценарий A — demo dry-run

| Шаг | Результат |
|---|---|
| LLM mock + Confluence rest + local TXT | dry-run включается автоматически preflight |
| Один клик Start | worker стартует без второго нажатия |
| Stages visible | loading_source → extracting_metadata → ... → rendering |
| Confluence page | **не создана** (dry-run блокирует REST) |
| Статус | validation_failed (mock schema не проходит minLength) |

## Сценарий B — real publish

| Шаг | Результат |
|---|---|
| Real LLM + real Confluence | требует явного отключения dry-run |
| Confluence page создана | smoke page 213352588 подтверждена MCP read-back |

## Сценарий C — mixed mode protection

| Шаг | Результат |
|---|---|
| Mock LLM + real Confluence + dry_run=True | **dry-run включается автоматически** |
| Preflight warning | "demo-режим — автоматически включён dry-run" |

## Сценарий D — Telegram diagnostics

| Шаг | Результат |
|---|---|
| TelegramClient(bot_token="...", chat_id="...") | использует переданные значения, не settings |
| check_connection | работает с переданными параметрами |

## Preflight summary

- **Source-aware**: для local TXT Newton и Bitlink SKIPPED
- **Service checks**: LLM, Confluence, Telegram проверяются только когда участвуют
- **Mixed-mode**: demo → auto dry-run
- **Single-click**: успешный preflight → immediate worker start

## Общие проверки

| Команда | Результат |
|---|---|
| compileall | PASS |
| json.tool | PASS |
| pytest -q | 168 passed |
| ruff check . | All checks passed |
| mypy . | Success: no issues found |
| start_app.bat --startup-check | STARTUP_CHECK_OK |
