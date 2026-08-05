\# TASK-2026-08-01-start-app-confluence-mcp

\#\# Исправление Windows launcher и реальной публикации в Confluence через установленный MCP

\*\*Репозиторий:\*\* \`EVErmeev/bitlink-bot\`    
\*\*Draft PR:\*\* \`https://github.com/EVErmeev/bitlink-bot/pull/1\`    
\*\*Ветка:\*\* \`fix/audit-e7cc95f\`    
\*\*Проверенный head:\*\* \`034e2a5adab04e737cfdcef8a24b80e1a75dd4a4\`    
\*\*Статус:\*\* \`changes\_required\`; PR оставить Draft, merge запрещён.

\---

\# 1\. Новая вводная

На рабочем компьютере установлен Confluence MCP:

\`\`\`powershell  
irm https://mcp.1bitai.ru/dist/confluence-setup.ps1 | iex  
\`\`\`

После установки OpenCode перезапущен.

OpenCode обязан заново проверить Confluence-часть. Замечание о неподтверждённом API нельзя оставлять \`NOT\_VERIFIABLE\` без попытки использовать установленный MCP.

При этом установка MCP в OpenCode не означает автоматически, что приложение, запущенное через \`start\_app.bat\`, умеет обращаться к MCP. Нужно разделить:

\- \*\*контур OpenCode/MCP\*\* — discovery, чтение, запись smoke-page, read-back и проверка результата;  
\- \*\*runtime-контур приложения\*\* — явный provider \`rest\`, \`mcp\` или \`mock\`.

Нельзя привязывать приложение к внутренним файлам конфигурации OpenCode и нельзя коммитить MCP credentials.

\---

\# 2\. MCP discovery — выполнить до изменения Confluence-кода

\#\# 2.1. Обнаружить сервер и tools

Не угадывать имена tools. Получить фактический список MCP servers и доступных tools.

Зафиксировать:

\- имя server;  
\- версию, если доступна;  
\- tool names;  
\- обязательные аргументы;  
\- read/write capabilities;  
\- наличие операций: current user, search page, get page, list children, create page, update page, delete/archive page, spaces.

\#\# 2.2. Проверить авторизацию

Выполнить безопасный read-only запрос текущего пользователя или чтение доступной страницы.

Запрещено выводить или сохранять:

\- token;  
\- cookies;  
\- Authorization headers;  
\- passwords;  
\- credential-store content.

\#\# 2.3. Создать отчёт

Создать:

\`\`\`text  
docs/opencode/validations/CONFLUENCE-MCP-DISCOVERY-\<short\_sha\>.md  
\`\`\`

Обязательные поля:

\`\`\`text  
MCP server discovered: yes/no  
Server name:  
Available tools:  
Read access: pass/fail  
Write access: pass/fail/not tested  
Confluence base URL:  
Visible spaces:  
Selected space:  
Selected parent page title:  
Selected parent page ID:  
Runtime invocation from ordinary Python: supported/not supported/not verified  
Secrets committed: no  
\`\`\`

Если MCP после перезапуска не виден — остановить только Confluence-часть и зафиксировать точную ошибку. Исправление BAT и mock pipeline продолжить.

\---

\# 3\. Определить родительскую страницу

Приоритет:

1\. \`CONFLUENCE\_PARENT\_PAGE\_ID\` из локальных настроек;  
2\. \`CONFLUENCE\_PARENT\_PAGE\_TITLE\`;  
3\. точный поиск через MCP;  
4\. выбор только внутри определённого пространства.

Если найдено несколько страниц с одинаковым названием, не выбирать случайную. Вывести page ID, title, space, parent и URL и остановить write-test до однозначного выбора.

Не публиковать тестовую страницу в случайное пространство.

\---

\# 4\. Реализовать provider abstraction

Текущий \`ConfluenceClient\` в real-mode заканчивает \`NotImplementedError\`. Это должно быть заменено явной архитектурой.

Допустимая структура:

\`\`\`text  
services/confluence/  
├── base.py  
├── mock\_publisher.py  
├── rest\_publisher.py  
├── mcp\_publisher.py  
├── models.py  
└── errors.py  
\`\`\`

Интерфейс:

\`\`\`python  
class ConfluencePublisher(Protocol):  
    def check\_connection(self): ...  
    def get\_page(self, page\_id: str): ...  
    def find\_pages(self, title: str, space\_key: str | None \= None): ...  
    def create\_page(  
        self,  
        title: str,  
        storage\_html: str,  
        parent\_page\_id: str,  
        space\_key: str | None \= None,  
        idempotency\_key: str | None \= None,  
    ): ...  
\`\`\`

Добавить настройки:

\`\`\`env  
CONFLUENCE\_PROVIDER=mock  
CONFLUENCE\_MOCK=true  
CONFLUENCE\_BASE\_URL=  
CONFLUENCE\_TOKEN=  
CONFLUENCE\_SPACE\_KEY=  
CONFLUENCE\_PARENT\_PAGE\_ID=  
CONFLUENCE\_PARENT\_PAGE\_TITLE=  
CONFLUENCE\_MCP\_SERVER=  
CONFLUENCE\_MCP\_TIMEOUT\_SECONDS=60  
\`\`\`

Правила:

\- \`mock\` — только mock;  
\- \`rest\` — только REST, без fallback;  
\- \`mcp\` — только если подтверждён стабильный runtime-вызов из обычного Python-процесса;  
\- неизвестное значение — configuration error;  
\- отсутствие обязательной настройки — configuration error;  
\- автоматический переход на mock запрещён.

Если MCP доступен только как tool OpenCode, а не как runtime transport, приложение должно использовать \`rest\_publisher\`, а MCP — проверять созданную страницу.

Нельзя читать secrets из локальных конфигурационных файлов OpenCode.

\---

\# 5\. Использовать MCP для подтверждения реального контракта

Через MCP:

1\. прочитать существующую страницу;  
2\. определить фактический page object;  
3\. определить поля title, ID, URL, parent и body;  
4\. проверить представление storage/body;  
5\. определить write tool и его schema;  
6\. зафиксировать контракт без secrets;  
7\. на основании подтверждённого контракта реализовать provider.

Если runtime MCP недоступен, реализовать REST adapter по подтверждённой конфигурации, а MCP использовать для read-back.

\---

\# 6\. Безопасный MCP write smoke-test

Выполнять только после успешного read-only discovery и выбора parent page.

Создать ровно одну тестовую страницу:

\`\`\`text  
\[bitlink-bot-smoke\] \<UTC timestamp\> \<short\_sha\>  
\`\`\`

Использовать только синтетические данные. Body должен содержать:

\- marker \`BITLINK\_BOT\_SMOKE\_TEST\`;  
\- кириллицу;  
\- абзац;  
\- список;  
\- таблицу;  
\- ссылку.

После создания прочитать страницу через MCP и проверить:

\- page ID и URL получены;  
\- title совпадает;  
\- parent ID совпадает;  
\- marker присутствует;  
\- body не пустой;  
\- кириллица и таблица сохранены.

Если есть delete/archive tool — удалить или архивировать только созданную smoke-page. Если нет — оставить и указать \`cleanup\_required=true\` и URL.

Создать:

\`\`\`text  
docs/opencode/validations/CONFLUENCE-MCP-WRITE-\<short\_sha\>.md  
\`\`\`

\---

\# 7\. End-to-end публикация из приложения

После реализации provider выполнить реальную публикацию через приложение, запущенное через \`start\_app.bat\`.

Использовать синтетический TXT-транскрипт с:

\- двумя участниками;  
\- двумя темами;  
\- одним решением;  
\- одной задачей;  
\- одним вопросом;  
\- одним риском;  
\- сроком и ответственным.

Сценарий:

1\. открыть \`start\_app.bat\`;  
2\. добавить TXT;  
3\. выбрать шаблон;  
4\. отключить dry-run;  
5\. выбрать real Confluence provider;  
6\. выбрать проверенный parent page;  
7\. запустить обработку;  
8\. получить \`completed\`, \`success=true\`, непустой real URL;  
9\. прочитать страницу через MCP;  
10\. сопоставить title, parent, body и validated artifacts.

Запрещены:

\- mock URL;  
\- \`mock-confluence.example.com\`;  
\- публикация preview вместо final validated HTML;  
\- публикация реальной клиентской расшифровки в тесте.

\#\# Idempotency

Повторная публикация одного validated artifact не должна создавать бесконтрольные дубли.

Использовать \`protocol\_id\` или SHA validated artifact как idempotency key. Повторная операция должна вернуть существующую страницу либо обновить её только в явно заданном режиме.

\---

\# 8\. Исправить \`start\_app.bat\`

Фактическая ошибка пользователя:

\`\`\`text  
'жение' is not recognized as an internal or external command,  
operable program or batch file.  
\`\`\`

BAT — обязательная пользовательская точка запуска.

Требования:

1\. ASCII-only;  
2\. без кириллицы;  
3\. без \`chcp 65001\`;  
4\. CRLF line endings;  
5\. \`cd /d "%\~dp0"\`;  
6\. выбор Python: \`.venv\\Scripts\\python.exe\` → \`py \-3\` → \`python\`;  
7\. передача \`%\*\`;  
8\. traceback не скрывать;  
9\. реальный exit code сохранять;  
10\. \`pause\` только при ошибке.

Рекомендуемая реализация:

\`\`\`bat  
@echo off  
setlocal EnableExtensions  
cd /d "%\~dp0"

if exist ".venv\\Scripts\\python.exe" (  
    ".venv\\Scripts\\python.exe" app.py %\*  
    goto :after\_run  
)

where py \>nul 2\>nul  
if not errorlevel 1 (  
    py \-3 app.py %\*  
    goto :after\_run  
)

where python \>nul 2\>nul  
if not errorlevel 1 (  
    python app.py %\*  
    goto :after\_run  
)

echo Python 3 was not found.  
pause  
exit /b 9009

:after\_run  
set "APP\_EXIT\_CODE=%ERRORLEVEL%"  
if not "%APP\_EXIT\_CODE%"=="0" (  
    echo Application failed with exit code %APP\_EXIT\_CODE%.  
    pause  
)  
exit /b %APP\_EXIT\_CODE%  
\`\`\`

Добавить \`.gitattributes\`:

\`\`\`gitattributes  
\*.bat text eol=crlf  
\*.cmd text eol=crlf  
\`\`\`

\---

\# 9\. Добавить \`--startup-check\`

Команда:

\`\`\`cmd  
call start\_app.bat \--startup-check  
\`\`\`

должна:

\- не входить в \`mainloop\`;  
\- не показывать диалоги;  
\- импортировать settings и UI modules;  
\- загрузить TemplateRegistry;  
\- проверить четыре шаблона;  
\- создать mock Confluence provider;  
\- не создавать реальную страницу;  
\- вывести \`STARTUP\_CHECK\_OK\`;  
\- вернуть exit code 0\.

\---

\# 10\. Исправить default LLM mock

При \`LLM\_MOCK=true\` mock JSON должен проходить schema конкретного шаблона.

Требования:

\- все required fields присутствуют;  
\- типы корректны;  
\- для непустого transcript создаётся минимум одна тема;  
\- source item IDs относятся к текущему source context;  
\- default dry-run проходит без monkeypatch;  
\- нет schema retry exhaustion;  
\- нет foreign facts.

\---

\# 11\. Исправить слабые тесты

Удалить условные проверки вида:

\`\`\`python  
if result\["success"\]:  
\`\`\`

Успешный сценарий должен безусловно проверять:

\`\`\`python  
assert result\["success"\] is True  
assert result\["error"\] is None  
assert item.status \== "completed"  
\`\`\`

Добавить тесты:

\`\`\`text  
test\_default\_mock\_dry\_run\_completes  
test\_start\_app\_bat\_is\_ascii\_safe  
test\_startup\_check\_returns\_zero  
test\_mock\_payload\_valid\_for\_all\_templates  
test\_confluence\_provider\_does\_not\_fallback\_to\_mock  
test\_confluence\_parent\_is\_required\_for\_real\_publish  
test\_confluence\_publishes\_final\_validated\_html  
test\_confluence\_idempotency\_prevents\_duplicate  
test\_confluence\_secrets\_are\_not\_written\_to\_artifacts  
\`\`\`

MCP integration test запускать отдельно:

\`\`\`bash  
pytest \-q \-m confluence\_mcp  
\`\`\`

Не включать secrets в GitHub Actions.

\---

\# 12\. GitHub Actions

Оставить обязательными compileall, json.tool, manifest schema, pytest, Ruff и Mypy.

Добавить Windows gate:

\`\`\`yaml  
\- name: Windows launcher smoke test  
  if: runner.os \== 'Windows'  
  shell: cmd  
  run: call start\_app.bat \--startup-check  
\`\`\`

Без \`continue-on-error\`.

\---

\# 13\. Статусы замечаний

\`BB-CRIT-001\` оставить \`PARTIALLY\_FIXED\`, пока real БИТ.Link adapter отсутствует.

\`BB-MAJ-019\` перевести в \`IN\_PROGRESS\`; в \`FIXED\` — только после реального create \+ MCP read-back.

Добавить:

\`\`\`text  
BB-CRIT-021 — start\_app.bat не работает  
BB-CRIT-022 — CI не проверяет BAT launcher  
BB-CRIT-023 — default LLM mock не соответствует schema  
BB-MAJ-024 — слабые условные тесты  
BB-MAJ-025 — manifest содержит устаревший head  
BB-CRIT-026 — real Confluence publication не подтверждена через MCP  
BB-MAJ-027 — parent page и idempotency не валидированы  
\`\`\`

\---

\# 14\. Обязательные validation-файлы

Создать:

\`\`\`text  
docs/opencode/validations/CONFLUENCE-MCP-DISCOVERY-\<short\_sha\>.md  
docs/opencode/validations/CONFLUENCE-MCP-WRITE-\<short\_sha\>.md  
docs/opencode/validations/WINDOWS-LAUNCHER-MANUAL-\<short\_sha\>.md  
\`\`\`

В manual report указать Windows version, выбранный Python, BAT exit code, GUI launch, default mock dry-run, real Confluence URL, MCP read-back, созданные artifacts и ограничения.

\---

\# 15\. Обновить manifest

Перед началом:

\`\`\`json  
{  
  "active\_task\_id": "TASK-2026-08-01-start-app-confluence-mcp",  
  "active\_task\_file": "docs/opencode/tasks/TASK-2026-08-01-start-app-confluence-mcp.md",  
  "status": "in\_progress",  
  "validation\_state": "implementing\_fixes"  
}  
\`\`\`

После push выполнить:

\`\`\`bash  
gh pr view 1 \--json headRefOid,url,isDraft,statusCheckRollup  
\`\`\`

Записать exact \`headRefOid\`.

Добавить в required checks:

\`\`\`text  
call start\_app.bat \--startup-check  
pytest \-q \-m confluence\_mcp  \# local\_only  
\`\`\`

Не сохранять secrets в manifest или artifacts.

\---

\# 16\. Обязательные команды

\`\`\`bash  
python \-m compileall .  
python \-m json.tool docs/opencode/manifest.json  
python \-c "import json,jsonschema; m=json.load(open('docs/opencode/manifest.json',encoding='utf-8')); s=json.load(open('docs/opencode/schemas/manifest.schema.json',encoding='utf-8')); jsonschema.validate(m,s); print('Schema: PASS')"  
pytest \-q  
ruff check .  
mypy . \--ignore-missing-imports  
\`\`\`

Windows:

\`\`\`cmd  
call start\_app.bat \--startup-check  
\`\`\`

MCP local integration:

\`\`\`bash  
pytest \-q \-m confluence\_mcp  
\`\`\`

\---

\# 17\. Что вернуть

1\. Новый \`headRefOid\`.  
2\. URL Draft PR.  
3\. Workflow run ID и URL.  
4\. Список обнаруженных MCP tools.  
5\. MCP authorization result.  
6\. Выбранный runtime provider и обоснование.  
7\. Parent page title и ID.  
8\. Smoke-page ID и URL.  
9\. MCP read-back result.  
10\. Cleanup result.  
11\. \`start\_app.bat \--startup-check\` result.  
12\. Результат двойного клика BAT.  
13\. Default mock dry-run без monkeypatch.  
14\. Real Confluence publication URL.  
15\. Результаты pytest, Ruff, Mypy.  
16\. Пути к трём validation-файлам.  
17\. Список изменённых файлов.  
18\. Статусы BB-CRIT и BB-MAJ.  
19\. Оставшиеся ограничения.

Не переводить PR в Ready. Не выполнять merge. Не устанавливать \`accepted\`.  
