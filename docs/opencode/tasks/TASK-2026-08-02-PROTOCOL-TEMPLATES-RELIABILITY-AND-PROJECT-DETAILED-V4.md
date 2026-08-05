\# TASK-2026-08-02-PROTOCOL-TEMPLATES-RELIABILITY-AND-PROJECT-DETAILED-V4

\#\# 1\. Цель

Исправить формирование протоколов по всем зарегистрированным шаблонам.

Приоритеты:

1\. Исправить структуру и оформление \`project\_detailed\`.  
2\. Устранить падение \`management\_summary\` на невалидном JSON.  
3\. Обеспечить базовую работоспособность \`project\_standard\` и \`business\_process\_discovery\`.  
4\. Не сломать Confluence, Telegram, выбор шаблона и advisory Quality Gate.

\#\# 2\. Репозиторий

\- Репозиторий: \`EVErmeev/bitlink-bot\`  
\- Ветка: \`fix/audit-e7cc95f\`  
\- Draft PR: \`https://github.com/EVErmeev/bitlink-bot/pull/1\`  
\- Проверенный base head: \`4dd1402cbcbc81a4e19fc65713fac79f57e9e57c\`

Перед изменениями получить фактический \`headRefOid\`. Если он изменился, изучить diff.

PR оставить Draft. Merge не выполнять. \`accepted\` не устанавливать.

\#\# 3\. Контрольный материал

Использовать приложенный экспорт:

\`\`\`text  
Встреча\_в\_Телемосте\_31\_07\_26\_14\_06\_05\_запись\_transcript.txt.doc  
\`\`\`

Ожидаемые дата и время из имени файла:

\`\`\`text  
31.07.2026  
14:06  
\`\`\`

\#\# 4\. Общий нормализатор метаданных

Создать общий механизм, используемый всеми шаблонами.

Приоритет источников:

1\. значения, заданные пользователем;  
2\. метаданные источника;  
3\. имя файла;  
4\. явная дата/время в расшифровке;  
5\. LLM только при отсутствии детерминированных данных.

Поддержать форматы:

\`\`\`text  
2026\_07\_31\_14\_06  
2026-07-31 14-06  
31\_07\_26\_14\_06\_05  
31.07.2026 14-06-05  
31-07-2026\_14-06  
\`\`\`

Для двухзначного года: \`00–79 → 2000–2079\`, \`80–99 → 1980–1999\`.

В HTML выводить \`31.07.2026\` и \`14:06\`. В JSON хранить ISO.

\#\# 5\. Смысловой заголовок и summary

Разделить:

\`\`\`text  
protocol\_title  
meeting\_summary  
\`\`\`

\`protocol\_title\`:

\- формируется по смыслу встречи;  
\- 5–14 слов, максимум 140 символов;  
\- не содержит расширение, \`\_transcript\`, слово «запись», технические идентификаторы;  
\- не является абзацем или summary;  
\- не повторяет дату.

Для контрольной встречи допустим заголовок:

\`\`\`text  
Разбор складских процессов, маркировки и работы с ТСД  
\`\`\`

Заголовок Confluence:

\`\`\`text  
Протокол встречи от 31.07.2026. \<protocol\_title\>  
\`\`\`

\`meeting\_summary\` выводить отдельным блоком.

Если LLM title недопустим, выполнить отдельный короткий запрос на заголовок; затем использовать очищенное имя файла как последний fallback.

\#\# 6\. Общий contract \`general\_info\`

Все шаблоны должны поддерживать:

\`\`\`json  
{  
  "general\_info": {  
    "meeting\_date": "2026-07-31",  
    "meeting\_time": "14:06",  
    "protocol\_title": "Разбор складских процессов, маркировки и работы с ТСД",  
    "meeting\_summary": "..."  
  }  
}  
\`\`\`

Создать общий mapper, который:

\- читает вложенный \`general\_info\`;  
\- поддерживает legacy top-level aliases;  
\- применяет детерминированные date/time поверх LLM;  
\- очищает title;  
\- не затирает заполненные поля пустыми строками.

\#\# 7\. Исправление \`project\_detailed\`

\#\#\# 7.1. Целевая структура

\`\`\`json  
{  
  "general\_info": {},  
  "participants": \[\],  
  "meeting\_goal": "",  
  "initial\_context": "",  
  "key\_outcomes": \[\],  
  "topic\_blocks": \[\],  
  "current\_state": \[\],  
  "decisions": \[\],  
  "questions": \[\],  
  "risks": \[\],  
  "tasks": \[\]  
}  
\`\`\`

\#\#\# 7.2. Цель и контекст

Не использовать одно поле для двух разделов.

\- \`meeting\_goal\` — зачем проводилась встреча и какой результат ожидался;  
\- \`initial\_context\` — ситуация к началу встречи и исходные ограничения.

Если тексты совпадают более чем на 80%, не выводить дубль.

\#\#\# 7.3. Ключевые итоги

\`key\_outcomes\` должен быть массивом строк. Рендерить через \`\<ul\>\<li\>...\</li\>\</ul\>\`.

Поддержать legacy string: распознавать переносы, \`1.\`, \`-\`, \`•\` и нормализовать в список.

\#\#\# 7.4. Тематические блоки

Целевая схема элемента:

\`\`\`json  
{  
  "title": "",  
  "discussion\_points": \[\],  
  "conclusion\_points": \[\],  
  "status": {  
    "state": "",  
    "reason": "",  
    "next\_action": "",  
    "responsible": "",  
    "deadline": ""  
  },  
  "source\_item\_ids": \[\]  
}  
\`\`\`

Поддержать legacy-поля \`discussion\_content\`, \`conclusion\`, \`status\_text\` и остальные \`status\_\*\`.

Рендерить тезисами и абзацами, а не стеной текста. Визуально отделить обсуждение, итог и статус.

\#\#\# 7.5. Текущее состояние

Использовать массив:

\`\`\`json  
\[  
  {  
    "object\_or\_process": "",  
    "state": "",  
    "issues": \[\],  
    "next\_step": ""  
  }  
\]  
\`\`\`

Рендерить таблицей или карточками. Поддержать legacy string.

\#\#\# 7.6. Полные схемы реестров

Описать \`items.properties\` для решений, вопросов, рисков и задач.

Решение:

\`\`\`text  
decision\_text, context\_and\_basis, agreed\_scope, boundaries,  
responsible, deadline, related\_topic, explicit\_agreement,  
confidence, evidence  
\`\`\`

Вопрос:

\`\`\`text  
question\_text, context, known\_info, to\_determine,  
responsible, deadline, next\_action, status, related\_topic  
\`\`\`

Риск:

\`\`\`text  
risk\_type, risk\_text, reason, impact, trigger\_condition,  
measures, responsible, deadline, status, related\_topic  
\`\`\`

Задача:

\`\`\`text  
task\_text, basis, expected\_result, responsible, co\_executors,  
deadline, dependencies, status, related\_topic, commitment\_confirmed  
\`\`\`

Mapper должен поддерживать aliases:

\`\`\`text  
decision/text/description  
question/open\_item/description  
risk/description/type  
task/action/description  
\`\`\`

Не присваивать всем решениям автоматически \`explicit\_agreement=true\` и \`confidence=0.9\`.  
Не присваивать всем задачам автоматически \`commitment\_confirmed=true\`.

Приоритет наполнения:

1\. массивы LLM;  
2\. atomic items как fallback;  
3\. не создавать фиктивные строки.

\#\#\# 7.7. Пустые разделы

Не выводить таблицу только с заголовками. Если список пуст, скрыть раздел либо вывести короткое сообщение без пустой таблицы.

\#\#\# 7.8. HTML

\- применять \`html.escape()\` ко всем данным LLM;  
\- использовать \`\<ul\>/\<ol\>\` для списков;  
\- разбивать длинные тексты на абзацы;  
\- широкие таблицы помещать в горизонтальный контейнер;  
\- локальный preview и Confluence storage HTML должны иметь одинаковую структуру.

\#\# 8\. Устойчивый JSON pipeline

\#\#\# 8.1. Provider возвращает raw

\`LLMProvider.generate()\` должен возвращать raw text. Provider не должен окончательно прерывать schema generation после первого \`JSONDecodeError\`.

\#\#\# 8.2. Parser и repair

Вынести обработку в отдельный модуль, например:

\`\`\`text  
services/json\_response\_parser.py  
\`\`\`

Последовательность:

1\. сохранить raw response;  
2\. убрать BOM и markdown fences;  
3\. извлечь один сбалансированный JSON object;  
4\. выполнить \`json.loads()\`;  
5\. выполнить schema validation;  
6\. при ошибке сформировать repair prompt;  
7\. повторить запрос с исходной ошибкой, raw JSON и точной schema;  
8\. максимум три попытки.

Repair prompt:

\`\`\`text  
Исправь только синтаксис и структуру JSON.  
Не изменяй фактическое содержание.  
Ошибка: \<error\>  
Верни только один JSON object без markdown.  
Схема: \<schema\>  
Исходный ответ: \<raw\>  
\`\`\`

Сохранять:

\`\`\`text  
llm\_attempt\_1\_raw.txt  
llm\_attempt\_1\_parse\_error.txt  
llm\_attempt\_2\_raw.txt  
llm\_attempt\_2\_schema\_errors.json  
llm\_final\_parsed.json  
\`\`\`

После исчерпания попыток возвращать \`LLM\_JSON\_INVALID\_AFTER\_REPAIR\` с line/column/char, template ID и путём к raw artifact.

\#\# 9\. \`management\_summary\`

Целевая структура:

\`\`\`json  
{  
  "general\_info": {},  
  "participants": \[\],  
  "executive\_summary": {  
    "overall\_status": "",  
    "summary": "",  
    "key\_changes": \[\]  
  },  
  "key\_results": \[\],  
  "decisions": \[\],  
  "risks\_and\_blockers": \[\],  
  "escalations": \[\],  
  "actions": \[\],  
  "next\_control\_points": \[\]  
}  
\`\`\`

Полностью описать элементы массивов и смэппировать все поля.

Atomic items использовать только как fallback.

Ошибка контрольного запуска:

\`\`\`text  
Expecting ',' delimiter: line 1 column 9405  
\`\`\`

должна запускать repair/retry, а не немедленно завершать элемент.

Недостаточный объём в advisory-режиме — warning, не generation failure.

\#\# 10\. Остальные шаблоны

\#\#\# \`project\_standard\`

Обеспечить metadata, semantic title, полные схемы массивов, полный mapper, корректный HTML, скрытие пустых таблиц и JSON repair/retry.

\#\#\# \`business\_process\_discovery\`

Обеспечить metadata, semantic title, полные схемы AS-IS, ролей, систем, шагов, проблем, требований, интеграций, решений, вопросов, рисков и задач. Не создавать искусственные требования и разрывы.

\#\# 11\. Общая совместимость

Реестр содержит четыре шаблона:

\`\`\`text  
management\_summary  
project\_standard  
project\_detailed  
business\_process\_discovery  
\`\`\`

На одной контрольной расшифровке каждый должен:

1\. получить raw LLM response;  
2\. получить schema-valid JSON после repair при необходимости;  
3\. собрать \`Protocol\`;  
4\. сформировать непустой HTML;  
5\. сохранить artifacts;  
6\. завершиться \`completed\` или \`completed\_with\_warnings\` в dry-run;  
7\. не завершаться необработанным исключением.

\#\# 12\. Тесты

Создать:

\`\`\`text  
tests/test\_meeting\_metadata\_filename\_formats.py  
tests/test\_common\_protocol\_metadata.py  
tests/test\_semantic\_protocol\_title.py  
tests/test\_project\_detailed\_v4\_mapping.py  
tests/test\_project\_detailed\_v4\_render.py  
tests/test\_json\_response\_repair.py  
tests/test\_management\_summary\_generation.py  
tests/test\_all\_templates\_smoke.py  
tests/test\_template\_empty\_sections.py  
tests/test\_template\_html\_escaping.py  
\`\`\`

Обязательные проверки:

\`\`\`text  
test\_extracts\_dd\_mm\_yy\_hh\_mm\_ss  
test\_control\_filename\_returns\_2026\_07\_31\_14\_06  
test\_deterministic\_date\_overrides\_llm\_date  
test\_semantic\_title\_does\_not\_use\_filename  
test\_semantic\_title\_is\_not\_summary  
test\_general\_info\_nested\_mapping  
test\_goal\_and\_context\_are\_not\_duplicates  
test\_key\_outcomes\_render\_as\_list  
test\_topic\_discussion\_renders\_as\_readable\_points  
test\_current\_state\_renders\_structured  
test\_llm\_decisions\_are\_mapped  
test\_llm\_questions\_are\_mapped  
test\_llm\_risks\_are\_mapped  
test\_llm\_tasks\_are\_mapped  
test\_alias\_fields\_are\_mapped  
test\_empty\_tables\_are\_hidden  
test\_provider\_returns\_raw\_invalid\_json  
test\_generate\_json\_retries\_after\_provider\_json\_error  
test\_json\_missing\_comma\_is\_repaired\_by\_retry  
test\_raw\_attempt\_is\_preserved  
test\_management\_summary\_control\_transcript\_completes  
test\_project\_standard\_control\_transcript\_completes  
test\_business\_process\_discovery\_control\_transcript\_completes  
test\_all\_registered\_templates\_render\_nonempty\_html  
test\_html\_escapes\_llm\_content  
\`\`\`

Запрещено использовать \`assert True\`.

\#\# 13\. Регрессия по приложенному протоколу

Повторно обработать ту же расшифровку с \`project\_detailed\`.

Ожидается:

\`\`\`text  
Дата: 31.07.2026  
Время: 14:06  
Заголовок: смысловой, не имя файла  
Summary: отдельный блок  
Цель и исходный контекст: не дублируются  
Ключевые итоги: оформленный список  
Тематические блоки: читаемые пункты/абзацы  
Текущее состояние: структурированный блок  
Решения: непустые при наличии подтверждённых решений  
Открытые вопросы: непустые при наличии вопросов  
Риски: непустые при наличии подтверждённых рисков/ограничений  
Задачи: непустые при наличии подтверждённых обязательств  
\`\`\`

Если список действительно пуст, приложить объяснение из atomic extraction и не выводить пустую таблицу.

\#\# 14\. Реальный E2E

Запускать через:

\`\`\`cmd  
call start\_app.bat  
\`\`\`

\#\#\# \`project\_detailed\`

\- обработать контрольный TXT;  
\- проверить локальный HTML;  
\- опубликовать в Confluence;  
\- получить Telegram-уведомление;  
\- проверить дату, время, смысловой заголовок и реестры.

\#\#\# Остальные шаблоны

На той же расшифровке выполнить:

\`\`\`text  
management\_summary  
project\_standard  
business\_process\_discovery  
\`\`\`

Для каждого получить schema-valid JSON и HTML без JSON parse failure.

Опубликовать под согласованной тестовой parent page либо выполнить dry-run с реальным LLM, чтобы не засорять рабочий раздел.

\#\# 15\. Команды

\`\`\`bash  
python \-m compileall .  
pytest \-q  
pytest \-q tests/test\_meeting\_metadata\_filename\_formats.py  
pytest \-q tests/test\_project\_detailed\_v4\_mapping.py  
pytest \-q tests/test\_project\_detailed\_v4\_render.py  
pytest \-q tests/test\_json\_response\_repair.py  
pytest \-q tests/test\_management\_summary\_generation.py  
pytest \-q tests/test\_all\_templates\_smoke.py  
ruff check .  
mypy . \--ignore-missing-imports  
\`\`\`

Windows:

\`\`\`cmd  
call start\_app.bat \--startup-check  
call start\_app.bat  
\`\`\`

\#\# 16\. Критерии приёмки

\- контрольный \`project\_detailed\` исправлен по разделу 13;  
\- \`management\_summary\` не падает на первом malformed JSON;  
\- все четыре шаблона проходят реальный pipeline;  
\- raw LLM attempts сохраняются;  
\- дата и время извлекаются из контрольного имени файла;  
\- semantic title отделён от summary;  
\- массивы LLM реально маппятся;  
\- пустые таблицы не публикуются;  
\- Confluence и Telegram продолжают работать;  
\- secrets отсутствуют в artifacts и логах.

\#\# 17\. Ответ OpenCode

Предоставить:

1\. Новый exact \`headRefOid\`.  
2\. URL Draft PR.  
3\. Список изменённых файлов.  
4\. Список новых тестов.  
5\. Результаты всех команд.  
6\. Путь к artifacts контрольного \`project\_detailed\`.  
7\. Новый semantic title.  
8\. Извлечённые дату и время.  
9\. Количество участников, итогов, тематических блоков, строк текущего состояния, решений, вопросов, рисков и задач.  
10\. Confluence page ID/URL и результат Telegram.  
11\. Для каждого другого шаблона: template ID, статус, JSON artifact, HTML artifact.  
12\. Доказательство repair/retry на malformed JSON.  
13\. Подтверждение отсутствия secrets.  
14\. Оставшиеся ограничения.

PR оставить Draft. Merge не выполнять. \`accepted\` не устанавливать.  
