#!/bin/bash
set -e
cd "$(dirname "$0")"

# Automatic 1-time legacy data sync from Fedora local folder if needed
if [ -f "$HOME/.local/share/podomoro_stats.db" ] && [ ! -L "$HOME/.local/share/podomoro_stats.db" ]; then
    python3 sync_database.py "$HOME/.local/share/podomoro_stats.db" 2>/dev/null || true
    ln -sf "$(pwd)/data/podomoro_stats.db" "$HOME/.local/share/podomoro_stats.db" 2>/dev/null || true
fi

if command -v python3 &>/dev/null; then
    exec python3 app.py "$@"
elif command -v python &>/dev/null; then
    exec python app.py "$@"
else
    echo "[ERROR] Python is not installed." >&2
    exit 1
fi
