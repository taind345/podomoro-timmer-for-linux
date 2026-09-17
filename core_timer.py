from datetime import datetime, timedelta
import database

def format_time(seconds):
    """Format seconds into MM:SS or HH:MM:SS."""
    seconds = max(0, int(seconds))
    m = seconds // 60
    s = seconds % 60
    if m >= 60:
        h = m // 60
        m = m % 60
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"

class PomodoroCore:
    def __init__(self, daily_goal=180, default_work_mins=120):
        self.daily_goal = daily_goal
        self.default_work_mins = default_work_mins
        self.total_work_mins = default_work_mins
        
        self.session_queue = []
        self.current_chunk_duration = 25 * 60
        self.time_left = self.current_chunk_duration
        self.is_working = True
        self.is_running = False
        self.total_blocks = 0
        self.current_block = 0
        
        self.session_start_time = None
        self.status_text = "Ready to Work"
        
        # Zen Mode
        self.is_zen_mode = False
        self.zen_time_elapsed = 0
        self.zen_start_time = None
        self.is_accumulate_mode = False
        self.zen_accumulated_seconds = 0
        
        self.generate_schedule(self.default_work_mins)

    def generate_schedule(self, total_work_mins):
        self.is_running = False
        self.total_work_mins = max(1, int(total_work_mins))
        self.session_queue = []
        self.session_start_time = None
        break_chunk = 5

        if self.total_work_mins < 30:
            num_sessions = 1
        else:
            num_sessions = int(self.total_work_mins / 30.0 + 0.5)

        session_duration = self.total_work_mins // num_sessions
        remainder = self.total_work_mins % num_sessions

        for i in range(num_sessions):
            curr_duration = session_duration
            if i == num_sessions - 1:
                curr_duration += remainder

            self.session_queue.append(("Work", curr_duration * 60))
            if i < num_sessions - 1:
                self.session_queue.append(("Break", break_chunk * 60))

        self.total_blocks = sum(1 for q in self.session_queue if q[0] == "Work")
        self.current_block = 0
        self.load_next_session()

    def load_next_session(self):
        if not self.session_queue:
            self.status_text = "Session Complete!"
            self.time_left = 0
            self.is_working = False
            self.is_running = False
            return False

        session_type, duration = self.session_queue.pop(0)
        self.is_working = (session_type == "Work")
        self.current_chunk_duration = duration
        self.time_left = duration

        if self.is_working:
            self.current_block += 1
            self.status_text = f"Working: Block {self.current_block} of {self.total_blocks} ({duration // 60}m)"
            if self.is_running:
                self.session_start_time = datetime.now()
            else:
                self.session_start_time = None
        else:
            self.status_text = f"Break Time! ({duration // 60}m)"
            self.session_start_time = None

        return True

    def start(self):
        self.is_running = True
        if self.is_zen_mode:
            if self.zen_start_time is None:
                self.zen_start_time = datetime.now()
        else:
            if self.is_working and self.session_start_time is None:
                self.session_start_time = datetime.now()

    def pause(self):
        self.is_running = False

    def reset(self):
        self.is_running = False
        self.generate_schedule(self.total_work_mins)

    def set_zen_mode(self, enabled):
        self.is_zen_mode = enabled
        self.is_running = False

        if not enabled:
            # Finishing Zen Mode
            duration_mins = self.zen_time_elapsed // 60
            if duration_mins > 0:
                start_time = self.zen_start_time or (datetime.now() - timedelta(seconds=self.zen_time_elapsed))
                database.add_session(duration_mins, start_time)
                saved_session = (duration_mins, start_time)
            else:
                saved_session = None
            self.zen_time_elapsed = 0
            self.zen_start_time = None
            self.generate_schedule(self.total_work_mins)
            return saved_session
        else:
            self.status_text = "Zen Mode"
            self.zen_time_elapsed = 0
            self.zen_start_time = None
            self.zen_accumulated_seconds = database.get_today_total() * 60
            return None

    def stop_zen(self):
        self.is_running = False
        duration_mins = self.zen_time_elapsed // 60
        saved = None
        if duration_mins > 0:
            start_time = self.zen_start_time or (datetime.now() - timedelta(seconds=self.zen_time_elapsed))
            database.add_session(duration_mins, start_time)
            saved = duration_mins
        self.zen_time_elapsed = 0
        self.zen_start_time = None
        self.zen_accumulated_seconds = database.get_today_total() * 60
        return saved

    def get_display_time(self):
        if self.is_zen_mode:
            display_seconds = self.zen_time_elapsed
            if self.is_accumulate_mode:
                display_seconds += self.zen_accumulated_seconds
            return format_time(display_seconds)
        return format_time(self.time_left)

    def tick(self):
        """Execute one second tick. Returns a dictionary describing events."""
        if not self.is_running:
            return {"event": "none"}

        if self.is_zen_mode:
            self.zen_time_elapsed += 1
            return {
                "event": "tick",
                "display_time": self.get_display_time(),
                "is_zen": True,
            }

        self.time_left -= 1
        display_time = self.get_display_time()

        if self.time_left <= 0:
            # Session chunk completed
            was_working = self.is_working
            saved_duration = 0
            if was_working:
                saved_duration = self.current_chunk_duration // 60
                start_time = self.session_start_time or (
                    datetime.now() - timedelta(seconds=self.current_chunk_duration)
                )
                database.add_session(saved_duration, start_time)
                self.session_start_time = None

            has_next = self.load_next_session()
            if not has_next:
                self.is_running = False
                return {
                    "event": "all_complete",
                    "was_working": was_working,
                    "duration_mins": saved_duration,
                    "display_time": "00:00",
                    "status_text": self.status_text,
                }
            else:
                return {
                    "event": "chunk_complete",
                    "was_working": was_working,
                    "duration_mins": saved_duration,
                    "display_time": self.get_display_time(),
                    "status_text": self.status_text,
                }

        return {
            "event": "tick",
            "display_time": display_time,
            "is_zen": False,
        }
