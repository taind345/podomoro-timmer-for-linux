import unittest
import os
import tempfile
import sqlite3
from datetime import datetime, timedelta

import database
import core_timer
import platform_utils

# Try importing GTK / Adwaita
try:
    import gi
    gi.require_version('Gtk', '4.0')
    gi.require_version('Adw', '1')
    gi.require_version('PangoCairo', '1.0')
    from gi.repository import Gtk, Adw, GLib
    import ui_gtk
    HAS_GI = True
except Exception:
    HAS_GI = False

try:
    import ui_win
    HAS_WIN_UI = True
except Exception:
    HAS_WIN_UI = False

class TestDatabase(unittest.TestCase):
    def setUp(self):
        self.original_db_path = database.DB_PATH
        self.temp_dir = tempfile.gettempdir()
        self.test_db_path = os.path.join(self.temp_dir, "test_podomoro_stats.db")
        database.DB_PATH = self.test_db_path
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)
        database.init_db()

    def tearDown(self):
        database.DB_PATH = self.original_db_path
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)

    def test_init_db(self):
        self.assertTrue(os.path.exists(self.test_db_path))

    def test_add_session_and_get_today(self):
        database.add_session(25)
        database.add_session(30)
        today_total = database.get_today_total()
        self.assertEqual(today_total, 55)
        sessions = database.get_today_sessions()
        self.assertEqual(len(sessions), 2)

    def test_start_time_cross_midnight(self):
        yesterday = datetime.now() - timedelta(days=1)
        yesterday_start = yesterday.replace(hour=23, minute=30, second=0)
        database.add_session(150, start_time=yesterday_start)
        
        conn = database.get_connection(self.test_db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT timestamp, duration FROM sessions")
        row = cursor.fetchone()
        conn.close()
        
        self.assertEqual(row[0], yesterday_start.strftime("%Y-%m-%d %H:%M:%S"))
        self.assertEqual(row[1], 150)
        self.assertEqual(database.get_today_total(), 0)

    def test_monthly_totals(self):
        now = datetime.now()
        day1 = now.replace(day=1, hour=10, minute=0, second=0)
        day2 = now.replace(day=2, hour=14, minute=0, second=0)
        
        database.add_session(60, start_time=day1)
        database.add_session(120, start_time=day2)
        
        month_data = database.get_daily_totals_for_month(now.year, now.month)
        self.assertEqual(month_data.get(1), 60)
        self.assertEqual(month_data.get(2), 120)

    def test_streak_calculation(self):
        now = datetime.now()
        database.add_session(180, start_time=now)
        yesterday = now - timedelta(days=1)
        database.add_session(200, start_time=yesterday)
        two_days_ago = now - timedelta(days=2)
        database.add_session(190, start_time=two_days_ago)
        three_days_ago = now - timedelta(days=3)
        database.add_session(50, start_time=three_days_ago)

        streak = database.get_current_streak(180)
        self.assertEqual(streak, 3)

    def test_legacy_migration(self):
        # Create a mock legacy database
        legacy_mock = os.path.join(self.temp_dir, "legacy_mock.db")
        new_target = os.path.join(self.temp_dir, "migrated_target.db")
        if os.path.exists(legacy_mock):
            os.remove(legacy_mock)
        if os.path.exists(new_target):
            os.remove(new_target)

        conn = sqlite3.connect(legacy_mock)
        conn.execute("CREATE TABLE sessions (id INTEGER PRIMARY KEY, timestamp TEXT, duration INTEGER)")
        conn.execute("INSERT INTO sessions (timestamp, duration) VALUES ('2026-01-01 10:00:00', 45)")
        conn.commit()
        conn.close()

        # Run migration
        res = database.migrate_from_legacy_db(target_db_path=new_target, legacy_path=legacy_mock)
        self.assertTrue(res)
        self.assertTrue(os.path.exists(new_target))

        # Verify data migrated
        conn2 = sqlite3.connect(new_target)
        rows = conn2.execute("SELECT timestamp, duration FROM sessions").fetchall()
        conn2.close()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][1], 45)

        # Clean up
        if os.path.exists(legacy_mock):
            os.remove(legacy_mock)
        if os.path.exists(new_target):
            os.remove(new_target)

class TestCoreTimer(unittest.TestCase):
    def test_format_time(self):
        self.assertEqual(core_timer.format_time(0), "00:00")
        self.assertEqual(core_timer.format_time(59), "00:59")
        self.assertEqual(core_timer.format_time(1500), "25:00")
        self.assertEqual(core_timer.format_time(3600), "01:00:00")
        self.assertEqual(core_timer.format_time(4505), "01:15:05")

    def test_generate_schedule_120_mins(self):
        core = core_timer.PomodoroCore(default_work_mins=120)
        self.assertEqual(core.total_blocks, 4)
        self.assertEqual(core.current_block, 1)
        self.assertEqual(core.time_left, 30 * 60)
        self.assertTrue(core.is_working)
        self.assertEqual(len(core.session_queue), 6)

    def test_generate_schedule_25_mins(self):
        core = core_timer.PomodoroCore(default_work_mins=25)
        self.assertEqual(core.total_blocks, 1)
        self.assertEqual(core.current_block, 1)
        self.assertEqual(core.time_left, 25 * 60)
        self.assertTrue(core.is_working)
        self.assertEqual(len(core.session_queue), 0)

    def test_zen_mode(self):
        core = core_timer.PomodoroCore()
        core.set_zen_mode(True)
        self.assertTrue(core.is_zen_mode)
        core.start()
        self.assertTrue(core.is_running)
        core.tick()
        self.assertEqual(core.zen_time_elapsed, 1)
        core.pause()
        self.assertFalse(core.is_running)

@unittest.skipIf(not HAS_WIN_UI, "Tkinter / ui_win is not available on this platform")
class TestWinApp(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.gettempdir()
        cls.test_db_path = os.path.join(cls.temp_dir, "test_win_app.db")
        cls.orig_db = database.DB_PATH
        database.DB_PATH = cls.test_db_path
        if os.path.exists(cls.test_db_path):
            os.remove(cls.test_db_path)
        database.init_db()

    @classmethod
    def tearDownClass(cls):
        database.DB_PATH = cls.orig_db
        if os.path.exists(cls.test_db_path):
            os.remove(cls.test_db_path)

    def setUp(self):
        self.app = ui_win.PomodoroWinApp()

    def tearDown(self):
        self.app.destroy()

    def test_tab_switching(self):
        self.app.switch_tab("stats")
        self.app.switch_tab("calendar")
        self.app.switch_tab("timer")

    def test_schedule_apply(self):
        self.app.preset_var.set(60)
        self.app.on_apply_clicked()
        self.assertEqual(self.app.core.total_work_mins, 60)

    def test_stats_and_calendar_rendering(self):
        self.app.refresh_stats()
        self.app.render_calendar()
        self.assertIsNotNone(self.app.month_year_label.cget("text"))

@unittest.skipIf(not HAS_GI, "GTK4 / Libadwaita is not installed on this platform")
class TestGTKAppLogic(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.gettempdir()
        cls.test_db_path = os.path.join(cls.temp_dir, "test_app_podomoro.db")
        cls.original_db_path = database.DB_PATH
        database.DB_PATH = cls.test_db_path
        if os.path.exists(cls.test_db_path):
            os.remove(cls.test_db_path)
        database.init_db()

    @classmethod
    def tearDownClass(cls):
        database.DB_PATH = cls.original_db_path
        if os.path.exists(cls.test_db_path):
            os.remove(cls.test_db_path)

    def setUp(self):
        self.gtk_app = Adw.Application(application_id='com.example.TestPomodoro')
        self.win = ui_gtk.PomodoroWindow(application=self.gtk_app)

    def test_format_time(self):
        self.assertEqual(self.win.format_time(0), "00:00")
        self.assertEqual(self.win.format_time(59), "00:59")
        self.assertEqual(self.win.format_time(1500), "25:00")
        self.assertEqual(self.win.format_time(3600), "01:00:00")
        self.assertEqual(self.win.format_time(4505), "01:15:05")

    def test_generate_schedule_120_mins(self):
        self.win.generate_schedule(120)
        self.assertEqual(self.win.total_blocks, 4)
        self.assertEqual(self.win.current_block, 1)
        self.assertEqual(self.win.time_left, 30 * 60)
        self.assertTrue(self.win.is_working)
        self.assertEqual(len(self.win.session_queue), 6)

    def test_generate_schedule_25_mins(self):
        self.win.generate_schedule(25)
        self.assertEqual(self.win.total_blocks, 1)
        self.assertEqual(self.win.current_block, 1)
        self.assertEqual(self.win.time_left, 25 * 60)
        self.assertTrue(self.win.is_working)
        self.assertEqual(len(self.win.session_queue), 0)

    def test_start_pause_reset(self):
        self.win.generate_schedule(25)
        self.win.on_start_clicked(None)
        self.assertIsNotNone(self.win.timer_id)
        self.assertIsNotNone(self.win.session_start_time)
        
        self.win.on_pause_clicked(None)
        self.assertIsNone(self.win.timer_id)
        
        self.win.on_reset_clicked(None)
        self.assertIsNone(self.win.timer_id)

    def test_zen_mode_lifecycle(self):
        self.win.on_zen_mode_toggled(None, True)
        self.assertTrue(self.win.is_zen_mode)
        self.assertEqual(self.win.zen_time_elapsed, 0)
        
        self.win.on_start_clicked(None)
        self.assertIsNotNone(self.win.timer_id)
        self.assertIsNotNone(self.win.zen_start_time)
        
        self.win.zen_time_elapsed = 120
        
        self.win.on_stop_clicked(None)
        self.assertIsNone(self.win.timer_id)
        self.assertEqual(self.win.zen_time_elapsed, 0)
        self.assertIsNone(self.win.zen_start_time)
        self.assertEqual(database.get_today_total(), 2)

    def test_calendar_rendering(self):
        self.win.render_calendar()
        self.assertIsNotNone(self.win.cal_grid)
        
        cur_month = self.win.current_month
        cur_year = self.win.current_year
        
        self.win.on_prev_month(None)
        expected_month = 12 if cur_month == 1 else cur_month - 1
        expected_year = cur_year - 1 if cur_month == 1 else cur_year
        self.assertEqual(self.win.current_month, expected_month)
        self.assertEqual(self.win.current_year, expected_year)
        
        self.win.on_next_month(None)
        self.assertEqual(self.win.current_month, cur_month)
        self.assertEqual(self.win.current_year, cur_year)

    def test_stats_refresh(self):
        self.win.refresh_stats()
        self.assertIn("min", self.win.goal_label.get_text())
        self.assertIn("days", self.win.streak_label.get_text())

if __name__ == '__main__':
    unittest.main()
