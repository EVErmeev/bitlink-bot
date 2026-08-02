\# TASK-2026-08-02-settings-finalization

\#\# Цель

Завершить страницу «Настройки» и достоверную проверку всех подключений.

После выполнения:

\- каждый сервис переключается в нужный provider/mode;  
\- каждая кнопка выполняет реальную проверку либо честно возвращает MOCK, NOT\_IMPLEMENTED, NOT\_CONFIGURED или SKIPPED;  
\- активный LLM входит в общую матрицу;  
\- GUI не зависает;  
\- worker-потоки не обращаются к Tkinter;  
\- newton health отображается читаемым русским текстом;  
\- невалидный токен выдаёт понятный FAIL без traceback;  
\- копирование диагностики не запускает проверки повторно;  
\- изменение полей инвалидирует предыдущий PASS.

\#\# Репозиторий

\- Repository: EVErmeev/bitlink-bot  
\- Branch: fix/audit-e7cc95f  
\- Draft PR: https://github.com/EVErmeev/bitlink-bot/pull/1  
\- Проверенный base head: c5428a156eea677dad1576ca6dae944fbeb75327

Перед началом получить фактический head:

\`\`\`bash  
gh pr view 1 \--json headRefOid,url,isDraft,statusCheckRollup  
\`\`\`

PR оставить Draft. Merge не выполнять. accepted не устанавливать.

\#\# 1\. Подтверждённое состояние

OneBit Newton CLI:

\`\`\`text  
CLI: C:\\Users\\egore\\AppData\\Local\\NewtonCLI\\newton.cmd  
Version: 2026.07.13  
Health: exit=0  
\`\`\`

Русский stdout health отображается битой кодировкой:

\`\`\`text  
╥ЁрэёъЁшсрЎш ...  
\`\`\`

Token check:

\`\`\`text  
AUTH\_TOKEN\_MALFORMED  
HTTP 401  
Malformed token: Not enough segments  
\`\`\`

Это корректный FAIL для невалидного токена.

Оставшиеся подтверждённые дефекты:

1\. Проверить все подключения не включает LLM.  
2\. OpenAI test остаётся синхронным.  
3\. Worker-функции читают Tkinter widgets через .get().  
4\. \_run\_on\_ui вызывается из worker thread и использует Tk methods.  
5\. Копировать диагностику повторно запускает version и health.  
6\. Нет provider selector у БИТ.Link, Newton transcription, Confluence и Telegram.  
7\. Нет надёжной инвалидации результата после изменения полей.

\#\# 2\. Исправить кодировку Newton CLI

Добавить:

\`\`\`text  
ONEBIT\_CLI\_OUTPUT\_ENCODING=auto|utf-8|cp866|cp1251  
\`\`\`

В режиме auto:

1\. Проверить UTF-8/UTF-8-SIG.  
2\. Декодировать CP866 и CP1251.  
3\. Рассчитать quality score.  
4\. Выбрать лучший вариант.

Score должен:

\- повышаться за нормальные русские буквы и слова;  
\- штрафовать псевдографику, управляющие символы и mojibake;  
\- учитывать слова healthy, транскрибация, русский, модель, сервис.

В ProcessExecutionResult добавить:

\`\`\`python  
stdout\_encoding: str  
stderr\_encoding: str  
stdout\_decode\_score: float | None  
stderr\_decode\_score: float | None  
\`\`\`

В диагностике показывать encoding и score.

Критерий: newton health читается по-русски без строки вида ╥ЁрэёъЁшсрЎш.

\#\# 3\. Добавить provider/mode selector

БИТ.Link:

\`\`\`text  
mock  
real  
\`\`\`

Переменная:

\`\`\`text  
BITLINK\_PROVIDER=mock|real  
\`\`\`

Синхронизировать BITLINK\_MOCK.

Newton — транскрибация видео:

\`\`\`text  
mock  
real  
\`\`\`

Переменная:

\`\`\`text  
NEWTON\_TRANSCRIPTION\_PROVIDER=mock|real  
\`\`\`

Синхронизировать NEWTON\_MOCK. Не смешивать с OneBit Newton LLM.

Confluence:

\`\`\`text  
disabled  
mock  
rest  
\`\`\`

Telegram:

\`\`\`text  
disabled  
mock  
real  
\`\`\`

LLM selector оставить:

\`\`\`text  
mock  
onebit\_newton\_cli  
openai\_compatible  
\`\`\`

Проверки используют provider из текущей формы, а не из глобального settings.

\#\# 4\. Immutable snapshot до worker

Создать:

\`\`\`python  
@dataclass(frozen=True)  
class ConnectionCheckInput:  
    service\_id: str  
    provider: str  
    base\_url: str \= ""  
    login: str \= ""  
    password: str \= ""  
    token: str \= ""  
    space\_key: str \= ""  
    parent\_page\_id: str \= ""  
    parent\_page\_title: str \= ""  
    chat\_id: str \= ""  
    cli\_path: str \= ""  
    model: str \= ""  
    timeout\_seconds: int \= 30  
    output\_encoding: str \= "auto"  
\`\`\`

Snapshot создаётся в UI thread.

Worker не должен вызывать:

\`\`\`text  
Entry.get()  
StringVar.get()  
BooleanVar.get()  
winfo\_exists()  
after()  
configure()  
messagebox.\*  
clipboard\_\*  
\`\`\`

\#\# 5\. Thread-safe runner

Создать:

\`\`\`text  
ui/connection\_check\_runner.py  
\`\`\`

Архитектура:

\`\`\`text  
UI thread  
→ capture snapshot  
→ worker  
→ result\_queue.put(result)  
→ UI poller через self.after  
→ обновление widgets  
\`\`\`

Требования:

\- один активный check на сервис;  
\- повторный клик не создаёт второй worker;  
\- worker не вызывает Tkinter;  
\- кнопка всегда возвращается в normal;  
\- поздний результат игнорируется после уничтожения frame;  
\- закрытие Settings во время проверки не даёт traceback;  
\- есть timeout и отмена долгого LLM check;  
\- ожидаемые ошибки подключения не печатают traceback.

\#\# 6\. Проверки сервисов

\#\#\# БИТ.Link

mock → MOCK.

real → пока адаптер не реализован:

\`\`\`text  
NOT\_IMPLEMENTED  
BITLINK\_REAL\_ADAPTER\_NOT\_IMPLEMENTED  
\`\`\`

Не показывать PASS и не использовать фиктивный authenticate().

\#\#\# Newton — транскрибация видео

mock → MOCK.

real → пока адаптер не реализован:

\`\`\`text  
NOT\_IMPLEMENTED  
NEWTON\_TRANSCRIPTION\_ADAPTER\_NOT\_IMPLEMENTED  
\`\`\`

Наличие token/Base URL не является PASS.

\#\#\# Confluence

disabled → SKIPPED.

mock → MOCK.

rest → реальная проверка текущих значений формы:

\`\`\`text  
configuration  
authentication  
space\_lookup  
parent\_page\_lookup  
\`\`\`

Запросы:

\`\`\`text  
GET /rest/api/user/current  
GET /rest/api/space/{space\_key}  
GET /rest/api/content/{parent\_page\_id}?expand=space,ancestors  
\`\`\`

PASS только после auth \+ space \+ parent page. Проверить принадлежность страницы space и её title.

\#\#\# Telegram

disabled → SKIPPED.

mock → MOCK.

real → выполнить getMe и getChat. PASS только после обоих запросов.

Тестовое сообщение вынести в отдельную кнопку с подтверждением пользователя.

\#\#\# OneBit Newton LLM

Разделить стадии:

\`\`\`text  
cli\_discovery  
version  
health  
token\_and\_generate  
json\_parse  
schema\_validation  
\`\`\`

Health PASS не означает token PASS.

Невалидный токен:

\`\`\`text  
FAIL  
AUTH\_TOKEN\_MALFORMED  
\`\`\`

Перед CLI проверить локальный формат JWT: три непустых сегмента через точку. Ошибка:

\`\`\`text  
AUTH\_TOKEN\_FORMAT\_INVALID  
\`\`\`

После корректного формата всё равно выполнить real CLI smoke-test.

Ожидаемый schema-valid ответ:

\`\`\`json  
{"status":"ok"}  
\`\`\`

\#\#\# OpenAI-compatible

Перевести на connection\_check\_runner. Использовать текущие URL/key/model.

Стадии:

\`\`\`text  
configuration  
authentication  
minimal\_completion  
json\_parse  
schema\_validation  
\`\`\`

Классифицировать 401, 403, 404, 405, 429, timeout, invalid JSON и schema failure. PASS только после schema-valid JSON.

\#\# 7\. Проверить все подключения

Матрица должна включать:

\- БИТ.Link;  
\- Newton — транскрибация видео;  
\- Confluence;  
\- Telegram;  
\- активный LLM provider.

Для OneBit выполнять полный token\_and\_generate. Для OpenAI — schema smoke-test.

Колонки:

\`\`\`text  
Сервис  
Provider  
Статус  
Этап  
Сообщение  
Время  
Проверено  
\`\`\`

Readiness:

\- READY — обязательные реальные сервисы PASS;  
\- PARTIALLY\_READY — LLM PASS, опциональные сервисы SKIPPED;  
\- DEMO\_ONLY — LLM mock;  
\- BLOCKED — основной LLM FAIL/NOT\_CONFIGURED/NOT\_IMPLEMENTED/TIMEOUT.

\#\# 8\. Диагностика

Копировать последние ConnectionCheckResult. Не запускать version/health повторно.

Добавить команды:

\`\`\`text  
Проверить заново  
Копировать последние результаты  
\`\`\`

Формат:

\`\`\`text  
service  
provider  
status  
stage  
code  
checked\_at  
duration  
encoding  
decode\_score  
exit\_code  
http\_status  
endpoint\_or\_command  
safe\_message  
recommendation  
\`\`\`

Secrets не включать.

\#\# 9\. Инвалидация

Изменение любого поля сервиса:

\- сбрасывает PASS;  
\- устанавливает NOT\_CHECKED;  
\- очищает timestamp;  
\- пересчитывает readiness.

Fingerprint может включать hash provider \+ endpoint \+ model \+ secret\_present \+ sha256(secret). Значение secret не выводить.

\#\# 10\. UX токена

Переименовать поле:

\`\`\`text  
JWT-токен БИТ Ньютон CLI  
\`\`\`

Подсказка:

\`\`\`text  
JWT обычно состоит из трёх частей, разделённых точками.  
Сам токен в диагностике не выводится.  
\`\`\`

Mock не считать PASS.

\#\# 11\. Тесты

Создать или обновить:

\`\`\`text  
tests/test\_cli\_encoding\_detection.py  
tests/test\_settings\_provider\_selectors.py  
tests/test\_connection\_check\_runner.py  
tests/test\_settings\_check\_all.py  
tests/test\_settings\_llm\_checks.py  
tests/test\_settings\_diagnostics.py  
tests/test\_settings\_result\_invalidation.py  
\`\`\`

Обязательные тесты:

\`\`\`text  
test\_cp1251\_health\_output\_is\_readable  
test\_cp866\_health\_output\_is\_readable  
test\_mojibake\_is\_penalized  
test\_explicit\_encoding\_override  
test\_provider\_selectors\_exist  
test\_unsaved\_provider\_is\_used  
test\_snapshot\_created\_on\_ui\_thread  
test\_worker\_never\_reads\_tk\_widgets  
test\_worker\_never\_calls\_after  
test\_worker\_never\_calls\_messagebox  
test\_destroyed\_frame\_ignores\_result  
test\_button\_reenabled\_after\_success  
test\_button\_reenabled\_after\_failure  
test\_openai\_check\_is\_async  
test\_copy\_diagnostics\_does\_not\_run\_process  
test\_check\_all\_includes\_active\_llm  
test\_check\_all\_runs\_onebit\_generation  
test\_check\_all\_runs\_openai\_schema\_test  
test\_mock\_is\_not\_ready  
test\_invalid\_jwt\_format\_is\_detected  
test\_auth\_token\_malformed\_is\_fail  
test\_field\_change\_invalidates\_result  
test\_secrets\_are\_redacted  
test\_confluence\_rest\_checks\_auth\_space\_parent  
test\_telegram\_real\_checks\_getme\_and\_getchat  
\`\`\`

Запрещены assert True и интеграционные тесты, заменяющие весь pipeline одной заглушкой.

\#\# 12\. Windows GUI E2E

Через:

\`\`\`cmd  
call start\_app.bat  
\`\`\`

Проверить:

1\. Version и health OneBit.  
2\. Читаемый русский health.  
3\. Невалидный JWT → AUTH\_TOKEN\_FORMAT\_INVALID или AUTH\_TOKEN\_MALFORMED.  
4\. Переключение provider у всех блоков.  
5\. Проверить все подключения с LLM в матрице.  
6\. Readiness.  
7\. GUI не зависает.  
8\. Закрытие Settings во время проверки не даёт traceback.  
9\. Копирование диагностики не запускает process.  
10\. Изменение поля сбрасывает результат в NOT\_CHECKED.

Создать:

\`\`\`text  
docs/opencode/validations/SETTINGS-FINALIZATION-E2E-\<HEAD\_SHORT\_SHA\>.md  
\`\`\`

\#\# 13\. Manifest

Добавить:

\`\`\`text  
BB-CRIT-105 — health stdout декодируется как mojibake  
BB-CRIT-106 — provider читается из global settings  
BB-CRIT-107 — Check All не включает LLM  
BB-CRIT-108 — OpenAI test синхронный  
BB-CRIT-109 — worker читает Tkinter widgets  
BB-CRIT-110 — Tkinter after вызывается из worker  
BB-MAJ-111 — Copy diagnostics повторно запускает CLI  
BB-MAJ-112 — нет provider selectors  
BB-MAJ-113 — нет инвалидации результата  
BB-MAJ-114 — readiness matrix неполная  
\`\`\`

Установить:

\`\`\`text  
active\_task\_id \= TASK-2026-08-02-settings-finalization  
active\_task\_file \= docs/opencode/tasks/TASK-2026-08-02-settings-finalization.md  
status \= in\_progress  
validation\_state \= implementing\_fixes  
\`\`\`

BB-CRIT-063 оставить USER\_ACTION\_REQUIRED.

\#\# 14\. Обязательные команды

\`\`\`bash  
python \-m compileall .  
python \-m json.tool docs/opencode/manifest.json  
pytest \-q  
pytest \-q tests/test\_cli\_encoding\_detection.py  
pytest \-q tests/test\_settings\_provider\_selectors.py  
pytest \-q tests/test\_connection\_check\_runner.py  
pytest \-q tests/test\_settings\_check\_all.py  
pytest \-q tests/test\_settings\_llm\_checks.py  
pytest \-q tests/test\_settings\_diagnostics.py  
pytest \-q tests/test\_settings\_result\_invalidation.py  
ruff check .  
mypy . \--ignore-missing-imports  
\`\`\`

Windows:

\`\`\`cmd  
call start\_app.bat \--startup-check  
\`\`\`

\#\# 15\. Ответ OpenCode

Предоставить:

1\. exact headRefOid;  
2\. Draft PR URL;  
3\. workflow run;  
4\. изменённые файлы;  
5\. созданные тесты;  
6\. результаты команд;  
7\. читаемый newton health;  
8\. stdout/stderr encoding и decode score;  
9\. provider selectors;  
10\. результат Check All с LLM;  
11\. readiness;  
12\. доказательство отсутствия Tk calls из worker;  
13\. доказательство асинхронного OpenAI test;  
14\. доказательство, что Copy diagnostics не запускает process;  
15\. Windows GUI E2E;  
16\. validation path;  
17\. отсутствие secrets в git/logs/artifacts;  
18\. ограничения.

PR оставить Draft. Merge не выполнять. accepted не устанавливать.  
