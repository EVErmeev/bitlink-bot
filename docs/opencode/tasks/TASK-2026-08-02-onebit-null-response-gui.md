\# TASK-2026-08-02-onebit-null-response-gui

\#\# Цель

Исправить GUI и runtime-проверку \`onebit\_newton\_cli\`, устранить ошибку:

\`\`\`text  
'NoneType' object is not subscriptable  
\`\`\`

и подтвердить реальную генерацию БИТ Ньютон от настроек GUI до обработки local TXT.

\#\# Репозиторий

\- Repository: \`EVErmeev/bitlink-bot\`  
\- Branch: \`fix/audit-e7cc95f\`  
\- Draft PR: \`https://github.com/EVErmeev/bitlink-bot/pull/1\`  
\- Base head: \`e454652b125093a0da5648d9bcbccccedd740324\`

Перед работой:

\`\`\`bash  
gh pr view 1 \--json headRefOid,url,isDraft,statusCheckRollup  
\`\`\`

PR оставить Draft. Merge и \`accepted\` запрещены.

\#\# Входные факты

\- CLI: \`C:\\Users\\egore\\AppData\\Local\\NewtonCLI\\newton.cmd\`  
\- Version: \`2026.07.13\`  
\- Transport: native Windows \`.cmd\`  
\- Health: \`7/7 healthy\`  
\- Ошибка real smoke-test: \`'NoneType' object is not subscriptable\`  
\- Отдельного token field в LLM-панели нет.  
\- OpenAI-поля остаются серыми вместо полного скрытия.

\#\# 1\. Переработать LLM GUI на provider panels

Создать отдельные панели:

\`\`\`text  
Mock  
БИТ Ньютон  
OpenAI-compatible  
\`\`\`

При переключении показывать только активную панель через \`grid\_remove()\`/\`pack\_forget()\`.

\#\#\# Панель БИТ Ньютон

Поля:

\- \`Токен БИТ Ньютон\`;  
\- показать/скрыть;  
\- CLI path;  
\- transport: native/WSL;  
\- model: llama/gpt4;  
\- timeout;  
\- \`Обнаружить CLI\`;  
\- \`Проверить версию\`;  
\- \`Проверить health\`;  
\- \`Проверить токен и LLM\`;  
\- \`Копировать диагностику\`;  
\- read-only status.

OpenAI Base URL/API Key/Model в этой панели не показывать.

\#\#\# Панель OpenAI-compatible

Показывать Base URL, API Key, Model, API paths, timeout, REST connection test и JSON smoke-test.

\#\#\# Панель Mock

Показывать demo-warning и forced dry-run.

\#\# 2\. Добавить отдельный токен

Использовать:

\`\`\`text  
ONEBIT\_LLM\_TOKEN  
\`\`\`

Fallback:

\`\`\`python  
ONEBIT\_LLM\_TOKEN or NEWTON\_TOKEN  
\`\`\`

GUI должен читать и сохранять \`ONEBIT\_LLM\_TOKEN\`.

Требования:

\- unsaved значение используется проверками;  
\- токен передаётся только через environment;  
\- токен не попадает в args, логи, GUI diagnostics, git и artifacts;  
\- ранее раскрытый токен не использовать.

\#\# 3\. Разделить проверки

\#\#\# Обнаружить CLI

Проверяет только path и transport.

\#\#\# Проверить версию

Выполняет только \`newton version\`. Не заявляет готовность LLM.

\#\#\# Проверить health

Выполняет \`newton health\`, показывает состояние LLM Summarize и пояснение:

\`\`\`text  
Health не проверяет токен и создание LLM-задачи.  
\`\`\`

\#\#\# Проверить токен и LLM

Выполняет реальную minimal generation со схемой:

\`\`\`json  
{  
  "type": "object",  
  "properties": {"status": {"type": "string"}},  
  "required": \["status"\]  
}  
\`\`\`

Проверяет стадии:

\`\`\`text  
provider\_config  
cli\_start  
task\_create  
task\_id\_received  
polling  
result\_received  
output\_file\_read  
json\_extract  
json\_parse  
schema\_validation  
completed  
\`\`\`

\#\# 4\. Устранить утечку внутренних исключений

Создать типизированную ошибку:

\`\`\`python  
class OneBitProviderError(RuntimeError):  
    stage: str  
    code: str  
    safe\_message: str  
    exit\_code: int | None  
    response\_type: str | None  
    safe\_stdout: str  
    safe\_stderr: str  
\`\`\`

Пользователь не должен видеть необработанные \`NoneType\`, \`KeyError\`, \`AttributeError\`, traceback или токен.

Оригинал сохранять только в redacted debug log.

\#\# 5\. Добавить subprocess diagnostics

Фиксировать:

\- command без secrets;  
\- stage;  
\- exit code;  
\- timeout;  
\- safe stdout;  
\- safe stderr;  
\- output file exists;  
\- output size;  
\- response type;  
\- parse/schema result.

Проверять output file до чтения:

\- существует;  
\- не пустой;  
\- содержит один JSON object или один fenced JSON block.

Несколько JSON blocks → \`MULTIPLE\_JSON\_BLOCKS\`.

\#\# 6\. Установить точную причину \`NoneType\`

Провести ручное воспроизведение тем же CLI path и новым токеном.

Зафиксировать:

\- exit code;  
\- safe stdout/stderr;  
\- output file;  
\- stage ошибки;  
\- дефект CLI или null-response сервиса;  
\- token/permission/model/arguments как возможные причины.

Не объявлять причину доказанной только по тексту \`NoneType\`.

\#\# 7\. Fallback при дефекте внешнего CLI

Если официальный CLI подтверждённо падает внутри собственного кода при корректных настройках:

1\. не изменять файл в \`AppData\`;  
2\. подтвердить фактический HTTP-контракт по установленному CLI;  
3\. только после подтверждения реализовать \`onebit\_newton\_api\`;  
4\. не угадывать endpoint, request и response structures.

\#\# 8\. Сохранение и runtime reload

Для CLI сохранять:

\`\`\`text  
LLM\_PROVIDER=onebit\_newton\_cli  
LLM\_MOCK=false  
LLM\_MODEL=gpt4|llama  
ONEBIT\_LLM\_TOKEN=\<secret\>  
ONEBIT\_CLI\_PATH=\<path\>  
ONEBIT\_CLI\_TRANSPORT=native|wsl  
ONEBIT\_CLI\_TIMEOUT\_SECONDS=\<int\>  
\`\`\`

После сохранения:

1\. reload \`.env\`;  
2\. reload \`settings\`;  
3\. \`reload\_runtime\_config()\`;  
4\. обновить banner/readiness;  
5\. restart не требуется.

\#\# 9\. Preflight/readiness

Для CLI проверять token, CLI path, transport, model, version, health, real smoke generation и schema validation.

OpenAI URL/Key не использовать.

Коды ошибок:

\`\`\`text  
ONEBIT\_TOKEN\_MISSING  
ONEBIT\_CLI\_NOT\_FOUND  
ONEBIT\_HEALTH\_FAILED  
ONEBIT\_SMOKE\_NOT\_PASSED  
ONEBIT\_SCHEMA\_FAILED  
\`\`\`

\#\# 10\. Копируемая диагностика

Формат:

\`\`\`text  
Provider  
Stage  
Code  
CLI path  
Transport  
Model  
Exit code  
Output file exists  
Output size  
Response type  
Safe message  
Recommendation  
\`\`\`

Сохранять:

\`\`\`text  
debug/llm\_checks/\<timestamp\>/onebit\_llm\_diagnostic.json  
\`\`\`

Credentials → \`\<redacted\>\`.

\#\# 11\. Обязательные тесты

Создать:

\`\`\`text  
tests/test\_onebit\_gui\_panels.py  
tests/test\_onebit\_diagnostics.py  
tests/test\_onebit\_provider\_smoke.py  
tests/test\_onebit\_settings\_integration.py  
\`\`\`

Тесты:

\`\`\`text  
test\_onebit\_panel\_hides\_openai\_fields  
test\_openai\_panel\_hides\_onebit\_fields  
test\_onebit\_panel\_contains\_token\_field  
test\_unsaved\_onebit\_token\_is\_used  
test\_version\_does\_not\_claim\_llm\_ready  
test\_health\_does\_not\_claim\_token\_valid  
test\_check\_llm\_runs\_real\_generate  
test\_none\_response\_is\_provider\_error\_not\_typeerror  
test\_missing\_output\_file\_is\_diagnostic  
test\_invalid\_json\_is\_diagnostic  
test\_multiple\_json\_blocks\_are\_rejected  
test\_schema\_invalid\_is\_diagnostic  
test\_token\_is\_redacted  
test\_settings\_save\_uses\_cli\_model  
test\_hidden\_openai\_values\_are\_not\_active  
test\_settings\_reload\_runtime\_provider  
test\_client\_factory\_receives\_onebit\_config  
test\_preflight\_requires\_real\_smoke\_pass  
\`\`\`

Запрещены \`assert True\` и тесты, заменяющие pipeline одной заглушкой.

\#\# 12\. Windows GUI E2E

Через \`start\_app.bat\`:

1\. выбрать БИТ Ньютон;  
2\. убедиться, что OpenAI panel скрыт;  
3\. ввести новый токен;  
4\. обнаружить CLI;  
5\. проверить version;  
6\. проверить health;  
7\. проверить real LLM;  
8\. получить schema-valid \`{"status":"ok"}\`;  
9\. сохранить настройки;  
10\. без restart открыть очередь;  
11\. добавить local TXT;  
12\. включить dry-run;  
13\. запустить одним кликом;  
14\. получить \`worker\_started\`;  
15\. получить LLM stage;  
16\. получить protocol artifacts;  
17\. убедиться, что \`NoneType\` отсутствует;  
18\. убедиться, что токен отсутствует в логах.

Создать:

\`\`\`text  
docs/opencode/validations/ONEBIT-NULL-RESPONSE-E2E-\<SHA\>.md  
\`\`\`

\#\# 13\. Проверки

\`\`\`bash  
python \-m compileall .  
python \-m json.tool docs/opencode/manifest.json  
pytest \-q  
pytest \-q tests/test\_onebit\_gui\_panels.py  
pytest \-q tests/test\_onebit\_diagnostics.py  
pytest \-q tests/test\_onebit\_provider\_smoke.py  
pytest \-q tests/test\_onebit\_settings\_integration.py  
ruff check .  
mypy . \--ignore-missing-imports  
\`\`\`

Windows:

\`\`\`cmd  
call start\_app.bat \--startup-check  
\`\`\`

\#\# 14\. Manifest

\`\`\`text  
active\_task\_id \= TASK-2026-08-02-onebit-null-response-gui  
active\_task\_file \= docs/opencode/tasks/TASK-2026-08-02-onebit-null-response-gui.md  
status \= in\_progress  
validation\_state \= implementing\_fixes

BB-CRIT-076..080 \= IN\_PROGRESS  
BB-MAJ-081..083 \= IN\_PROGRESS  
BB-CRIT-063 \= USER\_ACTION\_REQUIRED  
\`\`\`

\#\# 15\. Ответ OpenCode

Предоставить:

1\. exact headRefOid;  
2\. Draft PR URL;  
3\. workflow run;  
4\. результаты команд;  
5\. созданные test files;  
6\. provider panels;  
7\. отдельный token field;  
8\. version result;  
9\. health result с оговоркой;  
10\. доказанную причину \`NoneType\`;  
11\. safe diagnostic;  
12\. real JSON smoke-test;  
13\. local TXT dry-run;  
14\. first processing stage;  
15\. artifacts path;  
16\. E2E validation path;  
17\. подтверждение отсутствия токена;  
18\. ограничения.

PR оставить Draft. Merge и \`accepted\` запрещены.  
