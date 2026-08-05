\# TASK-2026-08-01-production-mode-settings

\#\# Назначение

Перевести приложение из глобального демонстрационного режима в управляемые рабочие профили и обеспечить реальную обработку локального TXT через настоящий LLM и Confluence.

Текущий баннер \`DEMO / MOCK\` продолжает отображаться не только из\-за настроек пользователя, но и из\-за архитектуры определения режима:

\- \`RuntimeConfig.is\_demo\_mode()\` возвращает \`True\`, если mock включён хотя бы у одного сервиса;  
\- Newton и БИТ.Link учитываются даже для локального TXT, хотя в этом сценарии не используются;  
\- значения по умолчанию для LLM, Newton, БИТ.Link и Telegram — mock;  
\- экран настроек не позволяет выбрать provider mode;  
\- на экране нет настроек LLM;  
\- Confluence provider нельзя переключить из GUI;  
\- пользователь не видит, какой именно сервис удерживает приложение в demo mode.

\#\# Репозиторий и PR

\- Repository: \`EVErmeev/bitlink-bot\`  
\- Branch: \`fix/audit-e7cc95f\`  
\- Draft PR: \`https://github.com/EVErmeev/bitlink-bot/pull/1\`  
\- Проверенный base head: \`5c3fc6c9de16440292b100f2d4bf62e1056be65a\`

PR оставить Draft. Merge не выполнять.

\#\# 1\. Новые замечания

Добавить в manifest:

\- \`BB-CRIT-043\` — demo mode определяется глобально, а не по фактическому сценарию;  
\- \`BB-CRIT-044\` — Settings GUI не позволяет включить real LLM;  
\- \`BB-CRIT-045\` — Settings GUI не позволяет управлять provider modes;  
\- \`BB-CRIT-046\` — пользователь не видит причины, по которым production readiness не достигнута;  
\- \`BB-CRIT-047\` — local TXT нельзя перевести в production profile через GUI;  
\- \`BB-MAJ-048\` — banner всегда учитывает BIT.Link mock, даже когда в очереди нет Bitlink;  
\- \`BB-MAJ-049\` — \`.env\` и GUI имеют разные модели настроек;  
\- \`BB-MAJ-050\` — нет безопасной проверки реального LLM до запуска обработки.

\#\# 2\. Реализовать рабочие профили

Добавить в \`RuntimeConfig\` явное поле:

\`\`\`python  
app\_profile: str  \# demo | local\_txt\_production | custom  
\`\`\`

Добавить метод:

\`\`\`python  
def get\_effective\_services(self, source\_type: str, item=None) \-\> dict:  
    ...  
\`\`\`

Метод должен возвращать только сервисы, реально участвующие в сценарии.

\#\#\# Профиль \`local\_txt\_production\`

Для локального TXT:

\- LLM: \`real\`;  
\- Confluence: \`rest\` или \`disabled\` при dry-run;  
\- Telegram: \`disabled\` или \`real\`;  
\- Newton: \`not\_applicable\`;  
\- BIT.Link: \`not\_applicable\`;  
\- dry-run: выбирается пользователем;  
\- режим не считается demo, если LLM работает реально.

\#\#\# Профиль \`demo\`

\- LLM: mock;  
\- публикация в реальный Confluence запрещена;  
\- Telegram real запрещён;  
\- dry-run включён автоматически;  
\- banner \`DEMO\` обязателен.

\#\#\# Профиль \`custom\`

\- пользователь выбирает режим каждого сервиса;  
\- mixed-mode safety остаётся обязательной;  
\- UI показывает предупреждения и блокеры.

\#\# 3\. Исправить определение demo mode

Заменить глобальную логику:

\`\`\`python  
any(service\_mode \== "mock" for all services)  
\`\`\`

на source-aware методы:

\`\`\`python  
def is\_demo\_for\_source(self, source\_type: str, item=None) \-\> bool:  
    effective \= self.get\_effective\_services(source\_type, item)  
    return any(v \== "mock" for v in effective.values())  
\`\`\`

Для \`local\_transcript\` Newton и BIT.Link не должны влиять на результат.

Для пустой очереди banner должен показывать общий профиль, а не делать вывод из неиспользуемых сервисов.

\#\# 4\. Полностью переработать Settings GUI

Создать отдельные блоки.

\#\#\# 4.1 Профиль приложения

Combobox:

\- Демонстрационный;  
\- Рабочий: локальные TXT;  
\- Пользовательский.

Показывать статус:

\- \`DEMO\`;  
\- \`PRODUCTION READY\`;  
\- \`PRODUCTION BLOCKED\`;  
\- \`MIXED MODE — DRY-RUN ONLY\`.

\#\#\# 4.2 LLM

Поля:

\- Mode: Mock / Real API;  
\- Base URL;  
\- API Key;  
\- Model;  
\- Timeout;  
\- кнопка \`Проверить соединение\`;  
\- кнопка \`Выполнить тестовую генерацию\`.

При проверке использовать текущие значения формы, даже если они ещё не сохранены.

Тестовая генерация должна:

1\. отправить короткий безопасный prompt;  
2\. запросить JSON по минимальной schema;  
3\. проверить JSON Schema;  
4\. показать модель, latency и краткий результат;  
5\. не выводить API key.

\#\#\# 4.3 Confluence

Поля:

\- Mode: Disabled / Mock / REST;  
\- Base URL;  
\- Token;  
\- Space Key;  
\- Parent Page ID;  
\- Parent Page Title.

MCP используется для read-back и discovery, но runtime provider остаётся REST.

\#\#\# 4.4 Telegram

Поля:

\- Mode: Disabled / Mock / Real;  
\- Bot Token;  
\- Chat ID;  
\- Send batch summary;  
\- Send protocol notification.

Проверка должна выполнять:

\- \`getMe\`;  
\- \`getChat\`;  
\- отдельную кнопку \`Отправить тестовое сообщение\`.

Точную ошибку показывать в копируемом окне.

\#\#\# 4.5 Newton

Поля:

\- Mode: Disabled / Mock;  
\- сообщение: \`Real Newton API contract is not implemented\`.

Убрать \`Path\`, \`Token\` и \`Base URL\` из обычного GUI до подтверждения контракта.

\#\#\# 4.6 BIT.Link

Поля:

\- Mode: Disabled / Mock;  
\- email/password скрыть или заблокировать при отсутствии real adapter;  
\- показать: \`Real BIT.Link adapter is not implemented\`.

\#\# 5\. Синхронизировать GUI и \`.env\`

После \`Сохранить настройки\` должны записываться и перечитываться:

\`\`\`text  
APP\_PROFILE  
LLM\_MOCK  
LLM\_API\_URL  
LLM\_API\_KEY  
LLM\_MODEL  
CONFLUENCE\_PROVIDER  
CONFLUENCE\_BASE\_URL  
CONFLUENCE\_TOKEN  
CONFLUENCE\_SPACE\_KEY  
CONFLUENCE\_PARENT\_PAGE\_ID  
CONFLUENCE\_PARENT\_PAGE\_TITLE  
TELEGRAM\_MOCK  
TELEGRAM\_ENABLED  
TG\_BOT\_TOKEN  
TG\_CHAT\_ID  
TELEGRAM\_SEND\_BATCH\_SUMMARY  
NEWTON\_MOCK  
BITLINK\_MOCK  
\`\`\`

После сохранения:

1\. перезагрузить \`settings\`;  
2\. вызвать \`reload\_runtime\_config()\`;  
3\. обновить banner без перезапуска приложения;  
4\. обновить preflight summary.

\#\# 6\. Добавить Production Readiness Panel

На экране настроек и в очереди показывать таблицу:

| Сервис | Эффективный режим | Используется | Проверка | Причина |  
|---|---|---:|---|---|  
| LLM | real | да | OK/FAIL | ... |  
| Confluence | rest | да/нет | OK/SKIPPED | ... |  
| Telegram | real/disabled | да/нет | OK/SKIPPED | ... |  
| Newton | not\_applicable | нет | SKIPPED | local TXT |  
| BIT.Link | not\_applicable | нет | SKIPPED | local TXT |

Production-ready для local TXT допускается только если:

\- LLM \= real;  
\- LLM connection check \= pass;  
\- schema generation test \= pass;  
\- Confluence \= REST с успешным read check, либо dry-run включён;  
\- Telegram disabled либо real с успешными getMe/getChat;  
\- Newton и BIT.Link помечены \`not\_applicable\`.

\#\# 7\. Исправить banner

\#\#\# Рабочий local TXT

\`\`\`text  
PRODUCTION READY | Source: local TXT | LLM: real | Confluence: REST | Telegram: disabled  
\`\`\`

\#\#\# Рабочий dry-run

\`\`\`text  
PRODUCTION DRY-RUN | Source: local TXT | LLM: real | Publication: disabled  
\`\`\`

\#\#\# Demo

\`\`\`text  
DEMO | Source: local TXT | LLM: mock | Dry-run forced  
\`\`\`

Newton и BIT.Link не выводить для local TXT как mock-сервисы.

\#\# 8\. Реальный LLM обязателен для снятия demo mode

Confluence MCP и REST не заменяют LLM.

Приложение не должно считать себя production-ready, если протокол генерируется mock-объектом.

OpenCode должен использовать локально введённые пользователем LLM URL/API key/model. Secrets не коммитить, не логировать и не включать в validation-файлы.

Если реальные реквизиты LLM отсутствуют:

\- не заявлять успешный production E2E;  
\- показать \`PRODUCTION BLOCKED: real LLM is not configured\`;  
\- перечислить точные поля, которые должен заполнить пользователь.

\#\# 9\. Исправить dry-run и публикацию

Для local TXT:

\- real LLM \+ dry-run \= разрешено;  
\- real LLM \+ real Confluence \+ dry-run off \= разрешено после успешного preflight;  
\- mock LLM \+ real Confluence \= только forced dry-run;  
\- mock LLM \+ real Telegram \= Telegram disabled для этой обработки;  
\- никакой mock-content не публиковать в production systems.

\#\# 10\. Обязательные тесты

Добавить:

\`\`\`text  
test\_local\_txt\_ignores\_newton\_mock\_for\_demo\_status  
test\_local\_txt\_ignores\_bitlink\_mock\_for\_demo\_status  
test\_local\_txt\_real\_llm\_is\_not\_demo  
test\_local\_txt\_mock\_llm\_is\_demo  
test\_empty\_queue\_banner\_uses\_selected\_profile  
test\_production\_profile\_sets\_expected\_modes  
test\_demo\_profile\_forces\_dry\_run  
test\_settings\_gui\_has\_app\_profile\_selector  
test\_settings\_gui\_has\_llm\_mode\_fields  
test\_settings\_gui\_has\_confluence\_mode\_selector  
test\_settings\_gui\_has\_telegram\_mode\_selector  
test\_settings\_gui\_hides\_newton\_path\_without\_contract  
test\_settings\_save\_reloads\_runtime\_config  
test\_banner\_updates\_after\_settings\_save  
test\_llm\_connection\_test\_uses\_unsaved\_form\_values  
test\_llm\_schema\_smoke\_test  
test\_production\_readiness\_blocks\_missing\_llm\_key  
test\_production\_readiness\_skips\_newton\_for\_local\_txt  
test\_production\_readiness\_skips\_bitlink\_for\_local\_txt  
test\_mock\_llm\_never\_publishes\_real\_confluence  
test\_mock\_llm\_never\_sends\_real\_telegram  
\`\`\`

\#\# 11\. Обязательные E2E-сценарии через \`start\_app.bat\`

\#\#\# A. Demo local TXT

\- профиль Demo;  
\- LLM mock;  
\- banner DEMO;  
\- dry-run forced;  
\- обработка завершается;  
\- Confluence page не создаётся.

\#\#\# B. Production local TXT dry-run

\- профиль Local TXT Production;  
\- real LLM;  
\- dry-run on;  
\- banner \`PRODUCTION DRY-RUN\`;  
\- протокол реально сформирован LLM;  
\- validated artifacts созданы;  
\- Confluence page не создаётся.

\#\#\# C. Production local TXT publish

\- real LLM;  
\- Confluence REST;  
\- dry-run off;  
\- preflight \= pass;  
\- страница создана из GUI pipeline;  
\- MCP read-back подтверждает title, parent, content и таблицы;  
\- mock markers отсутствуют.

\#\#\# D. Production blocked

\- real LLM selected;  
\- API key пустой или URL неверный;  
\- banner \`PRODUCTION BLOCKED\`;  
\- обработка не стартует;  
\- показана копируемая причина.

\#\#\# E. Telegram

\- Telegram real;  
\- getMe pass;  
\- getChat pass;  
\- test message pass;  
\- при disabled Telegram полностью пропускается.

Сохранить:

\`\`\`text  
docs/opencode/validations/PRODUCTION-MODE-E2E-\<HEAD\_SHORT\_SHA\>.md  
\`\`\`

\#\# 12\. Обязательные команды

\`\`\`bash  
python \-m compileall .  
python \-m json.tool docs/opencode/manifest.json  
pytest \-q  
ruff check .  
mypy . \--ignore-missing-imports  
\`\`\`

Windows:

\`\`\`cmd  
call start\_app.bat \--startup-check  
\`\`\`

\#\# 13\. Обновить manifest

\- установить новое активное задание;  
\- добавить BB-CRIT-043…047 и BB-MAJ-048…050;  
\- \`BB-CRIT-038\` оставить \`PARTIALLY\_FIXED\` до фактической переработки GUI;  
\- после E2E записать exact \`headRefOid\`;  
\- не сохранять secrets;  
\- не устанавливать \`accepted\`.

\#\# 14\. Формат ответа OpenCode

Предоставить:

1\. новый \`headRefOid\`;  
2\. URL Draft PR;  
3\. workflow run ID/URL;  
4\. результаты compileall, json.tool, pytest, Ruff и Mypy;  
5\. описание нового Settings GUI;  
6\. effective service matrix для local TXT;  
7\. результат LLM connection test без раскрытия secret;  
8\. результат JSON Schema smoke generation;  
9\. результаты E2E A–E;  
10\. URL страницы Confluence из production publish;  
11\. MCP read-back result;  
12\. путь к \`PRODUCTION-MODE-E2E-\<SHA\>.md\`;  
13\. оставшиеся ограничения.

PR оставить Draft.  
Merge не выполнять.  
\`accepted\` не устанавливать.  
