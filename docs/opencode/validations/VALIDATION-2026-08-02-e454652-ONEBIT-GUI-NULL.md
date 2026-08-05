\# VALIDATION-2026-08-02-e454652-ONEBIT-GUI-NULL

\#\# Объект проверки

\- Репозиторий: \`EVErmeev/bitlink-bot\`  
\- Draft PR: \`https://github.com/EVErmeev/bitlink-bot/pull/1\`  
\- Проверенный head: \`e454652b125093a0da5648d9bcbccccedd740324\`  
\- Сценарий: настройка \`onebit\_newton\_cli\` и проверка LLM через GUI.  
\- Факт пользователя: при «Проверить LLM» возникает \`'NoneType' object is not subscriptable\`.

\#\# Вердикт

\`CHANGES\_REQUIRED\`

PR оставить Draft. Merge и \`accepted\` запрещены до реального Windows GUI E2E.

\#\# Как проводился аудит

1\. Независимо проверен фактический \`headRefOid\` PR.  
2\. Проверена runtime-цепочка:

\`\`\`text  
Settings GUI  
→ .env  
→ RuntimeConfig  
→ preflight  
→ client\_factory  
→ LLMClient  
→ OneBitNewtonCLIProvider  
→ newton.cmd  
→ output file  
→ JSON parse  
→ JSON Schema validation  
\`\`\`

3\. Проверены файлы:

\- \`ui/settings\_frame.py\`;  
\- \`services/runtime\_config.py\`;  
\- \`services/preflight\_service.py\`;  
\- \`services/client\_factory.py\`;  
\- \`services/llm\_service.py\`;  
\- \`services/llm\_providers.py\`;  
\- тесты LLM provider;  
\- diff последнего commit.

4\. Заявления OpenCode сравнивались с фактическим кодом.  
5\. \`pytest\`, \`ruff\`, \`mypy\`, \`startup-check\` считались обязательными, но недостаточными.  
6\. Функциональная приёмка требовала реальной цепочки:

\`\`\`text  
GUI settings  
→ real provider  
→ minimal generation  
→ schema-valid JSON  
→ local TXT dry-run  
→ protocol artifacts  
\`\`\`

\#\# Подтверждённые исправления

\- \`RuntimeConfig\` загружает provider и CLI-поля.  
\- Preflight разделяет CLI и OpenAI credentials.  
\- \`.cmd\` запускается через \`COMSPEC\`.  
\- Несколько JSON fences больше не должны приниматься как успешный ответ.

\#\# Оставшиеся дефекты

\#\#\# BB-CRIT-076 — нет отдельного токена БИТ Ньютон

В LLM-панели отсутствует отдельное редактируемое поле \`ONEBIT\_LLM\_TOKEN\`. Токен скрыто берётся из старого блока Newton или окружения.

\#\#\# BB-CRIT-077 — «Проверить CLI» проверяет только версию

Успешный \`newton version\` не подтверждает токен, права, создание задачи или генерацию.

\#\#\# BB-CRIT-078 — health не является auth/LLM test

\`7/7 healthy\` подтверждает доступность сервисов, но не валидность токена и не успешную генерацию.

\#\#\# BB-CRIT-079 — внутренний TypeError показывается пользователю

\`'NoneType' object is not subscriptable\` — внутренняя ошибка Python/CLI. Точная стадия не доказана, потому что GUI не показывает exit code, stdout, stderr и состояние output-файла.

\#\#\# BB-CRIT-080 — нет поэтапной диагностики

Не фиксируются stage, exit code, safe stdout/stderr, output file existence/size, response type, JSON parse и schema validation.

\#\#\# BB-MAJ-081 — неактуальные поля disabled вместо скрытия

Для CLI OpenAI-поля правильно не должны редактироваться, но их нужно полностью скрывать. Серые поля создают ложное ощущение незавершённой настройки.

\#\#\# BB-MAJ-082 — реальный GUI E2E не пройден

Пользовательская кнопка падает, значит отчёт OpenCode не подтверждает рабочую генерацию.

\#\#\# BB-MAJ-083 — нет полного settings-to-provider integration test

Не подтверждён тест:

\`\`\`text  
Settings save  
→ reload RuntimeConfig  
→ provider selection  
→ real smoke generation  
→ JSON parse  
→ schema validation  
\`\`\`

\#\# Разъяснение по полям

Для \`onebit\_newton\_cli\` не нужны OpenAI Base URL, API Key и OpenAI Model. Они должны быть скрыты. Вместо них должны отображаться:

\- токен БИТ Ньютон;  
\- CLI path;  
\- transport;  
\- \`llama/gpt4\`;  
\- timeout;  
\- version;  
\- health;  
\- real LLM smoke-test;  
\- копируемая диагностика.

\#\# Условия повторной проверки

1\. Отдельные provider panels.  
2\. Отдельное поле токена БИТ Ньютон.  
3\. Проверки version, health и real LLM разделены.  
4\. \`NoneType\`, \`KeyError\`, traceback не показываются пользователю.  
5\. Structured JSON smoke-test проходит schema validation.  
6\. После сохранения restart не требуется.  
7\. Local TXT dry-run проходит через real LLM.  
8\. Создаются protocol artifacts.  
9\. Токен отсутствует в git, логах и validation artifacts.

\#\# Security

Ранее раскрытый токен считать скомпрометированным.

\`\`\`text  
BB-CRIT-063 \= USER\_ACTION\_REQUIRED  
\`\`\`  
