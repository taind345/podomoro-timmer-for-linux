@echo off
setlocal
cd /d "%~dp0"

net session >nul 2>&1
if %errorlevel% neq 0 (
    echo Requesting Administrator privileges to read Fedora partition...
    powershell -NoProfile -Command "Start-Process cmd.exe -ArgumentList '/c \"\"%~f0\"\"' -Verb RunAs"
    exit /b
)

echo [1/3] Mounting Fedora partition into WSL...
wsl --mount \\.\PHYSICALDRIVE0 --partition 7 2>nul
if %errorlevel% neq 0 (
    wsl --mount \\.\PHYSICALDRIVE0 --partition 7 -t btrfs 2>nul
)

echo [2/3] Searching for Fedora podomoro database...
wsl -d Ubuntu -u root -e bash -c "DB=\$(find /mnt/wsl/ -name 'podomoro_stats.db' 2>/dev/null | head -n 1); if [ -n \"\$DB\" ]; then cp \"\$DB\" /mnt/d/DESKTOP/DATA_DESKTOP/0-CODE/podomoro_linux/data/fedora_imported.db; echo \"[Found] Copied from \$DB\"; else echo \"[Not Found] Did not find in /mnt/wsl/\"; fi"

if exist "data\fedora_imported.db" (
    echo [3/3] Merging sessions into shared database...
    python sync_database.py "data\fedora_imported.db"
    del "data\fedora_imported.db" 2>nul
    echo.
    echo =======================================================
    echo [SUCCESS] All Fedora data has been synced to Windows!
    echo =======================================================
) else (
    echo.
    echo [NOTICE] Could not automatically mount partition 7 from Windows.
)

wsl --unmount \\.\PHYSICALDRIVE0 2>nul
pause
