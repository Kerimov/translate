@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
cd /d "%~dp0"
title CS2 Translate — тест микрофона

echo.
echo  Тест: ваш голос -^> английский -^> что услышит команда
echo  =====================================================
echo.

if not exist ".venv\Scripts\python.exe" (
    echo [ОШИБКА] Сначала запустите "CS2 Translate.bat" для установки.
    echo.
    pause
    exit /b 1
)

".venv\Scripts\python.exe" scripts\test_outgoing.py %*
if errorlevel 1 (
    echo.
    echo [ОШИБКА] Тест завершился с ошибкой.
    echo.
    pause
    exit /b 1
)
