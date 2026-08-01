# Постоянный служебный контур OpenCode

## Назначение

Директория `docs/opencode/` — постоянный служебный контур для управления качеством
репозитория `bitlink-bot`. Все изменения проходят через независимый цикл:

```
независимый аудит
  → audit-файл
    → task-файл
      → обновление manifest
        → исправление OpenCode
          → тесты
            → push и PR
              → независимая повторная валидация
                → validation-файл
```

## Правила работы

1. **Старые артефакты не удалять.** Аудиты, задания и валидации накапливаются.
2. **OpenCode не имеет права** устанавливать итоговый статус `accepted`.
3. **Перед началом исправлений** OpenCode всегда читает `manifest.json`.
4. **После начала работы** устанавливает:
   - `status = in_progress`
   - `validation_state = implementing_fixes`
5. **После push и создания PR** устанавливает:
   - `status = awaiting_independent_validation`
   - `validation_state = awaiting_review`
   - Заполняет `head_commit` и `pull_request_url`.
6. **Статусы замечаний:**
   - `OPEN` — не исправлено
   - `IN_PROGRESS` — в работе
   - `FIXED` — исправлено
   - `PARTIALLY_FIXED` — частично исправлено
   - `NOT_FIXED` — не исправлено (попытка была)
   - `NOT_VERIFIABLE` — невозможно проверить
   - `REGRESSION` — регресс (ранее работало, теперь сломано)

## Обязательные проверки

Перед PR всегда выполняются:

```bash
python -m compileall .
pytest -q
ruff check .
mypy .
```

## Структура

```
docs/opencode/
├── README.md                          ← этот файл
├── manifest.json                      ← точка входа, текущее состояние
├── audits/
│   └── AUDIT-YYYY-MM-DD-<sha>.md
├── tasks/
│   └── TASK-YYYY-MM-DD-<sha>.md
├── validations/
│   └── VALIDATION-YYYY-MM-DD-<sha>.md
├── templates/
│   ├── AUDIT_TEMPLATE.md
│   ├── TASK_TEMPLATE.md
│   └── VALIDATION_TEMPLATE.md
└── schemas/
    └── manifest.schema.json
```

## Версия

1.0 — 2026-08-01, инициализация контура по коммиту `e7cc95f`.
