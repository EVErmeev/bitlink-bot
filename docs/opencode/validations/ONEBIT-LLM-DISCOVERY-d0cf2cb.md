# ONEBIT-LLM-DISCOVERY-d0cf2cb

**Дата:** 2026-08-01
**Head:** `d0cf2cb`

## CLI Discovery Results

| Метод | Результат |
|---|---|
| PowerShell `Get-Command newton` | **не найден** |
| `where.exe newton` | **не найден** |
| WSL `wsl -e sh -lc "newton --help"` | **WSL не установлен** |
| Git Bash `command -v newton` | **не найден** |

## Заключение

OneBit Newton CLI **не установлен** на данной машине.

- CLI transport: **native** (документирован, готов к использованию)
- Для работы потребуется: установка CLI через `curl -sL https://gitlab.com/fadeyev1/newton-cli/-/raw/main/newton`
- До установки: использовать `LLM_PROVIDER=mock` или `LLM_PROVIDER=openai_compatible`

## REST контракт

| Поле | Статус |
|---|---|
| OpenAI-compatible | реализован (нормализация URL, models/chat paths) |
| `https://ys.1bitai.ru/` | 405 Method Not Allowed — endpoint/path не подтверждён |
| OneBit REST contract | **NOT_CONFIRMED** |

## API Key

BB-CRIT-063 — `USER_ACTION_REQUIRED`. Ранее опубликованный ключ считается скомпрометированным.
Ключ удалён из всех файлов и не присутствует в git diff.
