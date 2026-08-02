\# VALIDATION-2026-08-02-4dd1402-PROTOCOL-TEMPLATES

\#\# Объект проверки

\- Репозиторий: \`EVErmeev/bitlink-bot\`  
\- Ветка: \`fix/audit-e7cc95f\`  
\- Draft PR: \`https://github.com/EVErmeev/bitlink-bot/pull/1\`  
\- Проверенный head: \`4dd1402cbcbc81a4e19fc65713fac79f57e9e57c\`  
\- Контрольный результат: экспорт протокола \`Встреча\_в\_Телемосте\_31\_07\_26\_14\_06\_05\_запись\_transcript.txt.doc\`  
\- Шаблоны: \`project\_detailed\`, \`project\_standard\`, \`management\_summary\`, \`business\_process\_discovery\`

\#\# Вердикт

\`CHANGES\_REQUIRED\`

Генерация и публикация уже запускаются, но контракт шаблонов реализован частично. \`project\_detailed\` формирует документ с потерей метаданных и специализированных реестров, а \`management\_summary\` может завершиться до сборки протокола из\-за невалидного JSON.

\#\# Подтверждённые дефекты \`project\_detailed\`

1\. В протоколе дата и время отображаются как \`—\`, хотя имя файла содержит \`31\_07\_26\_14\_06\_05\`.  
2\. Заголовком становится техническое имя файла с \`\_transcript.txt\`, а не смысловая тема встречи.  
3\. Название и краткое резюме не разделены отдельными полями.  
4\. «Цель встречи» и «Исходный контекст» содержат один и тот же текст.  
5\. «Ключевые итоги» отображаются одним текстовым блоком вместо HTML-списка.  
6\. Тематические блоки и текущее состояние плохо читаются из\-за длинных сплошных текстов.  
7\. Таблицы решений, вопросов, рисков и задач выводятся пустыми, хотя соответствующие сведения присутствуют внутри тематических блоков.

\#\# Подтверждённые причины в коде

\#\#\# Метаданные

\`meeting\_metadata.py\` поддерживает в основном форматы с четырёхзначным годом в начале. Формат \`DD\_MM\_YY\_HH\_MM\_SS\` не распознаётся.

\#\#\# Несогласованность schema и mapper

\`project\_detailed.get\_schema()\` помещает \`protocol\_title\`, дату и контекст внутрь \`general\_info\`, но \`assemble\_from\_llm\_json()\` читает часть полей с верхнего уровня и почти не использует переданный \`meeting\_metadata\`.

\#\#\# Дублирование цели и контекста

\`assemble\_from\_llm\_json()\` присваивает \`purpose\_and\_context\` одновременно в \`meeting\_purpose\` и \`meeting\_context\`.

\#\#\# Нет схемы элементов массивов

\`decisions\`, \`questions\`, \`risks\`, \`tasks\` объявлены только как \`type=array\`. Mapper ожидает конкретные поля \`decision\_text\`, \`question\_text\`, \`risk\_text\`, \`task\_text\`. При других названиях полей элементы отбрасываются.

\#\#\# Технический заголовок устанавливается заранее

\`ProcessingService\` устанавливает \`protocol.protocol\_title \= item.display\_name\`. Если LLM title не был корректно смэппирован, это имя становится заголовком страницы Confluence.

\#\#\# Пустые таблицы всегда рендерятся

Renderer строит заголовки таблиц даже при отсутствии строк.

\#\#\# JSON retry не работает на provider-level ошибке

\`OneBitNewtonCLIProvider.generate()\` сам выполняет JSON parsing и выбрасывает \`JSON\_PARSE\_ERROR\`. Поэтому \`LLMClient.generate\_json()\` не получает raw-строку и не выполняет предусмотренные повторные попытки.

\#\#\# Raw-ответ не сохраняется

Временный output Newton удаляется в \`finally\`, поэтому полный malformed JSON не остаётся в папке элемента.

\#\#\# \`management\_summary\`

Schema и mapper не согласованы: массивы не типизированы, а \`assemble\_from\_llm\_json()\` почти не маппит их. Ошибка \`Expecting ',' delimiter\` должна приводить к repair/retry, а не к немедленному завершению.

\#\# Целевое состояние

Все четыре шаблона используют общий pipeline:

\`\`\`text  
metadata  
→ raw LLM response  
→ JSON parse/repair  
→ schema validation  
→ template mapper  
→ Protocol  
→ renderer  
→ advisory quality report  
→ Confluence  
→ Telegram  
\`\`\`

Каждый шаблон должен иметь полную JSON Schema, отдельный prompt, полный mapper, renderer и интеграционный тест на одной контрольной расшифровке.

\#\# Решение

Выполнить задачу:

\`\`\`text  
TASK-2026-08-02-PROTOCOL-TEMPLATES-RELIABILITY-AND-PROJECT-DETAILED-V4.md  
\`\`\`  
