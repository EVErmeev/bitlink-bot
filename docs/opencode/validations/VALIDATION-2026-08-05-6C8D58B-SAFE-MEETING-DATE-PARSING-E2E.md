\# VALIDATION-2026-08-05-6c8d58b-SAFE-MEETING-DATE-PARSING-E2E

\#\# 1\. Context

TASK-2026-08-05-3A58494-SAFE-MEETING-DATE-PARSING.

Repository: \`EVErmeev/bitlink-bot\`, branch \`fix/audit-e7cc95f\`, Draft PR \#1.

Checked remote head before: \`3a58494583620d7424da7a4371156be477d5952b\`.

Error reproduced: \`ValueError: month must be in 1..12, not 15\` from \`determine_meeting_date() -> extract_date_from_filename() -> date()\`.

\#\# 2\. Root cause (old code)

1\. \`DD_MM_YY_HH_MM_SS\` was checked BEFORE the ISO four-digit patterns.  
2\. \`regex.search()\` without strict numeric boundaries matched a suffix inside a four-digit year, e.g. for \`2026_07_24_09_14_30\` it captured \`26_07_24_09_14_30\`.  
3\. \`date()\`/\`time()\` were called directly without catching \`ValueError\`.  
4\. An invalid candidate aborted the whole fallback chain (no next format / no metadata).

Basename: \`31_15_26_10_30_00_video.mp4\`.

Old regex \`_PATTERN_DD_MM_YY_TIME\` matched and extracted groups:  
day=31, month=15, year=2026 в†’ \`date(2026, 15, 31)\` в†’ ValueError (month 15).

For \`2026_07_24_09_14_30_video.mp4\` the old regex captured \`26_07_24_09_14_30\` в†’ day=26, month=07, year=2024 в†’ \`2024-07-26 09:14\` (silently wrong).

\#\# 3\. New parser contract (meeting\_metadata.py)

\- Four-digit-year formats checked before two-digit-year formats.\- Every pattern uses strict numeric boundaries \`(?<!\d) вЂ¦ (?!\d)\`.\- \`_safe_build_datetime_candidate()\` wraps \`date()\`/\`time()` and returns \`(None, None)\` instead of raising.\- An invalid time candidate is fully rejected (no silent date-only fallback).\n- \`extract_date_from_filename\` always returns \`(date|None, time|None)\` and never raises.\n- No day/month guessing, no replacement with the current date.\n- \`diagnose_date_resolution()\` exposes a safe diagnostics object.

\#\# 4\. Regression cases

\`\`\`  
2026_07_24_09_14_30_video.mp4        -> 2026-07-24 09:14   OK  
2026_08_05_15_30_45_recording.mp4    -> 2026-08-05 15:30   OK  
31_07_26_14_06_05_recording.mp4      -> 2026-07-31 14:06   OK  
31.07.2026_protocol.docx             -> 2026-07-31, time=None OK  
31_07_2026_protocol.txt              -> 2026-07-31         OK  
2026-07-24-09-14-30.mp4              -> 2026-07-24 09:14   OK  
2026.07.24.09.14.30.mp4              -> 2026-07-24 09:14   OK  
\`\`\`

All 7 control cases match the target (including ISO-with-seconds not parsed as DD\_MM\_YY).

\#\# 5\. Negative cases

Invalid month/day/hour/minute, impossible calendar dates, time-only and hash filenames all return \`(None, None)\` without raising. \`invalid_candidates_count>0\`, \`fallback_used=true\`.

\#\# 6\. Checks

\`\`\`  
python -m compileall .                          -> OK  
pytest -q (offline subset, 328 passed)          -> OK  
pytest test_meeting_metadata* / pipeline (107)  -> OK  
ruff check meeting_metadata.py + tests          -> OK (ruff installed)  
mypy meeting_metadata.py --ignore-missing-imports -> OK (mypy installed)  
start_app.bat --startup-check                   -> STARTUP_CHECK_OK  
\`\`\`

Note: full-repo \`ruff\`/`mypy` show pre-existing \`E402\` in \`services/processing_service.py\` (imports after a logger statement) that predate this task; my changed files are clean.

\#\# 7\. E2E on the problematic video

Offline E2E ran the real standard pipeline on \`31_15_24_10_30_00_video.mp4\` (invalid month): no \`ValueError\`, standard protocol generated, debug artifacts produced.

\#\# 8\. Acceptance

1\. \`month must be in 1..12\` no longer occurs вЂ” OK.  
2\. Any filename handled without a raw \`ValueError\` вЂ” OK.  
3\. ISO-with-seconds not parsed as \`DD_MM_YY\` вЂ” OK.  
4\. Invalid filename does not block fallback вЂ” OK.  
5\. Original video filename used вЂ” OK.\n6\. Standard generation on the control video completes вЂ” OK.  
7\. Detailed not broken вЂ” detailed pipeline tests pass.\n8\. Negative/regression tests added вЂ” OK.\n9\. startup-check + E2E done вЂ” OK.\n10\. Pushed, PR stays Draft вЂ” pending.

\#\# 9\. Artifacts

\`docs/opencode/evidence/2026-08-05-3A58494-SAFE-MEETING-DATE-PARSING/\`

\`\`\`  
date_parser_cases.json  
invalid_filename_cases.json  
date_resolution_debug.json  
video_e2e_result.json  
standard_protocol_final.json  
standard_protocol_final.html  
\`\`\`

PR kept Draft. No merge. \`accepted\` not set.
