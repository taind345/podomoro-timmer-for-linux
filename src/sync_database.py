import os
import sys
import sqlite3
import shutil
import database

def sync_from_path(source_path, target_path=None):
    target = target_path or database.DB_PATH
    if not os.path.exists(source_path):
        print(f"[Sync] Source database does not exist: {source_path}")
        return 0

    if os.path.abspath(source_path) == os.path.abspath(target):
        print(f"[Sync] Source and target are the same file: {target}")
        return 0

    print(f"[Sync] Reading records from: {source_path}")
    src_conn = sqlite3.connect(source_path)
    src_cur = src_conn.cursor()
    try:
        src_cur.execute("SELECT timestamp, duration FROM sessions")
        rows = src_cur.fetchall()
    except Exception as e:
        print(f"[Sync] Error reading sessions from {source_path}: {e}")
        src_conn.close()
        return 0
    src_conn.close()

    if not rows:
        print(f"[Sync] No records found in {source_path}.")
        return 0

    print(f"[Sync] Found {len(rows)} records in source. Merging into {target}...")
    database.init_db(target)
    tgt_conn = database.get_connection(target)
    tgt_cur = tgt_conn.cursor()

    merged_count = 0
    for ts, dur in rows:
        tgt_cur.execute(
            "SELECT id FROM sessions WHERE timestamp = ? AND duration = ?",
            (ts, dur),
        )
        if not tgt_cur.fetchone():
            tgt_cur.execute(
                "INSERT INTO sessions (timestamp, duration) VALUES (?, ?)",
                (ts, dur),
            )
            merged_count += 1

    tgt_conn.commit()
    tgt_conn.close()
    print(f"[Sync] Successfully merged {merged_count} new records into {target} (Total in source: {len(rows)}).")
    return merged_count

def auto_detect_and_sync():
    """Detect and sync from standard legacy locations on Linux or Windows."""
    candidates = [
        os.path.expanduser("~/.local/share/podomoro_stats.db"),
        os.path.expanduser("~/.var/app/com.example.Pomodoro/data/podomoro_stats.db"),
        os.path.expanduser("~/podomoro_stats.db"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "podomoro_stats.db"),
    ]

    total_merged = 0
    for cand in candidates:
        if os.path.exists(cand) and os.path.abspath(cand) != os.path.abspath(database.DB_PATH):
            print(f"[Sync] Found potential legacy database: {cand}")
            merged = sync_from_path(cand)
            total_merged += merged

    # Print current stats in shared database
    print("\n--- Current Shared Database Status ---")
    print(f"Database Path: {database.DB_PATH}")
    print(f"Today Total: {database.get_today_total()} minutes")
    print(f"Current Streak: {database.get_current_streak(180)} days")
    print(f"Year Total: {database.get_year_total()} minutes")
    sessions = database.get_today_sessions()
    print(f"Today Sessions Count: {len(sessions)}")
    return total_merged

if __name__ == "__main__":
    if len(sys.argv) > 1:
        custom_src = sys.argv[1]
        sync_from_path(custom_src)
    else:
        auto_detect_and_sync()
