import sys
import os
import argparse

# Add 'src' package directory to Python path
SRC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

import platform_utils

def main():
    parser = argparse.ArgumentParser(description="Pomodoro Tracker (Windows & Linux Fedora Native)")
    parser.add_argument(
        "--ui",
        choices=["auto", "gtk", "win"],
        default="auto",
        help="Choose UI frontend: auto (detect OS), gtk (GTK4/Libadwaita), win (Windows Native/ttkbootstrap)"
    )
    args, unknown = parser.parse_known_args()

    chosen_ui = args.ui

    if chosen_ui == "gtk":
        from ui.ui_gtk import run_app
        return run_app()

    if chosen_ui == "win":
        from ui.ui_win import run_app
        return run_app()

    # Auto detection
    if platform_utils.is_linux():
        try:
            from ui.ui_gtk import run_app
            return run_app()
        except ImportError as e:
            print(f"[Notice] GTK4 / Libadwaita not available ({e}). Falling back to native cross-platform UI...")
            from ui.ui_win import run_app
            return run_app()
    else:
        # Windows or other OS
        from ui.ui_win import run_app
        return run_app()

# Compatibility exports for existing scripts and tests
if platform_utils.is_linux():
    try:
        from ui.ui_gtk import PomodoroWindow, PomodoroApp, ScalableTimer
    except ImportError:
        pass

if __name__ == "__main__":
    sys.exit(main() or 0)
