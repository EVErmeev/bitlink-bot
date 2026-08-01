\# TASK-2026-08-01-preflight-api-regression

\#\# Назначение

Исправить runtime-регрессию в GUI-запуске обработки и привести preflight API, source-aware demo logic и production readiness к одному согласованному контракту.

\#\# Репозиторий

\- Repository: \`EVErmeev/bitlink-bot\`  
\- Branch: \`fix/audit-e7cc95f\`  
\- Draft PR: \`https://github.com/EVErmeev/bitlink-bot/pull/1\`  
\- Проверенный head: \`3716058077904cb0e560db5f102281411b91ecb1\`

PR оставить Draft. Merge не выполнять.

\#\# 1\. Подтверждённая блокирующая ошибка

При нажатии «Запустить обработку» пользователь получает:

\`\`\`text  
TypeError: run\_preflight() got an unexpected keyword argument 'source\_types'  
\`\`\`

Фактический вызов в \`ui/source\_queue\_frame.py\`:

\`\`\`python  
source\_types \= list(set(i.source\_type or "local\_transcript" for i in items))  
preflight \= run\_preflight(items, config, source\_types=source\_types)  
\`\`\`

Фактическая сигнатура в \`services/preflight\_service.py\`:

\`\`\`python  
def run\_preflight(items: list\[BatchItem\], config: RuntimeConfig) \-\> dict:  
\`\`\`

GUI callback падает до запуска worker. Ни один этап pipeline не выполняется.

\#\# 2\. Канонический контракт preflight

Оставить один канонический API:

\`\`\`python  
def run\_preflight(items: list\[BatchItem\], config: RuntimeConfig) \-\> PreflightReport:  
    ...  
\`\`\`

\`run\_preflight()\` обязан самостоятельно определять тип источника из каждого \`BatchItem.source\_type\`.

Удалить из \`SourceQueueFrame.\_start\_processing()\`:

\`\`\`python  
source\_types \= ...  
source\_types=source\_types  
\`\`\`

Не добавлять неиспользуемый optional-параметр только ради подавления TypeError.

Добавить типизированную модель \`PreflightReport\` через dataclass или TypedDict. Поля:

\- \`passed\`;  
\- \`has\_warnings\`;  
\- \`has\_blocking\`;  
\- \`errors\`;  
\- \`warnings\`;  
\- \`items\_checked\`;  
\- \`items\_total\`;  
\- \`effective\_services\_by\_item\`;  
\- \`forced\_dry\_run\_items\`.

\#\# 3\. Исправить source-aware demo logic в preflight

В текущем \`\_check\_item()\` используется старый глобальный вызов:

\`\`\`python  
config.is\_demo\_mode()  
\`\`\`

Это противоречит новой source-aware логике.

Заменить на проверку конкретного источника:

\`\`\`python  
config.is\_demo\_for\_source(item.source\_type)  
\`\`\`

или эквивалентную проверку через \`get\_effective\_services(item.source\_type)\`.

Для local transcript:

\- Newton не применяется;  
\- BIT.Link не применяется;  
\- их mock-mode не должен включать dry-run и не должен давать DEMO.

\#\# 4\. Исправить \`RuntimeConfig.is\_demo\_for\_source()\`

Текущая реализация исключает \`newton\` и \`bitlink\` из mock-services независимо от типа источника. Это неправильно для local video и bitlink sources.

Правильная логика:

1\. \`get\_effective\_services(source\_type)\` возвращает \`not\_applicable\` для неиспользуемых сервисов.  
2\. Demo определяется по любому применимому сервису со значением \`mock\`.  
3\. Не использовать отдельное исключение \`k not in ("newton", "bitlink")\`.

Ожидаемое поведение:

\- local transcript \+ real LLM \+ mock Newton \+ mock BIT.Link → не DEMO;  
\- local video \+ mock Newton → DEMO;  
\- bitlink source \+ mock BIT.Link → DEMO;  
\- local transcript \+ mock LLM → DEMO.

\#\# 5\. Исправить production readiness

Текущий \`is\_production\_blocked()\` проверяет в основном названия режимов и может вернуть production-ready при пустых credentials.

Создать:

\`\`\`python  
def get\_production\_readiness(  
    self,  
    source\_type: str,  
    \*,  
    dry\_run: bool,  
    send\_telegram: bool,  
) \-\> dict:  
    ...  
\`\`\`

Проверять:

\#\#\# Local transcript

\- LLM real;  
\- LLM API URL указан;  
\- LLM API key указан;  
\- LLM model указан;  
\- connection test успешен либо ещё не выполнен и это явно отражено;  
\- Confluence URL/token/space/parent только при \`dry\_run=False\` и provider=REST;  
\- Telegram token/chat только при \`send\_telegram=True\` и mode=real;  
\- Newton и BIT.Link — not applicable.

Banner не должен показывать \`PRODUCTION\`, если обязательные credentials отсутствуют.

Правильный статус:

\`\`\`text  
PRODUCTION BLOCKED: LLM API URL/API Key не настроены  
\`\`\`

\#\# 6\. Обработка исключений GUI callback

\`\_start\_processing()\` не должен оставлять ошибку только в консоли.

Оборачивать запуск preflight в \`try/except\`.

При внутренней ошибке:

\- не запускать worker;  
\- вернуть Start button в normal state;  
\- показать копируемый dialog;  
\- вывести exception type, message и traceback;  
\- сохранить \`debug/runtime\_error.log\`;  
\- сохранить event \`preflight\_internal\_error\`;  
\- не показывать «Проверка пройдена».

\#\# 7\. Обязательные regression tests

Добавить минимум:

\`\`\`text  
test\_run\_preflight\_public\_signature\_accepts\_items\_and\_config  
test\_source\_queue\_start\_processing\_does\_not\_pass\_source\_types\_kwarg  
test\_source\_queue\_start\_processing\_reaches\_preflight\_without\_type\_error  
test\_successful\_preflight\_starts\_worker\_after\_one\_click  
test\_preflight\_internal\_exception\_is\_shown\_and\_logged  
test\_local\_transcript\_real\_llm\_ignores\_mock\_newton\_and\_bitlink  
test\_local\_transcript\_real\_llm\_does\_not\_force\_dry\_run\_from\_irrelevant\_mocks  
test\_local\_video\_mock\_newton\_is\_demo  
test\_bitlink\_source\_mock\_bitlink\_is\_demo  
test\_production\_readiness\_blocks\_missing\_llm\_url  
test\_production\_readiness\_blocks\_missing\_llm\_key  
test\_production\_readiness\_blocks\_missing\_llm\_model  
test\_banner\_never\_shows\_production\_with\_missing\_required\_credentials  
\`\`\`

Ключевой тест должен вызывать реальный \`SourceQueueFrame.\_start\_processing()\` с настоящей сигнатурой \`run\_preflight\`, а не подменять её mock-функцией, принимающей \`\*\*kwargs\`.

\#\# 8\. Контрактный тест между UI и service

Добавить тест, который использует \`inspect.signature()\` либо статическую проверку и гарантирует, что все keyword-аргументы вызова соответствуют публичной сигнатуре.

Предпочтительнее прямой integration test callback → real preflight.

\#\# 9\. Ручной GUI E2E

Через \`start\_app.bat\`:

1\. Запустить приложение.  
2\. Добавить локальный TXT.  
3\. Нажать «Запустить обработку» один раз.  
4\. Убедиться, что отсутствует traceback \`unexpected keyword argument\`.  
5\. В demo-profile получить предупреждение и после подтверждения увидеть \`worker\_started\` и реальные stages.  
6\. В local\_txt\_production без LLM credentials получить \`PRODUCTION BLOCKED\`, а не Python traceback.  
7\. При корректном real LLM получить переход к processing pipeline.

Сохранить:

\`\`\`text  
docs/opencode/validations/GUI-PREFLIGHT-REGRESSION-\<HEAD\_SHORT\_SHA\>.md  
\`\`\`

В validation-файле указать:

\- Windows version;  
\- точный head SHA;  
\- профиль;  
\- effective services;  
\- один клик или два;  
\- первый stage;  
\- итоговый status;  
\- traceback отсутствует;  
\- путь к event log.

\#\# 10\. Обновить manifest

Добавить замечания:

\- \`BB-CRIT-051\` — несовместимая сигнатура \`run\_preflight\` ломает GUI;  
\- \`BB-CRIT-052\` — preflight использует глобальный \`is\_demo\_mode\` вместо source-aware;  
\- \`BB-CRIT-053\` — production readiness не проверяет credentials;  
\- \`BB-MAJ-054\` — исключения GUI callback остаются только в консоли;  
\- \`BB-MAJ-055\` — тесты не покрывают реальный UI/service contract.

До успешного GUI E2E статус этих пунктов не может быть \`FIXED\`.

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

Дополнительно выполнить отдельный regression test:

\`\`\`bash  
pytest \-q tests/test\_preflight\_regression.py  
\`\`\`

\#\# 12\. Формат ответа OpenCode

Предоставить:

1\. Новый \`headRefOid\`.  
2\. URL Draft PR.  
3\. Workflow run ID/URL.  
4\. Результаты обязательных команд.  
5\. Результат \`tests/test\_preflight\_regression.py\`.  
6\. Подтверждение фактической сигнатуры \`run\_preflight\`.  
7\. Подтверждение, что GUI callback больше не передаёт \`source\_types\`.  
8\. Результат ручного GUI E2E.  
9\. Первый полученный processing stage.  
10\. Путь к validation-файлу.  
11\. Путь к \`runtime\_error.log\`, если проверялся негативный сценарий.  
12\. Оставшиеся ограничения.

PR оставить Draft.  
Merge не выполнять.  
\`accepted\` не устанавливать.  
