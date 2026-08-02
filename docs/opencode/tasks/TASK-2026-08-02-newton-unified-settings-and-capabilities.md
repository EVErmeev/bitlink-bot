\# TASK-2026-08-02-newton-unified-settings-and-capabilities

\#\# 1\. Цель

Переработать страницу «Настройки» после подтверждения рабочего токена БИТ Ньютон и привести конфигурацию к фактической архитектуре приложения.

Токен больше не считать техническим блокером, если реальный \`newton summarize\` проходит успешно.

Результат задачи:

1\. Один общий блок подключения «БИТ Ньютон CLI» с единым токеном и единым путём CLI.  
2\. Отдельные capability-проверки LLM Summary и транскрибации.  
3\. Реальная транскрибация через установленный Newton CLI.  
4\. Единые provider-переменные, совпадающие с RuntimeConfig.  
5\. Полностью thread-safe проверки подключений.  
6\. Readiness с учётом типа источника: локальный TXT, локальное видео, БИТ.Link.  
7\. Windows GUI E2E через \`start\_app.bat\`.

\#\# 2\. Репозиторий

\- Repository: \`EVErmeev/bitlink-bot\`  
\- Branch: \`fix/audit-e7cc95f\`  
\- Draft PR: \`https://github.com/EVErmeev/bitlink-bot/pull/1\`  
\- Проверенный base head: \`adac9395d2b30672075f6803818d0f8e20c73cb4\`

Перед началом:

\`\`\`bash  
gh pr view 1 \--json headRefOid,url,isDraft,statusCheckRollup  
\`\`\`

Если head изменился, сначала сравнить его с base head.

PR оставить Draft. Merge не выполнять. \`accepted\` не устанавливать.

\#\# 3\. Что считать исправленным

Пользователь подтвердил, что рабочий токен теперь доступен функционалу БИТ Ньютон.

Поэтому:

\- не требовать обязательного JWT-формата из трёх сегментов;  
\- не отклонять токен локально по длине, числу точек или форме;  
\- корректность подтверждать только реальным вызовом capability;  
\- удалить название \`JWT-токен БИТ Ньютон CLI\` и подсказку про три сегмента;  
\- использовать название \`Токен БИТ Ньютон CLI\`.

PASS для LLM допустим только после реальной schema-valid генерации.

\#\# 4\. Подтверждённые проблемы текущего head

\#\#\# 4.1. Дублирование Newton

Сейчас есть два независимых набора настроек:

\- \`Newton — транскрибация видео\`: \`NEWTON\_TOKEN\`, \`NEWTON\_PATH\`, \`NEWTON\_BASE\_URL\`;  
\- \`Нейросеть / LLM\`: \`ONEBIT\_LLM\_TOKEN\`, \`ONEBIT\_CLI\_PATH\`, модель и timeout.

Это один Newton CLI. Token и CLI path должны задаваться один раз.

\#\#\# 4.2. Конфликт env-переменных

Runtime молча использует:

\`\`\`text  
ONEBIT\_LLM\_TOKEN or NEWTON\_TOKEN  
\`\`\`

и отдельно:

\`\`\`text  
ONEBIT\_CLI\_PATH / NEWTON\_PATH  
\`\`\`

Если значения различаются, может использоваться старый token/path без предупреждения.

\#\#\# 4.3. Provider GUI не совпадает с runtime

GUI сохраняет \`BITLINK\_PROVIDER\`, \`NEWTON\_PROVIDER\`, \`TELEGRAM\_PROVIDER\`, но RuntimeConfig для части сервисов продолжает строить режим из \`BITLINK\_MOCK\`, \`NEWTON\_MOCK\`, \`TELEGRAM\_MOCK\`, \`TELEGRAM\_ENABLED\`.

Выбранный в форме режим может не стать фактическим runtime mode.

\#\#\# 4.4. Worker обращается к Tkinter

Worker-функции продолжают вызывать \`Entry.get()\`, \`StringVar.get()\`, \`\_get\_provider()\`, \`\_get\_cli\_path()\`, \`\_run\_on\_ui()\` и messagebox.

Все Tkinter-операции должны выполняться только в UI thread.

\#\#\# 4.5. ConnectionCheckRunner перезаписывает callback

В runner хранится одно поле \`\_on\_complete\`. При параллельных проверках новый callback заменяет предыдущий.

\#\#\# 4.6. OpenAI individual check остаётся синхронным

Индивидуальная \`\_test\_openai\_llm()\` выполняет network-вызовы в UI callback.

\#\#\# 4.7. Copy diagnostics имеет side effects

При отсутствии сохранённого результата копирование снова запускает \`newton version\` и \`newton health\`.

\#\#\# 4.8. Readiness не учитывает сценарий

БИТ.Link и транскрибация не нужны для локального TXT. Их \`NOT\_IMPLEMENTED\` не должен блокировать обработку TXT.

\#\#\# 4.9. Реальная транскрибация отсутствует

Необходимо использовать установленный Newton CLI, а не придумывать неподтверждённый REST API.

\#\# 5\. Новая структура Settings

\#\#\# 5.1. Общий блок «БИТ Ньютон CLI»

Поля:

\- Токен БИТ Ньютон CLI;  
\- показать/скрыть;  
\- путь к \`newton.cmd\`;  
\- transport \`native|wsl\`;  
\- timeout;  
\- output encoding \`auto|utf-8|cp866|cp1251\`;  
\- read-only version;  
\- read-only health;  
\- safe config fingerprint.

Кнопки:

\- Обнаружить CLI;  
\- Проверить версию;  
\- Проверить health;  
\- Проверить LLM Summary;  
\- Проверить транскрибацию;  
\- Копировать последние результаты.

LLM model в общем блоке не хранить.

\#\#\# 5.2. Блок «Генерация протокола / LLM»

Provider:

\`\`\`text  
mock  
onebit\_newton\_cli  
openai\_compatible  
\`\`\`

Для OneBit показывать только model \`llama|gpt4\`, temperature, max tokens и статус LLM capability. Token/path повторно не показывать.

Для OpenAI показывать Base URL, API Key, model, API paths, timeout и отдельную асинхронную проверку.

\#\#\# 5.3. Блок «Транскрибация видео»

Provider:

\`\`\`text  
disabled  
mock  
onebit\_newton\_cli  
\`\`\`

Для OneBit использовать общий token/path. Не показывать второй токен, путь и неподтверждённый Base URL.

\#\#\# 5.4. БИТ.Link

Provider:

\`\`\`text  
disabled  
mock  
real  
\`\`\`

Пока API-контракт не подтверждён:

\`\`\`text  
real → BLOCKED\_BY\_API\_CONTRACT / NOT\_IMPLEMENTED  
\`\`\`

Не выполнять фиктивную аутентификацию. Явно показывать, что БИТ.Link нужен только для источника БИТ.Link.

\#\#\# 5.5. Confluence и Telegram

Сохранить реальные проверки:

\- Confluence: auth → space → parent page → проверка принадлежности space;  
\- Telegram: getMe → getChat;  
\- тестовое сообщение только отдельной кнопкой с подтверждением.

\#\# 6\. Единая OneBit-конфигурация

Создать:

\`\`\`python  
@dataclass(frozen=True)  
class OneBitNewtonConfig:  
    token: str  
    cli\_path: str  
    transport: str  
    timeout\_seconds: int  
    output\_encoding: str \= "auto"  
\`\`\`

Обе capability используют один объект.

Канонические env:

\`\`\`text  
ONEBIT\_NEWTON\_TOKEN  
ONEBIT\_NEWTON\_CLI\_PATH  
ONEBIT\_NEWTON\_TRANSPORT  
ONEBIT\_NEWTON\_TIMEOUT\_SECONDS  
ONEBIT\_NEWTON\_OUTPUT\_ENCODING  
\`\`\`

Legacy fallback:

\`\`\`text  
ONEBIT\_NEWTON\_TOKEN → ONEBIT\_LLM\_TOKEN → NEWTON\_TOKEN  
ONEBIT\_NEWTON\_CLI\_PATH → ONEBIT\_CLI\_PATH → NEWTON\_PATH  
\`\`\`

Fallback разрешён только при отсутствии канонического значения.

Если legacy-значения различаются:

\- не выбирать молча;  
\- вернуть \`CONFIG\_CONFLICT\`;  
\- показать safe fingerprint: source env, length, sha256 prefix до 12 символов;  
\- token не показывать.

После сохранения писать канонические переменные. Стратегию миграции legacy-переменных описать в validation.

\#\# 7\. settings.py и RuntimeConfig

Добавить единые provider-переменные:

\`\`\`text  
BITLINK\_PROVIDER  
TRANSCRIPTION\_PROVIDER  
CONFLUENCE\_PROVIDER  
TELEGRAM\_PROVIDER  
LLM\_PROVIDER  
\`\`\`

Legacy \`\*\_MOCK\` использовать только как fallback.

RuntimeConfig должен хранить:

\`\`\`text  
bitlink\_mode \= disabled|mock|real  
transcription\_provider \= disabled|mock|onebit\_newton\_cli  
llm\_provider \= mock|onebit\_newton\_cli|openai\_compatible  
confluence\_mode \= disabled|mock|rest  
telegram\_mode \= disabled|mock|real  
\`\`\`

Удалить неоднозначное \`newton\_mode\` либо переименовать в \`transcription\_provider\`.

После сохранения выполнить \`.env\` write → dotenv override → settings reload → RuntimeConfig reload → UI refresh без restart.

\#\# 8\. Thread-safe runner

\#\#\# 8.1. Callback isolation

Заменить одно \`\_on\_complete\` на словарь callbacks по \`check\_id\`.

Каждый результат вызывает только свой callback. Callback удаляется после завершения.

\#\#\# 8.2. Snapshot в UI thread

Создать immutable \`ConnectionCheckInput\`.

До запуска worker считать все Entry/StringVar/BooleanVar в UI thread. Worker получает только обычные строки, числа и dataclass.

Worker запрещено вызывать:

\`\`\`text  
Entry.get  
StringVar.get  
BooleanVar.get  
winfo\_exists  
after  
configure  
messagebox  
clipboard  
Toplevel  
Treeview.insert  
\`\`\`

Только UI poller обновляет widgets, \`\_last\_results\`, readiness и показывает messagebox.

При закрытии Settings поздние результаты игнорируются, traceback отсутствует.

\#\# 9\. Capability checks

\#\#\# 9.1. Version

Выполнить \`newton version\`. Сохранить exit code, version, duration и encoding.

\#\#\# 9.2. Health

Выполнить \`newton health\`. Health не считать проверкой token, LLM или transcription capability.

\#\#\# 9.3. LLM Summary

Выполнить реальный \`newton summarize\`.

Стадии:

\`\`\`text  
cli\_execution  
output\_file\_exists  
output\_file\_not\_empty  
json\_extract  
json\_parse  
schema\_validation  
completed  
\`\`\`

Schema:

\`\`\`json  
{"type":"object","properties":{"status":{"type":"string"}},"required":\["status"\]}  
\`\`\`

PASS только при \`{"status":"ok"}\`. Не применять local segment-count validation.

\#\#\# 9.4. Transcription

Сначала получить контракт установленной версии:

\`\`\`text  
newton transcribe \--help  
\`\`\`

Не угадывать параметры.

Реализовать \`OneBitNewtonCLITranscriptionProvider\` по фактическому help.

Проверка использует короткий локальный media fixture без персональных данных и проходит:

\`\`\`text  
input\_validation  
cli\_execution  
task\_created\_or\_started  
polling\_if\_applicable  
result\_received  
output\_read  
transcript\_not\_empty  
completed  
\`\`\`

PASS только при непустом transcript.

\#\# 10\. Source-specific readiness

Добавить сценарий:

\`\`\`text  
Локальный TXT  
Локальное видео  
БИТ.Link  
Полная диагностика  
\`\`\`

\#\#\# Локальный TXT

Обязательные: LLM PASS; Confluence PASS или SKIPPED по режиму публикации. Bitlink и Transcription не блокируют.

\#\#\# Локальное видео

Обязательные: Transcription PASS и LLM PASS.

\#\#\# БИТ.Link

Обязательные: Bitlink real PASS; при необходимости Transcription PASS; LLM PASS. Пока Bitlink adapter отсутствует — \`BLOCKED\_BY\_API\_CONTRACT\`.

Статусы:

\`\`\`text  
READY  
PARTIALLY\_READY  
DEMO\_ONLY  
BLOCKED  
BLOCKED\_BY\_API\_CONTRACT  
\`\`\`

\#\# 11\. Check All и индивидуальные кнопки

\`Проверить все\` сначала снимает snapshots в UI thread, затем запускает pure workers, получает список \`ConnectionCheckResult\` и рассчитывает readiness выбранного сценария.

Колонки:

\`\`\`text  
Сервис/Capability  
Provider  
Статус  
Этап  
Сообщение  
Время  
Проверено  
Config fingerprint  
\`\`\`

На единый runner перевести:

\- Newton version;  
\- Newton health;  
\- Newton LLM;  
\- Newton transcription;  
\- OpenAI LLM;  
\- Confluence;  
\- Telegram;  
\- Bitlink.

Кнопки всегда восстанавливаются при PASS, FAIL, timeout, exception и закрытии frame.

\#\# 12\. Диагностика

\`Копировать последние результаты\` не запускает CLI и network.

При отсутствии результатов вывести \`Проверки ещё не выполнялись\`.

Формат:

\`\`\`text  
scenario  
service\_id  
capability  
provider  
status  
stage  
code  
checked\_at  
duration  
exit\_code  
http\_status  
stdout\_encoding  
stderr\_encoding  
safe\_message  
recommendation  
config\_fingerprint  
\`\`\`

Не сохранять token, password, API key, Authorization header и полный hash.

\#\# 13\. Семантика PASS

Нельзя возвращать PASS для mock, заполненных полей, version, health или неожиданного JSON.

Текущий результат \`OK, но неожиданный ответ\` должен стать:

\`\`\`text  
PARTIAL или FAIL  
code=UNEXPECTED\_RESPONSE  
\`\`\`

PASS только после полного контракта capability.

\#\# 14\. Manifest

Обновить \`docs/opencode/manifest.json\`, который сейчас содержит устаревшие active task, head, test count и validation state.

Установить active task:

\`\`\`text  
TASK-2026-08-02-newton-unified-settings-and-capabilities  
\`\`\`

Добавить findings:

\`\`\`text  
BB-CRIT-115 — конфликтующие token env одного Newton CLI  
BB-CRIT-116 — конфликтующие CLI path env  
BB-CRIT-117 — GUI providers не совпадают с RuntimeConfig  
BB-CRIT-118 — runner перезаписывает callback параллельной проверки  
BB-CRIT-119 — worker обращается к Tkinter  
BB-CRIT-120 — real transcription provider отсутствует  
BB-CRIT-121 — readiness не учитывает source scenario  
BB-MAJ-122 — Newton credentials дублируются  
BB-MAJ-123 — OpenAI individual check синхронный  
BB-MAJ-124 — copy diagnostics запускает CLI  
BB-MAJ-125 — unexpected response считается PASS  
BB-MAJ-126 — manifest устарел  
\`\`\`

Проблему старого токена отметить \`RESOLVED\_BY\_USER\`, если старый раскрытый токен отозван; иначе оставить \`USER\_ACTION\_REQUIRED\`, но не блокировать работу с новым токеном.

\#\# 15\. Обязательные тесты

Создать:

\`\`\`text  
tests/test\_onebit\_unified\_config.py  
tests/test\_newton\_config\_migration.py  
tests/test\_connection\_check\_runner\_concurrency.py  
tests/test\_settings\_snapshots.py  
tests/test\_newton\_llm\_capability.py  
tests/test\_newton\_transcription\_capability.py  
tests/test\_source\_readiness.py  
tests/test\_settings\_diagnostics\_no\_side\_effects.py  
tests/test\_runtime\_provider\_mapping.py  
tests/test\_settings\_full\_e2e\_contract.py  
\`\`\`

Обязательные сценарии:

\`\`\`text  
test\_onebit\_token\_field\_is\_not\_duplicated  
test\_onebit\_cli\_path\_is\_not\_duplicated  
test\_conflicting\_legacy\_tokens\_report\_config\_conflict  
test\_token\_shape\_is\_not\_rejected\_locally  
test\_llm\_summary\_real\_response\_is\_schema\_valid  
test\_transcription\_uses\_same\_onebit\_config  
test\_transcription\_returns\_non\_empty\_text  
test\_gui\_provider\_saved\_to\_runtime\_provider  
test\_parallel\_checks\_keep\_own\_callbacks  
test\_worker\_does\_not\_read\_tk\_widgets  
test\_worker\_does\_not\_call\_after  
test\_openai\_individual\_check\_is\_async  
test\_copy\_diagnostics\_has\_no\_subprocess\_side\_effect  
test\_copy\_diagnostics\_has\_no\_network\_side\_effect  
test\_local\_txt\_ready\_without\_bitlink  
test\_local\_txt\_ready\_without\_transcription  
test\_local\_video\_requires\_transcription  
test\_bitlink\_scenario\_blocked\_by\_contract  
test\_unexpected\_json\_is\_not\_pass  
test\_secrets\_are\_redacted  
test\_settings\_reload\_without\_restart  
\`\`\`

Запрещены \`assert True\` и E2E, в котором real provider полностью заменён mock.

\#\# 16\. Windows GUI E2E

Запускать через:

\`\`\`cmd  
call start\_app.bat  
\`\`\`

Проверить:

1\. Token/path Newton показаны один раз.  
2\. Version и health работают.  
3\. Реальный LLM Summary возвращает schema-valid \`{"status":"ok"}\`.  
4\. Реальная транскрибация короткого fixture возвращает непустой текст.  
5\. Confluence и Telegram проходят.  
6\. Локальный TXT получает READY/PARTIALLY\_READY без требования Bitlink/Transcription.  
7\. Локальное видео READY только при PASS Transcription и LLM.  
8\. Две параллельные проверки не путают callbacks.  
9\. Закрытие Settings во время проверки не даёт traceback.  
10\. Copy diagnostics не запускает новый process/network.  
11\. После сохранения повторная проверка работает без restart.  
12\. Token отсутствует в отчётах, логах и git diff.

Создать:

\`\`\`text  
docs/opencode/validations/NEWTON-UNIFIED-SETTINGS-E2E-\<HEAD\_SHORT\_SHA\>.md  
\`\`\`

\#\# 17\. Команды

\`\`\`bash  
python \-m compileall .  
python \-m json.tool docs/opencode/manifest.json  
pytest \-q  
pytest \-q tests/test\_onebit\_unified\_config.py  
pytest \-q tests/test\_newton\_config\_migration.py  
pytest \-q tests/test\_connection\_check\_runner\_concurrency.py  
pytest \-q tests/test\_settings\_snapshots.py  
pytest \-q tests/test\_newton\_llm\_capability.py  
pytest \-q tests/test\_newton\_transcription\_capability.py  
pytest \-q tests/test\_source\_readiness.py  
pytest \-q tests/test\_settings\_diagnostics\_no\_side\_effects.py  
pytest \-q tests/test\_runtime\_provider\_mapping.py  
pytest \-q tests/test\_settings\_full\_e2e\_contract.py  
ruff check .  
mypy . \--ignore-missing-imports  
\`\`\`

Windows:

\`\`\`cmd  
call start\_app.bat \--startup-check  
\`\`\`

\#\# 18\. Ограничения

\- не угадывать API БИТ.Link;  
\- не угадывать параметры \`newton transcribe\`, а прочитать help установленной версии;  
\- не менять рабочий token автоматически;  
\- не выводить secrets;  
\- не требовать JWT из трёх сегментов;  
\- не считать health capability-check;  
\- не считать mock реальным PASS;  
\- не заменять Windows GUI E2E unit-тестами;  
\- PR оставить Draft;  
\- merge и \`accepted\` запрещены.

\#\# 19\. Ответ OpenCode

Предоставить:

1\. Исходный и новый exact headRefOid.  
2\. Draft PR URL.  
3\. Compare summary.  
4\. Список изменённых файлов.  
5\. Схему новой Settings page.  
6\. Канонические env и миграцию legacy env.  
7\. Доказательство единого token/path для LLM и transcription.  
8\. Результат real LLM smoke.  
9\. Результат real transcription capability.  
10\. Readiness для Local TXT, Local Video и Bitlink.  
11\. Доказательство callback isolation.  
12\. Доказательство отсутствия Tkinter calls из worker.  
13\. Доказательство отсутствия side effects у Copy diagnostics.  
14\. Результаты команд и тестов.  
15\. Windows GUI E2E.  
16\. Validation path.  
17\. Подтверждение отсутствия secrets.  
18\. Оставшиеся ограничения.

PR оставить Draft. Merge не выполнять. \`accepted\` не устанавливать.  
