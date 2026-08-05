\# TASK-2026-08-02-LLM-FIRST-PROTOCOL-GENERATION

\#\# Цель

Упростить обработку расшифровки до ожидаемого пользовательского сценария:

\`\`\`text  
расшифровка  
→ выбранная в настройках нейросеть  
→ выбранный шаблон  
→ готовый протокол  
\`\`\`

Успешно сформированный нейросетью протокол не должен падать в ошибку из\-за процентного соотношения разделов, количества слов, незаполненных дополнительных ячеек, отсутствующих участников, необязательной evidence и других внутренних рекомендаций по качеству.

Quality Gate должен по умолчанию быть рекомендательным и не блокировать результат.

\#\# Репозиторий

\- Repository: \`EVErmeev/bitlink-bot\`  
\- Branch: \`fix/audit-e7cc95f\`  
\- Draft PR: \`https://github.com/EVErmeev/bitlink-bot/pull/1\`  
\- Проверенный base head: \`d38ff2c28d4bc271a45befd228bf06768346055d\`

Перед началом:

\`\`\`bash  
gh pr view 1 \--json headRefOid,url,isDraft,statusCheckRollup  
\`\`\`

Если head изменился, сначала изучить diff от base head до фактического head.

PR оставить Draft. Merge не выполнять. \`accepted\` не устанавливать.

\---

\# 1\. Основной принцип

Генерация протокола и оценка качества — разные этапы.

\#\# Генерация считается успешной, если

1\. Исходная расшифровка прочитана.  
2\. Выбранный LLM provider реально вызван.  
3\. Получен ответ LLM.  
4\. Ответ преобразован в допустимую структуру протокола.  
5\. Сформирован \`Protocol\`.  
6\. Сформирован HTML.  
7\. Артефакты сохранены.

После этого элемент очереди должен быть:

\`\`\`text  
completed  
\`\`\`

или:

\`\`\`text  
completed\_with\_warnings  
\`\`\`

\#\# Генерация считается failed только при технической ошибке

Допустимые блокирующие причины:

\`\`\`text  
SOURCE\_EMPTY  
LLM\_NOT\_CONFIGURED  
LLM\_REQUEST\_FAILED  
LLM\_TIMEOUT  
LLM\_EMPTY\_RESPONSE  
LLM\_JSON\_INVALID\_AFTER\_REPAIR  
ROOT\_SCHEMA\_INVALID  
PROTOCOL\_ASSEMBLY\_FAILED  
HTML\_RENDER\_FAILED  
ARTIFACT\_SAVE\_FAILED  
PUBLISH\_FAILED  
\`\`\`

Не считать технической ошибкой:

\`\`\`text  
THEMATIC\_RATIO\_LOW  
SECTION\_TOO\_SHORT  
EMPTY\_OPTIONAL\_CELL  
NO\_PARTICIPANTS  
LOW\_DECISION\_CONFIDENCE  
MISSING\_EVIDENCE  
TOPIC\_COVERAGE\_LOW  
TOPIC\_ALIGNMENT\_WARNING  
\`\`\`

\---

\# 2\. Добавить режим проверки качества

Добавить настройку:

\`\`\`text  
PROTOCOL\_QUALITY\_MODE=off|advisory|strict  
\`\`\`

Значение по умолчанию:

\`\`\`text  
advisory  
\`\`\`

\#\# off

\- Не запускать смысловые quality checks.  
\- Выполнить только техническую проверку результата.  
\- Протокол публикуется после успешного render.

\#\# advisory

\- Запустить quality checks.  
\- Сохранить отчёт.  
\- Показать предупреждения.  
\- Не блокировать сохранение и публикацию.  
\- Использовать \`completed\_with\_warnings\`, если есть предупреждения.

\#\# strict

\- Сохранить возможность блокировки публикации.  
\- Использовать только по явному выбору пользователя.  
\- \`validation\_failed\` допустим только здесь.

На странице «Настройки» добавить:

\`\`\`text  
Проверка качества протокола:  
\- Выключена  
\- Рекомендательная  
\- Строгая  
\`\`\`

Подсказка:

\`\`\`text  
Рекомендательный режим не блокирует готовый протокол.  
Строгий режим может остановить публикацию по внутренним правилам качества.  
\`\`\`

\---

\# 3\. Разделить техническую и смысловую валидацию

Создать либо реорганизовать:

\`\`\`text  
services/protocol\_generation\_validation.py  
services/protocol\_quality\_validation.py  
\`\`\`

\#\# TechnicalGenerationReport

\`\`\`python  
@dataclass  
class TechnicalGenerationReport:  
    passed: bool  
    blocking\_errors: list\[GenerationIssue\]  
\`\`\`

Технические проверки:

\- transcript непустой;  
\- llm response непустой;  
\- JSON parse успешен;  
\- обязательный root object существует;  
\- template id существует;  
\- protocol object создан;  
\- render вернул непустой HTML;  
\- HTML содержит \`\<html\>\` и \`\<body\>\`;  
\- артефакты записаны.

\#\# ProtocolQualityReport

\`\`\`python  
@dataclass  
class ProtocolQualityReport:  
    passed: bool  
    warnings: list\[QualityIssue\]  
    metrics: dict  
\`\`\`

Quality checks:

\- полнота разделов;  
\- длина тематических блоков;  
\- наличие контекста у решений;  
\- участники;  
\- evidence;  
\- topic coverage;  
\- topic alignment;  
\- доля разделов;  
\- дополнительные рекомендации шаблона.

Quality report не должен менять технический статус генерации в \`advisory\`.

\---

\# 4\. Исправить ProcessingService

Перестроить \`process\_item()\`.

Целевая последовательность:

\`\`\`text  
loading\_source  
extracting\_metadata  
generating\_protocol  
technical\_validation  
rendering  
saving\_artifacts  
quality\_review  
publishing\_confluence  
sending\_telegram  
completed  
\`\`\`

Atomic items могут использоваться как дополнительный контекст для LLM и отчёта качества, но не должны подменять основной результат нейросети.

После LLM:

\`\`\`python  
llm\_data, llm\_raw \= self.llm.generate\_json(...)  
protocol \= template.assemble\_from\_llm\_json(...)  
html \= template.render\_html(protocol)  
technical\_report \= validate\_generated\_protocol(protocol, html)  
\`\`\`

Если \`technical\_report.passed\`:

1\. сохранить артефакты;  
2\. выполнить quality review согласно режиму;  
3\. публиковать при \`off\` и \`advisory\`;  
4\. завершить успешно.

Логика статуса:

\`\`\`python  
if not technical\_report.passed:  
    item.status \= "failed"  
elif quality\_mode \== "strict" and not quality\_report.passed:  
    item.status \= "validation\_failed"  
elif quality\_report.warnings:  
    item.status \= "completed\_with\_warnings"  
else:  
    item.status \= "completed"  
\`\`\`

Не устанавливать в \`off\` или \`advisory\`:

\`\`\`python  
result\["error"\] \= "Protocol validation failed \- publication blocked"  
\`\`\`

\---

\# 5\. Исправить JSON Schema подробного шаблона

Полностью описать структуры массивов:

\`\`\`text  
decisions  
questions  
risks  
tasks  
\`\`\`

\#\# decisions

Поля:

\`\`\`text  
decision\_text  
context\_and\_basis  
agreed\_scope  
boundaries  
responsible  
deadline  
related\_topic  
evidence  
\`\`\`

Обязательное поле: \`decision\_text\`.

\#\# questions

Поля:

\`\`\`text  
question\_text  
context  
known\_info  
to\_determine  
responsible  
deadline  
next\_action  
status  
related\_topic  
\`\`\`

Обязательное поле: \`question\_text\`.

\#\# risks

Поля:

\`\`\`text  
risk\_type  
risk\_text  
reason  
impact  
trigger\_condition  
measures  
responsible  
deadline  
status  
related\_topic  
\`\`\`

Обязательное поле: \`risk\_text\`.

\#\# tasks

Поля:

\`\`\`text  
task\_text  
basis  
expected\_result  
responsible  
co\_executors  
deadline  
dependencies  
status  
related\_topic  
\`\`\`

Обязательное поле: \`task\_text\`.

Не требовать от нейросети придумывать отсутствующие данные.

В system prompt указать:

\`\`\`text  
Если сведения отсутствуют в расшифровке:  
\- используй пустую строку;  
\- либо «Не указано в расшифровке» для отображаемых обязательных ячеек;  
\- не выдумывай ответственных, сроки, основания и решения.  
\`\`\`

\---

\# 6\. Исправить assemble\_from\_llm\_json

\`assemble\_from\_llm\_json()\` должен преобразовывать в модели все данные LLM:

\`\`\`text  
participants  
topic\_blocks  
decisions  
questions  
risks  
tasks  
general\_info  
purpose\_and\_context  
key\_outcomes  
current\_state  
\`\`\`

Запрещено игнорировать LLM-массивы и затем заменять их atomic items.

Atomic items использовать только как fallback, если соответствующий массив LLM отсутствует.

Fallback-объекты должны заполнять отображаемые поля безопасными значениями:

\`\`\`text  
context\_and\_basis \= "Не указано в расшифровке"  
basis \= "Не указано в расшифровке"  
\`\`\`

Не создавать строку таблицы, если нет основного текста:

\`\`\`text  
decision\_text  
question\_text  
risk\_text  
task\_text  
\`\`\`

\---

\# 7\. Не перезаписывать результат нейросети непрозрачными коррекциями

В обычном режиме убрать из основного пути:

\`\`\`python  
protocol \= apply\_corrections(protocol)  
\`\`\`

В \`off\` и \`advisory\` автоматические смысловые коррекции не применять.

В \`strict\` коррекции разрешены только с отчётом before/after:

\`\`\`text  
protocol\_before\_corrections.json  
protocol\_after\_corrections.json  
corrections\_report.json  
\`\`\`

Для каждой коррекции указать правило и основание.

\---

\# 8\. Удалить блокирующий порог 55%

\`html\_thematic\_ratio\_low\` не должен быть \`FAILED\` в обычном режиме.

Метрика может сохраняться как warning:

\`\`\`text  
topic\_words  
total\_words  
topic\_ratio  
\`\`\`

Устранить противоречие:

\`\`\`text  
structure threshold \= 20%  
render threshold \= 55%  
\`\`\`

Доля 30.9% должна завершаться успешно в \`advisory\`.

\---

\# 9\. Пустые дополнительные ячейки не должны блокировать результат

Ошибки вида:

\`\`\`text  
Решение \#1: пустые ячейки: context\_and\_basis  
\`\`\`

в \`advisory\` должны быть warning.

В HTML для пустого значения использовать:

\`\`\`text  
Не указано в расшифровке  
\`\`\`

или \`—\`.

\---

\# 10\. Всегда сохранять результат

После успешной технической генерации сохранять:

\`\`\`text  
protocol.json  
protocol\_preview.html  
llm\_raw\_response.txt  
llm\_parsed\_response.json  
technical\_generation\_report.json  
quality\_report.json  
\`\`\`

Для \`completed\_with\_warnings\` в UI показать:

\`\`\`text  
Протокол сформирован с предупреждениями качества.  
\`\`\`

Кнопки:

\`\`\`text  
Открыть протокол  
Открыть HTML  
Посмотреть предупреждения  
Опубликовать  
\`\`\`

Предупреждения не должны скрывать результат.

\---

\# 11\. Публикация

\#\# advisory/off

После успешной технической генерации разрешить:

\- публикацию в Confluence;  
\- уведомление Telegram;  
\- успешный dry-run.

\#\# strict

Quality Gate может остановить автоматическую публикацию, но локальные артефакты должны остаться доступны.

\---

\# 12\. Статусы BatchItem и UI

Добавить статус:

\`\`\`text  
completed\_with\_warnings  
\`\`\`

Цвет: оранжевый.

Отображение:

\`\`\`text  
Готово с предупреждениями  
\`\`\`

\`error\_details\` использовать только для технической ошибки.

Для quality warnings добавить:

\`\`\`python  
item.quality\_warnings: list\[str\]  
item.quality\_report\_path: str | None  
\`\`\`

\---

\# 13\. Подтвердить выбранную нейросеть

В debug artifacts сохранять безопасные сведения:

\`\`\`json  
{  
  "provider": "onebit\_newton\_cli",  
  "model": "gpt4",  
  "template": "project\_detailed",  
  "request\_succeeded": true,  
  "response\_received": true  
}  
\`\`\`

Не сохранять token/API key.

В UI результата показать:

\`\`\`text  
Нейросеть: БИТ Ньютон / gpt4  
Шаблон: Подробный проектный протокол  
\`\`\`

\---

\# 14\. Тесты

Создать:

\`\`\`text  
tests/test\_llm\_first\_protocol\_pipeline.py  
tests/test\_quality\_mode.py  
tests/test\_project\_detailed\_llm\_mapping.py  
tests/test\_non\_blocking\_quality\_warnings.py  
tests/test\_protocol\_result\_statuses.py  
\`\`\`

Обязательные тесты:

\`\`\`text  
test\_successful\_llm\_and\_render\_is\_completed  
test\_quality\_warnings\_do\_not\_fail\_advisory\_mode  
test\_quality\_checks\_are\_skipped\_in\_off\_mode  
test\_quality\_failure\_blocks\_only\_in\_strict\_mode  
test\_low\_thematic\_ratio\_is\_warning\_not\_technical\_failure  
test\_30\_percent\_thematic\_ratio\_can\_complete  
test\_empty\_context\_and\_basis\_is\_warning  
test\_empty\_context\_and\_basis\_does\_not\_block\_publish\_in\_advisory  
test\_llm\_decisions\_are\_mapped\_to\_protocol  
test\_llm\_questions\_are\_mapped\_to\_protocol  
test\_llm\_risks\_are\_mapped\_to\_protocol  
test\_llm\_tasks\_are\_mapped\_to\_protocol  
test\_atomic\_fallback\_does\_not\_overwrite\_llm\_content  
test\_apply\_corrections\_not\_called\_in\_advisory  
test\_apply\_corrections\_not\_called\_in\_off\_mode  
test\_invalid\_json\_after\_retries\_is\_failed  
test\_render\_exception\_is\_failed  
test\_artifacts\_exist\_for\_completed\_with\_warnings  
test\_ui\_exposes\_generated\_protocol\_with\_warnings  
test\_selected\_llm\_provider\_recorded\_without\_secret  
\`\`\`

Запрещено использовать \`assert True\`.

\---

\# 15\. Регрессионный сценарий пользователя

Использовать тот же текстовый файл, на котором получено:

\`\`\`text  
Тематических слов: 1156  
Тем: 11  
Тематическая таблица: 30.9%  
Пустой context\_and\_basis у трёх решений  
\`\`\`

Ожидаемый результат в \`advisory\`:

\`\`\`text  
status \= completed\_with\_warnings  
success \= true  
protocol.json существует  
protocol\_preview.html существует  
quality\_report.json существует  
publication не заблокирована  
\`\`\`

Warnings допустимы, но основной результат успешен.

\---

\# 16\. Windows GUI E2E

Запустить через:

\`\`\`cmd  
call start\_app.bat  
\`\`\`

Сценарий:

1\. Выбрать локальный текстовый файл.  
2\. Выбрать рабочий LLM provider.  
3\. Выбрать подробный проектный шаблон.  
4\. Установить \`Рекомендательная\`.  
5\. Нажать «Запустить обработку».  
6\. Дождаться ответа LLM.  
7\. Получить \`completed\` или \`completed\_with\_warnings\`.  
8\. Открыть HTML-протокол.  
9\. Убедиться, что decisions/questions/risks/tasks заполнены данными LLM.  
10\. Убедиться, что 30.9% не блокирует результат.  
11\. Убедиться, что пустой \`context\_and\_basis\` не блокирует advisory.  
12\. Проверить Confluence.  
13\. Проверить Telegram.  
14\. Повторить в \`strict\`.  
15\. Проверить отсутствие secrets в artifacts/logs.

Создать:

\`\`\`text  
docs/opencode/validations/LLM-FIRST-PROTOCOL-E2E-\<HEAD\_SHORT\_SHA\>.md  
\`\`\`

\---

\# 17\. Manifest

Добавить:

\`\`\`text  
BB-CRIT-115 — Quality Gate блокирует успешно сформированный протокол  
BB-CRIT-116 — assembler игнорирует LLM decisions/questions/risks/tasks  
BB-CRIT-117 — противоречащие пороги thematic ratio  
BB-CRIT-118 — успешная генерация маркируется validation\_failed  
BB-MAJ-119 — technical и quality validation не разделены  
BB-MAJ-120 — apply\_corrections непрозрачно изменяет LLM результат  
BB-MAJ-121 — нет режима off/advisory/strict  
BB-MAJ-122 — UI скрывает сформированные artifacts при warnings  
\`\`\`

Активная задача:

\`\`\`text  
active\_task\_id \= TASK-2026-08-02-LLM-FIRST-PROTOCOL-GENERATION  
active\_task\_file \= docs/opencode/tasks/TASK-2026-08-02-LLM-FIRST-PROTOCOL-GENERATION.md  
status \= in\_progress  
validation\_state \= implementing\_fixes  
\`\`\`

\---

\# 18\. Команды

\`\`\`bash  
python \-m compileall .  
python \-m json.tool docs/opencode/manifest.json  
pytest \-q  
pytest \-q tests/test\_llm\_first\_protocol\_pipeline.py  
pytest \-q tests/test\_quality\_mode.py  
pytest \-q tests/test\_project\_detailed\_llm\_mapping.py  
pytest \-q tests/test\_non\_blocking\_quality\_warnings.py  
pytest \-q tests/test\_protocol\_result\_statuses.py  
ruff check .  
mypy . \--ignore-missing-imports  
\`\`\`

Windows:

\`\`\`cmd  
call start\_app.bat \--startup-check  
call start\_app.bat  
\`\`\`

Общий \`pytest \-q\` без GUI E2E не является достаточным доказательством.

\---

\# 19\. Ответ OpenCode

Предоставить:

1\. Новый exact \`headRefOid\`.  
2\. URL Draft PR.  
3\. Список изменённых файлов.  
4\. Список новых тестов.  
5\. Результаты обязательных команд.  
6\. Значение \`PROTOCOL\_QUALITY\_MODE\` по умолчанию.  
7\. Новую последовательность ProcessingService.  
8\. Доказательство mapping всех LLM-массивов.  
9\. Доказательство, что advisory warnings не блокируют протокол.  
10\. Доказательство, что 30.9% завершается успешно.  
11\. Доказательство, что пустой context\_and\_basis не блокирует advisory.  
12\. Пути к \`protocol.json\` и \`protocol\_preview.html\`.  
13\. Путь к \`quality\_report.json\`.  
14\. Результат публикации Confluence.  
15\. Результат Telegram.  
16\. Windows GUI E2E.  
17\. Путь к validation.  
18\. Подтверждение отсутствия secrets.  
19\. Оставшиеся ограничения.

PR оставить Draft. Merge не выполнять. \`accepted\` не устанавливать.  
