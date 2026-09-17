import os
import sys
import calendar
from datetime import datetime, timedelta
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk

import database
from core_timer import PomodoroCore, format_time
import platform_utils

# =====================================================================
# GNOME LIBADWAITA DARK PALETTE
# =====================================================================
COLOR_BG = "#242424"          # Base window background
COLOR_HEADER = "#1e1e1e"      # HeaderBar background
COLOR_CARD = "#2e2e2e"        # PreferencesGroup card surface
COLOR_CARD_BORDER = "#383838" # Card outline
COLOR_TEXT_PRIMARY = "#ffffff"
COLOR_TEXT_SECONDARY = "#9a9996"
COLOR_TEXT_MUTED = "#77767b"
COLOR_ACCENT_BLUE = "#3584e4" # Libadwaita suggested action
COLOR_ACCENT_HOVER = "#4a90e8"
COLOR_ACCENT_GREEN = "#33d17a" # Libadwaita success
COLOR_ACCENT_RED = "#e01b24"   # Libadwaita destructive
COLOR_RED_HOVER = "#e83a42"
COLOR_BTN_NEUTRAL = "#383838"  # Regular button background
COLOR_BTN_HOVER = "#444444"
COLOR_SEPARATOR = "#333333"

# =====================================================================
# CUSTOM WIDGETS MATCHING GTK4 / LIBADWAITA
# =====================================================================

class AdwSwitch(tk.Canvas):
    """Native Gtk.Switch equivalent in Tkinter with smooth rounded look."""
    def __init__(self, master, command=None, initial=False, width=44, height=24, **kwargs):
        super().__init__(
            master,
            width=width,
            height=height,
            bg=COLOR_BG,
            highlightthickness=0,
            cursor="hand2",
            **kwargs,
        )
        self.command = command
        self.state = initial
        self.bind("<Button-1>", self.toggle)
        self.draw()

    def toggle(self, event=None):
        self.state = not self.state
        self.draw()
        if self.command:
            self.command(self.state)

    def set_state(self, new_state):
        if self.state != new_state:
            self.state = new_state
            self.draw()

    def draw(self):
        self.delete("all")
        bg_col = COLOR_ACCENT_BLUE if self.state else COLOR_BTN_NEUTRAL
        # Pill track
        self.create_oval(2, 2, 22, 22, fill=bg_col, outline=bg_col)
        self.create_oval(22, 2, 42, 22, fill=bg_col, outline=bg_col)
        self.create_rectangle(12, 2, 32, 22, fill=bg_col, outline=bg_col)
        # Knob
        if self.state:
            self.create_oval(22, 3, 41, 21, fill="#ffffff", outline="#ffffff")
        else:
            self.create_oval(3, 3, 21, 21, fill="#ffffff", outline="#ffffff")

class AdwPillButton(tk.Canvas):
    """Pill-shaped rounded button styled after Libadwaita buttons."""
    def __init__(
        self,
        master,
        text="",
        bg_color=COLOR_BTN_NEUTRAL,
        hover_color=COLOR_BTN_HOVER,
        text_color=COLOR_TEXT_PRIMARY,
        command=None,
        width=100,
        height=36,
        font=("Segoe UI", 10, "bold"),
        **kwargs
    ):
        super().__init__(
            master,
            width=width,
            height=height,
            bg=COLOR_BG,
            highlightthickness=0,
            cursor="hand2",
            **kwargs
        )
        self.text = text
        self.bg_color = bg_color
        self.hover_color = hover_color
        self.current_bg = bg_color
        self.text_color = text_color
        self.command = command
        self.font = font
        self.w = width
        self.h = height
        self.is_enabled = True

        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)
        self.bind("<Button-1>", self.on_click)
        self.draw()

    def set_enabled(self, enabled):
        self.is_enabled = enabled
        self.configure(cursor="hand2" if enabled else "arrow")
        self.draw()

    def on_enter(self, e):
        if self.is_enabled:
            self.current_bg = self.hover_color
            self.draw()

    def on_leave(self, e):
        if self.is_enabled:
            self.current_bg = self.bg_color
            self.draw()

    def on_click(self, e):
        if self.is_enabled and self.command:
            self.command()

    def set_text(self, text):
        self.text = text
        self.draw()

    def draw(self):
        self.delete("all")
        bg = self.current_bg if self.is_enabled else "#2a2a2a"
        fg = self.text_color if self.is_enabled else COLOR_TEXT_MUTED

        r = self.h // 2
        # Pill shape: two circles + rectangle
        self.create_oval(2, 2, self.h - 2, self.h - 2, fill=bg, outline=bg)
        self.create_oval(self.w - self.h + 2, 2, self.w - 2, self.h - 2, fill=bg, outline=bg)
        self.create_rectangle(r, 2, self.w - r, self.h - 2, fill=bg, outline=bg)
        # Centered text
        self.create_text(self.w // 2, self.h // 2, text=self.text, fill=fg, font=self.font)

class AdwProgressBar(tk.Canvas):
    """Sleek rounded progress bar matching AdwProgressBar."""
    def __init__(self, master, height=8, **kwargs):
        super().__init__(master, height=height, bg=COLOR_CARD, highlightthickness=0, **kwargs)
        self.fraction = 0.0
        self.fill_color = COLOR_ACCENT_BLUE
        self.bind("<Configure>", self.draw)

    def set_fraction(self, fraction, is_goal_reached=False):
        self.fraction = max(0.0, min(1.0, fraction))
        self.fill_color = COLOR_ACCENT_GREEN if is_goal_reached else COLOR_ACCENT_BLUE
        self.draw()

    def draw(self, event=None):
        self.delete("all")
        w = self.winfo_width()
        h = self.winfo_height()
        if w <= 1:
            return

        r = h // 2
        # Background track
        self.create_oval(0, 0, h, h, fill=COLOR_BTN_NEUTRAL, outline=COLOR_BTN_NEUTRAL)
        self.create_oval(w - h, 0, w, h, fill=COLOR_BTN_NEUTRAL, outline=COLOR_BTN_NEUTRAL)
        self.create_rectangle(r, 0, w - r, h, fill=COLOR_BTN_NEUTRAL, outline=COLOR_BTN_NEUTRAL)

        # Active fill
        fill_w = int(w * self.fraction)
        if fill_w > h:
            self.create_oval(0, 0, h, h, fill=self.fill_color, outline=self.fill_color)
            self.create_oval(fill_w - h, 0, fill_w, h, fill=self.fill_color, outline=self.fill_color)
            self.create_rectangle(r, 0, fill_w - r, h, fill=self.fill_color, outline=self.fill_color)
        elif fill_w > 0:
            self.create_oval(0, 0, fill_w, h, fill=self.fill_color, outline=self.fill_color)

class ScalableTimerCanvas(tk.Canvas):
    """Cairo ScalableTimer equivalent for Tkinter with dynamic scaling."""
    def __init__(self, master, **kwargs):
        super().__init__(master, bg=COLOR_BG, highlightthickness=0, **kwargs)
        self.text = "25:00"
        self.text_id = self.create_text(0, 0, text=self.text, fill=COLOR_TEXT_PRIMARY, font=("Segoe UI", 48, "bold"))
        self.bind("<Configure>", self.on_resize)

    def set_label(self, text):
        self.text = text
        self.itemconfig(self.text_id, text=self.text)

    def on_resize(self, event):
        w = event.width
        h = event.height
        if w < 10 or h < 10:
            return
        scale = min(w / 3.0, h / 1.1)
        scale = max(18, min(130, int(scale)))
        font = ("Segoe UI", scale, "bold")
        self.itemconfig(self.text_id, font=font)
        self.coords(self.text_id, w / 2, h / 2)

# =====================================================================
# MAIN WINDOW (ADWAITA / WINDOWS NATIVE)
# =====================================================================

class PomodoroWinApp:
    def __init__(self):
        # Enable Windows High-DPI awareness
        if platform_utils.is_windows():
            try:
                import ctypes
                try:
                    ctypes.windll.shcore.SetProcessDpiAwareness(1)
                except Exception:
                    ctypes.windll.user32.SetProcessDPIAware()
            except Exception:
                pass

        self.root = tk.Tk()
        self.root.title("Pomodoro Tracker")
        self.root.geometry("450x670")
        self.root.minsize(400, 580)
        self.root.configure(bg=COLOR_BG)

        # Set Window Icon
        self.icon_image = None
        ico_path = os.path.join(platform_utils.ASSETS_DIR, "icon.ico")
        if platform_utils.is_windows() and os.path.exists(ico_path):
            try:
                self.root.iconbitmap(ico_path)
            except Exception:
                pass
        if os.path.exists(platform_utils.ICON_PATH):
            try:
                pil_img = Image.open(platform_utils.ICON_PATH)
                self.icon_image = ImageTk.PhotoImage(pil_img, master=self.root)
                self.root.iconphoto(True, self.icon_image)
            except Exception:
                pass

        # Core logic & Database initialization
        database.init_db()
        self.core = PomodoroCore(daily_goal=180, default_work_mins=120)
        self.timer_job = None

        # Calendar state
        now = datetime.now()
        self.cal_year = now.year
        self.cal_month = now.month

        # Build UI
        self.build_ui()
        self.switch_tab("timer")

    def build_ui(self):
        # 1. HeaderBar matching GNOME AdwHeaderBar
        header_bar = tk.Frame(self.root, bg=COLOR_HEADER, height=52)
        header_bar.pack(fill=tk.X)
        header_bar.pack_propagate(False)

        # ViewSwitcher (Segmented pill tabs centered in header)
        switcher_box = tk.Frame(header_bar, bg="#2b2b2b", highlightbackground=COLOR_CARD_BORDER, highlightthickness=1)
        switcher_box.pack(anchor=tk.CENTER, pady=8)

        self.nav_tabs = {}
        tab_defs = [("timer", "⏱️ Timer"), ("stats", "📊 Stats"), ("calendar", "📅 Calendar")]
        for tab_id, tab_label in tab_defs:
            lbl = tk.Label(
                switcher_box,
                text=tab_label,
                bg="#2b2b2b",
                fg=COLOR_TEXT_SECONDARY,
                font=("Segoe UI", 9, "bold"),
                padx=14,
                pady=5,
                cursor="hand2",
            )
            lbl.pack(side=tk.LEFT)
            lbl.bind("<Button-1>", lambda e, tid=tab_id: self.switch_tab(tid))
            self.nav_tabs[tab_id] = lbl

        # Separator line under HeaderBar
        tk.Frame(self.root, bg=COLOR_SEPARATOR, height=1).pack(fill=tk.X)

        # 2. Main Content Container
        self.main_container = tk.Frame(self.root, bg=COLOR_BG)
        self.main_container.pack(fill=tk.BOTH, expand=True)

        self.view_timer = tk.Frame(self.main_container, bg=COLOR_BG)
        self.view_stats = tk.Frame(self.main_container, bg=COLOR_BG)
        self.view_calendar = tk.Frame(self.main_container, bg=COLOR_BG)

        self.build_timer_view()
        self.build_stats_view()
        self.build_calendar_view()

    # -------------------------------------------------------------
    # TAB SWITCHING
    # -------------------------------------------------------------
    def switch_tab(self, active_tab):
        self.view_timer.pack_forget()
        self.view_stats.pack_forget()
        self.view_calendar.pack_forget()

        for tid, widget in self.nav_tabs.items():
            if tid == active_tab:
                widget.configure(bg="#3c3c3c", fg=COLOR_TEXT_PRIMARY)
            else:
                widget.configure(bg="#2b2b2b", fg=COLOR_TEXT_SECONDARY)

        if active_tab == "timer":
            self.view_timer.pack(fill=tk.BOTH, expand=True)
        elif active_tab == "stats":
            self.view_stats.pack(fill=tk.BOTH, expand=True)
            self.refresh_stats()
        elif active_tab == "calendar":
            self.view_calendar.pack(fill=tk.BOTH, expand=True)
            self.render_calendar()

    # -------------------------------------------------------------
    # 1. TIMER VIEW (Pure GNOME Libadwaita aesthetic)
    # -------------------------------------------------------------
    def build_timer_view(self):
        container = self.view_timer

        # Top Margin
        tk.Frame(container, bg=COLOR_BG, height=20).pack()

        # Mode Box (Zen Mode + Accumulate Switch)
        mode_frame = tk.Frame(container, bg=COLOR_BG)
        mode_frame.pack(fill=tk.X, pady=(0, 16))

        inner_mode = tk.Frame(mode_frame, bg=COLOR_BG)
        inner_mode.pack(anchor=tk.CENTER)

        tk.Label(inner_mode, text="Zen Mode:", bg=COLOR_BG, fg=COLOR_TEXT_PRIMARY, font=("Segoe UI", 10)).pack(side=tk.LEFT, padx=(0, 10))
        self.zen_switch = AdwSwitch(inner_mode, command=self.on_zen_mode_toggled)
        self.zen_switch.pack(side=tk.LEFT, padx=(0, 16))

        self.accumulate_container = tk.Frame(inner_mode, bg=COLOR_BG)
        tk.Label(self.accumulate_container, text="Show Accumulated Time:", bg=COLOR_BG, fg=COLOR_TEXT_PRIMARY, font=("Segoe UI", 10)).pack(side=tk.LEFT, padx=(0, 8))
        self.accumulate_switch = AdwSwitch(self.accumulate_container, command=self.on_accumulate_toggled)
        self.accumulate_switch.pack(side=tk.LEFT)

        # Preset Spinbox row (Total Work Time)
        self.preset_frame = tk.Frame(container, bg=COLOR_BG)
        self.preset_frame.pack(fill=tk.X, pady=(0, 18))

        inner_preset = tk.Frame(self.preset_frame, bg=COLOR_BG)
        inner_preset.pack(anchor=tk.CENTER)

        tk.Label(inner_preset, text="Total Work Time (min):", bg=COLOR_BG, fg=COLOR_TEXT_PRIMARY, font=("Segoe UI", 10)).pack(side=tk.LEFT, padx=(0, 10))

        self.preset_var = tk.IntVar(value=120)
        self.preset_spin = tk.Spinbox(
            inner_preset,
            from_=1,
            to=1440,
            increment=5,
            textvariable=self.preset_var,
            width=5,
            bg=COLOR_CARD,
            fg=COLOR_TEXT_PRIMARY,
            insertbackground="#ffffff",
            highlightbackground=COLOR_CARD_BORDER,
            highlightcolor=COLOR_ACCENT_BLUE,
            highlightthickness=1,
            bd=0,
            font=("Segoe UI", 10, "bold"),
            justify="center",
        )
        self.preset_spin.pack(side=tk.LEFT, padx=(0, 10), ipady=3)
        self.preset_spin.bind("<Return>", lambda e: self.on_apply_clicked())

        self.apply_btn = AdwPillButton(
            inner_preset,
            text="Apply",
            bg_color=COLOR_ACCENT_BLUE,
            hover_color=COLOR_ACCENT_HOVER,
            command=self.on_apply_clicked,
            width=70,
            height=30,
            font=("Segoe UI", 9, "bold"),
        )
        self.apply_btn.pack(side=tk.LEFT)

        # Status Label (Title-2)
        self.status_label = tk.Label(
            container,
            text=self.core.status_text,
            bg=COLOR_BG,
            fg=COLOR_TEXT_PRIMARY,
            font=("Segoe UI", 15, "bold"),
            anchor="center",
        )
        self.status_label.pack(fill=tk.X, pady=(6, 12))

        # Big Scalable Digital Timer Display (Pure minimalist, zero extra box)
        self.time_display = ScalableTimerCanvas(container)
        self.time_display.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        self.time_display.set_label(self.core.get_display_time())

        # Control Buttons Row (Horizontal centered pill buttons)
        btn_box = tk.Frame(container, bg=COLOR_BG)
        btn_box.pack(fill=tk.X, pady=(16, 24))

        inner_btn = tk.Frame(btn_box, bg=COLOR_BG)
        inner_btn.pack(anchor=tk.CENTER)

        self.start_btn = AdwPillButton(
            inner_btn,
            text="Start",
            bg_color=COLOR_ACCENT_BLUE,
            hover_color=COLOR_ACCENT_HOVER,
            command=self.on_start_clicked,
            width=88,
            height=38,
        )
        self.start_btn.pack(side=tk.LEFT, padx=6)

        self.pause_btn = AdwPillButton(
            inner_btn,
            text="Pause",
            bg_color=COLOR_BTN_NEUTRAL,
            hover_color=COLOR_BTN_HOVER,
            command=self.on_pause_clicked,
            width=88,
            height=38,
        )
        self.pause_btn.set_enabled(False)
        self.pause_btn.pack(side=tk.LEFT, padx=6)

        self.reset_btn = AdwPillButton(
            inner_btn,
            text="Reset",
            bg_color=COLOR_ACCENT_RED,
            hover_color=COLOR_RED_HOVER,
            command=self.on_reset_clicked,
            width=88,
            height=38,
        )
        self.reset_btn.pack(side=tk.LEFT, padx=6)

        self.stop_btn = AdwPillButton(
            inner_btn,
            text="Stop",
            bg_color=COLOR_ACCENT_RED,
            hover_color=COLOR_RED_HOVER,
            command=self.on_stop_clicked,
            width=88,
            height=38,
        )
        # stop_btn packed only in Zen Mode

    def on_start_clicked(self):
        self.core.start()
        self.start_btn.set_enabled(False)
        self.pause_btn.set_enabled(True)
        if self.core.is_zen_mode:
            self.stop_btn.set_enabled(True)
        if not self.timer_job:
            self.timer_job = self.root.after(1000, self.on_timer_tick)

    def on_pause_clicked(self):
        self.core.pause()
        if self.timer_job:
            self.root.after_cancel(self.timer_job)
            self.timer_job = None
        self.start_btn.set_enabled(True)
        self.pause_btn.set_enabled(False)

    def on_reset_clicked(self):
        if self.timer_job:
            self.root.after_cancel(self.timer_job)
            self.timer_job = None
        self.core.reset()
        self.update_timer_display()
        self.start_btn.set_enabled(True)
        self.pause_btn.set_enabled(False)

    def on_apply_clicked(self):
        if self.timer_job:
            self.root.after_cancel(self.timer_job)
            self.timer_job = None
        val = self.preset_var.get()
        self.core.generate_schedule(val)
        self.update_timer_display()
        self.start_btn.set_enabled(True)
        self.pause_btn.set_enabled(False)

    def on_zen_mode_toggled(self, state):
        if self.timer_job:
            self.root.after_cancel(self.timer_job)
            self.timer_job = None

        if state:
            self.core.set_zen_mode(True)
            self.preset_frame.pack_forget()
            self.reset_btn.pack_forget()
            self.stop_btn.pack(side=tk.LEFT, padx=6)
            self.accumulate_container.pack(side=tk.LEFT, padx=(12, 0))
            self.start_btn.set_enabled(True)
            self.pause_btn.set_enabled(False)
            self.stop_btn.set_enabled(False)
        else:
            saved = self.core.set_zen_mode(False)
            if saved:
                duration_mins, _ = saved
                platform_utils.play_alert_sound()
                platform_utils.send_notification(
                    "Zen Mode Finished",
                    f"Great job! You studied for {duration_mins} minutes."
                )
            self.accumulate_container.pack_forget()
            self.stop_btn.pack_forget()
            self.reset_btn.pack(side=tk.LEFT, padx=6)
            self.preset_frame.pack(fill=tk.X, pady=(0, 18), before=self.status_label)
            self.start_btn.set_enabled(True)
            self.pause_btn.set_enabled(False)

        self.update_timer_display()

    def on_accumulate_toggled(self, state):
        self.core.is_accumulate_mode = state
        self.update_timer_display()

    def on_stop_clicked(self):
        if self.timer_job:
            self.root.after_cancel(self.timer_job)
            self.timer_job = None

        saved_mins = self.core.stop_zen()
        if saved_mins:
            platform_utils.play_alert_sound()
            platform_utils.send_notification(
                "Zen Mode Finished",
                f"Great job! You studied for {saved_mins} minutes."
            )
        self.update_timer_display()
        self.start_btn.set_enabled(True)
        self.pause_btn.set_enabled(False)
        self.stop_btn.set_enabled(False)

    def on_timer_tick(self):
        res = self.core.tick()
        self.update_timer_display()

        if res.get("event") in ["chunk_complete", "all_complete"]:
            platform_utils.play_alert_sound()
            if res.get("was_working"):
                platform_utils.send_notification(
                    "Pomodoro Finished",
                    f"Great job! You studied for {res.get('duration_mins', 0)} minutes."
                )
            else:
                platform_utils.send_notification("Break Finished", "Time to get back to work!")

        if self.core.is_running:
            self.timer_job = self.root.after(1000, self.on_timer_tick)
        else:
            self.timer_job = None
            self.start_btn.set_enabled(True)
            self.pause_btn.set_enabled(False)

    def update_timer_display(self):
        self.status_label.configure(text=self.core.status_text)
        self.time_display.set_label(self.core.get_display_time())

    # -------------------------------------------------------------
    # 2. STATS VIEW (AdwPreferencesGroup & ActionRow design)
    # -------------------------------------------------------------
    def build_stats_view(self):
        container = self.view_stats

        # Scrollable area
        canvas = tk.Canvas(container, bg=COLOR_BG, highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient=tk.VERTICAL, command=canvas.yview)
        self.stats_inner = tk.Frame(canvas, bg=COLOR_BG)

        self.stats_inner.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        c_win = canvas.create_window((0, 0), window=self.stats_inner, anchor="nw")
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(c_win, width=e.width))

        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(16, 0), pady=12)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=12)

        # Helper to create an Adwaita PreferencesGroup
        def create_group(title_text):
            box = tk.Frame(self.stats_inner, bg=COLOR_BG)
            box.pack(fill=tk.X, pady=(0, 18))
            # Uppercase muted title
            tk.Label(
                box,
                text=title_text.upper(),
                bg=COLOR_BG,
                fg=COLOR_TEXT_SECONDARY,
                font=("Segoe UI", 9, "bold"),
            ).pack(anchor="w", padx=4, pady=(0, 6))
            card = tk.Frame(
                box,
                bg=COLOR_CARD,
                highlightbackground=COLOR_CARD_BORDER,
                highlightthickness=1,
                padx=16,
                pady=14,
            )
            card.pack(fill=tk.X)
            return card

        # Group 1: Today's Progress
        card1 = create_group("Today's Progress")
        self.goal_label = tk.Label(card1, text="", bg=COLOR_CARD, fg=COLOR_TEXT_PRIMARY, font=("Segoe UI", 11, "bold"))
        self.goal_label.pack(anchor="w", pady=(0, 10))
        self.progress_bar = AdwProgressBar(card1, height=8)
        self.progress_bar.pack(fill=tk.X)

        # Group 2: Current Streak
        card2 = create_group("Current Streak")
        self.streak_label = tk.Label(card2, text="🔥 0 days", bg=COLOR_CARD, fg=COLOR_TEXT_PRIMARY, font=("Segoe UI", 14, "bold"))
        self.streak_label.pack(anchor="w")

        # Group 3: Yearly Statistics
        card3 = create_group("Yearly Statistics")
        self.year_label = tk.Label(card3, text="0 minutes studied this year", bg=COLOR_CARD, fg="#dedede", font=("Segoe UI", 10))
        self.year_label.pack(anchor="w")

        # Group 4: Today's Sessions (Boxed List)
        card4 = create_group("Today's Sessions")
        self.sessions_box = tk.Frame(card4, bg=COLOR_CARD)
        self.sessions_box.pack(fill=tk.X)

        # Group 5: Data Synchronization & Import
        card5 = create_group("Data Synchronization (Dual-Boot)")
        sync_desc = tk.Label(
            card5,
            text=f"Shared DB: {database.DB_PATH}\n(Tự động đồng bộ với phân vùng dùng chung)",
            bg=COLOR_CARD,
            fg=COLOR_TEXT_SECONDARY,
            font=("Segoe UI", 9),
            justify="left",
        )
        sync_desc.pack(anchor="w", pady=(0, 10))

        btn_row = tk.Frame(card5, bg=COLOR_CARD)
        btn_row.pack(anchor="w")

        AdwPillButton(
            btn_row,
            text="🔄 Sync Fedora Data",
            bg_color=COLOR_ACCENT_BLUE,
            hover_color=COLOR_ACCENT_HOVER,
            command=self.on_sync_clicked,
            width=150,
            height=32,
            font=("Segoe UI", 9, "bold"),
        ).pack(side=tk.LEFT, padx=(0, 8))

        AdwPillButton(
            btn_row,
            text="📂 Import .db File",
            bg_color=COLOR_BTN_NEUTRAL,
            hover_color=COLOR_BTN_HOVER,
            command=self.on_import_db_clicked,
            width=130,
            height=32,
            font=("Segoe UI", 9, "bold"),
        ).pack(side=tk.LEFT)

    def on_sync_clicked(self):
        import sync_database
        merged = sync_database.auto_detect_and_sync()
        self.refresh_stats()
        messagebox.showinfo(
            "Sync Complete",
            f"Đã kiểm tra đồng bộ!\nĐã hợp nhất {merged} phiên học từ các nguồn cũ vào database dùng chung.",
        )

    def on_import_db_clicked(self):
        file_path = filedialog.askopenfilename(
            title="Select SQLite Database to Import",
            filetypes=[("SQLite Database", "*.db *.sqlite *.sqlite3"), ("All Files", "*.*")],
        )
        if file_path:
            import sync_database
            merged = sync_database.sync_from_path(file_path)
            self.refresh_stats()
            messagebox.showinfo(
                "Import Successful",
                f"Đã nhập thành công {merged} phiên học từ file:\n{file_path}",
            )

    def refresh_stats(self):
        # Update Today
        today_total = database.get_today_total()
        fraction = min(today_total / self.core.daily_goal, 1.0)
        is_reached = today_total >= self.core.daily_goal
        self.progress_bar.set_fraction(fraction, is_goal_reached=is_reached)

        if is_reached:
            self.goal_label.configure(
                text=f"🎉 Goal reached! {today_total} / {self.core.daily_goal} min",
                fg=COLOR_ACCENT_GREEN,
            )
        else:
            self.goal_label.configure(
                text=f"Study Time: {today_total} / {self.core.daily_goal} min",
                fg=COLOR_TEXT_PRIMARY,
            )

        # Update Streak
        streak = database.get_current_streak(self.core.daily_goal)
        self.streak_label.configure(text=f"🔥 {streak} days")

        # Update Year
        year_total = database.get_year_total()
        self.year_label.configure(text=f"{year_total} minutes studied this year")

        # Efficiently update sessions list
        for w in self.sessions_box.winfo_children():
            w.destroy()

        sessions = database.get_today_sessions()
        if not sessions:
            tk.Label(
                self.sessions_box,
                text="No sessions yet today",
                bg=COLOR_CARD,
                fg=COLOR_TEXT_SECONDARY,
                font=("Segoe UI", 10, "italic"),
            ).pack(anchor="w", pady=4)
        else:
            for idx, (timestamp, duration) in enumerate(sessions):
                if idx > 0:
                    tk.Frame(self.sessions_box, bg=COLOR_CARD_BORDER, height=1).pack(fill=tk.X, pady=3)

                row = tk.Frame(self.sessions_box, bg=COLOR_CARD, pady=4)
                row.pack(fill=tk.X)

                time_only = timestamp.split()[1] if " " in timestamp else timestamp
                tk.Label(row, text="▶", bg=COLOR_CARD, fg=COLOR_ACCENT_BLUE, font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=(0, 8))
                tk.Label(row, text=time_only, bg=COLOR_CARD, fg=COLOR_TEXT_PRIMARY, font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT, padx=(0, 12))
                tk.Label(
                    row,
                    text=f"{duration} minutes",
                    bg=COLOR_CARD,
                    fg=COLOR_ACCENT_GREEN if duration >= 25 else COLOR_TEXT_SECONDARY,
                    font=("Segoe UI", 9, "bold"),
                ).pack(side=tk.RIGHT)

    # -------------------------------------------------------------
    # 3. CALENDAR VIEW (Optimized with Pre-allocated 42 Cells)
    # -------------------------------------------------------------
    def build_calendar_view(self):
        container = self.view_calendar

        # Navigation Header
        nav_box = tk.Frame(container, bg=COLOR_BG, pady=16)
        nav_box.pack(fill=tk.X)

        inner_nav = tk.Frame(nav_box, bg=COLOR_BG)
        inner_nav.pack(anchor=tk.CENTER)

        self.prev_btn = AdwPillButton(
            inner_nav,
            text="◀",
            bg_color=COLOR_BTN_NEUTRAL,
            hover_color=COLOR_BTN_HOVER,
            command=self.on_prev_month,
            width=38,
            height=32,
            font=("Segoe UI", 10, "bold"),
        )
        self.prev_btn.pack(side=tk.LEFT, padx=12)

        self.month_year_label = tk.Label(
            inner_nav,
            text="",
            bg=COLOR_BG,
            fg=COLOR_TEXT_PRIMARY,
            font=("Segoe UI", 14, "bold"),
            width=18,
            anchor="center",
        )
        self.month_year_label.pack(side=tk.LEFT, padx=12)

        self.next_btn = AdwPillButton(
            inner_nav,
            text="▶",
            bg_color=COLOR_BTN_NEUTRAL,
            hover_color=COLOR_BTN_HOVER,
            command=self.on_next_month,
            width=38,
            height=32,
            font=("Segoe UI", 10, "bold"),
        )
        self.next_btn.pack(side=tk.LEFT, padx=12)

        # Calendar Grid Frame
        self.grid_frame = tk.Frame(container, bg=COLOR_BG, padx=14)
        self.grid_frame.pack(fill=tk.BOTH, expand=True)

        for i in range(7):
            self.grid_frame.columnconfigure(i, weight=1, uniform="cal_col")
        for i in range(7): # 0 = header, 1..6 = weeks
            self.grid_frame.rowconfigure(i, weight=1, uniform="cal_row")

        # Weekday headers (row 0)
        days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        for col_idx, d in enumerate(days):
            lbl = tk.Label(
                self.grid_frame,
                text=d,
                bg=COLOR_BG,
                fg=COLOR_TEXT_SECONDARY,
                font=("Segoe UI", 9, "bold"),
            )
            lbl.grid(row=0, column=col_idx, pady=(0, 8), sticky="nsew")

        # Pre-allocate 42 cells (6 rows x 7 cols) for maximum performance (< 1ms updates)
        self.cal_cells = []
        for r in range(6):
            row_cells = []
            for c in range(7):
                cell = tk.Frame(
                    self.grid_frame,
                    bg=COLOR_CARD,
                    highlightbackground=COLOR_CARD_BORDER,
                    highlightthickness=1,
                    padx=4,
                    pady=4,
                )
                cell.grid(row=r + 1, column=c, padx=3, pady=3, sticky="nsew")

                day_lbl = tk.Label(cell, text="", bg=COLOR_CARD, fg=COLOR_TEXT_SECONDARY, font=("Segoe UI", 8))
                day_lbl.pack(anchor="nw")

                val_lbl = tk.Label(cell, text="", bg=COLOR_CARD, fg=COLOR_ACCENT_BLUE, font=("Segoe UI", 10, "bold"))
                val_lbl.pack(expand=True, anchor="center")

                row_cells.append({"frame": cell, "day": day_lbl, "val": val_lbl})
            self.cal_cells.append(row_cells)

    def on_prev_month(self):
        if self.cal_month == 1:
            self.cal_month = 12
            self.cal_year -= 1
        else:
            self.cal_month -= 1
        self.render_calendar()

    def on_next_month(self):
        if self.cal_month == 12:
            self.cal_month = 1
            self.cal_year += 1
        else:
            self.cal_month += 1
        self.render_calendar()

    def render_calendar(self):
        month_name = calendar.month_name[self.cal_month]
        self.month_year_label.configure(text=f"{month_name} {self.cal_year}")

        month_data = database.get_daily_totals_for_month(self.cal_year, self.cal_month)
        cal = calendar.monthcalendar(self.cal_year, self.cal_month)

        # High-performance in-place update (takes < 0.5ms)
        for r in range(6):
            week = cal[r] if r < len(cal) else [0] * 7
            for c in range(7):
                day = week[c]
                widgets = self.cal_cells[r][c]
                cell = widgets["frame"]
                day_lbl = widgets["day"]
                val_lbl = widgets["val"]

                if day == 0:
                    cell.configure(bg=COLOR_BG, highlightthickness=0)
                    day_lbl.configure(text="", bg=COLOR_BG)
                    val_lbl.configure(text="", bg=COLOR_BG)
                else:
                    total_mins = month_data.get(day, 0)
                    cell.configure(bg=COLOR_CARD, highlightthickness=1)
                    day_lbl.configure(text=str(day), bg=COLOR_CARD)

                    if total_mins > 0:
                        val_col = COLOR_ACCENT_GREEN if total_mins >= self.core.daily_goal else COLOR_ACCENT_BLUE
                        val_lbl.configure(text=f"{total_mins}m", bg=COLOR_CARD, fg=val_col)
                    else:
                        val_lbl.configure(text="", bg=COLOR_CARD)

    def destroy(self):
        if self.timer_job:
            self.root.after_cancel(self.timer_job)
            self.timer_job = None
        self.root.destroy()

    def run(self):
        self.root.mainloop()

def run_app():
    app = PomodoroWinApp()
    app.run()

if __name__ == "__main__":
    run_app()
