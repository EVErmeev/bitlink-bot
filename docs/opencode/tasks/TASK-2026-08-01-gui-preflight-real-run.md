\# TASK-2026-08-01-gui-preflight-real-run

\#\# Назначение

Исправить пользовательский сценарий запуска обработки через GUI.

Текущая версия показывает successful preflight, но не запускает worker без второго нажатия одноимённой кнопки. При этом preflight не проверяет сервисы и допускает опасную публикацию mock-контента в real Confluence.

\#\# Репозиторий и PR

\- Repository: \`EVErmeev/bitlink-bot\`  
\- Branch: \`fix/audit-e7cc95f\`  
\- Draft PR: \`https://github.com/EVErmeev/bitlink-bot/pull/1\`  
\- Проверенный base head: \`d38f6055bc28eaa16413028bd2dc9f6745d96535\`

PR оставить Draft. Merge не выполнять.

\#\# 1\. Исправить UX запуска

Основная кнопка должна запускать обработку одним действием:

\`\`\`text  
click Start  
→ run full preflight  
→ blocking errors? show errors and stop  
→ warnings? show Continue / Cancel  
→ no errors and no warnings? start worker automatically  
\`\`\`

При успешном preflight:

\- не создавать success-only modal;  
\- записать \`Предстартовая проверка пройдена\`;  
\- немедленно вызвать \`\_do\_start\_processing()\`;  
\- отключить Start;  
\- показать \`Запуск обработки...\`;  
\- в течение 500 мс показать первый stage.

Запрещено использовать две последовательные кнопки с одинаковым названием «Запустить обработку».

\#\# 2\. Реализовать полный source-aware preflight

Создать \`services/preflight\_service.py\`.

Для local transcript проверять:

\- файл существует, не пуст и читается;  
\- debug directory доступен;  
\- template существует;  
\- LLM provider доступен или schema-valid mock;  
\- Confluence только если \`dry\_run=False\`;  
\- Telegram только если enabled и \`send\_telegram=True\`;  
\- parent page для real Confluence.

Newton и Bitlink для local transcript должны быть \`SKIPPED\`.

Для local video проверять Newton, LLM, Confluence и Telegram.

\#\# 3\. Защитить mixed mock/real mode

Если upstream provider работает в mock, а Confluence или Telegram работают в real, обычная публикация запрещена по умолчанию.

В demo mode:

\`\`\`python  
item.dry\_run \= True  
\`\`\`

Без явного подтверждения mock-контент нельзя отправлять в реальные системы.

\#\# 4\. Добавить dry-run в GUI

Добавить:

\- глобальный default Dry-run / Публикация;  
\- checkbox dry-run в параметрах строки;  
\- колонку \`Выполнение\`;  
\- явное предупреждение mixed mode.

\#\# 5\. Реально переработать Settings GUI

Добавить provider mode selectors:

\- LLM: Mock / Real API;  
\- Confluence: Mock / REST;  
\- Telegram: Disabled / Mock / Real;  
\- Newton: Disabled / Mock / Real unavailable;  
\- Bitlink: Disabled / Mock / Real.

Connection tests должны использовать текущие несохранённые значения формы.

Newton Path убрать до появления подтверждённого executable contract.

\#\# 6\. Добавить event log

В Queue window добавить read-only журнал событий.

Сохранять:

\`debug/\<batch\>/\<item\>/processing\_events.jsonl\`

Поля:

\- timestamp;  
\- stage;  
\- percent;  
\- severity;  
\- message;  
\- exception type.

\#\# 7\. Исправить batch lifecycle

\- отправлять \`batch\_done\` ровно один раз;  
\- добавить \`worker\_started\`;  
\- если thread завершился до первого stage — показать runtime error;  
\- различать preflight\_failed, starting, processing, completed, completed\_with\_errors, validation\_failed, failed, cancelled и nothing\_to\_process.

\#\# 8\. Исправить demo banner

Banner должен быть source-aware.

Для local TXT пример:

\`\`\`text  
DEMO: LLM работает в mock-режиме.  
Confluence: REST, но публикация заблокирована — Dry-run.  
Newton и Bitlink для этого источника не используются.  
\`\`\`

\#\# 9\. Обязательные тесты

Добавить:

\`\`\`text  
test\_successful\_preflight\_starts\_worker\_without\_second\_click  
test\_warning\_preflight\_requires\_explicit\_continue  
test\_blocking\_preflight\_does\_not\_start\_worker  
test\_preflight\_checks\_llm\_for\_local\_transcript  
test\_preflight\_skips\_newton\_for\_local\_transcript  
test\_preflight\_checks\_confluence\_only\_when\_not\_dry\_run  
test\_preflight\_checks\_telegram\_only\_when\_enabled  
test\_mock\_llm\_real\_confluence\_forces\_dry\_run  
test\_mock\_llm\_real\_telegram\_forces\_dry\_run  
test\_demo\_mode\_items\_default\_to\_dry\_run  
test\_item\_params\_can\_toggle\_dry\_run  
test\_settings\_test\_uses\_unsaved\_form\_values  
test\_telegram\_getme\_and\_getchat\_diagnostics  
test\_newton\_path\_not\_shown\_without\_contract  
test\_batch\_done\_emitted\_once\_on\_exception  
test\_worker\_started\_event\_emitted  
test\_processing\_events\_jsonl\_is\_written  
test\_gui\_start\_handler\_reaches\_processing\_stage  
\`\`\`

\#\# 10\. Обязательный GUI E2E

Через \`start\_app.bat\` проверить:

\#\#\# A — безопасный demo dry-run

\- LLM mock;  
\- Confluence rest;  
\- local TXT;  
\- dry-run назначается автоматически;  
\- один клик Start запускает worker;  
\- видны stages;  
\- completed;  
\- Confluence page не создана.

\#\#\# B — fully real publish

Только при real LLM и real Confluence:

\- dry-run явно выключен;  
\- создана Confluence page;  
\- MCP read-back подтверждает результат.

\#\#\# C — mixed mode protection

LLM mock \+ Confluence rest \+ dry-run off должно блокироваться без explicit confirmation.

\#\#\# D — Telegram diagnostics

Несохранённые token/chat ID должны проверяться прямо из формы.

Сохранить:

\`docs/opencode/validations/GUI-E2E-\<HEAD\_SHORT\_SHA\>.md\`

\#\# 11\. Обязательные команды

\`\`\`bash  
python \-m compileall .  
python \-m json.tool docs/opencode/manifest.json  
pytest \-q  
ruff check .  
mypy . \--ignore-missing-imports  
\`\`\`

На Windows:

\`\`\`cmd  
call start\_app.bat \--startup-check  
\`\`\`

\#\# 12\. Обновить manifest

Добавить:

\- BB-CRIT-035;  
\- BB-CRIT-036;  
\- BB-CRIT-037;  
\- BB-CRIT-038;  
\- BB-CRIT-039;  
\- BB-MAJ-040;  
\- BB-MAJ-041;  
\- BB-MAJ-042.

\`BB-CRIT-026\` вернуть в \`PARTIALLY\_FIXED\` или \`NOT\_FIXED\` до реальной переработки GUI.

\#\# 13\. Формат ответа OpenCode

Предоставить:

1\. Новый \`headRefOid\`.  
2\. URL Draft PR.  
3\. Workflow run ID/URL.  
4\. Результаты обязательных команд.  
5\. Результат GUI E2E A–D.  
6\. Описание Settings provider modes.  
7\. Source-aware preflight summary.  
8\. Путь к \`processing\_events.jsonl\`.  
9\. Путь к \`GUI-E2E-\<SHA\>.md\`.  
10\. URL Confluence page только для fully real publish.  
11\. Подтверждение, что demo dry-run не создал страницу.  
12\. Оставшиеся ограничения.

PR оставить Draft.  
Merge не выполнять.  
\`accepted\` не устанавливать.  
