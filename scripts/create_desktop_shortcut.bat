@echo off
setlocal
cd /d "%~dp0"

echo Creating Desktop Shortcut for Pomodoro Tracker...

set "SCRIPT_DIR=%~dp0"
set "ROOT_DIR=%SCRIPT_DIR%..\"
set "TARGET=%ROOT_DIR%scripts\run_silent.vbs"
set "ICON=%ROOT_DIR%assets\icon.ico"
set "SHORTCUT_PATH=%USERPROFILE%\Desktop\Pomodoro Tracker.lnk"

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$ws = New-Object -ComObject WScript.Shell; " ^
    "$s = $ws.CreateShortcut('%SHORTCUT_PATH%'); " ^
    "$s.TargetPath = '%TARGET%'; " ^
    "$s.WorkingDirectory = '%ROOT_DIR%'; " ^
    "$s.IconLocation = '%ICON%'; " ^
    "$s.Description = 'Pomodoro Tracker for Windows and Fedora'; " ^
    "$s.Save()"

if exist "%SHORTCUT_PATH%" (
    echo [SUCCESS] Shortcut created at: "%SHORTCUT_PATH%"
) else (
    echo [ERROR] Failed to create shortcut.
)

pause
endlocal
