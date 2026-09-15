@echo off
setlocal
rem Launch the guarded cloud self-coding loop for this repository.
cd /d "%~dp0"
set "REPO=%CD%"
set "PY="
where py >nul 2>&1 && set "PY=py -3"
if not defined PY where python >nul 2>&1 && set "PY=python"
if not defined PY (
  echo Python 3 is required for the self-coding runner.
  exit /b 1
)
%PY% -m self_coding.run %*
exit /b %ERRORLEVEL%
