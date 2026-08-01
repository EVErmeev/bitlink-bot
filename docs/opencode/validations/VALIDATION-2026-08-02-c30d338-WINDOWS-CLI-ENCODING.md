\# VALIDATION-2026-08-02-c30d338-WINDOWS-CLI-ENCODING

\#\# Объект проверки

\- Repository: \`EVErmeev/bitlink-bot\`  
\- Draft PR: \`https://github.com/EVErmeev/bitlink-bot/pull/1\`  
\- Проверенный head: \`c30d3388eb6c0c56c1d6c9949e68337da1338b8d\`  
\- Сценарий: кнопка \`Проверить токен и LLM\` для \`onebit\_newton\_cli\` на Windows.  
\- Фактическая ошибка:

\`\`\`text  
Exception in thread Thread-4 (\_readerthread)  
UnicodeDecodeError: 'utf-8' codec can't decode byte 0xce ...  
\`\`\`

\#\# Вердикт

\`CHANGES\_REQUIRED\`

PR оставить Draft. Merge и \`accepted\` запрещены.

\#\# Как проводился аудит

1\. Независимо проверен фактический \`headRefOid\` PR.  
2\. Проверен diff между \`e454652\` и \`c30d338\`.  
3\. Проверены:  
   \- \`services/llm\_providers.py\`;  
   \- \`ui/settings\_frame.py\`;  
   \- список реально изменённых файлов;  
   \- наличие новых regression tests.  
4\. Пользовательский traceback сопоставлен с фактическими параметрами \`subprocess.run()\`.  
5\. Проверен порядок обработки:

\`\`\`text  
subprocess reader thread  
→ decode stdout/stderr  
→ CompletedProcess  
→ returncode handling  
→ provider diagnostics  
\`\`\`

\#\# Подтверждённая причина текущей ошибки

В \`OneBitNewtonCLIProvider.generate()\` используется:

\`\`\`python  
subprocess.run(  
    ...,  
    capture\_output=True,  
    text=True,  
    encoding="utf-8",  
)  
\`\`\`

Windows CLI вернул байты не в UTF-8. Декодирование выполняется внутри служебного \`\_readerthread\`, поэтому \`UnicodeDecodeError\` возникает раньше provider-specific обработки ошибок.

Байт \`0xCE\` допустим в однобайтовых Windows-кодировках, но недопустим в указанной позиции UTF-8. Исходную кодировку требуется определять безопасно.

\#\# Почему предыдущая причина \`NoneType\` не доказана

OpenCode сообщил:

\`\`\`text  
CLI вернул 401, output-файл был пустым,  
код пытался распарсить пустую строку → NoneType.  
\`\`\`

Фактический код выполняет другую последовательность:

1\. после \`subprocess.run()\` проверяет \`returncode\`;  
2\. при \`returncode \!= 0\` сразу формирует \`CLI\_NONZERO\_EXIT\`;  
3\. проверка output-файла выполняется позже;  
4\. пустой файл не передаётся в JSON parser.

После падения reader thread \`result.stderr\` может оказаться \`None\`. Операция:

\`\`\`python  
result.stderr\[:300\]  
\`\`\`

сама способна вызвать:

\`\`\`text  
'NoneType' object is not subscriptable  
\`\`\`

Следовательно, HTTP 401 может быть реальным, но исходный \`NoneType\` мог быть вызван ошибкой декодирования и небезопасной обработкой \`stderr=None\`.

\#\# Новые замечания

\#\#\# BB-CRIT-084 — CLI output принудительно декодируется как UTF-8

Windows \`.cmd\` может возвращать UTF-8, CP866, CP1251 или текущую console code page.

\#\#\# BB-CRIT-085 — decode exception возникает вне provider boundary

Исключение падает во внутреннем \`\_readerthread\` и печатает traceback в терминал.

\#\#\# BB-CRIT-086 — stdout/stderr считаются обязательными строками

Используются небезопасные операции \`stderr\[:300\]\` и \`stdout.strip()\` без нормализации \`None\`.

\#\#\# BB-CRIT-087 — auth error маскируется инфраструктурной ошибкой

Пользователь должен видеть \`AUTH\_TOKEN\_MALFORMED\` или \`AUTH\_FAILED\`, а не traceback Python.

\#\#\# BB-MAJ-088 — subprocess-логика дублируется

Отдельные вызовы находятся в provider и Settings GUI для version, health и diagnostics.

\#\#\# BB-MAJ-089 — encoding regression tests отсутствуют

Между предыдущим и текущим head не добавлены требовавшиеся тестовые файлы. Общее число тестов осталось \`226\`.

\#\#\# BB-MAJ-090 — real LLM smoke-test блокирует Tkinter main thread

Кнопка синхронно вызывает \`subprocess.run()\` с таймаутом до 120 секунд в Tk callback.

\#\#\# BB-MAJ-091 — кодировки используются непоследовательно

\`generate()\` жёстко использует UTF-8, а version/health полагаются на локаль Python.

\#\# Ожидаемое поведение

При stderr в CP1251 или CP866 приложение должно:

1\. не печатать traceback reader thread;  
2\. получить return code;  
3\. безопасно декодировать stderr;  
4\. распознать HTTP 401;  
5\. показать копируемое сообщение:

\`\`\`text  
Проверка БИТ Ньютон не пройдена.  
Код: AUTH\_TOKEN\_MALFORMED  
Этап: cli\_execution  
CLI exit code: 1  
Причина: токен отклонён сервисом как некорректный JWT.  
\`\`\`

Токен в сообщение не включать.

\#\# Security

Ранее раскрытый токен остаётся скомпрометированным:

\`\`\`text  
BB-CRIT-063 \= USER\_ACTION\_REQUIRED  
\`\`\`

Для production E2E требуется новый действующий токен БИТ Ньютон CLI.  
