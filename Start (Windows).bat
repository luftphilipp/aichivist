@echo off
rem Double-click to start aichivist - no installation needed.
chcp 65001 >nul
set PYTHONUTF8=1
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 -m aichivist start
) else (
  where python >nul 2>nul
  if errorlevel 1 (
    echo Python 3 is missing / Python 3 fehlt: https://www.python.org/downloads/
    start "" https://www.python.org/downloads/
  ) else (
    python -m aichivist start
  )
)
pause
