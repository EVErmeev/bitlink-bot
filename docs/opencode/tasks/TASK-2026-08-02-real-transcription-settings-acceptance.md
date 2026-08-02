\# TASK-2026-08-02-real-transcription-settings-acceptance

\#\# Цель

Завершить текущую итерацию настроек и доказать реальную работу транскрибации через установленный БИТ Ньютон CLI в производственном конвейере приложения.

После выполнения должно быть подтверждено:

\`\`\`text  
local video  
→ build\_transcription\_client  
→ newton transcribe  
→ task\_id  
→ polling READY  
→ output file  
→ непустой transcript  
→ LLM Summary  
→ protocol artifacts  
→ dry-run completed  
\`\`\`

До завершения этой задачи не переходить к \`BB-MAJ-011–020\`.

\#\# Репозиторий

\- Repository: \`EVErmeev/bitlink-bot\`  
\- Branch: \`fix/audit-e7cc95f\`  
\- Draft PR: \`https://github.com/EVErmeev/bitlink-bot/pull/1\`  
\- Проверенный base head: \`a48bef437f020a3a4c09ad1d611858ba1b77d6a3\`

Перед началом получить фактический headRefOid и изучить diff, если head изменился.

PR оставить Draft. Merge не выполнять. \`accepted\` не устанавливать.

\#\# 1\. Сохранить правильную архитектуру настроек

Оставить один общий блок:

\`\`\`text  
БИТ Ньютон CLI  
\- token  
\- CLI path  
\- transport  
\- timeout  
\- output encoding  
\- version  
\- health  
\- capability status  
\`\`\`

Отдельные блоки должны отвечать только за выбор функции:

\`\`\`text  
Транскрибация  
\- disabled  
\- mock  
\- onebit\_newton\_cli  
\- engine  
\- language  
\- num\_speakers при diarize

Генерация протокола / LLM  
\- mock  
\- onebit\_newton\_cli  
\- openai\_compatible  
\- model  
\`\`\`

Не возвращать дублирующиеся token/path в LLM или Transcription.

\#\# 2\. Убрать неверное требование JWT

Переименовать:

\`\`\`text  
JWT-токен  
\`\`\`

в:

\`\`\`text  
Токен БИТ Ньютон  
\`\`\`

Удалить tooltip о трёх JWT-сегментах.

Приложение не должно отклонять token по длине, точкам или локальному формату. Источник истины — реальный ответ capability.

\#\# 3\. Создать единый Newton CLI command builder

Создать, например:

\`\`\`text  
services/newton\_cli.py  
\`\`\`

API:

\`\`\`python  
def build\_newton\_command(cli\_path: str, \*args: str) \-\> list\[str\]:  
    ...  
\`\`\`

Для \`.cmd/.bat\` на Windows:

\`\`\`text  
cmd.exe /d /s /c \<cli\_path\> \<args...\>  
\`\`\`

Для обычного executable/script:

\`\`\`text  
\<cli\_path\> \<args...\>  
\`\`\`

Один builder использовать в:

\- version;  
\- health;  
\- summarize;  
\- transcribe;  
\- diagnostics;  
\- preflight;  
\- Check All.

Запрещено собирать команды разными способами в разных классах.

\#\# 4\. Подключить реальный transcription adapter в client\_factory

Текущий дефект:

\`\`\`python  
if config.transcription\_provider \== "onebit\_newton\_cli":  
    return TranscriptionClient()  
\`\`\`

Заменить на реальный adapter, реализующий ожидаемый контракт ProcessingService:

\`\`\`python  
class OneBitNewtonTranscriptionClient:  
    def check\_connection(...) \-\> ...:  
        ...

    def transcribe\_video(self, video\_path: Path, output\_dir: Path) \-\> str:  
        ...  
\`\`\`

Допустимо адаптировать существующий \`OneBitNewtonTranscriptionProvider\`, но production factory обязан возвращать объект, который реально вызывает Newton CLI.

Старый \`TranscriptionClient\` оставить только для mock-режима либо удалить после миграции всех вызовов.

При \`onebit\_newton\_cli\` запрещено возвращать старый mock/NotImplemented client.

\#\# 5\. Реализовать transcribe по фактическому контракту CLI

Использовать подтверждённый контракт установленного CLI:

\`\`\`text  
newton transcribe \<file\>  
  \--engine v3|parakeet|diarize|stereo-v3  
  \--language \<language\>  
  \--num-speakers \<N\>  
  \--output \<file\>  
\`\`\`

Не угадывать параметры.

Поведение CLI:

1\. Загружает файл.  
2\. Возвращает task\_id в stdout.  
3\. Выполняет polling до READY или ERROR.  
4\. Скачивает результат в \`--output\`.  
5\. Для \`v3\` результат обычно TXT.  
6\. Для \`parakeet\`, \`diarize\`, \`stereo-v3\` результат может быть JSON.

Adapter должен:

\- передавать \`NEWTON\_TOKEN\` только через child env;  
\- использовать unified process runner;  
\- применять timeout;  
\- redaction token;  
\- поддерживать \`.cmd\` через command builder;  
\- проверять наличие input-файла;  
\- создавать output\_dir;  
\- выбирать расширение output по engine;  
\- проверять существование и размер output;  
\- читать TXT как UTF-8;  
\- разбирать JSON-результат поддерживаемых engine;  
\- преобразовывать JSON в нормализованный transcript string;  
\- сохранять raw result рядом с нормализованным TXT;  
\- возвращать непустой transcript.

\#\# 6\. Нормализация результатов разных engine

\#\#\# v3

Если output — текст:

\- сохранить исходный TXT;  
\- вернуть текст без потери временных меток.

\#\#\# parakeet

Если JSON:

\- определить фактическую структуру по real result;  
\- сохранить raw JSON;  
\- извлечь текст и сегменты;  
\- не выдумывать поля, которых нет в фактическом ответе.

\#\#\# diarize

\- сохранить speaker labels;  
\- форматировать строки как минимум:

\`\`\`text  
\[HH:MM:SS\] Speaker N: текст  
\`\`\`

\#\#\# stereo-v3

\- сохранить channel/backchannel metadata, когда они присутствуют;  
\- не терять speaker/channel attribution.

Если структура неизвестна, вернуть controlled error с безопасным фрагментом schema keys, а не silent empty transcript.

\#\# 7\. Разделить уровни проверки транскрибации

\#\#\# Проверка capability

\`\`\`text  
newton transcribe \--help  
\`\`\`

Результат:

\`\`\`text  
status=PARTIAL  
stage=cli\_capability  
message=Команда transcribe доступна; токен и обработка файла не проверялись  
\`\`\`

Запрещено возвращать PASS.

\#\#\# Реальная проверка

Добавить кнопку:

\`\`\`text  
Проверить транскрибацию файлом...  
\`\`\`

Она должна:

1\. открыть file dialog;  
2\. позволить выбрать короткий media-файл;  
3\. снять snapshot настроек в UI thread;  
4\. запустить real transcribe в worker;  
5\. показать progress/stage;  
6\. получить output;  
7\. показать preview первых 300 символов;  
8\. показать engine, duration, output size, elapsed time;  
9\. сохранить безопасный diagnostic result;  
10\. вернуть PASS только при непустом transcript.

Файл пользователя и transcript не коммитить.

\#\# 8\. Исправить Check All

Строка Transcription должна различать:

\`\`\`text  
SKIPPED  
MOCK  
PARTIAL — CLI command available only  
PASS — real media transcribed  
FAIL  
\`\`\`

Обычный \`Проверить все подключения\` без media fixture не должен ложно показывать PASS.

Добавить источник readiness:

\#\#\# Local TXT

Обязательные:

\- LLM PASS;  
\- Confluence PASS или disabled;  
\- Telegram PASS или disabled.

Transcription и Bitlink не применимы.

\#\#\# Local Video

Обязательные:

\- Newton CLI PASS;  
\- Transcription real PASS;  
\- LLM PASS;  
\- Confluence PASS или disabled;  
\- Telegram PASS или disabled.

\#\#\# Bitlink

До реализации adapter:

\`\`\`text  
BLOCKED\_BY\_API\_CONTRACT  
\`\`\`

Bitlink не должен блокировать TXT/Video readiness.

\#\# 9\. Исправить асинхронность GUI

Все worker-функции обязаны возвращать \`ConnectionCheckResult\` через \`ConnectionCheckRunner\`.

Запрещено внутри worker вызывать:

\`\`\`text  
self.\_run\_on\_ui  
self.after  
winfo\_exists  
configure  
messagebox  
clipboard  
Entry.get  
StringVar.get  
\`\`\`

Version, health, token/LLM, OpenAI и Transcription должны использовать один queue-based механизм.

\`ConnectionCheckRunner\` обязан хранить callback отдельно для каждого \`check\_id\` и удалять его после завершения.

Закрытие Settings во время проверки не должно приводить к traceback.

\#\# 10\. Исправить OpenAI individual check

\`\_test\_openai\_llm()\` сейчас не должен выполнять network/LLM в GUI callback.

Схема:

\`\`\`text  
UI snapshot  
→ ConnectionCheckRunner  
→ worker check\_connection \+ schema smoke  
→ result queue  
→ UI update  
\`\`\`

\#\# 11\. Исправить диагностику

\`Копировать диагностику\` не должна запускать version, health, summarize или transcribe.

Она копирует только сохранённые результаты последних проверок.

Если результатов нет:

\`\`\`text  
Проверки ещё не выполнялись  
\`\`\`

Диагностика Newton:

\`\`\`text  
cli\_path  
version  
health  
llm\_status  
transcription\_capability\_status  
transcription\_real\_status  
engine  
output\_format  
duration  
exit\_code  
stdout\_encoding  
stderr\_encoding  
safe\_message  
\`\`\`

Не включать token, Authorization, child env и полный transcript.

\#\# 12\. Обработка ошибок transcribe

Классифицировать:

\`\`\`text  
TRANSCRIPTION\_INPUT\_NOT\_FOUND  
TRANSCRIPTION\_TOKEN\_MISSING  
TRANSCRIPTION\_CLI\_NOT\_FOUND  
TRANSCRIPTION\_CLI\_START\_FAILED  
TRANSCRIPTION\_TIMEOUT  
TRANSCRIPTION\_AUTH\_FAILED  
TRANSCRIPTION\_UPLOAD\_FAILED  
TRANSCRIPTION\_REMOTE\_ERROR  
TRANSCRIPTION\_OUTPUT\_MISSING  
TRANSCRIPTION\_OUTPUT\_EMPTY  
TRANSCRIPTION\_OUTPUT\_INVALID  
TRANSCRIPTION\_CANCELLED  
\`\`\`

Не использовать общий \`RuntimeError("Transcription failed")\` как единственную диагностику.

В stderr/stdout хранить только redacted безопасные фрагменты.

\#\# 13\. Реальная отмена

Долгая транскрибация должна поддерживать cancel request на уровне приложения.

Минимум:

\- кнопка отмены в GUI;  
\- прекращение ожидания результата;  
\- subprocess termination;  
\- controlled \`TRANSCRIPTION\_CANCELLED\`;  
\- очистка временных файлов.

Удалённая задача может продолжить работу, если CLI/API не поддерживает cancel. Это явно указать в результате.

\#\# 14\. Обязательные тесты

Создать реальные файлы:

\`\`\`text  
tests/test\_newton\_command\_builder.py  
tests/test\_newton\_transcription\_provider.py  
tests/test\_transcription\_client\_factory.py  
tests/test\_transcription\_settings\_checks.py  
tests/test\_transcription\_output\_normalization.py  
tests/test\_settings\_async\_regressions.py  
tests/test\_source\_specific\_readiness.py  
\`\`\`

Обязательные кейсы:

\`\`\`text  
test\_cmd\_path\_uses\_cmd\_exe\_wrapper  
test\_executable\_path\_runs\_directly  
test\_factory\_returns\_real\_newton\_transcription\_client  
test\_factory\_does\_not\_return\_legacy\_client\_for\_onebit  
test\_transcribe\_help\_is\_partial\_not\_pass  
test\_real\_transcribe\_requires\_media\_file  
test\_real\_transcribe\_pass\_requires\_nonempty\_output  
test\_v3\_txt\_result\_normalized  
test\_json\_result\_preserved\_and\_normalized  
test\_missing\_output\_is\_fail  
test\_empty\_output\_is\_fail  
test\_token\_is\_passed\_only\_in\_child\_env  
test\_token\_is\_redacted  
test\_worker\_does\_not\_touch\_tkinter  
test\_openai\_individual\_check\_is\_async  
test\_copy\_diagnostics\_does\_not\_run\_process  
test\_local\_txt\_readiness\_ignores\_transcription\_and\_bitlink  
test\_local\_video\_readiness\_requires\_real\_transcription  
test\_bitlink\_readiness\_is\_blocked\_by\_api\_contract  
test\_cancel\_terminates\_local\_process  
\`\`\`

Моки subprocess допустимы для unit-тестов, но обязательна отдельная real Windows acceptance.

\#\# 15\. Windows real acceptance

Запускать через:

\`\`\`cmd  
call start\_app.bat  
\`\`\`

Использовать реальный короткий media-файл с речью продолжительностью примерно 10–60 секунд. Файл не добавлять в git.

Сценарий:

1\. Открыть Settings.  
2\. Проверить Newton version.  
3\. Проверить health.  
4\. Проверить LLM smoke.  
5\. Нажать \`Проверить транскрибацию файлом...\`.  
6\. Выбрать реальный media-файл.  
7\. Убедиться, что создана удалённая задача.  
8\. Дождаться READY.  
9\. Получить непустой transcript.  
10\. Зафиксировать engine, output extension, output size и char count.  
11\. Добавить тот же файл в основную очередь приложения.  
12\. Выполнить local video dry-run.  
13\. Подтвердить цепочку:

\`\`\`text  
video → transcript → LLM → protocol.json → protocol\_preview.html  
\`\`\`

14\. Убедиться, что mock transcript не использовался.  
15\. Убедиться, что \`NotImplementedError\` не возник.  
16\. Убедиться, что GUI не зависает.  
17\. Закрыть Settings во время отдельной проверки и проверить отсутствие traceback.  
18\. Проверить cancel на второй попытке.  
19\. Проверить, что token не попал в лог/отчёт.

Создать:

\`\`\`text  
docs/opencode/validations/REAL-TRANSCRIPTION-SETTINGS-E2E-\<HEAD\_SHORT\_SHA\>.md  
\`\`\`

Validation должна содержать только безопасные данные:

\- input file name без полного приватного пути;  
\- media duration;  
\- file size;  
\- engine;  
\- task\_id в сокращённом/redacted виде;  
\- output type;  
\- output size;  
\- transcript char count;  
\- protocol artifacts paths;  
\- PASS/FAIL по каждому этапу.

\#\# 16\. Manifest

Добавить:

\`\`\`text  
BB-CRIT-115 — real transcription provider not wired to factory  
BB-CRIT-116 — legacy TranscriptionClient remains mock/NotImplemented  
BB-CRIT-117 — transcribe \--help incorrectly reported as PASS  
BB-CRIT-118 — transcription .cmd invocation bypasses Windows wrapper  
BB-CRIT-119 — no real media E2E  
BB-MAJ-120 — no regression tests added for Newton integration  
BB-MAJ-121 — OpenAI individual check remains synchronous  
BB-MAJ-122 — workers still call Tkinter  
BB-MAJ-123 — copy diagnostics may start subprocess  
BB-MAJ-124 — misleading JWT-only tooltip  
BB-MAJ-125 — readiness not fully source-specific  
\`\`\`

Обновить active task, head, test results и remaining blockers.

\#\# 17\. Команды

\`\`\`bash  
python \-m compileall .  
python \-m json.tool docs/opencode/manifest.json  
pytest \-q  
pytest \-q tests/test\_newton\_command\_builder.py  
pytest \-q tests/test\_newton\_transcription\_provider.py  
pytest \-q tests/test\_transcription\_client\_factory.py  
pytest \-q tests/test\_transcription\_settings\_checks.py  
pytest \-q tests/test\_transcription\_output\_normalization.py  
pytest \-q tests/test\_settings\_async\_regressions.py  
pytest \-q tests/test\_source\_specific\_readiness.py  
ruff check .  
mypy . \--ignore-missing-imports  
\`\`\`

Windows:

\`\`\`cmd  
call start\_app.bat \--startup-check  
call start\_app.bat  
\`\`\`

\#\# 18\. Ответ OpenCode

Предоставить:

1\. exact headRefOid;  
2\. Draft PR URL;  
3\. список изменённых файлов;  
4\. список созданных тестов;  
5\. результаты всех команд;  
6\. доказательство factory wiring;  
7\. фактическую команду transcribe без token;  
8\. real media E2E;  
9\. output extension/size/char count;  
10\. local video dry-run artifacts;  
11\. доказательство отсутствия mock transcript;  
12\. доказательство отсутствия NotImplementedError;  
13\. доказательство Windows \`.cmd\` wrapper;  
14\. source-specific readiness;  
15\. async GUI evidence;  
16\. cancel evidence;  
17\. redaction evidence;  
18\. validation path;  
19\. оставшиеся ограничения.

Не отмечать real transcription PASS по результату \`--help\`.

PR оставить Draft. Merge не выполнять. \`accepted\` не устанавливать.  
