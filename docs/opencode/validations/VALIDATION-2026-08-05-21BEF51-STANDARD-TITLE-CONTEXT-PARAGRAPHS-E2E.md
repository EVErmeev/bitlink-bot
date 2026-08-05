\# VALIDATION-2026-08-05-21bef51-STANDARD-TITLE-CONTEXT-PARAGRAPHS-E2E

\#\# 1\. Context

TASK-2026-08-05-19BD410-STANDARD-TITLE-CONTEXT-AND-PARAGRAPH-RENDERING.

Repository: \`EVErmeev/bitlink-bot\`, branch \`fix/audit-e7cc95f\`, Draft PR \#1.

Control transcript: РЈСЂР°Р»Р”СЂРѕРЅР—Р°РІРѕРґ \+ РџРµСЂРІС‹Р№ Р‘РРў 31\.07\.2026 (block В«РџСЂРѕРёР·РІРѕРґСЃС‚РІРѕВ»), \`debug/fb860189/ef6a3922/source_transcript.txt\`.

\#\# 2\. Result of the four defect directions

\#\#\# 2\.1\. Title \(no longer from meeting\_purpose\)

\`\`\`  
РџСЂРѕС‚РѕРєРѕР» РѕС‚ 31\.07\.26\. РЈСЂР°Р»Р”СЂРѕРЅР—Р°РІРѕРґ \+ РџРµСЂРІС‹Р№ Р‘РРў вЂ” Р”РµРјРѕРЅСЃС‚СЂР°С†РёСЏ РїСЂРѕС†РµСЃСЃРѕРІ Р±Р»РѕРєР° В«РџСЂРѕРёР·РІРѕРґСЃС‚РІРѕВ»  
\`\`\`

\- No \`Р¦РµР»СЊ РІСЃС‚СЂРµС‡Рё вЂ”\`;  
\- two\-digit year;  
\- client \+ РџРµСЂРІС‹Р№ Р‘РРў;  
\- no ellipsis;  
\- page/document title not duplicated\.

\#\#\# 2\.2\. Client and meeting type

\- client\_name \= \`РЈСЂР°Р»Р”СЂРѕРЅР—Р°РІРѕРґ\`;  
\- meeting\_type \= \`external\`, confidence \= \`high\`;  
\- client row shows \`РЈСЂР°Р»Р”СЂРѕРЅР—Р°РІРѕРґ\` \(not В«РќРµ РѕРїСЂРµРґРµР»РµРЅРѕВ»\)\.

\#\#\# 2\.3\. РўРµРјР°/РїСЂРѕРµРєС‚

\`Р”РµРјРѕРЅСЃС‚СЂР°С†РёСЏ РїСЂРѕС†РµСЃСЃРѕРІ Р±Р»РѕРєР° В«РџСЂРѕРёР·РІРѕРґСЃС‚РІРѕВ»\` \+ \`вЂ” Р’РЅРµРґСЂРµРЅРёРµ 1РЎ:ERP\`\. No goal.

\#\#\# 2\.4\. РљРѕРЅС‚РµРєСЃС‚ РІСЃС‚СЂРµС‡Рё (initial\_situation / main\_problem)

Semantic fields derived via \`resolve_standard_context\` \(no metadata\)\.

\#\#\# 2\.5\. Cell rendering

Paragraphs by default; lists only for genuine enumerations; control cell renders as \`<p>\` without \`<ul>/<li>\`.

\#\# 3\. Checks

\`\`\`  
python \-m compileall \. в†’ OK  
python \-m pytest \. \(offline subset, 234 passed\) в†’ OK  
call start_app\.bat \-\-startup\-check в†’ STARTUP\_CHECK\_OK  
\`\`\`

\`ruff\`/`mypy` not installed in the environment \(pre\-existing\)\.

\#\# 4\. E2E

Offline E2E on the control transcript produced all \`В§21\` artifacts in \`docs/opencode/evidence/2026-08-05-19BD410-STANDARD-TITLE-CONTEXT-PARAGRAPHS/\`\.

\`\`\`  
meeting\_type\_resolution\.json  
project\_context\_resolution\.json  
meeting\_topic\_resolution\.json  
standard\_title\_resolution\.json  
standard\_context\_fields\.json  
standard\_cell\_structure\_report\.json  
standard\_protocol\_final\.json  
standard\_protocol\_confluence\_storage\.html  
standard\_protocol\_standalone\.html  
standard\_protocol\.docx  
\`\`\`

\`standalone\` contains exactly one \`<h1>\`; \`confluence\_storage\` contains none \(title rendered once by the page itself\).

Confluence page / Telegram message: not published in this offline run \(needs live credentials and network\)\. Real publication is documented as remaining manual step; the rendering modes used by the publish path are verified directly.

\#\# 5\. Acceptance items

1\. Client \= РЈСЂР°Р»Р”СЂРѕРЅР—Р°РІРѕРґ вЂ” OK.  
2\. meeting\_type \= external вЂ” OK.  
3\. Topic в‰  goal вЂ” OK.  
4\. Title matches target format вЂ” OK.  
5\. No ellipsis вЂ” OK.  
6\. Title once вЂ” OK \(standalone 1\|\0 conf\. storage 0\).  
7\. initial\_situation describes process state вЂ” OK.  
8\. main\_problem consolidates gaps вЂ” OK.  
9\. No metadata leak in context fields вЂ” OK.  
10. Ordinary fragments render as paragraphs вЂ” OK.  
11. Lists only for true enumerations вЂ” OK.  
12. Control cell 5Г—\`<p>\`, no \`<ul>\`/\`<li>\` вЂ” verified in unit test; in the offline E2E the cell renders as paragraphs with no list.  
13. Checks green вЂ” OK \(except live\-network tests\).  
14. Real E2E вЂ” partial \(offline; live publish pending credentials\).  
15. DOCX produced вЂ” OK.  
16. Detailed not broken вЂ” 29 detailed\-related tests pass.  
17. Committed/pushed вЂ” pending.  
18. PR stays Draft вЂ” maintained.

\#\# 6\. Files changed

\`\#\` вЂ” see commit log.
