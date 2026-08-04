# VALIDATION-2026-08-04-D0860E9-STANDARD-GROUPED

## TASK
- TASK-2026-08-04-D0860E9-PROJECT-STANDARD-STRUCTURE-AND-GROUPING (см. `docs/opencode/tasks/TASK-2026-08-04-D0860E9-PROJECT-STANDARD-STRUCTURE-AND-GROUPING.md`)
- Репозиторий: https://github.com/EVErmeev/bitlink-bot (Draft PR #1, ветка `fix/audit-e7cc95f`)

## Что сделано

Полностью переработан пользовательский вид шаблона `project_standard`:

1. **Общий канонический слой** — `project_standard` теперь переиспользует схему, системный промпт и
   `assemble_from_llm_json` шаблона `project_detailed` (композиция через `ProjectDetailedTemplate`),
   поэтому извлекает встречу тем же проверенным конвейером (включая обогащённые register pipeline
   decisions/questions/risks/tasks, `source_context_id`, evidence, client/project).
2. **Отдельный этап группировки** — `services/standard_protocol_grouper.py`:
   - `group_topic_blocks` — смысловое укрупнение подробных тем (общий семантический набор + совместимый статус);
   - `group_decisions` / `group_risks` / `group_tasks` — объединение только при совпадении ответственных/сроков/статусов;
   - `dedupe_questions` — открытые вопросы сохраняются подробно, только удаление **точных** дублей;
   - `validate_group_coverage`, `build_grouping_map`, `build_consistency_report`.
   Каждый укрупнённый элемент несёт `source_ids`, `grouping_reason`, `semantic_theme`, `preserved_facts/responsibles/deadlines`, `coverage_status`.
3. **Общий `ProtocolTitleBuilder`** — `services/protocol_title.py`: `build_protocol_title`, `extract_short_topic`, `detect_meeting_type`, `build_recording_source`. Название никогда не содержит техническое имя файла; формат `Протокол встречи от ДД.ММ.ГГГГ. {тема} — {клиент}, {проект}` / внутренняя встреча / частичные случаи.
4. **Новый рендер `project_standard.py`** — ровно **9 целевых разделов** в заданном порядке, XHTML storage-совместимый, только самозакрывающиеся `<br/>`, таблицы с `<thead>/<tbody>`, ключевые итоги отдельными `<li>`, экранирование, без legacy-разделов и без пустых «Тематический блок N: —».
5. **Валидатор standard** — блокировка по условиям TASK §12 (raw filename в title, недостающие секции, ключей общей информации != 4, коллективные строки участников, пустые/placeholder-темы, legacy-заголовки, нетрассируемые элементы, потерянные элементы).
6. **processing_service.py** — для `project_standard`: вычисление канонического title через builder, сохранение debug-артефактов `standard_*` + `title_resolution.json`.

## Тесты

Файл `tests/test_project_standard_structure.py` — **34 теста** (29 из TASK §14 + pipeline-wiring и др.).

```
python -m pytest tests/test_project_standard_structure.py tests/test_project_detailed_html_contract.py -q
41 passed in 0.29s
```

Отдельные наборы (detailed contract + visible columns + semantic split + rich text + standard):

```
58 passed in 0.33s
```

## Команды проверки

- `python -m compileall .` — exit 0.
- `pytest -q` (полный) — **не запускался целиком**: часть тестов выполняет живые сетевые вызовы с токеном и зависает; прогонялись точечные наборы (см. выше). Ограничение окружения, не регрессия кода.
- `python -m ruff` — **модуль не установлен** в окружении (`No module named ruff`).
- `python -m mypy` — **модуль не установлен** (`No module named mypy`).

## Реальный Windows E2E

Команда (headless runner поверх `services/processing_service`):
`python <temp>/run_std_e2e.py`

Контрольная расшифровка: `C:\Users\EVErmeev\Downloads\Telegram Desktop\local-872b2e3cdd76beb0_transcript.txt`, шаблон `project_standard`, LLM `onebit_newton_cli` / `gpt4`.

- **SUCCESS: True**, без предупреждений качества (`warnings: []`).
- **Новая страница Confluence:** https://art-conf.spbco.1cbit.ru/spaces/TXT/pages/213877138 (id `213877138`).
- **Telegram**: отправлено, `telegram_message_id = 102`.
- **Debug-каталог:** `C:\Users\EVErmeev\AppData\Local\Temp\opencode\e2e_std` (копии в `docs/opencode/evidence/2026-08-04-D0860E9-STANDARD-GROUPED/`).

Проверка опубликованной страницы (`/rest/api/content/...?expand=body.storage`):
- `PAGE_TITLE` — содержательное название, **не** содержит `local-`, `_transcript.txt`, расширения файла;
- 8 таблиц с `<thead>`/`<tbody>`; самозакрывающихся `<br/>` — 0 (в данных нет переносов строк, `bare <br>` — 0);
- техническое имя файла присутствует ровно 1 раз — только в строке «Источник записи»;
- `<h1>` присутствует в storage.

**Экспорт в DOC:** REST-эндпоинты `/rest/api/content/{id}/exportword` вернули 404/HTML (Confluence Server выдаёт DOCX только через браузерную сессию / UI-экспорт). Корректность storage (XHTML с `<thead>/<tbody>`, самозакрывающиеся `<br/>`) проверена — именно это содержимое импортируется в DOC при экспорте из UI. Проверка оформлена как «attempted + storage verified».

## Результаты валидации (standard_validation.json)

- `required_sections_present`: 9
- `general_info_keys_present`: 4
- `confirmed_participants_count`: 15
- `participant_group_rows_count`: 0
- `key_outcomes_count`: 4
- `detailed_topic_count`: 17, `standard_topic_group_count`: 13, `topic_source_coverage`: 1.0
- `detailed_decision_count`: 15, `standard_decision_group_count`: 15, `decision_source_coverage`: 1.0
- `open_question_count`: 14
- `risk_source_coverage`: 1.0, `task_source_coverage`: 1.0
- `legacy_heading_count`: 0
- `raw_filename_in_title`: false
- `empty_cell_count`: 0
- `silent_drop_count`: 0

## Согласованность standard и detailed (standard_vs_detailed_consistency.json)

- `metadata_match`: true
- `participants_match`: true
- `decision/question/risk/task/topic_source_coverage`: 1.0
- `unsupported_standard_items`: 0
- `lost_critical_items`: []

## Пример сформированного title

`Протокол внутренней встречи. Цель встречи — сверить фактическое закрытие июля с планом, определить ответственных за акты, неГА и коммуникации с субподрядчиками, выявить…`

(Клиент/проект не распознались для этой расшифровки → title по правилу «клиент и проект отсутствуют», без технического имени.)

## Изменённые/созданные файлы

- `services/protocol_title.py` (новый)
- `services/standard_protocol_grouper.py` (новый)
- `protocol_templates/project_standard.py` (переписан)
- `services/processing_service.py` (подключение standard title + артефактов)
- `tests/test_project_standard_structure.py` (новый, 34 теста)
- `docs/opencode/evidence/2026-08-04-D0860E9-STANDARD-GROUPED/*` (доказательства)

## PR

- PR #1 остаётся **Draft**; merge **не** выполнялся; флаг `accepted` **не** устанавливался.