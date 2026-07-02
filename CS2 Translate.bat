@echo off
chcp 65001 >nul
cd /d "%~dp0"
title CS2 Translate

echo.
echo  CS2 Translate - перевод голоса в CS2
echo  =====================================
echo.

where py >nul 2>&1
if %errorlevel%==0 (
    set "PY=py -3"
) else (
    set "PY=python"
)

%PY% --version >nul 2>&1
if errorlevel 1 (
    echo [ОШИБКА] Python не найден.
    echo.
    echo Установите Python 3.9+ с https://www.python.org/downloads/
    echo При установке отметьте "Add python.exe to PATH"
    echo.
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo [1/2] Первая установка, создаю окружение...
    %PY% -m venv .venv
    if errorlevel 1 (
        echo [ОШИБКА] Не удалось создать виртуальное окружение.
        pause
        exit /b 1
    )
)

call ".venv\Scripts\activate.bat"
if errorlevel 1 (
    echo [ОШИБКА] Не удалось активировать окружение.
    pause
    exit /b 1
)

echo [2/2] Проверка зависимостей...
python -m pip install -q -r requirements.txt
if errorlevel 1 (
    echo [ОШИБКА] Не удалось установить зависимости.
    pause
    exit /b 1
)

if not exist "vendor\libportaudio64bit.dll" (
    python scripts\enable_wasapi_loopback.py
)
if exist "vendor\libportaudio64bit.dll" (
    copy /Y "vendor\libportaudio64bit.dll" ".venv\Lib\site-packages\_sounddevice_data\portaudio-binaries\libportaudio64bit.dll" >nul
)

python launcher.py
if errorlevel 1 (
    echo.
    echo [ОШИБКА] Программа завершилась с ошибкой.
    pause
)
