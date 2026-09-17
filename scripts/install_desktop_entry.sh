#!/bin/bash
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
APP_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
DESKTOP_FILE="$HOME/.local/share/applications/pomodoro-tracker.desktop"

mkdir -p "$HOME/.local/share/applications"

cat > "$DESKTOP_FILE" <<EOF
[Desktop Entry]
Name=Pomodoro Tracker
Comment=Pomodoro Timer and Focus Tracker (Dual-boot Windows & Fedora)
Exec="$APP_DIR/run.sh"
Icon=$APP_DIR/icon.png
Terminal=false
Type=Application
Categories=Utility;Clock;Education;
StartupNotify=true
EOF

chmod +x "$DESKTOP_FILE"
echo "[SUCCESS] Desktop entry created at: $DESKTOP_FILE"
