\# TASK-2026-08-02-settings-real-connection-checks

\#\# Цель

Полностью довести страницу «Настройки» до рабочего состояния, чтобы каждая кнопка проверки:

1\. использовала текущие значения формы;  
2\. выполняла реальный подтверждённый вызов сервиса или честно показывала \`NOT\_IMPLEMENTED\`;  
3\. не блокировала Tkinter GUI;  
4\. возвращала подробный результат в интерфейс;  
5\. не выводила secrets;  
6\. участвовала в единой сводке готовности приложения.

\#\# Репозиторий

\- Repository: \`EVErmeev/bitlink-bot\`  
\- Branch: \`fix/audit-e7cc95f\`  
\- Draft PR: \`https://github.com/EVErmeev/bitlink-bot/pull/1\`  
\- Проверенный base head: \`2be955460fe664b9295da890e15bd89421a7e93c\`

Перед началом:

\`\`\`bash  
gh pr view 1 \--json headRefOid,url,isDraft,statusCheckRollup  
\`\`\`

PR оставить Draft. Merge и \`accepted\` запрещены.

\---

\# 1\. Исправить текущий LLM GUI blocker

Фактическая ошибка:

\`\`\`text  
AttributeError: 'SettingsFrame' object has no attribute 'root'. Did you mean: '\_root'?  
\`\`\`

Текущие worker-потоки используют:

\`\`\`python  
self.root.after(...)  
\`\`\`

\`SettingsFrame\` не имеет атрибута \`root\`.

\#\# Требование

Создать один безопасный способ возврата результата в UI:

\`\`\`python  
def \_run\_on\_ui(self, callback, \*args, \*\*kwargs):  
    if not self.winfo\_exists():  
        return  
    self.after(0, lambda: callback(\*args, \*\*kwargs))  
\`\`\`

Допускается эквивалентная реализация через \`winfo\_toplevel()\`, но запрещено:

\- создавать случайный \`self.root\` только ради подавления ошибки;  
\- обновлять Tkinter widgets из worker thread;  
\- использовать \`main\_window.root\` напрямую в каждом callback;  
\- оставлять разные механизмы в разных кнопках.

Заменить все \`self.root.after(...)\`.

Кнопки version/health/token должны всегда возвращаться в \`NORMAL\` в UI-finalizer, включая:

\- success;  
\- provider error;  
\- timeout;  
\- unexpected exception;  
\- уничтожение SettingsFrame.

\---

\# 2\. Создать единую модель результата проверки

Создать:

\`\`\`text  
services/connection\_checks.py  
\`\`\`

Модель:

\`\`\`python  
@dataclass  
class ConnectionCheckResult:  
    service\_id: str  
    provider: str  
    status: str  
    stage: str  
    safe\_message: str  
    recommendation: str \= ""  
    endpoint\_or\_command: str \= ""  
    http\_status: int | None \= None  
    exit\_code: int | None \= None  
    latency\_seconds: float | None \= None  
    checked\_at: str \= ""  
    details: dict \= field(default\_factory=dict)  
\`\`\`

Допустимые статусы:

\`\`\`text  
PASS  
FAIL  
TIMEOUT  
NOT\_CONFIGURED  
MOCK  
NOT\_IMPLEMENTED  
SKIPPED  
\`\`\`

Правила:

\- \`MOCK\` не является \`PASS\`;  
\- \`NOT\_IMPLEMENTED\` не является \`PASS\`;  
\- наличие полей конфигурации не является \`PASS\`;  
\- \`PASS\` допустим только после фактического вызова, который подтверждает назначение проверки;  
\- details не содержат secrets;  
\- endpoint/command маскирует credentials.

\---

\# 3\. Создать единый async runner для SettingsFrame

Создать UI helper или методы SettingsFrame:

\`\`\`python  
def \_start\_check(  
    self,  
    check\_id: str,  
    button: ttk.Button,  
    worker: Callable\[\[\], ConnectionCheckResult\],  
    on\_complete: Callable\[\[ConnectionCheckResult\], None\],  
) \-\> None:  
    ...  
\`\`\`

Требования:

1\. Запретить двойной запуск одной проверки.  
2\. Disable только соответствующую кнопку.  
3\. Показывать \`Проверка...\` и stage.  
4\. Запускать worker в daemon thread или ThreadPoolExecutor.  
5\. Ни одного сетевого/CLI-вызова в UI thread.  
6\. Возвращать результат через \`self.after\`.  
7\. В \`finally\` восстанавливать кнопку.  
8\. После уничтожения frame не обращаться к widget.  
9\. Перехватывать все исключения и преобразовывать в safe \`ConnectionCheckResult\`.  
10\. Не печатать traceback в пользовательский терминал для ожидаемых ошибок подключения.

Для внутренних ошибок сохранить redacted traceback:

\`\`\`text  
debug/connection\_checks/internal\_error\_\<timestamp\>.log  
\`\`\`

\---

\# 4\. Использовать текущие значения формы

Все проверки должны строить временную конфигурацию из GUI fields.

Нельзя:

\`\`\`python  
BitlinkClient()  
ConfluenceClient()  
TelegramClient()  
TranscriptionClient()  
\`\`\`

если это приводит к чтению старых глобальных settings.

Использовать явные параметры, например:

\`\`\`python  
ConfluenceClient(  
    base\_url=current\_base\_url,  
    token=current\_token,  
    space\_key=current\_space\_key,  
    provider="rest",  
)  
\`\`\`

Если существующий конструктор не принимает provider/mode — расширить контракт.

Проверка должна работать до нажатия «Сохранить настройки».

После сохранения текущая и сохранённая конфигурации должны совпадать.

\---

\# 5\. Переработать блоки страницы настроек

У каждого блока добавить:

\- \`Режим / Provider\`;  
\- read-only status;  
\- \`Проверить\`;  
\- \`Копировать диагностику\`;  
\- timestamp последней проверки;  
\- краткую расшифровку результата.

Цвета:

\`\`\`text  
PASS — green  
FAIL/TIMEOUT — red  
MOCK — orange  
NOT\_IMPLEMENTED — orange  
NOT\_CONFIGURED/SKIPPED — gray  
CHECKING — blue  
\`\`\`

Не использовать зелёный цвет для mock.

\---

\# 6\. БИТ.Link

\#\# Текущее состояние

Real adapter не реализован. \`check\_connection()\` не выполняет HTTP-auth, а \`authenticate()\` без запроса устанавливает \`\_authenticated=True\`.

\#\# Требование

Пока реальный API-контракт не реализован:

\- provider \`mock\` → \`MOCK\`;  
\- provider \`real\` → \`NOT\_IMPLEMENTED\`;  
\- не показывать \`PASS\`;  
\- вывести:

\`\`\`text  
Реальный адаптер БИТ.Link не реализован. Проверка подключения невозможна.  
\`\`\`

Проверить наличие email/password можно только как config validation со статусом \`NOT\_IMPLEMENTED\`, а не \`PASS\`.

Не выполнять фиктивный \`authenticate()\`.

В отдельной diagnostic detail указать:

\`\`\`text  
Configuration fields present: yes/no  
API contract: not implemented  
Network call performed: no  
\`\`\`

\---

\# 7\. Newton — транскрибация видео

Это отдельный сервис от LLM «БИТ Ньютон».

\#\# Текущее состояние

\`TranscriptionClient.check\_connection()\` проверяет только наличие token/base URL. Real \`transcribe\_video()\` не реализован.

\#\# Требование

До реализации подтверждённого transcription adapter:

\- mock → \`MOCK\`;  
\- real → \`NOT\_IMPLEMENTED\`;  
\- наличие token/base URL не считать \`PASS\`;  
\- явно показать, что тестовая транскрибация не выполнялась.

Не смешивать:

\`\`\`text  
Newton transcription  
OneBit Newton LLM CLI  
\`\`\`

Переименовать блок GUI:

\`\`\`text  
Newton — транскрибация видео  
\`\`\`

LLM-блок оставить отдельно.

\---

\# 8\. Confluence

Добавить provider selector:

\`\`\`text  
Disabled  
Mock  
REST  
\`\`\`

\#\# Для Disabled

\`SKIPPED\`.

\#\# Для Mock

\`MOCK\`, не \`PASS\`.

\#\# Для REST

Использовать текущие поля формы и выполнить стадии:

\#\#\# Stage 1 — base URL

\- normalize trailing slash;  
\- проверить URL format;  
\- не допускать двойных slash.

\#\#\# Stage 2 — authentication

\`\`\`text  
GET /rest/api/user/current  
\`\`\`

Показать:

\- HTTP status;  
\- username/display name, если безопасно;  
\- latency.

\#\#\# Stage 3 — space access

Проверить текущий Space Key реальным REST-запросом.

При 404:

\`\`\`text  
CONFLUENCE\_SPACE\_NOT\_FOUND  
\`\`\`

При 403:

\`\`\`text  
CONFLUENCE\_SPACE\_FORBIDDEN  
\`\`\`

\#\#\# Stage 4 — parent page

Если Parent Page ID заполнен:

\`\`\`text  
GET /rest/api/content/{id}?expand=space,ancestors  
\`\`\`

Проверить:

\- page exists;  
\- page belongs to configured space;  
\- title получен;  
\- введённый Parent Page Title совпадает либо показать warning.

\#\#\# Итог

\`PASS\` только если auth \+ space \+ parent page проверки пройдены.

Если Parent Page ID пустой — \`NOT\_CONFIGURED\`, а не \`PASS\`, если публикация требует parent.

\#\# Отдельная кнопка write test

Добавить:

\`\`\`text  
Проверить право публикации  
\`\`\`

Только после явного подтверждения пользователя.

Сценарий:

1\. создать временную страницу под выбранным parent;  
2\. прочитать её обратно;  
3\. удалить её;  
4\. подтвердить create/read/delete;  
5\. при невозможности cleanup показать ID созданной страницы.

Если delete adapter ещё не реализован — сначала реализовать безопасное удаление временной страницы.

Стандартная кнопка «Проверить подключение» должна оставаться read-only и ничего не создавать.

\---

\# 9\. Telegram

Добавить mode selector:

\`\`\`text  
Disabled  
Mock  
Real  
\`\`\`

\#\# Disabled

\`SKIPPED\`.

\#\# Mock

\`MOCK\`.

\#\# Real — кнопка проверки

Использовать текущие Bot Token и Chat ID.

Стадии:

\#\#\# getMe

Проверить bot token:

\`\`\`text  
GET https://api.telegram.org/bot\<TOKEN\>/getMe  
\`\`\`

Сохранить safe bot username/id.

\#\#\# getChat

Проверить Chat ID:

\`\`\`text  
GET https://api.telegram.org/bot\<TOKEN\>/getChat?chat\_id=\<CHAT\_ID\>  
\`\`\`

Проверить:

\- чат существует;  
\- bot видит чат;  
\- тип чата;  
\- title/username без sensitive content.

\`PASS\` только после getMe \+ getChat.

\#\# Отдельная кнопка

\`\`\`text  
Отправить тестовое сообщение  
\`\`\`

Требует явного нажатия и отправляет:

\`\`\`text  
Тест подключения генератора протоколов. Сообщение можно удалить.  
\`\`\`

Показать message\_id.

Не отправлять сообщение при обычной проверке.

\---

\# 10\. БИТ Ньютон LLM CLI

Исправить все три кнопки:

\`\`\`text  
Проверить версию  
Проверить health  
Проверить токен и LLM  
\`\`\`

\#\# Version

Фактически выполнить \`newton version\` через \`run\_process\`.

\`PASS\` означает только:

\`\`\`text  
CLI найден и запускается  
\`\`\`

Не означает готовность LLM.

\#\# Health

Фактически выполнить \`newton health\`.

Проверить, что в результате найден сервис LLM Summarize и он healthy.

\`PASS\` означает только состояние сервисов. В сообщении обязательно:

\`\`\`text  
Health не проверяет токен и право создания LLM-задачи.  
\`\`\`

\#\# Token \+ LLM

Выполнить real minimal generation.

Стадии:

\`\`\`text  
provider\_config  
cli\_version  
cli\_execution  
output\_check  
json\_parse  
schema\_validation  
\`\`\`

Schema:

\`\`\`json  
{  
  "type": "object",  
  "properties": {  
    "status": {"type": "string", "const": "ok"}  
  },  
  "required": \["status"\],  
  "additionalProperties": false  
}  
\`\`\`

\`PASS\` только при schema-valid \`{"status":"ok"}\`.

Ошибки \`AUTH\_TOKEN\_MALFORMED\`, \`AUTH\_FAILED\`, \`AUTH\_FORBIDDEN\` отображать пользователю без traceback.

Использовать новый binary \`run\_process\`.

Запрещено прямое \`subprocess.run(..., text=True)\`.

\#\# Callback

Все результаты возвращать через единый \`\_run\_on\_ui\`, без \`self.root\`.

\---

\# 11\. OpenAI-compatible LLM

Перевести \`\_test\_openai\_llm()\` на общий async runner.

Стадии:

1\. validate fields;  
2\. connection/auth;  
3\. model availability или минимальная completion;  
4\. structured JSON generation;  
5\. schema validation.

Использовать unsaved URL/key/model.

Не блокировать GUI.

Кнопка должна:

\- становиться disabled во время проверки;  
\- показывать stage;  
\- восстанавливаться при любом результате.

HTTP 401/403/404/405/429/5xx/timeout различать.

\---

\# 12\. Кнопка «Проверить все подключения»

Добавить вверху страницы.

Она запускает проверки последовательно или с ограниченным пулом, чтобы не перегружать GUI.

Проверять только активные providers.

Не выполнять действия с побочным эффектом:

\- не публиковать Confluence page;  
\- не отправлять Telegram message;  
\- не обрабатывать файлы.

Результат — таблица:

| Сервис | Provider | Конфигурация | Connectivity | Functional | Итог | Проверено |  
|---|---|---|---|---|---|---|

Пример:

\`\`\`text  
БИТ.Link | mock | заполнено | не проверялось | не проверялось | MOCK  
Newton transcription | real | заполнено | не проверялось | не реализовано | NOT\_IMPLEMENTED  
Confluence | rest | заполнено | PASS | parent PASS | PASS  
Telegram | real | заполнено | getMe PASS | getChat PASS | PASS  
LLM | onebit\_newton\_cli | заполнено | version/health PASS | schema PASS | PASS  
\`\`\`

Общий статус:

\`\`\`text  
READY  
PARTIALLY\_READY  
NOT\_READY  
DEMO  
\`\`\`

Правила:

\- обязательный active LLM должен быть \`PASS\`;  
\- mock LLM → \`DEMO\`;  
\- Confluence может быть \`SKIPPED\` только при dry-run/disabled publication;  
\- Telegram disabled не блокирует READY;  
\- БИТ.Link/Newton transcription \`NOT\_IMPLEMENTED\` не блокируют local TXT, но блокируют соответствующие source types.

\---

\# 13\. Диагностика

Добавить:

\`\`\`text  
Копировать все результаты  
Сохранить отчёт  
\`\`\`

Путь:

\`\`\`text  
debug/connection\_checks/connection\_check\_\<timestamp\>.json  
\`\`\`

Содержимое:

\- safe settings summary;  
\- provider modes;  
\- результаты;  
\- stages;  
\- statuses;  
\- latency;  
\- codes;  
\- recommendations;  
\- app version/head, если доступно.

Запрещено сохранять:

\- tokens;  
\- passwords;  
\- API keys;  
\- Authorization header;  
\- Telegram bot URL с token;  
\- полный CLI env.

Добавить secret redaction для всех текущих значений формы.

\---

\# 14\. Обновление readiness после сохранения

После «Сохранить настройки»:

1\. reload \`.env\`;  
2\. reload \`settings\`;  
3\. \`reload\_runtime\_config()\`;  
4\. сбросить старые результаты, если изменился config fingerprint;  
5\. обновить readiness panel;  
6\. не показывать старый PASS для новой конфигурации;  
7\. restart не требуется.

Config fingerprint строить из non-secret normalized settings \+ hash secrets, но сами secrets не сохранять.

\---

\# 15\. Обязательные тесты

Создать:

\`\`\`text  
tests/test\_settings\_async\_checks.py  
tests/test\_connection\_check\_results.py  
tests/test\_settings\_service\_checks.py  
tests/test\_settings\_check\_all.py  
\`\`\`

Тесты:

\`\`\`text  
test\_settings\_frame\_uses\_after\_not\_missing\_root  
test\_version\_result\_returns\_to\_ui\_thread  
test\_health\_result\_returns\_to\_ui\_thread  
test\_token\_error\_returns\_to\_ui\_thread  
test\_buttons\_reenabled\_after\_success  
test\_buttons\_reenabled\_after\_failure  
test\_buttons\_reenabled\_after\_timeout  
test\_destroyed\_frame\_ignores\_late\_callback  
test\_unsaved\_bitlink\_values\_are\_used  
test\_unsaved\_newton\_transcription\_values\_are\_used  
test\_unsaved\_confluence\_values\_are\_used  
test\_unsaved\_telegram\_values\_are\_used  
test\_unsaved\_onebit\_values\_are\_used  
test\_unsaved\_openai\_values\_are\_used  
test\_mock\_is\_not\_pass  
test\_bitlink\_real\_is\_not\_implemented  
test\_newton\_transcription\_real\_is\_not\_implemented  
test\_confluence\_checks\_current\_user\_space\_parent  
test\_confluence\_401\_is\_auth\_failed  
test\_confluence\_403\_is\_forbidden  
test\_confluence\_404\_parent\_not\_found  
test\_telegram\_checks\_get\_me\_and\_get\_chat  
test\_telegram\_check\_does\_not\_send\_message  
test\_telegram\_test\_message\_is\_explicit  
test\_onebit\_version\_does\_not\_claim\_llm\_ready  
test\_onebit\_health\_does\_not\_claim\_token\_valid  
test\_onebit\_schema\_smoke\_is\_required\_for\_pass  
test\_openai\_check\_runs\_off\_ui\_thread  
test\_check\_all\_skips\_disabled\_services  
test\_check\_all\_reports\_mock\_as\_demo  
test\_check\_all\_local\_txt\_ignores\_unimplemented\_bitlink  
test\_diagnostics\_redacts\_all\_form\_secrets  
test\_changed\_config\_invalidates\_previous\_pass  
\`\`\`

Не использовать \`assert True\`.

Не подменять весь check pipeline одним mock result.

\---

\# 16\. Windows GUI E2E

Запустить через:

\`\`\`cmd  
call start\_app.bat  
\`\`\`

Проверить:

\#\# Общая работа

1\. Страница открывается.  
2\. Каждая кнопка реагирует сразу.  
3\. GUI не зависает.  
4\. Во время проверки виден stage.  
5\. После проверки кнопка активна.  
6\. В терминале нет traceback.  
7\. В частности нет:

\`\`\`text  
AttributeError: SettingsFrame has no attribute root  
UnicodeDecodeError  
NoneType object is not subscriptable  
\`\`\`

\#\# БИТ.Link

\- mock показывает \`MOCK\`, не success;  
\- real показывает \`NOT\_IMPLEMENTED\`.

\#\# Newton transcription

\- mock показывает \`MOCK\`;  
\- real показывает \`NOT\_IMPLEMENTED\`.

\#\# Confluence

\- проверить current user;  
\- проверить space;  
\- проверить parent page;  
\- неверный token → понятный 401/403;  
\- неверный parent → 404;  
\- текущие несохранённые значения используются.

\#\# Telegram

\- getMe;  
\- getChat;  
\- неверный chat ID → ошибка;  
\- обычная проверка ничего не отправляет;  
\- отдельная кнопка отправляет тестовое сообщение.

\#\# БИТ Ньютон LLM

\- version возвращается в GUI;  
\- health возвращается в GUI;  
\- невалидный token показывает \`AUTH\_TOKEN\_MALFORMED\`;  
\- кнопка не виснет;  
\- действующий token при наличии проходит schema test.

\#\# OpenAI

\- timeout не замораживает окно;  
\- error возвращается в GUI.

\#\# Check all

\- формируется полная матрица;  
\- отчёт копируется;  
\- отчёт сохраняется;  
\- secrets отсутствуют.

Создать:

\`\`\`text  
docs/opencode/validations/SETTINGS-CONNECTIONS-WINDOWS-E2E-\<SHA\>.md  
\`\`\`

\---

\# 17\. Manifest

Обновить:

\`\`\`text  
active\_task\_id \= TASK-2026-08-02-settings-real-connection-checks  
active\_task\_file \= docs/opencode/tasks/TASK-2026-08-02-settings-real-connection-checks.md  
status \= in\_progress  
validation\_state \= implementing\_fixes  
\`\`\`

Добавить:

\`\`\`text  
BB-CRIT-092 — worker callbacks use missing SettingsFrame.root  
BB-CRIT-093 — service checks ignore unsaved form values  
BB-CRIT-094 — mock is shown as successful connection  
BB-CRIT-095 — Bitlink real adapter falsely appears checkable  
BB-CRIT-096 — Newton transcription only validates config presence  
BB-CRIT-097 — Confluence check does not validate space/parent/current form  
BB-CRIT-098 — Telegram check does not validate target chat  
BB-CRIT-099 — OpenAI check blocks Tkinter main thread  
BB-MAJ-100 — no unified connection result model  
BB-MAJ-101 — boolean result cannot express provider states  
BB-MAJ-102 — buttons remain disabled after callback errors  
BB-MAJ-103 — no Check All/readiness matrix  
BB-MAJ-104 — no persistent safe diagnostic report  
\`\`\`

Статус предыдущего Windows encoding task менять только по фактической проверке.

\`BB-CRIT-063\` оставить \`USER\_ACTION\_REQUIRED\` до подтверждения ротации раскрытого токена.

\---

\# 18\. Обязательные команды

\`\`\`bash  
python \-m compileall .  
python \-m json.tool docs/opencode/manifest.json  
pytest \-q  
pytest \-q tests/test\_settings\_async\_checks.py  
pytest \-q tests/test\_connection\_check\_results.py  
pytest \-q tests/test\_settings\_service\_checks.py  
pytest \-q tests/test\_settings\_check\_all.py  
ruff check .  
mypy . \--ignore-missing-imports  
\`\`\`

Windows:

\`\`\`cmd  
call start\_app.bat \--startup-check  
\`\`\`

\---

\# 19\. Формат ответа OpenCode

Предоставить:

1\. exact \`headRefOid\`;  
2\. Draft PR URL;  
3\. workflow run ID/URL;  
4\. результаты обязательных команд;  
5\. список созданных файлов;  
6\. описание общего async runner;  
7\. подтверждение удаления всех \`self.root.after\` из SettingsFrame;  
8\. таблицу фактических проверок по каждому сервису;  
9\. результат использования несохранённых значений;  
10\. результат БИТ Ньютон version;  
11\. результат health;  
12\. результат invalid-token test;  
13\. результат valid-token schema test либо \`NOT\_RUN: valid token unavailable\`;  
14\. результат Confluence auth/space/parent;  
15\. результат Telegram getMe/getChat;  
16\. результат Check All;  
17\. путь к JSON diagnostics;  
18\. путь к Windows E2E validation;  
19\. подтверждение отсутствия secrets;  
20\. оставшиеся ограничения.

Не считать задачу выполненной только по unit tests.

PR оставить Draft.  
Merge не выполнять.  
\`accepted\` не устанавливать.  
