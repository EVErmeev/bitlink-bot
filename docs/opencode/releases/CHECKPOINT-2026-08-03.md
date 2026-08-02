# CHECKPOINT-2026-08-03

**Tag:** `checkpoint-2026-08-03`
**Commit:** `1da90bd79756d9e13c36f679d1df6aa3b6478a3a`
**Date:** 2026-08-03

## Что работает

### Pipeline доставки

```
Локальный TXT/MD
  → Newton CLI summarization (gpt4/llama)
  → project_detailed / management_summary / project_standard / business_process_discovery
  → HTML preview
  → Confluence REST API (space TXT, parent 212730370)
  → Telegram notification
```

### project_detailed (v3.0)

- Дата и время из имени файла (`DD_MM_YY_HH_MM_SS`, `YYYY_MM_DD`, `DD.MM.YYYY`)
- Смысловой заголовок (не имя файла)
- Клиент и проект в заголовке Confluence и шапке HTML
- 10-13 тематических блоков
- Ключевые итоги списком
- **Реестры: решения, вопросы, риски, задачи** (LLM extraction pass)

### management_summary

- Генерация через LLM
- Базовая структура с управленческим резюме
- Контрольные точки

### Инфраструктура

- Один Newton CLI для LLM и транскрибации
- `PYTHONIOENCODING=utf-8` — нет проблем с кодировкой
- `PROTOCOL_QUALITY_MODE=advisory` — качество не блокирует публикацию
- `process_runner.py` — безопасный subprocess без _readerthread ошибок
- `json_response_parser.py` — repair/retry для malformed JSON

## Последний контрольный запуск

| Параметр | Значение |
|---|---|
| Файл | Встреча_в_Телемосте_31_07_26_14_06_05_запись_transcript.txt |
| Дата | 31.07.2026 |
| Время | 14:06 |
| Клиент | Роял Фуд |
| Проект | Склад 3PL |
| Решения | 1 |
| Вопросы | 5 |
| Риски | 4 |
| Задачи | 5 |
| Confluence page ID | 213876763 |
| Telegram | отправлен |

## Известные ограничения

1. **BB-CRIT-063**: `USER_ACTION_REQUIRED` — раскрытый токен требует ротации
2. Роли участников: все `—` (не извлекаются из LLM)
3. management_summary: реестры могут быть пусты
4. project_standard, business_process_discovery: базовая работоспособность
5. BB-MAJ-011..020: 10 существенных замечаний открыты

## Инструкция по продолжению

См. `docs/opencode/HANDOFF-2026-08-03.md` и `docs/opencode/START-NEXT-SESSION.md`.