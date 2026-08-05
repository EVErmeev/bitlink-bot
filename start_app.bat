@echo off
setlocal EnableExtensions
cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" app.py %*
    goto :after_run
)

where py >nul 2>nul
if not errorlevel 1 (
    py -3 app.py %*
    goto :after_run
)

where python >nul 2>nul
if not errorlevel 1 (
    python app.py %*
    goto :after_run
)

echo Python 3 was not found.
pause
exit /b 9009

:after_run
set "APP_EXIT_CODE=%ERRORLEVEL%"
if not "%APP_EXIT_CODE%"=="0" (
    echo Application failed with exit code %APP_EXIT_CODE%.
    pause
)
exit /b %APP_EXIT_CODE%