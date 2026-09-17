import sys
import os
import argparse
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
        from ui_gtk import run_app
        return run_app()

    if chosen_ui == "win":
        from ui_win import run_app
        return run_app()

    # Auto detection
    if platform_utils.is_linux():
        try:
            from ui_gtk import run_app
            return run_app()
        except ImportError as e:
            print(f"[Notice] GTK4 / Libadwaita not available ({e}). Falling back to native cross-platform UI...")
            from ui_win import run_app
            return run_app()
    else:
        # Windows or other OS
        from ui_win import run_app
        return run_app()

# Compatibility exports for existing scripts and tests
if platform_utils.is_linux():
    try:
        from ui_gtk import PomodoroWindow, PomodoroApp, ScalableTimer
    except ImportError:
        pass

if __name__ == "__main__":
    sys.exit(main() or 0)
