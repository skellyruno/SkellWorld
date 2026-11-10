@echo off
setlocal
cd /d "%~dp0"
title SkellWorld Local Hub
echo.
echo   SKELLWORLD  /  LOCAL CONNECTION HUB
echo   Listening only on your own computer.  Ctrl+C to exit.
echo.
where py >nul 2>nul
if not errorlevel 1 (
    py -3 tools\skellworld_hub.py
    goto :done
)
where python >nul 2>nul
if not errorlevel 1 (
    python tools\skellworld_hub.py
    goto :done
)
echo Python 3 is required for this developer preview hub.
echo No plugins connect automatically and no software was installed.
:done
echo.
echo SkellWorld hub has stopped.
pause
