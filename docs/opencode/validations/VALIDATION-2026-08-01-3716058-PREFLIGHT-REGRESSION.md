\# VALIDATION-2026-08-01-3716058-PREFLIGHT-REGRESSION

\#\# Объект проверки

\- Repository: \`EVErmeev/bitlink-bot\`  
\- Draft PR: \`https://github.com/EVErmeev/bitlink-bot/pull/1\`  
\- Проверенный head: \`3716058077904cb0e560db5f102281411b91ecb1\`  
\- Основание: фактическая ошибка пользователя при запуске обработки через GUI

\#\# Итоговый статус

\`CHANGES\_REQUIRED\`

PR оставить Draft. Merge запрещён.

\#\# Подтверждённая runtime-ошибка

Пользователь получает:

\`\`\`text  
TypeError: run\_preflight() got an unexpected keyword argument 'source\_types'  
\`\`\`

В \`ui/source\_queue\_frame.py\` вызывается:

\`\`\`python  
run\_preflight(items, config, source\_types=source\_types)  
\`\`\`

В \`services/preflight\_service.py\` функция объявлена:

\`\`\`python  
def run\_preflight(items, config):  
\`\`\`

Следствие: callback Tkinter завершается до создания worker thread. Обработка не начинается.

\#\# Дополнительные обнаруженные расхождения

1\. Preflight продолжает использовать \`config.is\_demo\_mode()\` вместо \`config.is\_demo\_for\_source(item.source\_type)\`.  
2\. \`is\_demo\_for\_source()\` исключает Newton и BIT.Link из demo-проверки даже для источников, где они применимы.  
3\. \`is\_production\_blocked()\` не проверяет фактическое наличие LLM URL, API key и model.  
4\. Banner способен показать \`PRODUCTION\` при отсутствующих credentials.  
5\. 182 теста не покрывают реальный контракт между \`SourceQueueFrame.\_start\_processing()\` и \`run\_preflight()\`.  
6\. Исключение GUI callback остаётся в консоли и не сохраняется как копируемый runtime report.

\#\# Статусы новых замечаний

\- \`BB-CRIT-051\` — NOT\_FIXED;  
\- \`BB-CRIT-052\` — NOT\_FIXED;  
\- \`BB-CRIT-053\` — NOT\_FIXED;  
\- \`BB-MAJ-054\` — NOT\_FIXED;  
\- \`BB-MAJ-055\` — NOT\_FIXED.

\#\# Критерий повторной проверки

Исправление принимается только после фактического GUI E2E через \`start\_app.bat\`:

1\. Добавление local TXT.  
2\. Один клик «Запустить обработку».  
3\. Отсутствие TypeError.  
4\. Успешный вызов real preflight.  
5\. Получение \`worker\_started\`.  
6\. Получение первого processing stage.  
7\. Корректный source-aware banner.  
8\. Production blocked при отсутствующих LLM credentials.  
9\. Копируемая ошибка и runtime log для негативного сценария.

Формальные \`pytest\`, Ruff и Mypy без GUI regression test недостаточны.  
