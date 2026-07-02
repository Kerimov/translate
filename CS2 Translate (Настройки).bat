@echo off
chcp 65001 >nul
cd /d "%~dp0"
call ".venv\Scripts\activate.bat" 2>nul
if not exist ".venv\Scripts\python.exe" (
    call "CS2 Translate.bat"
    exit /b
)
python launcher.py --setup
