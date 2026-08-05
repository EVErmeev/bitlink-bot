# START-NEXT-SESSION — инструкция новому чату OpenCode

**Прочитай это первым, прежде чем вносить любые изменения в код.**

## Порядок действий

1. **Прочитай `AGENTS.md`** — постоянные правила проекта.
2. **Прочитай `docs/opencode/HANDOFF-2026-08-03.md`** — полное описание текущего состояния.
3. **Прочитай `docs/opencode/manifest.json`** — активная задача, статусы, remaining blockers.
4. **Проверь remote head:**
   ```bash
   gh pr view 1 --json headRefOid,url,isDraft
   ```
   Сравни с commit в HANDOFF. Если отличается — изучи diff.
5. **Проверь release tag:**
   ```bash
   gh release view checkpoint-2026-08-03
   ```
6. **НЕ ИЗМЕНЯЙ КОД** до составления краткого плана.
7. **НЕ ПОВТОРЯЙ** уже закрытые задачи (см. HANDOFF, раздел «Что уже исправлено»).
8. **Продолжай только после новой обратной связи пользователя** — пользователь должен указать, какую задачу делать следующей.
9. Каждая новая итерация должна иметь свой TASK-файл в `docs/opencode/tasks/`.

## Быстрый старт

```bash
cd D:\OpenCode\bitlink-bot
git checkout fix/audit-e7cc95f
git pull
call start_app.bat --startup-check
```

## Рабочий pipeline (подтверждён)

```
TXT → LLM (Newton CLI) → Protocol → HTML → Confluence → Telegram
```

Настройки в `.env`. Не менять их без явного указания пользователя.

## Что НЕ делать

- Не переводить PR в Ready for review
- Не выполнять merge
- Не устанавливать `accepted`
- Не коммитить `.env` или токены
- Не дублировать настройки Newton CLI (token/path едины)
- Не менять `PROTOCOL_QUALITY_MODE=advisory`