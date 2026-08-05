\# TASK-2026-08-02-windows-cli-encoding-auth

\#\# Цель

Исправить выполнение БИТ Ньютон CLI на Windows:

\- устранить \`UnicodeDecodeError\` во внутреннем \`subprocess.\_readerthread\`;  
\- исключить повторный \`NoneType\` из\-за \`stdout/stderr=None\`;  
\- корректно показать HTTP 401 и причину отклонения токена;  
\- сделать проверки version, health и real LLM неблокирующими для GUI;  
\- добавить regression tests кодировок Windows.

\#\# Репозиторий

\- Repository: \`EVErmeev/bitlink-bot\`  
\- Branch: \`fix/audit-e7cc95f\`  
\- Draft PR: \`https://github.com/EVErmeev/bitlink-bot/pull/1\`  
\- Base head: \`c30d3388eb6c0c56c1d6c9949e68337da1338b8d\`

Перед началом:

\`\`\`bash  
gh pr view 1 \--json headRefOid,url,isDraft,statusCheckRollup  
\`\`\`

PR оставить Draft. Merge и \`accepted\` запрещены.

\#\# Воспроизводимая ошибка

\`\`\`text  
Exception in thread Thread-4 (\_readerthread):  
UnicodeDecodeError: 'utf-8' codec can't decode byte 0xce ...  
\`\`\`

Текущий provider запускает CLI с \`text=True\` и \`encoding="utf-8"\`. CLI на Windows возвращает не-UTF-8 stderr.

\#\# 1\. Создать единый binary subprocess runner

Создать:

\`\`\`text  
services/process\_runner.py  
\`\`\`

Интерфейс:

\`\`\`python  
@dataclass  
class ProcessExecutionResult:  
    args\_safe: list\[str\]  
    returncode: int  
    stdout: str  
    stderr: str  
    stdout\_encoding: str  
    stderr\_encoding: str  
    duration\_seconds: float

def run\_process(  
    args: list\[str\],  
    \*,  
    input\_text: str | None \= None,  
    env: dict\[str, str\] | None \= None,  
    timeout\_seconds: int,  
    secret\_values: list\[str\] | None \= None,  
) \-\> ProcessExecutionResult:  
    ...  
\`\`\`

Обязательная реализация:

\`\`\`python  
subprocess.run(  
    args,  
    input=input\_bytes,  
    stdout=subprocess.PIPE,  
    stderr=subprocess.PIPE,  
    text=False,  
    shell=False,  
    ...  
)  
\`\`\`

Запрещено использовать для CLI \`text=True\` и жёсткое \`encoding="utf-8"\`.

Prompt передавать как UTF-8 bytes:

\`\`\`python  
input\_bytes \= input\_text.encode("utf-8")  
\`\`\`

\#\# 2\. Безопасно декодировать Windows output

Создать:

\`\`\`python  
def decode\_process\_output(  
    data: bytes | None,  
    \*,  
    preferred\_encoding: str | None \= None,  
) \-\> tuple\[str, str\]:  
    ...  
\`\`\`

Требования:

1\. \`None\` и \`b""\` возвращают пустую строку без исключений.  
2\. Поддержать BOM.  
3\. Сначала проверять строгий UTF-8.  
4\. На Windows учитывать:  
   \- \`GetConsoleOutputCP()\`;  
   \- \`GetOEMCP()\`;  
   \- \`locale.getpreferredencoding(False)\`;  
   \- CP866;  
   \- CP1251.  
5\. Не выбирать первую однобайтовую кодировку вслепую.  
6\. При неоднозначности использовать scoring: штраф за replacement/control/box-drawing, приоритет читаемому ASCII/Cyrillic.  
7\. Последний fallback — UTF-8 с \`errors="replace"\`.  
8\. Возвращать имя выбранной кодировки.

Добавить настройку:

\`\`\`text  
ONEBIT\_CLI\_OUTPUT\_ENCODING=auto|utf-8|cp866|cp1251  
\`\`\`

Default: \`auto\`.

\#\# 3\. Перевести все вызовы Newton CLI на единый runner

Использовать \`run\_process()\` для:

\- version;  
\- health;  
\- summarize;  
\- копирования диагностики;  
\- preflight smoke-test;  
\- runtime generation.

Удалить прямые \`subprocess.run()\` Newton CLI из \`ui/settings\_frame.py\` и provider, кроме общего runner.

\#\# 4\. Нормализовать stdout/stderr

После runner гарантировать:

\`\`\`python  
stdout: str  
stderr: str  
\`\`\`

Создать helper:

\`\`\`python  
def safe\_excerpt(value: str | None, limit: int \= 300\) \-\> str:  
    return (value or "")\[:limit\]  
\`\`\`

Запрещены небезопасные операции с потенциальным \`None\`.

\#\# 5\. Классифицировать auth errors

При non-zero exit сначала анализировать декодированный stderr/stdout.

Маппинг:

\`\`\`text  
HTTP 401 \+ Malformed token / Not enough segments  
→ AUTH\_TOKEN\_MALFORMED

HTTP 401 / Unauthorized  
→ AUTH\_FAILED

HTTP 403 / Forbidden  
→ AUTH\_FORBIDDEN

остальной non-zero  
→ CLI\_NONZERO\_EXIT  
\`\`\`

Сообщение для текущего случая:

\`\`\`text  
Токен отклонён сервисом БИТ Ньютон как некорректный JWT.  
Получите новый токен для Newton CLI и повторите проверку.  
\`\`\`

Не утверждать, что output-файл является первопричиной, если CLI завершился с non-zero exit.

Порядок:

\`\`\`text  
subprocess completed  
→ decode stdout/stderr  
→ non-zero exit classification  
→ только при exit=0 проверять output file  
→ JSON parse  
→ schema validation  
\`\`\`

\#\# 6\. Исправить OneBitProviderError

Добавить поля:

\`\`\`python  
stdout\_encoding: str | None  
stderr\_encoding: str | None  
duration\_seconds: float | None  
\`\`\`

Все secrets автоматически redacted.

Пользователь не должен видеть:

\- \`UnicodeDecodeError\`;  
\- \`\_readerthread\`;  
\- \`NoneType\`;  
\- traceback;  
\- токен.

\#\# 7\. Убрать блокировку Tkinter

Проверки version, health и token+LLM выполнять в background worker.

Требования:

1\. Tk callback только запускает worker.  
2\. Кнопки временно disabled.  
3\. Status показывает текущий stage.  
4\. Worker не изменяет Tk widgets напрямую.  
5\. Результат возвращается через \`after()\` или thread-safe queue.  
6\. При закрытии окна результат не обращается к уничтоженному widget.  
7\. Таймаут и Cancel отображаются корректно.

\#\# 8\. Копируемая диагностика

Показывать:

\`\`\`text  
Provider  
Stage  
Code  
CLI path  
Transport  
Model  
Exit code  
stdout encoding  
stderr encoding  
Duration  
Safe stdout  
Safe stderr  
Recommendation  
\`\`\`

Для текущего случая ожидается:

\`\`\`text  
Code: AUTH\_TOKEN\_MALFORMED  
Exit code: 1  
stderr encoding: фактически определённая кодировка  
\`\`\`

Secrets — \`\<redacted\>\`.

\#\# 9\. Исправить root cause в документации

Не утверждать без доказательств:

\`\`\`text  
пустой output распарсили и получили NoneType  
\`\`\`

Зафиксировать:

\`\`\`text  
CLI вернул non-zero/401.  
Принудительное UTF-8 декодирование stderr завершилось ошибкой во внутреннем reader thread.  
stderr мог стать None, после чего небезопасный slice мог породить NoneType.  
\`\`\`

\#\# 10\. Обязательные тесты

Создать:

\`\`\`text  
tests/test\_process\_runner\_encoding.py  
tests/test\_onebit\_auth\_diagnostics.py  
tests/test\_onebit\_gui\_async\_checks.py  
\`\`\`

Тесты:

\`\`\`text  
test\_decode\_utf8\_output  
test\_decode\_utf8\_bom\_output  
test\_decode\_cp1251\_cyrillic\_output  
test\_decode\_cp866\_cyrillic\_output  
test\_decode\_none\_output\_returns\_empty\_string  
test\_decode\_unknown\_bytes\_never\_raises  
test\_runner\_uses\_binary\_pipes  
test\_runner\_returns\_strings\_for\_empty\_pipes  
test\_nonzero\_exit\_cp1251\_stderr\_is\_provider\_error  
test\_nonzero\_exit\_cp866\_stderr\_is\_provider\_error  
test\_malformed\_token\_maps\_to\_auth\_token\_malformed  
test\_unauthorized\_maps\_to\_auth\_failed  
test\_forbidden\_maps\_to\_auth\_forbidden  
test\_stderr\_none\_does\_not\_raise\_none\_type  
test\_stdout\_none\_does\_not\_raise\_none\_type  
test\_output\_file\_not\_checked\_before\_nonzero\_exit  
test\_token\_redacted\_from\_stdout\_stderr  
test\_version\_health\_generate\_use\_same\_runner  
test\_gui\_llm\_check\_does\_not\_block\_main\_thread  
test\_gui\_updates\_via\_after  
test\_gui\_worker\_error\_is\_copyable  
\`\`\`

Не использовать \`assert True\` и условные skip при фактическом дефекте.

\#\# 11\. Windows GUI E2E

Через \`start\_app.bat\`:

\#\#\# A — невалидный токен

1\. Выбрать БИТ Ньютон.  
2\. Ввести тестовый невалидный token локально.  
3\. Нажать \`Проверить токен и LLM\`.  
4\. GUI не зависает.  
5\. В терминале нет \`\_readerthread\` traceback.  
6\. Показан \`AUTH\_TOKEN\_MALFORMED\` или точный auth code.  
7\. Диагностика копируется.  
8\. Токен отсутствует в диагностике.

\#\#\# B — CP1251 fixture

Запустить test CLI fixture, возвращающий русскоязычный stderr в CP1251. Ожидается безопасная строка без traceback.

\#\#\# C — CP866 fixture

Аналогично для CP866.

\#\#\# D — действующий токен

После предоставления нового действующего токена:

1\. real smoke-test;  
2\. schema-valid \`{"status":"ok"}\`;  
3\. local TXT dry-run;  
4\. LLM processing stage;  
5\. protocol artifacts.

Сценарий D нельзя объявлять PASS без действующего токена.

Создать:

\`\`\`text  
docs/opencode/validations/WINDOWS-ONEBIT-ENCODING-E2E-\<SHA\>.md  
\`\`\`

\#\# 12\. Manifest

Добавить:

\`\`\`text  
BB-CRIT-084 — fixed UTF-8 decoding breaks Windows CLI output  
BB-CRIT-085 — reader-thread decode exception escapes provider boundary  
BB-CRIT-086 — stdout/stderr None handled unsafely  
BB-CRIT-087 — auth error masked by decoding infrastructure error  
BB-MAJ-088 — subprocess logic duplicated  
BB-MAJ-089 — encoding regression tests absent  
BB-MAJ-090 — GUI smoke-test blocks Tk main thread  
BB-MAJ-091 — inconsistent output encoding policy  
\`\`\`

Статусы:

\`\`\`text  
active\_task\_id \= TASK-2026-08-02-windows-cli-encoding-auth  
active\_task\_file \= docs/opencode/tasks/TASK-2026-08-02-windows-cli-encoding-auth.md  
status \= in\_progress  
validation\_state \= implementing\_fixes  
BB-CRIT-063 \= USER\_ACTION\_REQUIRED  
\`\`\`

\#\# 13\. Обязательные команды

\`\`\`bash  
python \-m compileall .  
python \-m json.tool docs/opencode/manifest.json  
pytest \-q  
pytest \-q tests/test\_process\_runner\_encoding.py  
pytest \-q tests/test\_onebit\_auth\_diagnostics.py  
pytest \-q tests/test\_onebit\_gui\_async\_checks.py  
ruff check .  
mypy . \--ignore-missing-imports  
\`\`\`

Windows:

\`\`\`cmd  
call start\_app.bat \--startup-check  
\`\`\`

\#\# 14\. Ответ OpenCode

Предоставить:

1\. exact \`headRefOid\`;  
2\. Draft PR URL;  
3\. workflow run;  
4\. результаты команд;  
5\. созданные test files;  
6\. единый process runner;  
7\. фактически выбранную кодировку stderr;  
8\. результат invalid-token E2E;  
9\. отсутствие \`\_readerthread\` traceback;  
10\. auth error code;  
11\. результат CP1251 fixture;  
12\. результат CP866 fixture;  
13\. подтверждение async GUI;  
14\. путь к validation-файлу;  
15\. подтверждение отсутствия токена;  
16\. статус real E2E с действующим токеном;  
17\. ограничения.

PR оставить Draft. Merge и \`accepted\` запрещены.  
