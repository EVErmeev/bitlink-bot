# WINDOWS-LAUNCHER-MANUAL-034e2a5

**Дата:** 2026-08-01
**Windows version:** Windows 11
**Python selected:** py -3 (Python 3.13.7)

## BAT launcher test

| Проверка | Результат |
|---|---|
| `call start_app.bat --startup-check` | **PASS** (STARTUP_CHECK_OK, exit 0) |
| BAT is ASCII-only | **yes** |
| No chcp 65001 | **yes** |
| .gitattributes CRLF | **yes** |
| Python discovery order | .venv → py -3 → python |
| Error handling | pause only on error, exit code preserved |
| Double-click BAT smoke | **PASS** |

## Default mock dry-run

| Проверка | Результат |
|---|---|
| LLM_MOCK=true → schema-valid JSON | **yes** (_build_mock_from_schema) |
| All 4 template schemas supported | **yes** |
| pytest -q | **168 passed, 0 failed** |
| ruff check . | **All checks passed** |
| mypy . | **Success: no issues found** |
| compileall | **PASS** |

## Real Confluence publication

| Проверка | Результат |
|---|---|
| CONFLUENCE_PROVIDER=rest | **working** |
| Smoke page created | ID: 213352588 |
| MCP read-back | **pass** |
| Parent page | Ананьев Никита (212730370) |
| Space | TXT |
| Base URL | https://art-conf.spbco.1cbit.ru |

## GitHub Actions

| Проверка | Статус |
|---|---|
| Windows launcher gate | **added** |
| continue-on-error | **removed** |
| compileall, json, pytest, ruff, mypy | **all required** |
