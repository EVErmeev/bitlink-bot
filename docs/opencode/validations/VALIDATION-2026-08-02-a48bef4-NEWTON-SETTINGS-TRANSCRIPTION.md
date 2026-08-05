\# VALIDATION-2026-08-02-a48bef4-NEWTON-SETTINGS-TRANSCRIPTION

\#\# Объект проверки

\- Репозиторий: \`EVErmeev/bitlink-bot\`  
\- Draft PR: \`https://github.com/EVErmeev/bitlink-bot/pull/1\`  
\- Проверенный head: \`a48bef437f020a3a4c09ad1d611858ba1b77d6a3\`  
\- Объект: страница настроек, единый БИТ Ньютон CLI, LLM и транскрибация.

\#\# Вердикт

\`CHANGES\_REQUIRED\`

Переходить к \`BB-MAJ-011–020\` пока рано. Сначала необходимо завершить текущий блок и подтвердить реальную транскрибацию в производственном конвейере.

PR оставить Draft. Merge и \`accepted\` запрещены.

\#\# Что подтверждено

1\. Настройки token/path БИТ Ньютон действительно объединены в одном блоке.  
2\. LLM использует общий token/path и отдельно хранит только выбор модели.  
3\. Newton version, health и реальный LLM smoke проходят.  
4\. Confluence и Telegram ранее дали реальные PASS.  
5\. PR остаётся Draft и не смержен.

\#\# Критические замечания

\#\#\# BB-CRIT-115 — реальная транскрибация не подключена к рабочему конвейеру

В \`services/client\_factory.py\` для provider \`onebit\_newton\_cli\` возвращается старый \`TranscriptionClient()\`:

\`\`\`python  
if config.transcription\_provider \== "onebit\_newton\_cli":  
    return TranscriptionClient()  
\`\`\`

Новый \`OneBitNewtonTranscriptionProvider\` фабрикой не используется.

\#\#\# BB-CRIT-116 — старый TranscriptionClient остаётся mock/NotImplemented

\`services/transcription\_service.py\`:

\- читает старые \`NEWTON\_MOCK\`, \`NEWTON\_TOKEN\`, \`NEWTON\_BASE\_URL\`;  
\- в mock возвращает учебную расшифровку;  
\- в real вызывает \`NotImplementedError\`.

Следовательно, добавление видео в реальную очередь не гарантирует вызов \`newton transcribe\`.

\#\#\# BB-CRIT-117 — проверка транскрибации является только проверкой CLI-контракта

И индивидуальная кнопка, и \`Проверить все подключения\` запускают:

\`\`\`text  
newton transcribe \--help  
\`\`\`

Это доказывает только наличие подкоманды. Не проверяются:

\- токен;  
\- загрузка media-файла;  
\- создание task\_id;  
\- polling;  
\- получение READY;  
\- скачивание результата;  
\- непустой текст.

Статус \`PASS\` для \`transcribe \--help\` является ложноположительным. Корректный статус: \`PARTIAL\` или \`CAPABILITY\_AVAILABLE\`.

\#\#\# BB-CRIT-118 — Windows \`.cmd\` вызывается неодинаково

LLM-provider правильно оборачивает \`.cmd/.bat\` через \`cmd.exe /d /s /c\`.

\`OneBitNewtonTranscriptionProvider\` вызывает:

\`\`\`python  
\[self.config.cli\_path, "transcribe", ...\]  
\`\`\`

Для Windows \`.cmd\` это не тот же контракт и может завершиться ошибкой запуска. Нужен единый builder команд для всех capability Newton.

\#\#\# BB-CRIT-119 — отсутствует реальный E2E с media-файлом

OpenCode сообщил только:

\`\`\`text  
Transcription contract: newton transcribe \<file\> ...  
\`\`\`

Это не результат транскрибации. Нет доказательств:

\- какой файл обработан;  
\- какой engine использован;  
\- был ли task\_id;  
\- был ли READY;  
\- какой output создан;  
\- сколько символов получено;  
\- что результат дошёл до ProcessingService.

\#\# Существенные замечания

\#\#\# BB-MAJ-120 — тесты не добавлены

Между \`adac939\` и \`a48bef4\` изменены production-файлы, но тестовые файлы не изменялись. Общий результат остался \`229 passed\`, то есть новые сценарии не закреплены regression-тестами.

\#\#\# BB-MAJ-121 — индивидуальная OpenAI-проверка остаётся синхронной

\`\_test\_openai\_llm()\` выполняет сетевой check и \`generate\_json()\` напрямую из обработчика GUI. Заявление о полном async-переводе не соответствует текущему коду.

\#\#\# BB-MAJ-122 — worker продолжает вызывать Tkinter

Version, health и token workers вызывают \`\_run\_on\_ui()\` из фонового потока. Это обход \`ConnectionCheckRunner\` и нарушение принятой архитектуры queue → UI poller.

\#\#\# BB-MAJ-123 — копирование диагностики всё ещё может запускать subprocess

Если \`\_last\_results\["llm"\]\` отсутствует, \`\_copy\_diagnostics()\` повторно запускает version и health. Кнопка копирования должна только копировать уже сохранённые результаты.

\#\#\# BB-MAJ-124 — неверная подсказка про JWT

В GUI всё ещё указано, что токен обычно должен состоять из трёх частей. Пользователь уже подтвердил рабочий токен другого формата. Локальная форма токена не должна навязываться приложением.

\#\#\# BB-MAJ-125 — проверка всех подключений не является source-specific acceptance

Общая таблица показывает технические capability, но не отвечает отдельно:

\- готов ли локальный TXT;  
\- готово ли локальное видео;  
\- готов ли источник БИТ.Link.

БИТ.Link \`NOT\_IMPLEMENTED\` не должен блокировать локальный TXT и локальное видео.

\#\# Корректная трактовка текущего состояния

\`\`\`text  
БИТ Ньютон CLI         PASS  
LLM Summary             PASS  
Confluence              PASS  
Telegram                PASS  
Transcription command   AVAILABLE  
Real transcription      NOT VALIDATED  
Video processing        BLOCKED  
Local TXT processing    READY к отдельному E2E  
БИТ.Link                BLOCKED\_BY\_API\_CONTRACT  
\`\`\`

\#\# Критерии повторной приёмки

1\. \`build\_transcription\_client()\` возвращает реальный Newton CLI adapter.  
2\. Производственный вызов \`transcribe\_video()\` доходит до \`newton transcribe\`.  
3\. \`.cmd\` запускается через единый Windows-safe builder.  
4\. \`--help\` отображается как PARTIAL, а не PASS.  
5\. Есть кнопка выбора тестового media-файла и реальная транскрибация.  
6\. Получен непустой output и безопасная диагностика task/result.  
7\. Выполнен E2E: local video → transcript → LLM → protocol dry-run.  
8\. Добавлены отдельные tests, а не только повторный общий pytest.  
9\. OpenAI-check не блокирует GUI.  
10\. Worker не вызывает Tkinter.  
11\. Copy diagnostics не запускает процессы.  
12\. Tooltip не требует JWT-формата.  
13\. Manifest обновлён фактическим head и findings.  
