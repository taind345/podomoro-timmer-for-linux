import sys
import app
win = app.PomodoroWindow()
win.preset_spin.set_value(60)
win.on_apply_clicked(None)
print("Queue:", win.session_queue)
print("Time left:", win.time_left)
