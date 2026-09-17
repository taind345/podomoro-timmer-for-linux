import sys
import os
import subprocess
import calendar
from datetime import datetime, timedelta

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
gi.require_version('PangoCairo', '1.0')
from gi.repository import Gtk, Adw, GLib, Pango, Gio, PangoCairo

import database
import platform_utils

class ScalableTimer(Gtk.DrawingArea):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_draw_func(self.on_draw)
        self.text = "25:00"
        
    def set_label(self, text):
        self.text = text
        self.queue_draw()

    def on_draw(self, area, cr, width, height):
        layout = self.create_pango_layout(self.text)
        desc = Pango.FontDescription("Sans Bold")
        
        # Scale to fit width and height. 
        scale = min(width / 3.0, height / 1.2)
        if scale < 10: scale = 10
        elif scale > 150: scale = 150
        
        desc.set_absolute_size(int(scale * Pango.SCALE))
        layout.set_font_description(desc)
        
        ink_rect, logical_rect = layout.get_extents()
        text_width = logical_rect.width / Pango.SCALE
        text_height = logical_rect.height / Pango.SCALE
        
        x = (width - text_width) / 2
        y = (height - text_height) / 2
        
        context = self.get_style_context()
        color = context.get_color()
        cr.set_source_rgba(color.red, color.green, color.blue, color.alpha)
        
        cr.move_to(x, y)
        PangoCairo.show_layout(cr, layout)

class PomodoroWindow(Adw.ApplicationWindow):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_title("Pomodoro Tracker")
        self.set_default_size(400, 600)

        # Timer constants
        self.session_queue = []
        self.current_chunk_duration = 25 * 60
        self.time_left = self.current_chunk_duration
        self.timer_id = None
        self.is_working = True
        self.DAILY_GOAL = 180 # minutes
        self.is_zen_mode = False
        self.zen_time_elapsed = 0
        self.is_accumulate_mode = False
        self.zen_accumulated_seconds = 0
        self.session_start_time = None
        self.zen_start_time = None
        
        database.init_db()

        # UI Setup
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_content(self.main_box)

        # HeaderBar with ViewSwitcher
        self.header = Adw.HeaderBar()
        self.main_box.append(self.header)

        self.view_stack = Adw.ViewStack()
        
        self.switcher_title = Adw.ViewSwitcherTitle()
        self.switcher_title.set_stack(self.view_stack)
        self.switcher_title.set_title("Pomodoro")
        self.header.set_title_widget(self.switcher_title)
        
        self.main_box.append(self.view_stack)

        # Build Views
        self.build_timer_view()
        self.build_stats_view()
        self.build_calendar_view()
        
        # Initialize default schedule
        self.on_apply_clicked(None)

    def build_timer_view(self):
        page = self.view_stack.add_titled_with_icon(Gtk.Box(), "timer", "Timer", "timer-symbolic")
        vbox = page.get_child()
        vbox.set_orientation(Gtk.Orientation.VERTICAL)
        vbox.set_spacing(24)
        vbox.set_margin_top(48)
        vbox.set_margin_bottom(48)
        vbox.set_margin_start(48)
        vbox.set_margin_end(48)
        vbox.set_halign(Gtk.Align.FILL)
        vbox.set_valign(Gtk.Align.FILL)

        # Zen Mode toggle
        mode_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        mode_box.set_halign(Gtk.Align.CENTER)
        
        mode_lbl = Gtk.Label(label="Zen Mode:")
        mode_box.append(mode_lbl)
        
        self.zen_switch = Gtk.Switch()
        self.zen_switch.set_valign(Gtk.Align.CENTER)
        self.zen_switch.connect("state-set", self.on_zen_mode_toggled)
        mode_box.append(self.zen_switch)
        
        self.accumulate_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.accumulate_box.set_margin_start(24)
        accumulate_lbl = Gtk.Label(label="Show Accumulated Time:")
        self.accumulate_box.append(accumulate_lbl)
        self.accumulate_switch = Gtk.Switch()
        self.accumulate_switch.set_valign(Gtk.Align.CENTER)
        self.accumulate_switch.connect("state-set", self.on_accumulate_toggled)
        self.accumulate_box.append(self.accumulate_switch)
        self.accumulate_box.set_visible(False)
        mode_box.append(self.accumulate_box)
        
        vbox.append(mode_box)

        # Flexible Session selector
        self.preset_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        self.preset_box.set_halign(Gtk.Align.CENTER)
        
        preset_lbl = Gtk.Label(label="Total Work Time (min):")
        self.preset_box.append(preset_lbl)
        
        adj = Gtk.Adjustment(value=120.0, lower=1.0, upper=1440.0, step_increment=5.0, page_increment=30.0, page_size=0.0)
        self.preset_spin = Gtk.SpinButton(adjustment=adj, numeric=True)
        self.preset_spin.connect("activate", self.on_apply_clicked)
        self.preset_box.append(self.preset_spin)
        
        apply_btn = Gtk.Button(label="Apply")
        apply_btn.add_css_class("suggested-action")
        apply_btn.connect("clicked", self.on_apply_clicked)
        self.preset_box.append(apply_btn)
        
        vbox.append(self.preset_box)
        
        # Status Label
        self.status_label = Gtk.Label(label="Ready to Work")
        self.status_label.add_css_class("title-2")
        vbox.append(self.status_label)

        # Scalable Time Area
        self.time_label = ScalableTimer()
        self.time_label.set_size_request(200, 100)
        self.time_label.set_label(self.format_time(self.time_left))
        self.time_label.set_vexpand(True)
        self.time_label.set_hexpand(True)
        vbox.append(self.time_label)

        # Buttons
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        button_box.set_halign(Gtk.Align.CENTER)
        
        self.start_btn = Gtk.Button(label="Start")
        self.start_btn.add_css_class("suggested-action")
        self.start_btn.add_css_class("pill")
        self.start_btn.connect("clicked", self.on_start_clicked)
        button_box.append(self.start_btn)
        
        self.pause_btn = Gtk.Button(label="Pause")
        self.pause_btn.set_sensitive(False)
        self.pause_btn.add_css_class("pill")
        self.pause_btn.connect("clicked", self.on_pause_clicked)
        button_box.append(self.pause_btn)

        self.stop_btn = Gtk.Button(label="Stop")
        self.stop_btn.set_sensitive(False)
        self.stop_btn.set_visible(False)
        self.stop_btn.add_css_class("destructive-action")
        self.stop_btn.add_css_class("pill")
        self.stop_btn.connect("clicked", self.on_stop_clicked)
        button_box.append(self.stop_btn)
        
        self.reset_btn = Gtk.Button(label="Reset")
        self.reset_btn.add_css_class("destructive-action")
        self.reset_btn.add_css_class("pill")
        self.reset_btn.connect("clicked", self.on_reset_clicked)
        button_box.append(self.reset_btn)

        vbox.append(button_box)

    def build_stats_view(self):
        # We need a ScrolledWindow for the stats page so it doesn't overflow
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=24)
        vbox.set_margin_top(24)
        vbox.set_margin_bottom(24)
        vbox.set_margin_start(24)
        vbox.set_margin_end(24)
        scrolled.set_child(vbox)

        # Today's Progress Box
        prog_group = Adw.PreferencesGroup()
        prog_group.set_title("Today's Progress")
        
        self.goal_label = Gtk.Label(label="")
        self.goal_label.set_halign(Gtk.Align.START)
        self.goal_label.add_css_class("heading")
        
        self.progress_bar = Gtk.ProgressBar()
        
        prog_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        prog_vbox.append(self.goal_label)
        prog_vbox.append(self.progress_bar)
        prog_vbox.set_margin_top(16)
        prog_vbox.set_margin_bottom(16)
        prog_vbox.set_margin_start(16)
        prog_vbox.set_margin_end(16)
        
        prog_row = Adw.ActionRow()
        prog_row.set_child(prog_vbox)
        prog_group.add(prog_row)
        vbox.append(prog_group)

        # Streak
        streak_group = Adw.PreferencesGroup()
        streak_group.set_title("Current Streak")
        self.streak_label = Gtk.Label(label="🔥 0 days")
        self.streak_label.set_halign(Gtk.Align.START)
        self.streak_label.add_css_class("title-3")
        
        streak_row = Adw.ActionRow()
        streak_row.set_child(self.streak_label)
        streak_group.add(streak_row)
        vbox.append(streak_group)

        # Yearly Total
        year_group = Adw.PreferencesGroup()
        year_group.set_title("Yearly Statistics")
        self.year_label = Gtk.Label(label="0 minutes studied this year")
        self.year_label.set_halign(Gtk.Align.START)
        
        year_row = Adw.ActionRow()
        year_row.set_child(self.year_label)
        year_group.add(year_row)
        vbox.append(year_group)

        # Today's Sessions Table
        session_group = Adw.PreferencesGroup()
        session_group.set_title("Today's Sessions")
        
        self.session_listbox = Gtk.ListBox()
        self.session_listbox.add_css_class("boxed-list")
        self.session_listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        
        session_group.add(self.session_listbox)
        vbox.append(session_group)

        self.view_stack.add_titled_with_icon(scrolled, "stats", "Stats", "view-list-symbolic")

        # Hook up view stack change to refresh stats
        self.view_stack.connect("notify::visible-child", self.on_view_changed)

    def build_calendar_view(self):
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        
        self.cal_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        self.cal_vbox.set_margin_top(24)
        self.cal_vbox.set_margin_bottom(24)
        self.cal_vbox.set_margin_start(24)
        self.cal_vbox.set_margin_end(24)
        scrolled.set_child(self.cal_vbox)

        # Header with Month/Year and navigation
        nav_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        nav_box.set_halign(Gtk.Align.CENTER)
        
        self.prev_month_btn = Gtk.Button(icon_name="go-previous-symbolic")
        self.prev_month_btn.connect("clicked", self.on_prev_month)
        self.prev_month_btn.add_css_class("flat")
        
        self.month_year_label = Gtk.Label()
        self.month_year_label.add_css_class("title-2")
        self.month_year_label.set_width_chars(15)
        
        self.next_month_btn = Gtk.Button(icon_name="go-next-symbolic")
        self.next_month_btn.connect("clicked", self.on_next_month)
        self.next_month_btn.add_css_class("flat")
        
        nav_box.append(self.prev_month_btn)
        nav_box.append(self.month_year_label)
        nav_box.append(self.next_month_btn)
        
        self.cal_vbox.append(nav_box)

        # The Grid for the calendar
        self.cal_grid = Gtk.Grid()
        self.cal_grid.set_column_spacing(6)
        self.cal_grid.set_row_spacing(6)
        self.cal_grid.set_halign(Gtk.Align.CENTER)
        self.cal_grid.set_valign(Gtk.Align.START)
        self.cal_vbox.append(self.cal_grid)

        # Initialize current month/year
        now = datetime.now()
        self.current_year = now.year
        self.current_month = now.month

        self.view_stack.add_titled_with_icon(scrolled, "calendar", "Calendar", "x-office-calendar-symbolic")

    def render_calendar(self):
        # Clear existing grid
        while child := self.cal_grid.get_first_child():
            self.cal_grid.remove(child)

        month_name = calendar.month_name[self.current_month]
        self.month_year_label.set_label(f"{month_name} {self.current_year}")

        # Day of week headers
        days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        for i, d in enumerate(days):
            lbl = Gtk.Label(label=d)
            lbl.add_css_class("dim-label")
            lbl.set_margin_bottom(8)
            self.cal_grid.attach(lbl, i, 0, 1, 1)

        # Get data for this month
        month_data = database.get_daily_totals_for_month(self.current_year, self.current_month)

        # Calendar matrix
        cal = calendar.monthcalendar(self.current_year, self.current_month)
        
        for row_idx, week in enumerate(cal):
            for col_idx, day in enumerate(week):
                if day == 0:
                    continue # empty cell
                
                # Cell Box
                cell = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
                cell.set_size_request(85, 85)
                
                # Add a border
                frame = Gtk.Frame()
                frame.set_child(cell)
                
                # Day label
                day_lbl = Gtk.Label(label=str(day))
                day_lbl.set_halign(Gtk.Align.START)
                day_lbl.set_margin_start(4)
                day_lbl.set_margin_top(4)
                day_lbl.add_css_class("caption")
                cell.append(day_lbl)

                # Data label
                total_mins = month_data.get(day, 0)
                if total_mins > 0:
                    data_lbl = Gtk.Label(label=f"{total_mins}m")
                    data_lbl.set_halign(Gtk.Align.CENTER)
                    data_lbl.set_valign(Gtk.Align.CENTER)
                    data_lbl.set_hexpand(True)
                    data_lbl.set_vexpand(True)
                    
                    if total_mins >= self.DAILY_GOAL:
                        data_lbl.add_css_class("success")
                    else:
                        data_lbl.add_css_class("accent")
                        
                    cell.append(data_lbl)
                
                self.cal_grid.attach(frame, col_idx, row_idx + 1, 1, 1)

    def on_prev_month(self, btn):
        if self.current_month == 1:
            self.current_month = 12
            self.current_year -= 1
        else:
            self.current_month -= 1
        self.render_calendar()

    def on_next_month(self, btn):
        if self.current_month == 12:
            self.current_month = 1
            self.current_year += 1
        else:
            self.current_month += 1
        self.render_calendar()

    def on_view_changed(self, stack, param):
        visible_child = stack.get_visible_child_name()
        if visible_child == "stats":
            self.refresh_stats()
        elif visible_child == "calendar":
            self.render_calendar()

    def refresh_stats(self):
        # Update Today
        today_total = database.get_today_total()
        fraction = min(today_total / self.DAILY_GOAL, 1.0)
        self.progress_bar.set_fraction(fraction)
        
        if today_total >= self.DAILY_GOAL:
            self.goal_label.set_text(f"🎉 Goal reached! {today_total} / {self.DAILY_GOAL} min")
        else:
            self.goal_label.set_text(f"Study Time: {today_total} / {self.DAILY_GOAL} min")
            
        # Update Streak
        streak = database.get_current_streak(self.DAILY_GOAL)
        self.streak_label.set_text(f"🔥 {streak} days")

        # Update Year
        year_total = database.get_year_total()
        self.year_label.set_text(f"{year_total} minutes studied this year")
        
        # Update ListBox
        while child := self.session_listbox.get_first_child():
            self.session_listbox.remove(child)
            
        sessions = database.get_today_sessions()
        if not sessions:
            row = Adw.ActionRow()
            row.set_title("No sessions yet today")
            self.session_listbox.append(row)
        else:
            for timestamp, duration in sessions:
                row = Adw.ActionRow()
                time_only = timestamp.split()[1] if " " in timestamp else timestamp
                row.set_title(f"{time_only}")
                row.set_subtitle(f"{duration} minutes")
                
                icon = Gtk.Image.new_from_icon_name("media-playback-start-symbolic")
                row.add_prefix(icon)
                self.session_listbox.append(row)

    def format_time(self, seconds):
        m = seconds // 60
        s = seconds % 60
        if m >= 60:
            h = m // 60
            m = m % 60
            return f"{h:02d}:{m:02d}:{s:02d}"
        return f"{m:02d}:{s:02d}"

    def on_start_clicked(self, btn):
        if not self.timer_id:
            self.timer_id = GLib.timeout_add(1000, self.on_timer_tick)
            self.start_btn.set_sensitive(False)
            self.pause_btn.set_sensitive(True)
            if self.is_zen_mode:
                self.stop_btn.set_sensitive(True)
                if self.zen_start_time is None:
                    self.zen_start_time = datetime.now()
            else:
                if self.is_working and self.session_start_time is None:
                    self.session_start_time = datetime.now()

    def on_pause_clicked(self, btn):
        if self.timer_id:
            GLib.source_remove(self.timer_id)
            self.timer_id = None
            self.start_btn.set_sensitive(True)
            self.pause_btn.set_sensitive(False)

    def on_zen_mode_toggled(self, switch, state):
        self.is_zen_mode = state
        self.preset_box.set_visible(not state)
        self.stop_btn.set_visible(state)
        self.reset_btn.set_visible(not state)
        self.accumulate_box.set_visible(state)
        
        if self.timer_id:
            GLib.source_remove(self.timer_id)
            self.timer_id = None
            
        if not state:
            duration_mins = self.zen_time_elapsed // 60
            if duration_mins > 0:
                start_time = self.zen_start_time or (datetime.now() - timedelta(seconds=self.zen_time_elapsed))
                database.add_session(duration_mins, start_time)
                platform_utils.play_alert_sound()
                self.send_notification("Zen Mode Finished", f"Great job! You studied for {duration_mins} minutes.")
            self.zen_time_elapsed = 0
            self.zen_start_time = None
        
        if state:
            self.status_label.set_label("Zen Mode")
            self.zen_time_elapsed = 0
            self.zen_start_time = None
            self.zen_accumulated_seconds = database.get_today_total() * 60
            self.update_zen_time_display()
            self.start_btn.set_sensitive(True)
            self.pause_btn.set_sensitive(False)
            self.stop_btn.set_sensitive(False)
        else:
            self.on_apply_clicked(None)
            
        return False

    def on_accumulate_toggled(self, switch, state):
        self.is_accumulate_mode = state
        self.update_zen_time_display()
        return False

    def update_zen_time_display(self):
        if not self.is_zen_mode:
            return
        display_seconds = self.zen_time_elapsed
        if self.is_accumulate_mode:
            display_seconds += self.zen_accumulated_seconds
        self.time_label.set_label(self.format_time(display_seconds))

    def on_stop_clicked(self, btn):
        if self.timer_id:
            GLib.source_remove(self.timer_id)
            self.timer_id = None
            
        duration_mins = self.zen_time_elapsed // 60
        if duration_mins > 0:
            start_time = self.zen_start_time or (datetime.now() - timedelta(seconds=self.zen_time_elapsed))
            database.add_session(duration_mins, start_time)
            platform_utils.play_alert_sound()
            self.send_notification("Zen Mode Finished", f"Great job! You studied for {duration_mins} minutes.")
            
        self.zen_time_elapsed = 0
        self.zen_start_time = None
        self.zen_accumulated_seconds = database.get_today_total() * 60
        self.update_zen_time_display()
        self.start_btn.set_sensitive(True)
        self.pause_btn.set_sensitive(False)
        self.stop_btn.set_sensitive(False)

    def on_apply_clicked(self, btn):
        total_work_mins = int(self.preset_spin.get_value())
        self.generate_schedule(total_work_mins)
            
    def generate_schedule(self, total_work_mins):
        if self.timer_id:
            GLib.source_remove(self.timer_id)
            self.timer_id = None
            
        self.session_queue = []
        self.session_start_time = None
        break_chunk = 5
        
        if total_work_mins < 30:
            num_sessions = 1
        else:
            num_sessions = int(total_work_mins / 30.0 + 0.5)
            
        session_duration = total_work_mins // num_sessions
        remainder = total_work_mins % num_sessions
        
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
            self.status_label.set_label("Session Complete!")
            self.time_left = 0
            self.time_label.set_label("00:00")
            self.is_working = False
            self.start_btn.set_sensitive(False)
            self.pause_btn.set_sensitive(False)
            return
            
        session_type, duration = self.session_queue.pop(0)
        self.is_working = (session_type == "Work")
        self.current_chunk_duration = duration
        self.time_left = duration
        
        if self.is_working:
            self.current_block += 1
            self.status_label.set_label(f"Working: Block {self.current_block} of {self.total_blocks} ({duration//60}m)")
            if self.timer_id:
                self.session_start_time = datetime.now()
            else:
                self.session_start_time = None
        else:
            self.status_label.set_label(f"Break Time! ({duration//60}m)")
            self.session_start_time = None
            
        self.time_label.set_label(self.format_time(self.time_left))
        
        if not self.timer_id:
            self.start_btn.set_sensitive(True)
            self.pause_btn.set_sensitive(False)

    def on_reset_clicked(self, btn):
        self.on_apply_clicked(None)

    def on_timer_tick(self):
        if self.is_zen_mode:
            self.zen_time_elapsed += 1
            self.update_zen_time_display()
            return True

        self.time_left -= 1
        self.time_label.set_label(self.format_time(self.time_left))
        
        if self.time_left <= 0:
            platform_utils.play_alert_sound()

            if self.is_working:
                duration_mins = self.current_chunk_duration // 60
                start_time = self.session_start_time or (datetime.now() - timedelta(seconds=self.current_chunk_duration))
                database.add_session(duration_mins, start_time)
                self.send_notification("Pomodoro Finished", f"Great job! You studied for {duration_mins} minutes.")
                self.session_start_time = None
            else:
                self.send_notification("Break Finished", "Time to get back to work!")
                
            self.load_next_session()
            
            if self.time_left > 0:
                return True
            else:
                self.timer_id = None
                return False
            
        return True

    def send_notification(self, title, body):
        notification = Gio.Notification.new(title)
        notification.set_body(body)
        app = self.get_application()
        app.send_notification("pomodoro-alert", notification)

class PomodoroApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id='com.example.Pomodoro')

    def do_activate(self):
        win = self.props.active_window
        if not win:
            win = PomodoroWindow(application=self)
        win.present()

def run_app():
    app = PomodoroApp()
    return app.run(sys.argv)

if __name__ == '__main__':
    run_app()
