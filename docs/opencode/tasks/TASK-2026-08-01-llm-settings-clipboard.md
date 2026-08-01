\# TASK-2026-08-01-llm-settings-clipboard

\#\# Назначение

Исправить два пользовательских блокера:

1\. приложение остаётся в режиме \`LLM mock\`, потому что реальный LLM нельзя полноценно настроить и проверить через GUI;  
2\. во всех формах приложения не работают стандартные операции буфера обмена \`Ctrl+C\`, \`Ctrl+V\`, \`Ctrl+X\`, \`Ctrl+A\`, особенно при русской раскладке Windows.

\#\# Репозиторий и PR

\- Repository: \`EVErmeev/bitlink-bot\`  
\- Branch: \`fix/audit-e7cc95f\`  
\- Draft PR: \`https://github.com/EVErmeev/bitlink-bot/pull/1\`  
\- Фактический проверенный head PR: \`c1983b6fbfa3ed65c0f13982c73e832d14dfcea7\`

OpenCode ранее сообщил SHA \`c1983b60e0c1a9779b1b947cb7126310f7f8da20\`, но такого commit в PR нет. Перед началом получить exact SHA через:

\`\`\`bash  
gh pr view 1 \--json headRefOid,url,isDraft,statusCheckRollup  
\`\`\`

PR оставить Draft. Merge не выполнять.

\---

\# 1\. Текущее поведение LLM

Предупреждение:

\`\`\`text  
LLM в mock-режиме  
\`\`\`

является корректным. Оно означает, что протокол формируется тестовым mock-генератором, а не реальной нейросетью.

Предупреждение нельзя скрывать или удалять без настройки реального LLM.

Текущий Settings GUI не содержит:

\- режима LLM \`Mock / Real API\`;  
\- поля LLM Base URL;  
\- поля API Key;  
\- поля Model;  
\- полноценной проверки real LLM;  
\- structured JSON smoke-test;  
\- production readiness для LLM.

\---

\# 2\. Полностью добавить LLM в Settings GUI

Создать отдельный блок \`Нейросеть / LLM\`.

\#\# 2.1. Поля

Добавить:

\- \`Режим\`: \`Mock\` / \`Real API\`;  
\- \`Base URL\`;  
\- \`API Key\`;  
\- \`Model\`;  
\- \`Timeout, сек.\` — необязательно, default 120;  
\- checkbox \`Показать API Key\`;  
\- read-only статус соединения;  
\- read-only статус structured JSON test.

При режиме \`Mock\` поля URL/Key/Model могут быть визуально disabled, но должны сохранять введённые значения.

При режиме \`Real API\` обязательны:

\- Base URL;  
\- API Key;  
\- Model.

\#\# 2.2. Сохранение

Сохранять в \`.env\`:

\`\`\`text  
APP\_PROFILE  
LLM\_MOCK  
LLM\_API\_URL  
LLM\_API\_KEY  
LLM\_MODEL  
\`\`\`

После сохранения обязательно:

1\. \`importlib.reload(settings)\`;  
2\. \`reload\_runtime\_config()\`;  
3\. обновить banner текущего окна;  
4\. обновить Production Readiness Panel;  
5\. не требовать перезапуска приложения.

Secrets нельзя выводить в консоль, логи, validation-файлы и manifest.

\#\# 2.3. Проверка несохранённых значений

Кнопка \`Проверить LLM\` должна использовать значения, которые сейчас введены в форму, даже если пользователь ещё не нажал \`Сохранить\`.

Для этого изменить контракт клиента:

\`\`\`python  
LLMClient(  
    api\_url: str,  
    api\_key: str,  
    model: str,  
    mock\_mode: bool,  
    timeout\_seconds: int \= 120,  
)  
\`\`\`

Нельзя брать \`mock\_mode\` только из глобального \`settings.LLM\_MOCK\`.

\#\# 2.4. Двухэтапная проверка

Кнопка должна выполнять:

\#\#\# Этап 1 — connection/auth test

\- корректно нормализовать Base URL;  
\- не создавать двойной \`/v1/v1\`;  
\- проверить endpoint models либо другой подтверждённый OpenAI-compatible endpoint;  
\- показать HTTP status и безопасное описание ошибки;  
\- не показывать API Key.

\#\#\# Этап 2 — structured JSON smoke-test

Отправить минимальный безопасный запрос со схемой:

\`\`\`json  
{  
  "type": "object",  
  "properties": {  
    "status": {"type": "string"}  
  },  
  "required": \["status"\]  
}  
\`\`\`

Проверить:

\- ответ получен;  
\- JSON распарсен;  
\- schema validation пройдена;  
\- retries работают;  
\- итоговый статус отображён в GUI.

\#\# 2.5. Production readiness

Для \`local\_transcript\` статус \`PRODUCTION READY\` разрешён только когда:

\- \`LLM mode \= real\`;  
\- Base URL заполнен;  
\- API Key заполнен;  
\- Model заполнен;  
\- connection test пройден в текущей сессии либо сохранён валидный результат с timestamp;  
\- structured JSON smoke-test пройден;  
\- при публикации Confluence настроен;  
\- при отправке Telegram настроен.

При отсутствии настроек показать конкретно:

\`\`\`text  
PRODUCTION BLOCKED  
Не настроен реальный LLM:  
\- Base URL;  
\- API Key;  
\- Model.  
\`\`\`

\#\# 2.6. Поведение mock warning

При mock LLM preflight должен показать понятное предупреждение:

\`\`\`text  
Демонстрационный режим: протокол будет сформирован тестовым mock-генератором.  
Результат не предназначен для рабочей публикации.  
Dry-run включён автоматически.  
\`\`\`

Кнопки:

\- \`Продолжить demo dry-run\`;  
\- \`Открыть настройки LLM\`;  
\- \`Отмена\`.

Mock-протокол нельзя публиковать в real Confluence и отправлять в real Telegram.

\---

\# 3\. Исправить буфер обмена во всём приложении

\#\# 3.1. Создать единый модуль

Создать:

\`\`\`text  
ui/clipboard\_support.py  
\`\`\`

Экспортировать:

\`\`\`python  
install\_clipboard\_support(root: tk.Tk) \-\> None  
\`\`\`

Вызывать один раз после создания \`tk.Tk()\` и до открытия пользовательских форм.

\#\# 3.2. Поддерживаемые виджеты

Поддержать:

\- \`tk.Entry\`;  
\- \`ttk.Entry\`;  
\- \`tk.Text\`;  
\- \`ttk.Combobox\`;  
\- \`tk.Spinbox\`, если используется;  
\- поля внутри \`Toplevel\` dialogs;  
\- error/details text widgets;  
\- Settings GUI;  
\- Confluence parent dialog;  
\- item parameters dialog.

\#\# 3.3. Горячие клавиши

Обязательные сочетания:

\`\`\`text  
Ctrl+C — Copy  
Ctrl+V — Paste  
Ctrl+X — Cut  
Ctrl+A — Select All  
Ctrl+Insert — Copy  
Shift+Insert — Paste  
Shift+Delete — Cut  
\`\`\`

Они должны работать:

\- в английской раскладке;  
\- в русской раскладке;  
\- при включённом Caps Lock;  
\- с буквами верхнего и нижнего регистра.

Для Windows нельзя полагаться только на \`event.keysym\`, потому что в русской раскладке keysym может быть не \`c/v/x/a\`.

Использовать сочетание:

\- \`event.keycode\` Windows virtual key codes: A=65, C=67, V=86, X=88;  
\- fallback по \`event.keysym.lower()\`;  
\- стандартные virtual events \`\<\<Copy\>\>\`, \`\<\<Paste\>\>\`, \`\<\<Cut\>\>\`.

Возвращать \`"break"\` только когда действие действительно обработано.

Не допускать двойной вставки из\-за одновременного выполнения стандартного и пользовательского binding.

\#\# 3.4. Select All

Для Entry/Combobox:

\`\`\`python  
widget.selection\_range(0, tk.END)  
widget.icursor(tk.END)  
\`\`\`

Для Text:

\`\`\`python  
widget.tag\_add("sel", "1.0", "end-1c")  
widget.mark\_set("insert", "end-1c")  
widget.see("insert")  
\`\`\`

\#\# 3.5. Read-only и disabled поля

\- read-only поля должны разрешать Copy и Select All;  
\- read-only поля не должны разрешать Paste/Cut;  
\- disabled Text с ошибкой должен разрешать Copy выделенного текста;  
\- секретные поля должны разрешать Paste;  
\- поведение Copy секретного значения должно соответствовать обычному Windows Entry.

\#\# 3.6. Контекстное меню мыши

По правой кнопке мыши для текстовых полей показать меню:

\- Вырезать;  
\- Копировать;  
\- Вставить;  
\- Выделить всё.

Недоступные действия должны быть disabled.

Контекстное меню должно работать и при русской раскладке.

\---

\# 4\. Обязательные тесты

Создать:

\`\`\`text  
tests/test\_clipboard\_support.py  
tests/test\_llm\_settings\_gui.py  
\`\`\`

Добавить тесты:

\`\`\`text  
test\_clipboard\_dispatch\_ctrl\_c\_by\_windows\_keycode  
test\_clipboard\_dispatch\_ctrl\_v\_by\_windows\_keycode  
test\_clipboard\_dispatch\_ctrl\_x\_by\_windows\_keycode  
test\_clipboard\_dispatch\_ctrl\_a\_by\_windows\_keycode  
test\_clipboard\_dispatch\_works\_with\_cyrillic\_keysym  
test\_clipboard\_does\_not\_handle\_unrelated\_shortcut  
test\_select\_all\_entry  
test\_select\_all\_text  
test\_readonly\_widget\_allows\_copy\_not\_paste  
test\_context\_menu\_contains\_required\_actions  
test\_clipboard\_support\_installed\_once  
test\_llm\_client\_accepts\_explicit\_mock\_mode  
test\_llm\_test\_uses\_unsaved\_form\_values  
test\_llm\_settings\_saved\_to\_env  
test\_runtime\_config\_reloaded\_after\_save  
test\_production\_blocked\_without\_llm\_credentials  
test\_production\_ready\_after\_connection\_and\_schema\_test  
test\_mock\_warning\_opens\_llm\_settings  
test\_mock\_llm\_forces\_dry\_run  
\`\`\`

Не использовать \`assert True\` и условные assertions, которые пропускают проверку при ошибке.

\---

\# 5\. Windows ручная проверка

Через \`start\_app.bat\` выполнить:

\#\# 5.1. Clipboard E2E

В английской и русской раскладке проверить:

1\. вставить LLM Base URL через Ctrl+V;  
2\. вставить API Key через Ctrl+V;  
3\. вставить Model через Ctrl+V;  
4\. выделить всё Ctrl+A;  
5\. копировать Ctrl+C;  
6\. вырезать Ctrl+X;  
7\. вставить обратно Ctrl+V;  
8\. копировать текст ошибки из error dialog;  
9\. использовать правую кнопку мыши;  
10\. проверить Ctrl+Insert и Shift+Insert.

\#\# 5.2. LLM GUI E2E

1\. открыть Settings;  
2\. выбрать \`Real API\`;  
3\. вставить URL/Key/Model;  
4\. не сохранять;  
5\. нажать \`Проверить LLM\`;  
6\. убедиться, что используются текущие значения формы;  
7\. сохранить;  
8\. вернуться в Queue;  
9\. убедиться, что banner обновился без перезапуска;  
10\. запустить local TXT;  
11\. убедиться, что предупреждение mock отсутствует только при реально пройденной проверке.

Сохранить:

\`\`\`text  
docs/opencode/validations/WINDOWS-CLIPBOARD-LLM-GUI-\<HEAD\_SHORT\_SHA\>.md  
\`\`\`

Не включать API Key в файл.

\---

\# 6\. Обновить manifest

Добавить замечания:

\- \`BB-CRIT-056\` — real LLM отсутствует в Settings GUI;  
\- \`BB-CRIT-057\` — Ctrl+C/Ctrl+V не работают в формах;  
\- \`BB-MAJ-058\` — mock warning не предлагает переход к настройкам;  
\- \`BB-MAJ-059\` — LLMClient не поддерживает проверку несохранённого real mode;  
\- \`BB-MAJ-060\` — OpenCode сообщил неверный полный head SHA.

После финального push записать фактический \`headRefOid\`.

\---

\# 7\. Обязательные команды

\`\`\`bash  
python \-m compileall .  
python \-m json.tool docs/opencode/manifest.json  
pytest \-q  
pytest \-q tests/test\_clipboard\_support.py  
pytest \-q tests/test\_llm\_settings\_gui.py  
ruff check .  
mypy . \--ignore-missing-imports  
\`\`\`

На Windows:

\`\`\`cmd  
call start\_app.bat \--startup-check  
\`\`\`

Все команды должны завершиться с exit code 0\.

\---

\# 8\. Формат ответа OpenCode

Предоставить:

1\. Новый exact \`headRefOid\`.  
2\. URL Draft PR.  
3\. Workflow run ID/URL.  
4\. Результаты обязательных команд.  
5\. Описание нового LLM-блока GUI.  
6\. Подтверждение проверки несохранённых значений.  
7\. Результат connection test без раскрытия credentials.  
8\. Результат structured JSON smoke-test.  
9\. Результат Ctrl+C/Ctrl+V в английской раскладке.  
10\. Результат Ctrl+C/Ctrl+V в русской раскладке.  
11\. Результат контекстного меню.  
12\. Путь к validation-файлу.  
13\. Оставшиеся ограничения.

PR оставить Draft.  
Merge не выполнять.  
\`accepted\` не устанавливать.  
