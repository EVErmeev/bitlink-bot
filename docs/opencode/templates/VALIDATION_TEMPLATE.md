# VALIDATION_TEMPLATE

**Файл:** `docs/opencode/validations/VALIDATION-YYYY-MM-DD-<sha>.md`

```markdown
# VALIDATION-YYYY-MM-DD-<sha>

**Дата:** YYYY-MM-DD
**Валидатор:** Независимая проверка
**Проверяемый PR:** `<url>`
**Проверяемый коммит:** `<full_sha>`
**Исходный аудит:** AUDIT-YYYY-MM-DD-<sha>
**Итоговое заключение:** `accepted` | `changes_required`

---

## Результаты автоматических проверок

| Проверка | Результат |
|----------|-----------|
| `python -m compileall .` | PASS / FAIL |
| `pytest -q` | N passed, M failed |
| `ruff check .` | PASS / FAIL (N errors) |
| `mypy .` | PASS / FAIL (N errors) |

---

## Проверка замечаний

| ID | Исходный статус | Новый статус | Комментарий |
|----|----------------|-------------|-------------|
| BB-CRIT-001 | OPEN | FIXED / NOT_FIXED / ... | ... |

---

## Общее заключение

<Описание: все ли замечания исправлены, есть ли регрессии,
 требуется ли повторный цикл исправлений.>

---

## Решение

`accepted` — все замечания устранены, проверки пройдены.
`changes_required` — требуются дополнительные исправления (см. выше).
```