\# TASK-2026-08-01-runtime-settings-queue

\#\# Цель

Восстановить реальный пользовательский сценарий приложения \`bitlink-bot\`:

\`\`\`text  
настройки  
→ проверка подключений  
→ добавление источника  
→ preflight  
→ поэтапная обработка  
→ понятный результат или копируемая ошибка  
→ debug/validated artifacts  
→ публикация в Confluence  
→ отправка Telegram  
\`\`\`

Работать в существующем Draft PR:

\- Repository: \`EVErmeev/bitlink-bot\`  
\- Branch: \`fix/audit-e7cc95f\`  
\- PR: \`https://github.com/EVErmeev/bitlink-bot/pull/1\`  
\- Проверенный base head: \`68a161b1a57975f56bf893cceae1af7e1710a6f6\`

PR оставить Draft. Merge запрещён.

\#\# 1\. Добавить документы цикла

Сохранить в репозитории:

\`\`\`text  
docs/opencode/validations/VALIDATION-2026-08-01-68a161b-RUNTIME.md  
docs/opencode/tasks/TASK-2026-08-01-runtime-settings-queue.md  
\`\`\`

Обновить \`docs/opencode/manifest.json\`:

\`\`\`text  
active\_task\_id \= TASK-2026-08-01-runtime-settings-queue  
active\_task\_file \= docs/opencode/tasks/TASK-2026-08-01-runtime-settings-queue.md  
status \= in\_progress  
validation\_state \= implementing\_fixes  
\`\`\`

Добавить замечания:

\`\`\`text  
BB-CRIT-026 — GUI настроек не управляет provider/mock-флагами  
BB-CRIT-027 — batch объявляется completed независимо от ошибок  
BB-CRIT-028 — runtime errors скрыты от пользователя  
BB-CRIT-029 — real Newton transcription отсутствует  
BB-CRIT-030 — Telegram test не проверяет введённую конфигурацию  
BB-CRIT-031 — отсутствует preflight перед processing  
BB-MAJ-032 — повторный запуск непроцессируемой очереди завершается молча  
BB-MAJ-033 — GUI не назначает debug\_directory  
BB-MAJ-034 — параметры новых строк hardcoded  
\`\`\`

\#\# 2\. Переработать экран настроек

\#\#\# 2.1. Общий принцип

Каждый блок интеграции должен содержать явный режим работы и понятный статус:

\`\`\`text  
Отключено  
Mock / демонстрационный режим  
Real / рабочий режим  
\`\`\`

Нельзя считать, что заполнение token или URL автоматически переключает provider.

\#\#\# 2.2. Проверять текущие значения формы

Кнопка \`Проверить подключение\` должна использовать значения, которые прямо сейчас находятся в Entry/Combobox/Checkbutton.

Запрещено:

\`\`\`python  
client \= TelegramClient()  
\`\`\`

без передачи текущих значений формы.

Правильно:

\`\`\`python  
client \= TelegramClient(  
    bot\_token=bot\_token\_entry.get().strip(),  
    chat\_id=chat\_id\_entry.get().strip(),  
    mock\_mode=telegram\_mode\_var.get() \== "mock",  
    enabled=telegram\_enabled\_var.get(),  
)  
\`\`\`

Аналогичный принцип применить к Newton, Confluence, Bitlink и LLM.

\#\#\# 2.3. Сохранение и применение

После \`Сохранить настройки\`:

1\. записать \`.env\`;  
2\. выполнить \`load\_dotenv(..., override=True)\`;  
3\. обновить runtime config;  
4\. пересоздать clients либо использовать client factory;  
5\. не требовать перезапуска приложения;  
6\. показать сводку фактически применённых provider/mode без секретов.

Не создавать временные \`tk.Entry()\` как fallback в \`.get()\`.

\#\# 3\. Newton: убрать неясные параметры и зафиксировать контракт

\#\#\# 3.1. Текущее состояние

\`NEWTON\_PATH\` сейчас не используется. Real \`transcribe\_video()\` не реализован.

\#\#\# 3.2. Что сделать в UI

Вместо полей \`Путь\` и \`Base URL\` без объяснения добавить:

\`\`\`text  
Режим Newton:  
\- Отключено  
\- Mock  
\- HTTP API  
\- Локальный executable  
\`\`\`

Показывать provider-specific поля условно.

\#\#\#\# Отключено

Для локального TXT это допустимый и рекомендуемый режим.

\#\#\#\# Mock

Показывать красное/жёлтое предупреждение:

\`Используется демонстрационная расшифровка. Реальное видео не транскрибируется.\`

\#\#\#\# HTTP API

Показывать:

\- \`Base URL\` — корневой URL подтверждённого Newton HTTP API;  
\- \`Token\`;  
\- при необходимости endpoint path, но только если он подтверждён реальным контрактом.

\#\#\#\# Локальный executable

Показывать:

\- путь к конкретному executable или script;  
\- кнопку выбора файла;  
\- command template;  
\- проверку запуска \`--version\`/\`--help\`, если это поддерживается подтверждённым инструментом.

\#\#\# 3.3. Запрет выдумывать контракт

OpenCode должен найти подтверждённый Newton contract в:

\- существующей локальной конфигурации;  
\- установленном MCP/CLI;  
\- документации проекта;  
\- исходных требованиях.

Если контракт не найден:

1\. не реализовывать фиктивный HTTP-вызов;  
2\. \`HTTP API\` и \`Локальный executable\` показывать как \`Недоступно: контракт не подтверждён\`;  
3\. удалить обязательность \`NEWTON\_PATH\` и \`NEWTON\_BASE\_URL\` для TXT;  
4\. заблокировать real-video processing с понятной ошибкой до старта batch.

\#\#\# 3.4. Проверка Newton

Результат подключения должен показывать:

\- mode;  
\- resolved endpoint/path;  
\- auth status;  
\- version/capabilities при наличии;  
\- exact error;  
\- кнопку \`Копировать диагностику\`.

\#\# 4\. Telegram: полноценная диагностика

\#\#\# 4.1. Поля UI

Добавить:

\- \`Включить Telegram\`;  
\- mode \`Mock / Real\`;  
\- Bot Token;  
\- Chat ID;  
\- \`Проверить бота\`;  
\- \`Проверить чат\`;  
\- \`Отправить тестовое сообщение\`.

\#\#\# 4.2. Проверка token

В real-mode выполнить \`getMe\`.

Показать:

\- success/failure;  
\- username бота;  
\- bot ID;  
\- HTTP status;  
\- Telegram \`description\` при ошибке.

\#\#\# 4.3. Проверка chat ID

После успешного \`getMe\` проверить доступ к чату через поддерживаемый Telegram Bot API метод, например \`getChat\`.

Проверить:

\- существует ли chat;  
\- видит ли его бот;  
\- корректен ли знак ID для группы/канала;  
\- разрешена ли отправка.

\#\#\# 4.4. Тестовое сообщение

Отправлять только по отдельной кнопке и явному подтверждению пользователя.

Текст:

\`\`\`text  
bitlink-bot: проверка подключения Telegram  
\`\`\`

\#\#\# 4.5. Ошибки

Не показывать только:

\`Telegram не настроен (опционально)\`.

Показывать точную, копируемую диагностику:

\`\`\`text  
Stage: getMe / getChat / sendMessage  
HTTP status: ...  
Telegram error\_code: ...  
Description: ...  
Chat ID: ...  
Bot token: \*\*\*redacted\*\*\*  
\`\`\`

Секреты не писать в лог.

\#\# 5\. Добавить client factory и runtime configuration

Создать единый слой, например:

\`\`\`text  
services/client\_factory.py  
services/runtime\_config.py  
\`\`\`

Функции:

\`\`\`python  
build\_bitlink\_client(config)  
build\_transcription\_client(config)  
build\_confluence\_client(config)  
build\_telegram\_client(config)  
build\_llm\_client(config)  
\`\`\`

\`ProcessingService\` не должен навсегда захватывать устаревшие значения импортированного модуля \`settings\`.

Каждый запуск batch должен использовать snapshot актуальной конфигурации.

Сохранить snapshot без секретов в:

\`\`\`text  
runtime\_config\_snapshot.json  
\`\`\`

\#\# 6\. Реализовать обязательный preflight

Перед созданием worker thread выполнить preflight всех processable items.

\#\#\# 6.1. Общие проверки файла

Для локального источника:

\- файл существует;  
\- это файл, а не каталог;  
\- размер \> 0;  
\- файл читается;  
\- расширение поддерживается;  
\- source type соответствует расширению;  
\- TXT/MD не бинарный;  
\- видео имеет поддерживаемый контейнер;  
\- item не \`completed\`/\`skipped\`, если не выбран retry/reset.

\#\#\# 6.2. Требуемые сервисы по типу источника

\#\#\#\# local\_transcript

Требуются:

\- LLM;  
\- Confluence, если не dry-run;  
\- Telegram, только если \`send\_telegram=True\`.

Newton не нужен.

\#\#\#\# local\_video

Требуются:

\- Newton;  
\- LLM;  
\- Confluence, если не dry-run;  
\- Telegram, только если \`send\_telegram=True\`.

\#\#\#\# bitlink

Требуются:

\- Bitlink;  
\- Newton или подтверждённый transcript source;  
\- LLM;  
\- Confluence, если не dry-run;  
\- Telegram, только если \`send\_telegram=True\`.

\#\#\# 6.3. Preflight UI

Перед запуском показать таблицу:

| Элемент | Проверка | Результат | Причина | Следующее действие |  
|---|---|---|---|---|

При блокирующей ошибке batch не стартует.

Сообщение должно копироваться.

Сохранить:

\`\`\`text  
preflight\_report.json  
preflight\_report.txt  
\`\`\`

\#\# 7\. Исправить жизненный цикл batch

\#\#\# 7.1. Сброс состояния запуска

Перед новым batch:

\`\`\`python  
batch.cancel\_requested \= False  
batch.stop\_after\_current \= False  
\`\`\`

Не сбрасывать completed автоматически.

\#\#\# 7.2. Processable items

Явно рассчитать:

\`\`\`python  
processable \= \[  
    item for item in batch.items  
    if item.status in ("pending", "ready", "failed", "validation\_failed", "failed\_interrupted")  
\]  
\`\`\`

Для failed/validation\_failed пользователь должен выбрать \`Повторить\`.

Если \`processable\` пуст:

\- не запускать thread;  
\- показать \`Нет элементов для обработки\`;  
\- перечислить количество completed/skipped/cancelled;  
\- предложить \`Добавить файлы\`, \`Повторить ошибочные\`, \`Сбросить выбранные в pending\`.

\#\#\# 7.3. Worker exception boundary

Весь \`\_process\_batch\`, включая создание \`ProcessingService\`, завернуть в top-level \`try/except/finally\`.

Любая ошибка должна:

\- попасть в \`batch.error\_details\`;  
\- попасть в \`runtime\_error.log\`;  
\- отправиться в UI queue;  
\- не оставлять \`self.processing=True\`;  
\- не маскироваться как completed.

\#\#\# 7.4. Итоговый статус batch

Использовать:

\`\`\`text  
completed  
completed\_with\_errors  
failed  
cancelled  
nothing\_to\_process  
\`\`\`

Правила:

\- \`completed\` — все processable items успешны;  
\- \`completed\_with\_errors\` — есть completed и failed/validation\_failed;  
\- \`failed\` — нет ни одного successful item и есть ошибки;  
\- \`nothing\_to\_process\` — processable list пуст;  
\- \`cancelled\` — отмена.

\#\# 8\. Показывать реальный результат обработки

\#\#\# 8.1. Статус строки

Добавить колонки:

\- Stage;  
\- Status;  
\- Duration;  
\- Error summary;  
\- Artifact path;  
\- Confluence URL;  
\- Telegram status.

\#\#\# 8.2. Детали ошибки

По двойному клику или кнопке \`Детали\` открыть окно с:

\- item ID;  
\- source path;  
\- stage;  
\- exception class;  
\- message;  
\- traceback;  
\- HTTP status;  
\- response body в безопасном объёме;  
\- config modes без секретов;  
\- debug path;  
\- кнопкой \`Копировать\`.

\#\#\# 8.3. Итог batch

После завершения показывать не универсальное \`Обработка завершена\`, а сводку:

\`\`\`text  
Всего: N  
Успешно: N  
Ошибки: N  
Не прошли валидацию: N  
Пропущено: N  
Отменено: N  
Длительность: ...  
Batch report: ...  
\`\`\`

\#\# 9\. Всегда создавать debug\_directory

При добавлении строки назначать:

\`\`\`text  
debug/\<batch\_id\>/\<item\_id\>/  
\`\`\`

Сохранять минимум:

\- \`runtime\_config\_snapshot.json\`;  
\- \`preflight\_report.json\`;  
\- \`source\_transcript.txt\`;  
\- \`llm\_request.json\`;  
\- \`llm\_response\_raw.txt\`;  
\- \`llm\_response\_parsed.json\`;  
\- \`llm\_schema\_validation.json\`;  
\- \`topic\_coverage\_report.json\`;  
\- \`protocol.json\`;  
\- \`protocol\_preview.html\`;  
\- \`input\_manifest.json\`;  
\- \`runtime\_error.log\`, если была ошибка;  
\- validated artifacts при успехе.

\#\# 10\. Использовать настройки по умолчанию

При добавлении нового файла использовать фактические:

\`\`\`python  
protocol\_template \= runtime\_config.protocol\_template  
protocol\_mode \= runtime\_config.protocol\_mode  
send\_telegram \= runtime\_config.telegram\_enabled  
parent\_page\_id \= runtime\_config.confluence\_parent\_page\_id  
\`\`\`

Не использовать hardcoded \`project\_detailed\`, \`auto\` и \`send\_telegram=True\`.

\#\# 11\. Отдельно различать Mock и Real

В главном окне и очереди показывать banner:

\`\`\`text  
Режим: DEMO / MOCK  
\`\`\`

если хотя бы LLM или source service работают в mock.

Mock-результат нельзя визуально выдавать за рабочий протокол.

Для real processing перед стартом требовать:

\- \`LLM\_MOCK=false\` и рабочее LLM connection;  
\- real Confluence, если нужна публикация;  
\- real Newton только для видео;  
\- real Telegram только если включена отправка.

\#\# 12\. Confluence

Существующий REST publisher и MCP read-back сохранить.

Исправить GUI:

\- добавить provider \`mock/rest\`;  
\- сохранить \`CONFLUENCE\_PROVIDER\`;  
\- проверять текущие поля формы;  
\- показывать реальный provider в сообщении;  
\- не писать \`Подключение успешно (mock-режим)\` для REST;  
\- проверить parent page до batch;  
\- для real publication выполнить create \+ read-back;  
\- при ошибке публикации item не считать completed.

\#\# 13\. Обязательные тесты

Добавить минимум:

\`\`\`text  
test\_settings\_test\_uses\_unsaved\_form\_values  
test\_settings\_save\_applies\_without\_restart  
test\_newton\_path\_not\_required\_for\_local\_transcript  
test\_real\_video\_is\_blocked\_when\_newton\_contract\_unavailable  
test\_telegram\_getme\_failure\_exposes\_description  
test\_telegram\_chat\_id\_is\_checked  
test\_telegram\_test\_uses\_current\_entries  
test\_preflight\_blocks\_missing\_file  
test\_preflight\_blocks\_zero\_size\_file  
test\_preflight\_local\_transcript\_does\_not\_require\_newton  
test\_preflight\_video\_requires\_newton  
test\_empty\_processable\_queue\_does\_not\_start\_thread  
test\_completed\_items\_are\_explained\_as\_skipped  
test\_batch\_all\_failed\_has\_failed\_status  
test\_batch\_partial\_failure\_has\_completed\_with\_errors\_status  
test\_processing\_service\_init\_error\_is\_reported  
test\_cancel\_requested\_is\_reset\_before\_new\_run  
test\_debug\_directory\_created\_for\_every\_item  
test\_new\_items\_use\_runtime\_defaults  
test\_batch\_report\_contains\_exact\_item\_errors  
test\_mock\_mode\_is\_visible\_to\_user  
test\_real\_confluence\_failure\_does\_not\_mark\_completed  
\`\`\`

Запрещены:

\`\`\`python  
assert True  
if result\["success"\]:  
\`\`\`

Успешный E2E тест должен безусловно проверять success.

\#\# 14\. Обязательный GUI E2E сценарий

OpenCode должен выполнить вручную на Windows через \`start\_app.bat\`.

\#\#\# Сценарий A — локальный TXT, dry-run

1\. Запустить \`start\_app.bat\`.  
2\. Открыть настройки.  
3\. Выбрать:  
   \- Newton: Отключено;  
   \- LLM: Mock;  
   \- Confluence: Mock;  
   \- Telegram: Отключено.  
4\. Сохранить.  
5\. Добавить реальный локальный \`.txt\` файл.  
6\. Убедиться, что debug path создан.  
7\. Нажать \`Запустить обработку\`.  
8\. Проверить видимое прохождение стадий.  
9\. Получить \`completed\`, \`success=true\`, \`error=null\`.  
10\. Проверить artifacts.

\#\#\# Сценарий B — неверный Telegram token

1\. Выбрать Telegram Real.  
2\. Ввести заведомо неверный token.  
3\. Нажать \`Проверить бота\` без предварительного Save.  
4\. Получить точный Telegram error в копируемом окне.

\#\#\# Сценарий C — реальный Confluence

1\. Выбрать Confluence REST.  
2\. Использовать установленную конфигурацию.  
3\. Проверить connection и parent page.  
4\. Опубликовать синтетический валидированный протокол.  
5\. Выполнить read-back через MCP.

\#\#\# Сценарий D — local video без real Newton

1\. Выбрать Newton Disabled или неподтверждённый Real.  
2\. Добавить видео.  
3\. Preflight должен заблокировать batch до запуска.  
4\. Сообщение должно объяснить, какие Newton параметры отсутствуют и почему.

Сохранить отчёт:

\`\`\`text  
docs/opencode/validations/WINDOWS-GUI-E2E-\<head-short-sha\>.md  
\`\`\`

\#\# 15\. Обязательные команды

\`\`\`bash  
python \-m compileall .  
python \-m json.tool docs/opencode/manifest.json  
python \-c "import json,jsonschema; m=json.load(open('docs/opencode/manifest.json',encoding='utf-8')); s=json.load(open('docs/opencode/schemas/manifest.schema.json',encoding='utf-8')); jsonschema.validate(m,s); print('Schema: PASS')"  
pytest \-q  
ruff check .  
mypy . \--ignore-missing-imports  
\`\`\`

На Windows:

\`\`\`cmd  
call start\_app.bat \--startup-check  
\`\`\`

\#\# 16\. Что вернуть после выполнения

1\. Новый \`headRefOid\`.  
2\. URL Draft PR.  
3\. Workflow run ID/URL.  
4\. Список изменённых файлов.  
5\. Результаты всех обязательных команд.  
6\. Путь к \`WINDOWS-GUI-E2E-\*.md\`.  
7\. Результат каждого сценария A–D.  
8\. Скриншот или точный текст batch summary.  
9\. Пример копируемой Telegram ошибки с redacted token.  
10\. Фактическое определение Newton provider/contract.  
11\. Путь к одному полному debug directory успешного TXT.  
12\. Путь к runtime\_error.log неуспешного сценария.  
13\. URL страницы Confluence, созданной из GUI pipeline.  
14\. Статусы BB-CRIT-026–031 и BB-MAJ-032–034.  
15\. Оставшиеся ограничения.

PR оставить Draft.  
Merge не выполнять.  
Статус \`accepted\` не устанавливать.  
