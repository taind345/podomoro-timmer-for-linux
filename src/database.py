import sqlite3
from datetime import datetime, timedelta
import os
import shutil

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
DEFAULT_DATA_DIR = os.path.join(PROJECT_ROOT, "data")
DEFAULT_DB_PATH = os.path.join(DEFAULT_DATA_DIR, "podomoro_stats.db")
LEGACY_LINUX_DB_PATH = os.path.expanduser("~/.local/share/podomoro_stats.db")

# Allow environment override, otherwise default to shared project data dir
DB_PATH = os.environ.get("PODOMORO_DB_PATH", DEFAULT_DB_PATH)

def get_connection(db_path=None):
    target = db_path or DB_PATH
    conn = sqlite3.connect(target, timeout=10.0)
    conn.execute("PRAGMA busy_timeout = 5000")
    return conn

def migrate_from_legacy_db(target_db_path=None, legacy_path=None):
    """Migrate sessions from legacy Linux DB path if shared DB is new/empty."""
    target = target_db_path or DB_PATH
    legacy = legacy_path or LEGACY_LINUX_DB_PATH

    # If legacy DB exists, is a different file, and target DB does not exist or has no records
    if os.path.exists(legacy) and os.path.abspath(legacy) != os.path.abspath(target):
        try:
            os.makedirs(os.path.dirname(os.path.abspath(target)), exist_ok=True)
            
            # Check if target already has records
            target_exists = os.path.exists(target)
            if not target_exists:
                # Direct file copy is fastest and cleanest if target doesn't exist yet
                shutil.copy2(legacy, target)
                print(f"[Database] Migrated legacy database from {legacy} to {target}")
                return True
            else:
                # Merge records from legacy if target exists
                leg_conn = sqlite3.connect(legacy, timeout=5.0)
                leg_cur = leg_conn.cursor()
                leg_cur.execute("SELECT timestamp, duration FROM sessions")
                legacy_rows = leg_cur.fetchall()
                leg_conn.close()

                if legacy_rows:
                    tgt_conn = get_connection(target)
                    tgt_cur = tgt_conn.cursor()
                    # Insert ignoring duplicates (same timestamp and duration)
                    for ts, dur in legacy_rows:
                        tgt_cur.execute(
                            "SELECT id FROM sessions WHERE timestamp = ? AND duration = ?",
                            (ts, dur),
                        )
                        if not tgt_cur.fetchone():
                            tgt_cur.execute(
                                "INSERT INTO sessions (timestamp, duration) VALUES (?, ?)",
                                (ts, dur),
                            )
                    tgt_conn.commit()
                    tgt_conn.close()
                    print(f"[Database] Merged {len(legacy_rows)} records from {legacy} into {target}")
                    return True
        except Exception as e:
            print(f"[Database] Notice: Legacy DB migration check skipped: {e}")
    return False

def init_db(db_path=None, auto_migrate=True):
    target = db_path or DB_PATH
    target_dir = os.path.dirname(os.path.abspath(target))
    if target_dir:
        os.makedirs(target_dir, exist_ok=True)

    conn = get_connection(target)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            duration INTEGER NOT NULL
        )
    ''')
    try:
        cursor.execute("PRAGMA journal_mode = WAL")
        cursor.execute("PRAGMA synchronous = NORMAL")
        cursor.execute("PRAGMA cache_size = -2000")
        cursor.execute("PRAGMA temp_store = MEMORY")
    except Exception:
        pass
    conn.commit()
    conn.close()

    # Attempt migration from legacy DB if enabled and not a temporary test DB
    if auto_migrate and not target.startswith("/tmp") and "test" not in os.path.basename(target).lower():
        migrate_from_legacy_db(target)

def add_session(duration_minutes, start_time=None, db_path=None):
    conn = get_connection(db_path)
    cursor = conn.cursor()
    if start_time is None:
        start_time = datetime.now()
    if isinstance(start_time, datetime):
        time_str = start_time.strftime("%Y-%m-%d %H:%M:%S")
    else:
        time_str = str(start_time)
    cursor.execute('INSERT INTO sessions (timestamp, duration) VALUES (?, ?)', (time_str, duration_minutes))
    conn.commit()
    conn.close()

def get_today_sessions(db_path=None):
    conn = get_connection(db_path)
    cursor = conn.cursor()
    today_str = datetime.now().strftime("%Y-%m-%d")
    cursor.execute('''
        SELECT timestamp, duration 
        FROM sessions 
        WHERE timestamp LIKE ?
        ORDER BY timestamp DESC
    ''', (today_str + '%',))
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_today_total(db_path=None):
    conn = get_connection(db_path)
    cursor = conn.cursor()
    today_str = datetime.now().strftime("%Y-%m-%d")
    cursor.execute('''
        SELECT SUM(duration) 
        FROM sessions 
        WHERE timestamp LIKE ?
    ''', (today_str + '%',))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row[0] is not None else 0

def get_year_total(db_path=None):
    conn = get_connection(db_path)
    cursor = conn.cursor()
    year_str = datetime.now().strftime("%Y")
    cursor.execute('''
        SELECT SUM(duration) 
        FROM sessions 
        WHERE timestamp LIKE ?
    ''', (year_str + '%',))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row[0] is not None else 0

def get_daily_totals_for_month(year, month, db_path=None):
    conn = get_connection(db_path)
    cursor = conn.cursor()
    month_str = f"{year:04d}-{month:02d}"
    cursor.execute('''
        SELECT date(timestamp) as d, SUM(duration)
        FROM sessions
        WHERE timestamp LIKE ?
        GROUP BY d
    ''', (month_str + '%',))
    rows = cursor.fetchall()
    conn.close()
    
    # Return a dictionary {day_integer: total_minutes}
    result = {}
    for r in rows:
        # Date string is YYYY-MM-DD
        day = int(r[0].split('-')[2])
        result[day] = r[1]
    return result

def get_current_streak(daily_goal, db_path=None):
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT date(timestamp) as d, SUM(duration)
        FROM sessions
        GROUP BY d
        ORDER BY d DESC
    ''')
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return 0

    daily_totals = {r[0]: r[1] for r in rows}
    
    streak = 0
    current_date = datetime.now()
    today_str = current_date.strftime("%Y-%m-%d")
    
    if daily_totals.get(today_str, 0) >= daily_goal:
        streak += 1
        check_date = current_date - timedelta(days=1)
    else:
        check_date = current_date - timedelta(days=1)
        
    while True:
        date_str = check_date.strftime("%Y-%m-%d")
        if daily_totals.get(date_str, 0) >= daily_goal:
            streak += 1
            check_date -= timedelta(days=1)
        else:
            break
            
    return streak
