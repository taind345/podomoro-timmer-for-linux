@echo off
setlocal
cd /d "%~dp0"

where pythonw >nul 2>nul
if %errorlevel% equ 0 (
    start "" pythonw app.py
) else (
    where python >nul 2>nul
    if %errorlevel% equ 0 (
        start "" python app.py
    ) else (
        echo [ERROR] Python is not found in PATH. Please install Python or add it to PATH.
        pause
    )
)
endlocal
