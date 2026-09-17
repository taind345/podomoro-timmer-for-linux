import os
import sys
import subprocess

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
CHIME_PATH = os.path.join(ASSETS_DIR, "chime.wav")
TOAST_SCRIPT = os.path.join(ASSETS_DIR, "toast.ps1")
ICON_PATH = os.path.join(BASE_DIR, "icon.png")

def is_windows():
    return sys.platform.startswith("win")

def is_linux():
    return sys.platform.startswith("linux")

def is_windows_dark_mode():
    """Detect if Windows is set to dark theme for apps."""
    if not is_windows():
        return False
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
        )
        val, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
        return val == 0
    except Exception:
        return True # Default to dark theme

def play_alert_sound():
    """Play alert sound asynchronously on either Linux or Windows."""
    if is_windows():
        try:
            import winsound
            if os.path.exists(CHIME_PATH):
                winsound.PlaySound(CHIME_PATH, winsound.SND_FILENAME | winsound.SND_ASYNC)
            else:
                winsound.MessageBeep(winsound.MB_ICONASTERISK)
        except Exception as e:
            print(f"Error playing sound on Windows: {e}")
    else:
        # Linux
        system_sound = "/usr/share/sounds/freedesktop/stereo/complete.oga"
        sound_to_play = system_sound if os.path.exists(system_sound) else CHIME_PATH
        for player in ["paplay", "pw-play", "aplay"]:
            try:
                subprocess.Popen([player, sound_to_play], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return
            except FileNotFoundError:
                continue
            except Exception as e:
                print(f"Error playing sound on Linux with {player}: {e}")

def send_notification(title, message, app=None):
    """Send desktop notification on either Linux or Windows."""
    if is_windows():
        if os.path.exists(TOAST_SCRIPT):
            try:
                subprocess.Popen(
                    [
                        "powershell",
                        "-NoProfile",
                        "-ExecutionPolicy", "Bypass",
                        "-WindowStyle", "Hidden",
                        "-File", TOAST_SCRIPT,
                        "-Title", title,
                        "-Message", message,
                    ],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
                return
            except Exception as e:
                print(f"Error triggering Windows toast: {e}")
    else:
        # Linux Gio notification if app is provided
        if app is not None:
            try:
                from gi.repository import Gio
                notification = Gio.Notification.new(title)
                notification.set_body(message)
                app.send_notification("pomodoro-alert", notification)
                return
            except Exception:
                pass
        # Fallback to notify-send
        try:
            subprocess.Popen(["notify-send", title, message], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            print(f"Error sending notification via notify-send: {e}")
