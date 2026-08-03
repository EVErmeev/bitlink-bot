# VALIDATION-2026-08-03-D6410D7-REGISTER-ENRICHMENT-RESTORED

Задача: TASK-2026-08-03-D6410D7-RESTORE-RICH-REGISTERS
Ветка: `fix/audit-e7cc95f`
PR: https://github.com/EVErmeev/bitlink-bot/pull/1 (Draft, merge не выполнялся, accepted не устанавливался)
Коммит реализации: `56a99ad`
Базовый независимо проверенный remote head (до задачи): `d6410d776ac903bc06c09ad199fbef4a03d5c00e`

## Статус

Достигнуто. Все четыре реестра возвращены к полной содержательной структуре,
контрольный протокол перегенерирован реальным pipeline, опубликован в Confluence,
Telegram-уведомление отправлено.

## Что сделано

1. Новый модуль `services/protocol_register_pipeline.py`:
   - обработка ПОЛНОГО транскрипта по частям (нет `transcript[:8000]` как единственного источника);
   - модель кандидата реестра (item_id/item_type/text/topic_id/source_item_ids/evidence/...);
   - связывание кандидатов с тематическими блоками (`link_candidates_to_topics`);
   - обогащение ответственных и сроков (`enrich_register_ownership_and_deadlines`,
     источники explicit/adjacent/linked_topic/linked_action/proposed/unknown);
   - специфичная стратегия по каждому риску (`generate_risk_response_strategy`,
     strategy_source = meeting | derived_recommendation, strategy_status = agreed | proposed);
   - проверяемый ожидаемый результат задачи (`generate_task_expected_result`);
   - выбор наиболее полной подтверждённой формулировки (`select_most_complete_supported_text`);
   - слияние `merge_enriched_registers` и `register_diff.json` с drop_reason, без молчаливого
     уменьшения количества элементов.
2. `services/protocol_register_extractor.py` — полная схема полей всех четырёх реестров,
   без обрезки по фиксированному префиксу.
3. `services/protocol_register_validation.py` — метрики покрытия и блокировка публикации
   при массовых placeholder (all_question_responsibles_unknown, all_question_deadlines_unknown,
   all_risk_strategies_generic, all_risk_responsibles_unknown, all_task_expected_results_empty,
   silent_drop > 0).
4. `services/processing_service.py` — pipeline встроен, ВСЕ поля переносятся в Protocol,
   пишутся артефакты register_candidates_by_chunk / register_topic_links / register_enriched /
   register_merge_report / register_diff / register_quality_report, блокировка при провале гейта.
5. `protocol_templates/project_detailed.py` — возвращены целевые колонки:
   - Решения: № | Принятое решение | Контекст и основание | Ответственные | Срок
   - Вопросы: № | Открытый вопрос | Что требуется определить | Ответственный | Срок / контрольная точка | Статус
   - Риски: № | Тип | Риск / ограничение | Причина | Влияние | Стратегия реагирования | Ответственный
   - Задачи: № | Задача | Основание | Ожидаемый результат | Ответственный | Срок | Статус
   Добавлено примечание «Стратегии реагирования, не согласованные на встрече, сформированы
   как рекомендации…». Массовые fallback-ячейки убраны.

## Реальный Windows E2E (headless, реальный LLM + Confluence)

Запуск реального pipeline на контрольной расшифровке 31.07.2026 (103 659 байт) с реальным
LLM (onebit_newton_cli, gpt4) и публикацией в Confluence. Результат:

- `success: true`
- URL новой страницы Confluence: https://art-conf.spbco.1cbit.ru/spaces/TXT/pages/213876954
- Клиент: Роял Фуд | Проект: Склад 3PL
- Количество: decisions=15, questions=11, risks=16, tasks=20
- Telegram: отправлено, message_id=93
- Все артефакты сохранены в `docs/opencode/evidence/D6410D7-registers/`.

Итоговый HTML (проверено): целевые колонки всех четырёх таблиц; отсутствуют строки
«Требуется назначить», «Не указан», «Стратегия не определена», «Не определён»;
примечание про стратегии присутствует.

## register_quality_report.json

```json
{
  "decisions_count": 15, "questions_count": 11, "risks_count": 16, "tasks_count": 20,
  "decision_context_coverage": 1.0, "question_responsible_coverage": 1.0,
  "question_deadline_coverage": 1.0, "risk_reason_coverage": 1.0, "risk_impact_coverage": 1.0,
  "risk_strategy_coverage": 1.0, "risk_responsible_coverage": 1.0,
  "task_basis_coverage": 1.0, "task_expected_result_coverage": 1.0,
  "task_responsible_coverage": 1.0, "task_deadline_coverage": 1.0,
  "generic_placeholder_count": 177, "silent_drop_count": 0
}
```

`register_diff.json`: `silent_drop_count: 0` (ни один элемент не потерян молча).

Контрольное решение #2 сохранено полностью: «Предварительно назначить на вторник, 4-го числа,
разбор документации, которую успеют изучить, включая комментарии, необходимые доработки,
функциональные разрывы и необходимость повторной демонстрации», с контекстом, ответственными
и сроком.

## Автопроверки

- `python -m compileall services protocol_templates models tests` — exit 0.
- `pytest` (9 файлов): 62 passed.
- `ruff check` / `mypy` — НЕ установлены в окружении (не выполнялись), отмечено как ограничение.
- `python app.py --startup-check` — `STARTUP_CHECK_OK`.

## Ограничения

- ruff и mypy недоступны в окружении.
- Интерактивный GUI-сценарий (выбор файла мышью в окне tkinter) выполняется вручную;
  headless реальный прогон pipeline + Confluence + Telegram выполнен автоматически.