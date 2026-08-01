\# TASK-2026-08-01-onebit-llm-provider

\#\# Цель

Исправить подключение внутренней нейросети Первого Бита \`https://ys.1bitai.ru/\` к генератору протоколов.

Текущая реализация ошибочно считает любой real LLM OpenAI-compatible API и всегда отправляет запрос на:

\`\`\`text  
{LLM\_API\_URL}/chat/completions  
\`\`\`

При Base URL \`https://ys.1bitai.ru/\` получается неверный адрес:

\`\`\`text  
https://ys.1bitai.ru//chat/completions  
\`\`\`

Сервер отвечает \`405 Method Not Allowed\`. Это означает, что сервер доступен, но выбранный route или HTTP method не поддерживается. Это не подтверждает ошибку API key.

Пользователь сообщил способ установки внутреннего CLI:

\`\`\`bash  
curl \-sL https://gitlab.com/fadeyev1/newton-cli/-/raw/main/newton \-o \~/.local/bin/newton && chmod \+x \~/.local/bin/newton  
\`\`\`

Нельзя угадывать REST endpoint. Сначала требуется исследовать фактический контракт CLI и сервиса.

\#\# Репозиторий

\- Repository: \`EVErmeev/bitlink-bot\`  
\- Branch: \`fix/audit-e7cc95f\`  
\- Draft PR: \`https://github.com/EVErmeev/bitlink-bot/pull/1\`  
\- Проверенный head: \`d0cf2cb3079317c218b6ef60b22513969cca8d18\`

Перед началом получить точный SHA:

\`\`\`bash  
gh pr view 1 \--json headRefOid,url,isDraft,statusCheckRollup  
\`\`\`

PR оставить Draft. Merge не выполнять.

\#\# 1\. Безопасность

Ранее опубликованный API key считать скомпрометированным.

Требуется:

1\. Не повторять ключ в коде, тестах, логах, manifest, validation-файлах и ответе OpenCode.  
2\. Добавить маскирование credentials в исключениях и диагностике.  
3\. Не передавать key в command line.  
4\. Добавить замечание \`BB-CRIT-063\` со статусом \`USER\_ACTION\_REQUIRED\` до подтверждения ротации ключа пользователем.

\#\# 2\. Разделить провайдеры LLM

Реализовать отдельные provider modes:

\`\`\`text  
mock  
openai\_compatible  
onebit\_cli  
\`\`\`

Переменные окружения:

\`\`\`text  
LLM\_PROVIDER=mock|openai\_compatible|onebit\_cli  
LLM\_API\_URL=  
LLM\_API\_KEY=  
LLM\_MODEL=  
LLM\_MODELS\_PATH=/v1/models  
LLM\_CHAT\_PATH=/v1/chat/completions  
ONEBIT\_CLI\_PATH=  
ONEBIT\_CLI\_TRANSPORT=native|wsl  
ONEBIT\_CLI\_TIMEOUT\_SECONDS=120  
\`\`\`

Не использовать \`NEWTON\_PATH\` для LLM: Newton уже используется в проекте для транскрибации.

\#\# 3\. Discovery установленного CLI

На машине пользователя безопасно выполнить:

\#\#\# PowerShell

\`\`\`powershell  
Get-Command newton \-ErrorAction SilentlyContinue | Format-List \*  
where.exe newton  
\`\`\`

\#\#\# Git Bash

\`\`\`bash  
command \-v newton  
newton \--help  
newton \--version  
\`\`\`

\#\#\# WSL

\`\`\`powershell  
wsl \-e sh \-lc "command \-v newton"  
wsl \-e sh \-lc "newton \--help"  
wsl \-e sh \-lc "newton \--version"  
\`\`\`

Определить и задокументировать:

\- фактический путь к executable;  
\- native Windows или WSL;  
\- поддерживаемые аргументы;  
\- способ передачи prompt и system prompt;  
\- способ выбора модели;  
\- способ авторизации без раскрытия key;  
\- JSON output;  
\- exit codes;  
\- stdout/stderr;  
\- фактический transport и endpoint;  
\- наличие или отсутствие официального REST-контракта.

Допускается прочитать установленный скрипт \`newton\`, но запрещено менять его или выводить credentials.

Создать:

\`\`\`text  
docs/opencode/validations/ONEBIT-LLM-DISCOVERY-\<HEAD\_SHORT\_SHA\>.md  
\`\`\`

\#\# 4\. Provider architecture

Создать интерфейс:

\`\`\`python  
class LLMProvider(Protocol):  
    def check\_connection(self) \-\> ConnectionCheckResult: ...  
    def generate(self, system\_prompt: str, user\_prompt: str, \*, model: str, temperature: float, max\_tokens: int) \-\> str: ...  
\`\`\`

Реализации:

\`\`\`text  
MockLLMProvider  
OpenAICompatibleProvider  
OneBitCLIProvider  
\`\`\`

\`LLMClient\` должен делегировать выбранному provider.

\#\# 5\. OpenAI-compatible provider

\#\#\# 5.1. Нормализация URL

Запрещена простая конкатенация:

\`\`\`python  
f"{api\_url}/chat/completions"  
\`\`\`

Обязательное поведение:

\`\`\`text  
Base URL: https://host/  
Path: /v1/chat/completions  
Result: https://host/v1/chat/completions  
\`\`\`

Двойной slash после hostname недопустим.

Пути \`/v1/models\` и \`/v1/chat/completions\` являются default только для provider \`openai\_compatible\` и должны быть редактируемыми.

\#\#\# 5.2. Connection test

Добавить режимы проверки:

\`\`\`text  
models\_endpoint  
minimal\_completion  
custom\_health\_endpoint  
\`\`\`

Проверка не должна всегда требовать \`/models\`.

Возвращать структурированный результат:

\`\`\`python  
@dataclass  
class ConnectionCheckResult:  
    ok: bool  
    stage: str  
    status\_code: int | None  
    endpoint: str  
    safe\_message: str  
    response\_content\_type: str | None  
\`\`\`

При HTTP 405 показывать:

\`\`\`text  
Сервер доступен, но endpoint или HTTP method не поддерживается.  
Проверьте provider и подтверждённый API prefix.  
\`\`\`

Не утверждать, что key неверный без соответствующего ответа сервера.

\#\# 6\. OneBit CLI provider

Реализацию строить только после discovery фактического контракта.

Запускать через:

\`\`\`python  
subprocess.run(  
    args,  
    input=prompt,  
    text=True,  
    capture\_output=True,  
    timeout=timeout\_seconds,  
    check=False,  
    shell=False,  
)  
\`\`\`

Требования:

\- \`shell=False\`;  
\- аргументы списком;  
\- prompt через stdin, если это поддерживает CLI;  
\- API key не передавать в args;  
\- не логировать environment с secrets;  
\- проверять exit code;  
\- безопасно показывать stderr;  
\- поддержать UTF-8 и кириллицу;  
\- поддержать timeout;  
\- корректно работать из Windows-приложения.

Если CLI доступен только в WSL, создать явный transport \`onebit\_cli\_wsl\` и вызывать его через \`wsl.exe\`. Не угадывать WSL distribution.

\#\# 7\. Structured JSON

Генератор протоколов должен получать один валидный JSON object.

Если CLI возвращает Markdown code fence, разрешено безопасно извлечь единственный блок \`json\`.

Запрещено:

\- брать произвольный текст между первой \`{\` и последней \`}\`;  
\- принимать несколько JSON objects;  
\- считать schema-invalid ответ успешным;  
\- игнорировать текст после JSON без явной политики.

После получения ответа выполнять существующие JSON parsing, JSON Schema validation и retries.

\#\# 8\. Settings GUI

В блоке \`Нейросеть / LLM\` добавить provider selector:

\`\`\`text  
Mock  
OpenAI-compatible REST  
Первый Бит CLI  
\`\`\`

\#\#\# Для Mock

Показывать статус демонстрационного режима.

\#\#\# Для OpenAI-compatible REST

Показывать:

\- Base URL;  
\- API Key;  
\- Model;  
\- Models path;  
\- Chat completions path;  
\- Connection test mode;  
\- Timeout;  
\- кнопку проверки;  
\- копируемую безопасную диагностику.

\#\#\# Для Первый Бит CLI

Показывать:

\- CLI path;  
\- Native / WSL;  
\- Model;  
\- Timeout;  
\- \`Обнаружить CLI\`;  
\- \`Проверить CLI\`;  
\- command preview без secrets;  
\- результат structured JSON test.

Для CLI Base URL не должен быть обязательным.

\#\# 9\. Диагностика ошибки 405

Показывать копируемый отчёт, например:

\`\`\`text  
Provider: OpenAI-compatible REST  
Stage: minimal\_completion  
Base URL: https://ys.1bitai.ru  
HTTP status: 405  
Meaning: server is reachable, endpoint or method is unsupported  
Suggestion: select First Bit CLI or specify a confirmed API prefix  
\`\`\`

Добавить кнопку \`Копировать диагностику\`.

\#\# 10\. Тесты

Создать:

\`\`\`text  
tests/test\_llm\_provider\_selection.py  
tests/test\_openai\_url\_normalization.py  
tests/test\_onebit\_cli\_provider.py  
tests/test\_llm\_405\_diagnostics.py  
\`\`\`

Обязательные тесты:

\`\`\`text  
test\_base\_url\_trailing\_slash\_does\_not\_create\_double\_slash  
test\_openai\_default\_paths\_include\_v1  
test\_custom\_chat\_path\_is\_respected  
test\_models\_endpoint\_is\_not\_mandatory\_in\_minimal\_completion\_mode  
test\_405\_is\_reported\_as\_endpoint\_method\_mismatch  
test\_api\_key\_is\_redacted\_from\_exception  
test\_api\_key\_is\_not\_logged  
test\_provider\_mock\_does\_not\_require\_url  
test\_provider\_openai\_requires\_url\_key\_model  
test\_provider\_onebit\_cli\_does\_not\_require\_rest\_url  
test\_onebit\_cli\_uses\_shell\_false  
test\_onebit\_cli\_passes\_prompt\_via\_stdin  
test\_onebit\_cli\_does\_not\_put\_key\_in\_args  
test\_onebit\_cli\_timeout  
test\_onebit\_cli\_nonzero\_exit\_code  
test\_onebit\_cli\_cyrillic\_roundtrip  
test\_onebit\_cli\_extracts\_single\_json\_code\_fence  
test\_onebit\_cli\_rejects\_multiple\_json\_objects  
test\_onebit\_cli\_schema\_validation  
test\_unsaved\_provider\_values\_are\_used\_by\_connection\_test  
\`\`\`

\#\# 11\. Ручные сценарии

\#\#\# A. Текущая ошибка

\- Provider: OpenAI-compatible REST;  
\- Base URL: \`https://ys.1bitai.ru/\`;  
\- убедиться, что двойной slash отсутствует;  
\- при 405 получить точную диагностику route/method mismatch.

\#\#\# B. CLI discovery

\- выбрать \`Первый Бит CLI\`;  
\- обнаружить путь и версию;  
\- подтвердить native или WSL;  
\- выполнить minimal prompt;  
\- не раскрывать key.

\#\#\# C. Structured JSON

Проверить schema:

\`\`\`json  
{  
  "type": "object",  
  "properties": {"status": {"type": "string"}},  
  "required": \["status"\]  
}  
\`\`\`

\#\#\# D. Local TXT dry-run

\- local TXT;  
\- real \`onebit\_cli\` provider;  
\- dry-run;  
\- mock warning отсутствует;  
\- LLM stages выполняются;  
\- validated artifacts создаются;  
\- публикация не выполняется.

Создать:

\`\`\`text  
docs/opencode/validations/ONEBIT-LLM-E2E-\<HEAD\_SHORT\_SHA\>.md  
\`\`\`

\#\# 12\. Manifest

Добавить:

\`\`\`text  
BB-CRIT-061 — LLM REST endpoint жёстко задан как /chat/completions  
BB-CRIT-062 — внутренний OneBit CLI не поддерживается  
BB-CRIT-063 — API key раскрыт и должен быть перевыпущен  
BB-MAJ-064 — trailing slash создаёт двойной //  
BB-MAJ-065 — connection test жёстко требует /models  
BB-MAJ-066 — HTTP 405 отображается как общая LLM API error  
BB-MAJ-067 — конфликт названия Newton для transcription и LLM CLI  
\`\`\`

\`BB-CRIT-063\` оставить \`USER\_ACTION\_REQUIRED\` до подтверждения ротации key.

\#\# 13\. Обязательные команды

\`\`\`bash  
python \-m compileall .  
python \-m json.tool docs/opencode/manifest.json  
pytest \-q  
pytest \-q tests/test\_llm\_provider\_selection.py  
pytest \-q tests/test\_openai\_url\_normalization.py  
pytest \-q tests/test\_onebit\_cli\_provider.py  
pytest \-q tests/test\_llm\_405\_diagnostics.py  
ruff check .  
mypy . \--ignore-missing-imports  
\`\`\`

Windows:

\`\`\`cmd  
call start\_app.bat \--startup-check  
\`\`\`

\#\# 14\. Формат ответа OpenCode

Предоставить:

1\. Новый exact \`headRefOid\`.  
2\. URL Draft PR.  
3\. Workflow run ID/URL.  
4\. Результаты обязательных команд.  
5\. Путь и версию обнаруженного CLI.  
6\. Native или WSL transport.  
7\. Подтверждённый CLI contract.  
8\. Подтверждённый REST contract либо \`NOT\_CONFIRMED\`.  
9\. Результат 405 diagnostic.  
10\. Результат structured JSON smoke-test.  
11\. Результат local TXT dry-run.  
12\. Пути к discovery и E2E validation.  
13\. Подтверждение отсутствия credentials в git diff и логах.  
14\. Оставшиеся ограничения.

PR оставить Draft. Merge не выполнять. \`accepted\` не устанавливать.  
