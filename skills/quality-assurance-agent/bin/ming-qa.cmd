@echo off
setlocal enabledelayedexpansion
set "SCRIPT_DIR=%~dp0"
set "SKILL_ROOT=%SCRIPT_DIR%.."
set "SCRIPT=%SKILL_ROOT%\scripts\qa_agent.py"

where python >nul 2>nul
if not errorlevel 1 (
  python "%SCRIPT%" %*
  exit /b %errorlevel%
)

where python3 >nul 2>nul
if not errorlevel 1 (
  python3 "%SCRIPT%" %*
  exit /b %errorlevel%
)

where py >nul 2>nul
if not errorlevel 1 (
  py -3 "%SCRIPT%" %*
  exit /b %errorlevel%
)

echo python3/python/py not found in PATH. 1>&2
exit /b 1
