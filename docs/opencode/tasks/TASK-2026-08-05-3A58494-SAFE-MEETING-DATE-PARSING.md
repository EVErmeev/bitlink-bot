\# TASK-2026-08-05-3A58494-SAFE-MEETING-DATE-PARSING

\#\# 1\. Контекст

Репозиторий: https://github.com/EVErmeev/bitlink-bot

Draft PR: https://github.com/EVErmeev/bitlink-bot/pull/1

Ветка: \`fix/audit-e7cc95f\`

Последний независимо проверенный remote head:

\`3a58494583620d7424da7a4371156be477d5952b\`

Ошибка воспроизводится при обработке локального видео по шаблону \`project\_standard\`:

\`\`\`text  
ValueError: month must be in 1..12, not 15  
\`\`\`

Стек:

\`\`\`text  
services/processing\_service.py \-\> determine\_meeting\_date()  
meeting\_metadata.py \-\> extract\_date\_from\_filename()  
date(y, m, d)  
\`\`\`

PR оставить Draft. Merge не выполнять. \`accepted\` не устанавливать.

\#\# 2\. Цель

Исправить определение даты и времени встречи из имени локального файла так, чтобы:

1\. Некорректное или неоднозначное имя файла не приводило к падению обработки.  
2\. ISO-имена с четырёхзначным годом не распознавались как \`DD\_MM\_YY\`.  
3\. Время, длительность, номер и hash не принимались за дату.  
4\. Невалидный кандидат из filename не блокировал fallback на metadata.  
5\. Транскрибация и генерация standard/detailed продолжались при нераспознанной дате.  
6\. Пользователь не видел raw traceback.

\#\# 3\. Подтверждённая корневая причина

В \`meeting\_metadata.py\` шаблон \`DD\_MM\_YY\_HH\_MM\_SS\` проверяется раньше ISO-шаблонов и использует \`search()\` без строгих цифровых границ.

Текущий порядок:

\`\`\`text  
DD\_MM\_YY\_HH\_MM\_SS  
DD.MM.YYYY  
YYYY-MM-DD...  
\`\`\`

После совпадения сразу вызываются \`date()\` и \`time()\`, а \`ValueError\` не перехватывается. Ошибка одного кандидата прерывает весь fallback pipeline.

Дополнительный скрытый дефект: имя

\`\`\`text  
2026\_07\_24\_09\_14\_30\_video.mp4  
\`\`\`

может быть ошибочно сопоставлено как:

\`\`\`text  
26\_07\_24\_09\_14\_30  
\`\`\`

и дать \`2024-07-26 09:14\` вместо \`2026-07-24 09:14\`.

\#\# 4\. Целевой контракт

\`extract\_date\_from\_filename(filepath)\` должен:

\- всегда возвращать \`(date | None, time | None)\`;  
\- не выбрасывать \`ValueError\` для пользовательского имени;  
\- принимать только валидный кандидат;  
\- при невалидном кандидате переходить к следующему формату;  
\- при отсутствии валидного кандидата возвращать \`(None, None)\`.

\`determine\_meeting\_date()\` должен сохранять приоритет:

\`\`\`text  
user\_date  
bitlink\_metadata  
валидная дата из filename  
file\_metadata  
None  
\`\`\`

\#\# 5\. Переписать parser на явные форматы

Поддержать минимум:

\`\`\`text  
YYYY\_MM\_DD\_HH\_MM\_SS  
YYYY-MM-DD-HH-MM-SS  
YYYY.MM.DD.HH.MM.SS  
YYYY\_MM\_DD\_HH\_MM  
YYYY-MM-DDTHH-MM  
YYYY\_MM\_DD  
YYYY-MM-DD  
YYYY.MM.DD  
DD\_MM\_YY\_HH\_MM\_SS  
DD-MM-YY-HH-MM-SS  
DD.MM.YYYY  
DD\_MM\_YYYY  
DD-MM-YYYY  
\`\`\`

Порядок:

1\. Форматы с четырёхзначным годом и временем.  
2\. Форматы с четырёхзначным годом без времени.  
3\. \`DD.MM.YYYY\` / \`DD\_MM\_YYYY\`.  
4\. Форматы с двухзначным годом — последними.

Для всех regex использовать границы:

\`\`\`regex  
(?\<\!\\d)  
...  
(?\!\\d)  
\`\`\`

Кандидат не должен быть частью более длинной цифровой последовательности.

\#\# 6\. Безопасная валидация кандидата

Создать внутреннюю функцию, например:

\`\`\`python  
def \_safe\_build\_datetime\_candidate(  
    \*, year: int, month: int, day: int,  
    hour: int | None \= None,  
    minute: int | None \= None,  
    second: int | None \= None,  
) \-\> tuple\[date | None, time | None\]:  
    ...  
\`\`\`

Требования:

\- \`date()\` и \`time()\` остаются окончательной календарной валидацией;  
\- \`ValueError\` перехватывается внутри parser;  
\- невалидный кандидат возвращает \`(None, None)\`;  
\- значения нельзя автоматически переставлять, ограничивать или заменять текущей датой.

\#\# 7\. Обязательные regression cases

\`\`\`text  
2026\_07\_24\_09\_14\_30\_video.mp4 \-\> 2026-07-24 09:14  
2026\_08\_05\_15\_30\_45\_recording.mp4 \-\> 2026-08-05 15:30  
31\_07\_26\_14\_06\_05\_recording.mp4 \-\> 2026-07-31 14:06  
31.07.2026\_protocol.docx \-\> 2026-07-31, time=None  
\`\`\`

DD\_MM\_YY parser не должен начинать совпадение с \`26\_08\_05...\` внутри \`2026\_08\_05...\`.

\#\# 8\. Невалидные имена не должны падать

Проверить минимум:

\`\`\`text  
15\_15\_26\_10\_30\_00\_video.mp4  
31\_15\_26\_10\_30\_00\_video.mp4  
2026\_15\_31\_10\_30\_00\_video.mp4  
2026\_02\_30\_10\_30\_00\_video.mp4  
2026\_08\_05\_25\_30\_00\_video.mp4  
2026\_08\_05\_15\_70\_00\_video.mp4  
local-872b2e3cdd76beb0\_transcript.txt  
meeting\_15\_30\_45\_recording.mp4  
recording\_01\_30\_15\_22\_44\_99.mp4  
\`\`\`

Ожидается \`(None, None)\` либо валидный результат другого однозначного формата. Исключение наружу не выходит.

\#\# 9\. Использовать оригинальное имя видео

Проверить pipeline локального видео. Дата должна определяться из оригинального пользовательского имени, а не из:

\- временного файла;  
\- hash-имени;  
\- промежуточной расшифровки;  
\- \`local-\<hash\>\_transcript.txt\`;  
\- output-файла Newton.

Если объект очереди хранит \`source\_path\`, \`original\_filename\`, \`display\_name\`, \`transcript\_path\`, использовать исходное имя до транскрибации.

В debug сохранять только basename, без полного локального пути.

\#\# 10\. Fallback на metadata

Для:

\`\`\`text  
31\_15\_26\_10\_30\_00\_video.mp4  
\`\`\`

и:

\`\`\`python  
file\_metadata={"date": "2026-08-05"}  
\`\`\`

ожидается дата \`2026-08-05\`.

Невалидный filename должен быть проигнорирован.

\#\# 11\. Поведение при полном отсутствии даты

Отсутствие даты не должно блокировать:

\- транскрибацию;  
\- LLM generation;  
\- standard protocol;  
\- detailed protocol;  
\- локальный HTML.

Использовать:

\`\`\`text  
meeting\_date \= None  
meeting\_time \= None  
meeting\_date\_source \= unresolved  
\`\`\`

Пользовательское сообщение:

\`\`\`text  
Дата встречи не определена автоматически. Обработка продолжена без даты; проверьте имя файла или metadata источника.  
\`\`\`

Если публикация требует дату для title, вернуть управляемую validation, а не traceback.

\#\# 12\. Диагностика

Сформировать безопасный объект:

\`\`\`json  
{  
  "meeting\_date": "2026-08-05",  
  "meeting\_time": "15:30",  
  "source": "filename",  
  "matched\_format": "YYYY\_MM\_DD\_HH\_MM\_SS",  
  "filename\_basename": "2026\_08\_05\_15\_30\_45\_recording.mp4",  
  "invalid\_candidates\_count": 0,  
  "fallback\_used": false  
}  
\`\`\`

Для невалидного имени значения даты/времени и \`matched\_format\` равны \`null\`, \`invalid\_candidates\_count \> 0\`, \`fallback\_used=true\`.

\#\# 13\. Тесты

Расширить \`tests/test\_meeting\_metadata.py\`. При необходимости добавить:

\`\`\`text  
tests/test\_meeting\_metadata\_invalid\_filenames.py  
tests/test\_video\_date\_metadata\_pipeline.py  
\`\`\`

Обязательные тесты:

\`\`\`text  
test\_iso\_with\_seconds\_is\_not\_parsed\_as\_dd\_mm\_yy  
test\_iso\_2026\_08\_05\_15\_30\_45  
test\_dd\_mm\_yy\_with\_time\_is\_supported  
test\_invalid\_month\_does\_not\_raise  
test\_invalid\_day\_does\_not\_raise  
test\_invalid\_hour\_does\_not\_raise  
test\_invalid\_minute\_does\_not\_raise  
test\_invalid\_calendar\_date\_does\_not\_raise  
test\_time\_only\_filename\_is\_not\_date  
test\_hash\_filename\_is\_not\_date  
test\_invalid\_filename\_falls\_back\_to\_file\_metadata  
test\_original\_video\_filename\_is\_used\_for\_date\_resolution  
test\_transcript\_hash\_filename\_is\_not\_used\_as\_original\_source  
test\_determine\_meeting\_date\_never\_leaks\_value\_error  
test\_standard\_generation\_continues\_when\_date\_unresolved  
test\_detailed\_generation\_continues\_when\_date\_unresolved  
\`\`\`

Добавить параметризованный набор минимум из 50 произвольных имён с правилом:

\`\`\`text  
extract\_date\_from\_filename(name) never raises  
\`\`\`

Усилить существующий \`test\_date\_from\_slash\_format\`: проверить год, месяц, день, час и минуту. Добавить вариант с секундами.

\#\# 14\. Проверки

\`\`\`text  
python \-m compileall .  
pytest \-q tests/test\_meeting\_metadata.py  
pytest \-q tests/test\_meeting\_metadata\_invalid\_filenames.py  
pytest \-q tests/test\_video\_date\_metadata\_pipeline.py  
pytest \-q  
ruff check .  
mypy . \--ignore-missing-imports  
call start\_app.bat \--startup-check  
\`\`\`

Если \`ruff\` или \`mypy\` отсутствуют, установить dev dependencies проекта, а не пропускать проверку.

\#\# 15\. Реальный Windows E2E

Запустить:

\`\`\`text  
call start\_app.bat  
\`\`\`

1\. Выбрать то же видео, на котором возникла ошибка.  
2\. Выбрать \`project\_standard\`.  
3\. Запустить транскрибацию.  
4\. Дождаться LLM generation.  
5\. Проверить дату и title.  
6\. Выполнить публикацию Confluence, Telegram и DOCX, если подключения доступны.

Ожидается:

\`\`\`text  
ValueError отсутствует  
транскрибация завершена  
standard protocol сформирован  
\`\`\`

Проверка только unit-тестами без запуска проблемного видео недостаточна.

\#\# 16\. Артефакты

Сохранить:

\`\`\`text  
docs/opencode/evidence/2026-08-05-3A58494-SAFE-MEETING-DATE-PARSING/  
\`\`\`

Минимум:

\`\`\`text  
date\_parser\_cases.json  
invalid\_filename\_cases.json  
date\_resolution\_debug.json  
video\_e2e\_result.json  
standard\_protocol\_final.json  
standard\_protocol\_final.html  
\`\`\`

\#\# 17\. Критерии приёмки

1\. Ошибка \`month must be in 1..12\` не воспроизводится.  
2\. Любое имя файла обрабатывается без необработанного \`ValueError\`.  
3\. ISO с секундами не интерпретируется как \`DD\_MM\_YY\`.  
4\. Невалидный filename не блокирует fallback.  
5\. Используется оригинальное имя видео.  
6\. Standard завершается на контрольном видео.  
7\. Detailed не сломан.  
8\. Добавлены negative/regression tests.  
9\. Выполнены startup-check и реальный E2E.  
10\. Изменения запушены, PR остаётся Draft.

\#\# 18\. Итоговая validation

Создать:

\`\`\`text  
docs/opencode/validations/VALIDATION-2026-08-05-\<NEW\_HEAD\_SHORT\>-SAFE-MEETING-DATE-PARSING-E2E.md  
\`\`\`

\#\# 19\. Ответ OpenCode

Предоставить:

1\. Remote head до/после.  
2\. Commit SHA.  
3\. Basename проблемного файла.  
4\. Какой старый regex совпал и какие группы извлёк.  
5\. Новый порядок форматов.  
6\. Результаты negative cases и ISO-with-seconds regression.  
7\. Результаты compileall, pytest, ruff, mypy, startup-check.  
8\. Результат реального E2E на проблемном видео.  
9\. Определённые дату и время.  
10\. Confluence URL, Telegram ID и DOCX path, если публикация включена.  
11\. Путь к итоговой validation.  
12\. Подтверждение Draft/no merge/no accepted.

Не писать «готово», если реальный запуск проблемного видео не выполнен.  
