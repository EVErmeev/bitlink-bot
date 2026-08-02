\# TASK-2026-08-02-4dd1402-TEMPLATE-CONTENT-AND-JSON-PIPELINE

\#\# 1\. Цель

Исправить генерацию шаблонов так, чтобы:

1\. \`project\_detailed\` создавал структурированный читаемый протокол с заполненными итоговыми таблицами.  
2\. \`management\_summary\` стабильно формировался без падения на невалидном JSON.  
3\. \`project\_standard\` и \`business\_process\_discovery\` проходили полный pipeline и создавали непустой HTML.  
4\. Клиент и проект попадали в заголовок страницы и шапку протокола.  
5\. Изменения были реально закоммичены и запушены в Draft PR.

\#\# 2\. Репозиторий

\- Репозиторий: \`EVErmeev/bitlink-bot\`  
\- Ветка: \`fix/audit-e7cc95f\`  
\- Draft PR: \`https://github.com/EVErmeev/bitlink-bot/pull/1\`  
\- Проверенный remote head: \`4dd1402cbcbc81a4e19fc65713fac79f57e9e57c\`

PR оставить Draft. Merge не выполнять. \`accepted\` не устанавливать.

\#\# 3\. Сначала поставить заявленные изменения в GitHub

OpenCode уже сообщил о добавлении:

\- \`services/json\_response\_parser.py\`;  
\- parsing \`DD\_MM\_YY\_HH\_MM\_SS\`;  
\- raw provider response;  
\- field aliases.

Но remote head не изменился, а \`services/json\_response\_parser.py\` в GitHub отсутствует.

Перед реализацией выполнить:

\`\`\`  
git status  
git branch \--show-current  
git rev-parse HEAD  
git log \-5 \--oneline  
git diff  
git diff \--cached  
\`\`\`

Если изменения существуют локально:

1\. проверить;  
2\. добавить тесты;  
3\. закоммитить;  
4\. запушить в \`fix/audit-e7cc95f\`;  
5\. получить новый remote \`headRefOid\`.

Нельзя отвечать «готово», пока remote head не изменился.

\#\# 4\. Не ломать рабочую доставку

Сохранить работающий сценарий:

\`\`\`  
TXT/MD → LLM → Protocol → HTML → Confluence → Telegram  
\`\`\`

Не переделывать настройки Newton, Confluence и Telegram. Quality mode остаётся \`advisory\`.

\#\# 5\. Добавить клиента и проект

Добавить в \`BatchItem\`, \`Protocol\`, state и pipeline metadata:

\`\`\`  
client\_name  
project\_name  
\`\`\`

На экране добавления локального файла добавить необязательные поля:

\`\`\`  
Клиент  
Проект  
\`\`\`

Значения должны сохраняться в очереди, восстанавливаться после перезапуска, передаваться в LLM context, попадать в \`protocol.json\`, Confluence и Telegram.

Приоритет источников:

\`\`\`  
1\. Явно введённое пользователем значение.  
2\. Сохранённое значение элемента очереди.  
3\. Явное значение из metadata.  
4\. «Не определено».  
\`\`\`

Не придумывать клиента или проект.

Для контрольного файла использовать:

\`\`\`  
Клиент: Роял Фуд  
Проект: Склад 3PL  
\`\`\`

\#\# 6\. Исправить название протокола

Разделить:

\`\`\`  
protocol\_title  
meeting\_summary  
client\_name  
project\_name  
\`\`\`

\`protocol\_title\`:

\- одна строка;  
\- 6–14 слов;  
\- максимум 120 символов;  
\- без даты;  
\- без имени файла;  
\- без summary;  
\- без вводных фраз.

Пример:

\`\`\`  
Складские процессы, маркировка и работа с ТСД  
\`\`\`

Название Confluence page:

\`\`\`  
Протокол встречи от 31.07.2026. Роял Фуд — складские процессы и маркировка  
\`\`\`

В шапке выводить отдельно: клиент, проект, тема встречи, дата, время, источник.

\#\# 7\. Перестроить schema \`project\_detailed\`

Целевая структура:

\`\`\`  
{  
  "general\_info": {  
    "client\_name": "",  
    "project\_name": "",  
    "meeting\_date": "",  
    "meeting\_time": "",  
    "protocol\_title": "",  
    "meeting\_summary": ""  
  },  
  "participants": \[\],  
  "meeting\_context": {  
    "goal": "",  
    "initial\_situation": "",  
    "main\_problem": "",  
    "expected\_result": ""  
  },  
  "key\_outcomes": \[\],  
  "discussion\_blocks": \[\],  
  "current\_state": \[\],  
  "decisions": \[\],  
  "questions": \[\],  
  "risks": \[\],  
  "tasks": \[\]  
}  
\`\`\`

Все массивы должны иметь \`items\` schema.

\#\#\# 7.1. Summary

\`meeting\_summary\` — 2–4 предложения, максимум 700 символов, отдельный раздел «Краткое резюме встречи». Не использовать в title.

\#\#\# 7.2. Контекст

Поля \`goal\`, \`initial\_situation\`, \`main\_problem\`, \`expected\_result\` заполнять независимо. Не присваивать один текст нескольким полям. Добавить проверку literal duplication.

\#\#\# 7.3. Ключевые итоги

\`key\_outcomes\` должен быть \`array\[string\]\`:

\- 3–10 отдельных пунктов;  
\- один пункт — одна мысль;  
\- без внутренней нумерации;  
\- до 300 символов.

В HTML выводить \`\<ul\>\<li\>...\</li\>\</ul\>\`.

\#\#\# 7.4. Тематические блоки

Schema элемента:

\`\`\`  
{  
  "topic\_id": "",  
  "title": "",  
  "current\_state": \[\],  
  "problems": \[\],  
  "discussion": \[\],  
  "options": \[\],  
  "arguments": \[\],  
  "conclusion": "",  
  "status": "",  
  "next\_actions": \[\],  
  "responsible": \[\],  
  "deadline": "",  
  "source\_item\_ids": \[\]  
}  
\`\`\`

В ячейке обсуждения выводить только непустые подразделы с подзаголовками и списками:

\- Текущее состояние;  
\- Проблемы;  
\- Обсуждение;  
\- Рассмотренные варианты;  
\- Аргументы и пояснения.

Не выводить один длинный абзац.

\#\#\# 7.5. Текущее состояние

\`current\_state\`:

\`\`\`  
\[  
  {  
    "object": "",  
    "state": ""  
  }  
\]  
\`\`\`

Выводить таблицей «Объект / процесс» — «Текущее состояние».

\#\# 8\. Реестры решений, вопросов, рисков и задач

Не использовать regex atomic items как единственный источник.

После тематических блоков выполнить отдельный LLM extraction pass:

\`\`\`  
extract\_protocol\_registers(transcript, discussion\_blocks, source\_items)  
\`\`\`

Результат:

\`\`\`  
{  
  "decisions": \[\],  
  "questions": \[\],  
  "risks": \[\],  
  "tasks": \[\]  
}  
\`\`\`

Для решений хранить: \`decision\_text\`, \`context\_and\_basis\`, \`responsible\`, \`deadline\`, \`related\_topic\`, \`explicit\_agreement\`, \`evidence\`, \`source\_timestamp\`, \`confidence\`.

Для вопросов: \`question\_text\`, \`context\`, \`known\_info\`, \`to\_determine\`, \`responsible\`, \`deadline\`, \`next\_action\`, \`status\`, \`related\_topic\`, \`evidence\`, \`source\_timestamp\`.

Для рисков: \`risk\_type\`, \`risk\_text\`, \`reason\`, \`impact\`, \`measures\`, \`responsible\`, \`deadline\`, \`status\`, \`related\_topic\`, \`evidence\`, \`source\_timestamp\`.

Для задач: \`task\_text\`, \`basis\`, \`expected\_result\`, \`responsible\`, \`co\_executors\`, \`deadline\`, \`dependencies\`, \`status\`, \`related\_topic\`, \`commitment\_confirmed\`, \`evidence\`, \`source\_timestamp\`.

Не устанавливать программно всем решениям \`explicit\_agreement=true\`, \`confidence=0.9\`; всем задачам — \`commitment\_confirmed=true\`.

Если в thematic blocks есть «согласовано», «договорились», «открытый вопрос», «требует проверки», следующие действия, ответственный или срок, но соответствующие массивы пусты, выполнить второй extraction pass.

Не публиковать тематические блоки с решениями и действиями одновременно с четырьмя пустыми итоговыми таблицами.

Если подтверждённых элементов после двух проходов нет, пустой раздел не выводить.

\#\# 9\. Исправить \`management\_summary\`

Согласовать schema, mapper и renderer.

Целевая структура:

\`\`\`  
{  
  "general\_info": {  
    "client\_name": "",  
    "project\_name": "",  
    "meeting\_date": "",  
    "meeting\_time": "",  
    "protocol\_title": ""  
  },  
  "participants": \[\],  
  "executive\_summary": {  
    "overall\_status": "",  
    "summary": "",  
    "key\_changes": \[\]  
  },  
  "key\_results": \[\],  
  "decisions": \[\],  
  "critical\_gaps\_and\_risks": \[\],  
  "tasks": \[\],  
  "control\_points": \[\]  
}  
\`\`\`

\`assemble\_from\_llm\_json()\` должен прочитать каждое поле. \`render\_html()\` должен отобразить каждое непустое поле.

Итоговый документ: 350–700 слов. Не требовать 500–1200 слов в одном большом JSON.

\#\# 10\. Реальный JSON repair/retry

\`OneBitNewtonCLIProvider.generate()\` должен возвращать raw text без обязательного JSON parsing.

Parsing выполнить в \`LLMClient.generate\_json()\` или \`services/json\_response\_parser.py\`:

1\. сохранить raw response;  
2\. удалить внешний Markdown fence;  
3\. найти полный top-level JSON object brace-balancing алгоритмом с учётом строк и escape;  
4\. выполнить \`json.loads()\`;  
5\. выполнить JSON Schema validation;  
6\. при parse error вызвать repair prompt;  
7\. передать raw response, точную ошибку и schema;  
8\. требовать вернуть только исправленный JSON;  
9\. повторить до трёх попыток;  
10\. при schema error выполнить schema repair.

Сохранять:

\`\`\`  
llm\_attempt\_1\_raw.txt  
llm\_attempt\_1\_parse\_error.txt  
llm\_attempt\_2\_raw.txt  
llm\_attempt\_2\_schema\_errors.json  
llm\_final\_parsed.json  
\`\`\`

Добавить регрессионный тест для:

\`\`\`  
Expecting ',' delimiter: line 1 column 9405  
\`\`\`

Pipeline не должен завершаться после первой ошибки.

\#\# 11\. Остальные шаблоны

Для \`project\_standard\` и \`business\_process\_discovery\` обеспечить:

\- schema с типами элементов массивов;  
\- mapper читает все schema-поля;  
\- renderer выводит mapped-поля;  
\- raw JSON проходит parser/repair;  
\- создаётся непустой HTML;  
\- пустые необязательные разделы скрываются;  
\- dry-run выполняется без ошибки.

\#\# 12\. Общие renderer helpers

Добавить безопасные функции:

\`\`\`  
render\_bullet\_list  
render\_labeled\_list  
render\_optional\_section  
render\_table  
normalize\_text\_list  
\`\`\`

Обязателен HTML escaping всех значений LLM. Не выводить пустые \`\<table\>\` и \`\<h2\>\`.

\#\# 13\. Contract tests

Создать:

\`\`\`  
tests/test\_template\_contract\_project\_detailed.py  
tests/test\_template\_contract\_management\_summary.py  
tests/test\_template\_contract\_project\_standard.py  
tests/test\_template\_contract\_business\_process\_discovery.py  
tests/test\_json\_response\_parser.py  
tests/test\_protocol\_register\_extraction.py  
tests/test\_protocol\_metadata\_client\_project.py  
tests/test\_protocol\_structured\_rendering.py  
\`\`\`

Обязательные тесты:

\`\`\`  
test\_project\_detailed\_title\_is\_short\_single\_line  
test\_project\_detailed\_summary\_is\_separate\_from\_title  
test\_client\_and\_project\_rendered\_in\_header  
test\_confluence\_title\_contains\_client\_or\_project  
test\_key\_outcomes\_render\_as\_li\_elements  
test\_topic\_block\_renders\_labeled\_lists  
test\_current\_state\_renders\_multiple\_rows  
test\_register\_extraction\_fills\_decisions  
test\_register\_extraction\_fills\_questions  
test\_register\_extraction\_fills\_risks  
test\_register\_extraction\_fills\_tasks  
test\_second\_pass\_runs\_when\_topics\_have\_actions\_but\_registers\_empty  
test\_empty\_optional\_table\_is\_not\_rendered  
test\_management\_summary\_schema\_mapper\_renderer\_contract  
test\_management\_summary\_invalid\_json\_is\_repaired  
test\_management\_summary\_missing\_comma\_error\_retried  
test\_provider\_returns\_raw\_text\_without\_json\_parse  
test\_each\_template\_produces\_nonempty\_html  
\`\`\`

\#\# 14\. Реальный Windows E2E

Запустить:

\`\`\`  
call start\_app.bat  
\`\`\`

\#\#\# \`project\_detailed\`

Контрольный файл:

\`\`\`  
Встреча\_в\_Телемосте\_31\_07\_26\_14\_06\_05\_запись\_transcript.txt  
\`\`\`

Поля:

\`\`\`  
Клиент: Роял Фуд  
Проект: Склад 3PL  
\`\`\`

Ожидается:

\- дата \`31.07.2026\`;  
\- время \`14:06\`;  
\- короткий title;  
\- summary отдельно;  
\- клиент и проект в шапке;  
\- клиент или проект в Confluence title;  
\- key outcomes как список;  
\- thematic blocks с подпунктами;  
\- current state как таблица;  
\- не все четыре итоговых реестра пусты;  
\- пустые разделы скрыты;  
\- Confluence опубликован;  
\- Telegram содержит ссылку.

\#\#\# \`management\_summary\`

На том же файле:

\- реальный Newton LLM call;  
\- schema-valid JSON;  
\- при malformed JSON срабатывает repair/retry;  
\- непустой HTML;  
\- нет необработанного \`JSONDecodeError\`.

\#\#\# Остальные шаблоны

Для каждого:

\- реальный LLM call;  
\- schema-valid JSON;  
\- непустой HTML;  
\- dry-run без ошибки.

\#\# 15\. Команды

\`\`\`  
python \-m compileall .  
pytest \-q  
ruff check .  
mypy . \--ignore-missing-imports  
call start\_app.bat \--startup-check  
call start\_app.bat  
\`\`\`

Unit tests без реальных E2E недостаточны.

\#\# 16\. Итоговая валидация

Создать:

\`\`\`  
docs/opencode/validations/VALIDATION-2026-08-02-\<NEW\_HEAD\_SHORT\>-TEMPLATE-CONTENT-AND-JSON-PIPELINE.md  
\`\`\`

\#\# 17\. Ответ OpenCode

Предоставить:

1\. Новый exact remote \`headRefOid\`.  
2\. URL Draft PR.  
3\. Commit SHA.  
4\. Список изменённых файлов.  
5\. Подтверждение наличия \`services/json\_response\_parser.py\` в GitHub.  
6\. Результаты команд.  
7\. \`project\_detailed\` E2E.  
8\. Путь к HTML.  
9\. Confluence page ID и URL.  
10\. Telegram message ID.  
11\. Итоговый Confluence title.  
12\. \`client\_name\`, \`project\_name\`, \`protocol\_title\`, \`meeting\_summary\`.  
13\. Количество key outcomes, thematic blocks, current state rows.  
14\. Количество decisions, questions, risks, tasks.  
15\. \`management\_summary\` E2E и номер успешной repair attempt.  
16\. Результаты остальных шаблонов.  
17\. Путь к validation.  
18\. Оставшиеся ограничения.

Не писать «готово», если remote head не изменился.

PR оставить Draft. Merge не выполнять. \`accepted\` не устанавливать.  
