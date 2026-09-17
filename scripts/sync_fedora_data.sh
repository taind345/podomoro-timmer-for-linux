#!/bin/bash
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
APP_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
SHARED_DB="$APP_DIR/data/podomoro_stats.db"
FEDORA_LEGACY_DB="$HOME/.local/share/podomoro_stats.db"

mkdir -p "$APP_DIR/data"
mkdir -p "$HOME/.local/share"

echo "=== Syncing Fedora Data with Shared Database ==="
echo "Shared DB: $SHARED_DB"
echo "Fedora Local DB: $FEDORA_LEGACY_DB"

if [ -f "$FEDORA_LEGACY_DB" ] && [ ! -L "$FEDORA_LEGACY_DB" ]; then
    echo "Found Fedora local database. Merging into shared database..."
    python3 "$APP_DIR/src/sync_database.py" "$FEDORA_LEGACY_DB"
    
    # Backup legacy file
    mv "$FEDORA_LEGACY_DB" "$FEDORA_LEGACY_DB.backup_$(date +%Y%m%d%H%M%S)"
    # Create symlink so any legacy path points to shared DB
    ln -s "$SHARED_DB" "$FEDORA_LEGACY_DB"
    echo "Created symlink: $FEDORA_LEGACY_DB -> $SHARED_DB"
elif [ -L "$FEDORA_LEGACY_DB" ]; then
    echo "Symlink already exists: $FEDORA_LEGACY_DB points to $(readlink "$FEDORA_LEGACY_DB")"
else
    # Create symlink directly
    ln -sf "$SHARED_DB" "$FEDORA_LEGACY_DB"
    echo "Created symlink: $FEDORA_LEGACY_DB -> $SHARED_DB"
fi

echo "Running status check..."
python3 "$APP_DIR/src/sync_database.py"
echo "=== Sync Complete! ==="
