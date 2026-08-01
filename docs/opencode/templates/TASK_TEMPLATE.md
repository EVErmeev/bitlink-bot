# TASK_TEMPLATE

**Файл:** `docs/opencode/tasks/TASK-YYYY-MM-DD-<sha>.md`

```markdown
# TASK-YYYY-MM-DD-<sha>

**Создано:** YYYY-MM-DD
**На основе:** AUDIT-YYYY-MM-DD-<sha>
**Базовый коммит:** `<full_sha>`

---

## Порядок работы

1. **Создать ветку** `fix/audit-<sha>` от `main`.
2. **Обновить manifest.json:** `status = in_progress`, `validation_state = implementing_fixes`.
3. **Исправить все замечания** согласно аудиту.
4. ...
5. **Запустить проверки:**
   ```bash
   python -m compileall .
   pytest -q
   ruff check .
   mypy .
   ```
6. **Обновить manifest.json:**
   - `head_commit` — новый SHA
   - `pull_request_url` — URL PR
   - `status = awaiting_independent_validation`
   - `validation_state = awaiting_review`
7. **Push и PR.**
8. **Остановиться.**

---

## Замечания к исправлению

| ID | Суть | Приоритет |
|----|------|-----------|

---

## Критерии готовности

- [ ] Все CRITICAL исправлены
- [ ] Все MAJOR исправлены
- [ ] `compileall` — без ошибок
- [ ] `pytest -q` — все тесты проходят
- [ ] `ruff check .` — без ошибок
- [ ] `mypy .` — без ошибок
- [ ] PR создан, статус `awaiting_independent_validation`
```