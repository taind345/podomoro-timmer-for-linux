import sqlite3
from datetime import datetime, timedelta
import os

DB_PATH = os.path.expanduser('~/.local/share/podomoro_stats.db')

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            duration INTEGER NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

def add_session(duration_minutes, start_time=None):
    conn = sqlite3.connect(DB_PATH)
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

def get_today_sessions():
    conn = sqlite3.connect(DB_PATH)
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

def get_today_total():
    conn = sqlite3.connect(DB_PATH)
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

def get_year_total():
    conn = sqlite3.connect(DB_PATH)
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

def get_daily_totals_for_month(year, month):
    conn = sqlite3.connect(DB_PATH)
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

def get_current_streak(daily_goal):
    conn = sqlite3.connect(DB_PATH)
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
