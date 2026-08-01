\# VALIDATION-2026-08-01-bbb1cc9

\#\# Объект проверки

\- Репозиторий: \`EVErmeev/bitlink-bot\`  
\- Draft PR: \`\#1\`  
\- Ветка: \`fix/audit-e7cc95f\`  
\- Заявленный commit: \`bbb1cc928ebfcd4d2ee8f4def16a14fe0c72e7f1\`  
\- Фактический head PR: \`bbb1cc99f056a23d5f0340d790c58f58dfe82060\`  
\- Базовый commit: \`2644b52dee92f7f6d2709496335f90364c47057f\`

\#\# Общий результат

\*\*Статус:\*\* \`changes\_required\`

PR необходимо оставить в состоянии Draft. Перевод в Ready for review и merge запрещены до устранения блокирующих дефектов.

\#\# CI

GitHub Actions запущен на Ubuntu и Windows для Python 3.11, 3.12 и 3.13.

Для Ubuntu / Python 3.11:

\- \`python \-m compileall .\` — пройден;  
\- \`python \-m json.tool docs/opencode/manifest.json\` — пройден;  
\- \`pytest \-q\` — \`168 passed\`;  
\- \`ruff check .\` — завершился с ошибкой, найдено 213 нарушений;  
\- \`mypy . \--ignore-missing-imports\` — завершился с ошибкой из\-за невалидного имени корневого пакета \`bitlink-bot\`.

Workflow отображается зелёным только потому, что Ruff и Mypy имеют \`continue-on-error: true\`. Текущий зелёный CI не подтверждает прохождение всех обязательных проверок.

\#\# Расхождения manifest

\- \`head\_commit\` содержит \`523747a7cb6b8d5c2ad42ff3c5c9beaab2c5b8e3\`, а фактический head PR — \`bbb1cc99f056a23d5f0340d790c58f58dfe82060\`;  
\- Ruff и Mypy отмечены как \`not run\`, хотя они запускались и упали;  
\- все \`BB-CRIT-\*\` отмечены \`FIXED\`, хотя часть функционала не завершена;  
\- сведения о проверках не соответствуют фактическому workflow.

\#\# Статусы критических замечаний

| ID | Независимый статус | Результат |  
|---|---|---|  
| BB-CRIT-001 | PARTIALLY\_FIXED | Явные mock-флаги добавлены; реальные БИТ.Link и Confluence adapters не реализованы |  
| BB-CRIT-002 | PARTIALLY\_FIXED | \`generate\_json()\` добавлен, но рабочий pipeline вызывает \`generate()\` и передаёт строку |  
| BB-CRIT-003 | PARTIALLY\_FIXED | Coverage добавлен, но mapping основан на совпадении слов и не сохраняется как артефакт |  
| BB-CRIT-004 | PARTIALLY\_FIXED | Шаблоны заполняются, но structured LLM JSON фактически не используется |  
| BB-CRIT-005 | FIXED | Провал валидации переводит элемент в \`validation\_failed\` и \`success=False\` |  
| BB-CRIT-006 | FIXED\_BY\_CODE | Повторные проверки в pipeline есть, но тесты не доказывают порядок вызовов |  
| BB-CRIT-007 | PARTIALLY\_FIXED | Source context усилен, но \`input\_manifest.json\` содержит неверные данные |  
| BB-CRIT-008 | PARTIALLY\_FIXED | Публикация пропускается, но успешный dry-run получает ошибку validation failed |  
| BB-CRIT-009 | NOT\_FIXED | Статус \`processing\` не переводится в повторно обрабатываемое состояние |  
| BB-CRIT-010 | NOT\_FIXED | SHA JSON рассчитывается не из тех байтов, которые записаны в файл |

\#\# Блокирующие дефекты

\#\#\# VAL-CRIT-001 — Structured LLM не подключена

\`LLMClient.generate\_json()\` существует, но \`ProcessingService.process\_item()\` вызывает \`self.llm.generate(...)\`. JSON Schema шаблона не применяется в рабочем конвейере. \`\_save\_llm\_artifacts()\` нигде не вызывается.

\#\#\# VAL-CRIT-002 — Тесты LLM не проверяют pipeline

\`tests/test\_llm\_json.py\` проверяет метод клиента отдельно. Он не доказывает, что ProcessingService вызывает structured generation и передаёт parsed dict реальному assembler.

\#\#\# VAL-CRIT-003 — Republish содержит несовместимый SHA

Валидированный JSON записывается через \`json.dump(..., indent=2, ensure\_ascii=False)\`, но SHA рассчитывается через \`json.dumps(..., sort\_keys=True)\` с другой сериализацией. При republish SHA считается по байтам файла и не совпадёт.

\#\#\# VAL-CRIT-004 — Queue recovery не восстанавливает строку

\`get\_resumable\_items()\` только возвращает сведения о \`processing\`, но не меняет статус. \`get\_pending\_items()\` не включает \`processing\`. Прерванная строка не будет обработана повторно.

\#\#\# VAL-CRIT-005 — Input manifest остаётся неверным

В manifest передаются debug-каталог вместо источника, пустой SHA, hardcoded \`local\_transcript\` и protocol ID вместо BatchItem ID.

\#\#\# VAL-CRIT-006 — Dry-run одновременно успешный и ошибочный

При успешном dry-run результат получает \`success=True\`, но поле \`error\` остаётся \`Protocol validation failed \- publication blocked\`.

\#\#\# VAL-CRIT-007 — Topic coverage не обеспечивает трассировку

Atomic items сопоставляются с темами задним числом по общим словам. В \`TopicBlock\` нет явных \`source\_item\_ids\`, отчёт coverage не сохраняется, evidence/timestamp mapping отсутствует.

\#\#\# VAL-CRIT-008 — Критические тесты ложноположительны

Обнаружены тесты, которые:

\- проверяют отсутствующий файл вместо провала валидатора;  
\- не вызывают проверяемый сервис;  
\- проверяют только значение \`dry\_run\`;  
\- используют условный \`if file.exists()\`;  
\- проверяют только наличие ключа \`success\`;  
\- не проверяют смену статуса при recovery;  
\- состоят из \`assert True\`;  
\- не проверяют фактический порядок post-correction validation.

Поэтому \`168 passed\` не подтверждает заявленные критические сценарии.

\#\#\# VAL-CRIT-009 — CI скрывает ошибки

Ruff и Mypy объявлены обязательными в manifest, но их падение не блокирует workflow.

\#\# Оставшиеся замечания

\`BB-MAJ-011\` — \`BB-MAJ-020\` остаются открытыми и в текущей итерации не принимались.

\#\# Критерии следующей проверки

1\. PR остаётся Draft.  
2\. Manifest содержит фактический \`headRefOid\`.  
3\. Ruff и Mypy обязательны и проходят.  
4\. Structured JSON реально используется в ProcessingService.  
5\. Queue recovery меняет статус прерванных строк.  
6\. Republish проходит на артефактах, созданных \`process\_item()\`.  
7\. Критические тесты переписаны без \`assert True\`, условных assert и проверок только наличия ключа.  
8\. CI проходит без \`continue-on-error\`.

\#\# Итог

\`\`\`text  
Статус PR: Draft / changes\_required  
Разрешение на Ready for review: нет  
Разрешение на merge: нет  
Повторная валидация: требуется после нового push  
\`\`\`  
