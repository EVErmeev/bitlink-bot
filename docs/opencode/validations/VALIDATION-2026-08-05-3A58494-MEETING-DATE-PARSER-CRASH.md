\# VALIDATION-2026-08-05-3A58494-MEETING-DATE-PARSER-CRASH

\#\# 1\. Объект проверки

Репозиторий: https://github.com/EVErmeev/bitlink-bot

Draft PR: https://github.com/EVErmeev/bitlink-bot/pull/1

Ветка: \`fix/audit-e7cc95f\`

Проверенный remote head:

\`3a58494583620d7424da7a4371156be477d5952b\`

Ошибка:

\`\`\`text  
ValueError: month must be in 1..12, not 15  
\`\`\`

Сценарий:

\`\`\`text  
локальное видео \-\> транскрибация \-\> project\_standard  
\`\`\`

\#\# 2\. Итоговый статус

\`\`\`text  
CHANGES\_REQUIRED  
\`\`\`

Предыдущая итерация по title/context/paragraph rendering запушена, но реальный пользовательский запуск выявил отдельный блокирующий дефект metadata parser. Standard protocol не формируется, потому что обработка падает до транскрибации и LLM generation.

\#\# 3\. Классификация

\`\`\`text  
Severity: CRITICAL  
Type: unhandled exception / filename parsing / pipeline blocker  
Scope: local video and potentially local transcript  
Regression area: meeting\_metadata.py  
\`\`\`

\#\# 4\. Подтверждённая причина

В \`meeting\_metadata.py\`:

1\. \`DD\_MM\_YY\_HH\_MM\_SS\` проверяется первым.  
2\. Используется \`regex.search()\` без строгих цифровых границ.  
3\. После совпадения сразу вызываются \`date()\` и \`time()\`.  
4\. \`ValueError\` не перехватывается.  
5\. Невалидный кандидат не позволяет перейти к другим форматам или \`file\_metadata\`.

Из-за этого число \`15\` из имени файла было использовано как месяц.

\#\# 5\. Дополнительный скрытый риск

Для имени:

\`\`\`text  
2026\_07\_24\_09\_14\_30\_video.mp4  
\`\`\`

старый \`DD\_MM\_YY\_HH\_MM\_SS\` regex способен начать совпадение с хвоста четырёхзначного года:

\`\`\`text  
26\_07\_24\_09\_14\_30  
\`\`\`

и получить:

\`\`\`text  
day=26  
month=7  
year=2024  
\`\`\`

вместо:

\`\`\`text  
2026-07-24 09:14  
\`\`\`

Дефект может давать не только исключение, но и тихо неверную дату.

\#\# 6\. Недостаточность текущих тестов

Текущие тесты проверяют преимущественно валидные имена. Отсутствуют проверки:

\- invalid month/day/hour/minute;  
\- несуществующая календарная дата;  
\- ISO filename с секундами;  
\- fallback после невалидного filename;  
\- отсутствие исключения на произвольном имени;  
\- использование оригинального имени видео вместо transcript/hash имени.

Существующий тест одного ISO-формата проверяет только год и может не обнаружить перестановку дня и года.

\#\# 7\. Ожидаемое поведение

\`\`\`text  
invalid filename candidate  
\-\> candidate rejected  
\-\> next format or metadata fallback  
\-\> no raw exception  
\-\> processing continues  
\`\`\`

При полном отсутствии даты:

\`\`\`text  
meeting\_date \= None  
meeting\_time \= None  
\`\`\`

Pipeline должен продолжить работу либо вернуть управляемую validation, но не traceback.

\#\# 8\. Требуемая задача

Выполнить:

\`\`\`text  
TASK-2026-08-05-3A58494-SAFE-MEETING-DATE-PARSING.md  
\`\`\`

\#\# 9\. Условия повторной проверки

Статус можно изменить после подтверждения:

1\. Безопасного parser для всех форматов.  
2\. Строгих границ regex.  
3\. Приоритета четырёхзначного года.  
4\. Перехвата \`ValueError\` внутри parser.  
5\. Fallback на metadata.  
6\. Negative tests.  
7\. ISO-with-seconds regression test.  
8\. Реального E2E на том же проблемном видео.  
9\. Успешного standard generation.  
10\. Отсутствия регрессии detailed.  
11\. Нового remote head.

До этого:

\`\`\`text  
CHANGES\_REQUIRED  
\`\`\`

PR оставить Draft. Merge не выполнять. \`accepted\` не устанавливать.  
