import sqlite3
import json
import os
from typing import Dict, Any, List, Optional

# Local SQLite Database Path inside data/ folder
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(BASE_DIR, "data")
DEFAULT_DB_PATH = os.path.join(DATA_DIR, "chess_scheduler.db")

def get_db_path() -> str:
    env_path = os.environ.get("CHESS_DB_PATH")
    if env_path:
        return os.path.abspath(env_path)
    return DEFAULT_DB_PATH

def log_db_status(context: str, db_path: Optional[str] = None):
    target_path = db_path or get_db_path()
    abs_path = os.path.abspath(target_path)
    exists = os.path.exists(abs_path)
    size_bytes = os.path.getsize(abs_path) if exists else 0
    student_count = 0
    coach_count = 0

    if exists:
        try:
            conn = get_connection(abs_path)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM students")
            student_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM coaches")
            coach_count = cursor.fetchone()[0]
            conn.close()
        except Exception as e:
            print(f"[{context}] Error reading DB counts: {e}", flush=True)

    print(f"==================================================", flush=True)
    print(f"[{context}] DATABASE STATUS LOG", flush=True)
    print(f"  - DB Absolute Path: {abs_path}", flush=True)
    print(f"  - DB Exists       : {exists}", flush=True)
    print(f"  - DB File Size    : {size_bytes} bytes", flush=True)
    print(f"  - Student Count   : {student_count}", flush=True)
    print(f"  - Coach Count     : {coach_count}", flush=True)
    print(f"==================================================", flush=True)

def get_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    target_path = db_path or get_db_path()
    os.makedirs(os.path.dirname(target_path), exist_ok=True)
    conn = sqlite3.connect(target_path)
    conn.row_factory = sqlite3.Row
    return conn

def init_db(db_path: Optional[str] = None):
    """
    Automatically initializes local SQLite tables for schedules, master students, master coaches, and metadata.
    """
    target_path = db_path or get_db_path()
    conn = get_connection(target_path)
    cursor = conn.cursor()
    
    # 1. Schedules table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS schedules (
            schedule_id TEXT PRIMARY KEY,
            status TEXT NOT NULL,
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            total_students INTEGER NOT NULL,
            scheduled_students INTEGER NOT NULL,
            unscheduled_students INTEGER NOT NULL,
            accountability_passed INTEGER NOT NULL,
            data_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    
    # 2. Master Students table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (
            student_id TEXT PRIMARY KEY,
            student_name TEXT NOT NULL,
            student_level TEXT NOT NULL,
            batch_type TEXT NOT NULL,
            region_timezone TEXT,
            required_classes INTEGER NOT NULL,
            data_json TEXT NOT NULL
        )
    """)

    # 3. Master Coaches table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS coaches (
            coach_name TEXT PRIMARY KEY,
            levels_handled_json TEXT NOT NULL,
            monthly_capacity_min INTEGER NOT NULL,
            monthly_capacity_max INTEGER NOT NULL,
            data_json TEXT NOT NULL
        )
    """)

    # 4. Active metadata table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS active_metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)
    
    conn.commit()
    conn.close()

def save_master_data_db(
    students: List[Dict[str, Any]], 
    coaches: List[Dict[str, Any]], 
    errors: List[Dict[str, Any]] = None,
    filename: str = "",
    upload_timestamp: str = "",
    db_path: Optional[str] = None
):
    """
    Persists uploaded master student and coach data into SQLite.
    Replaces existing master records cleanly in a transaction.
    """
    target_path = db_path or get_db_path()
    init_db(target_path)
    conn = get_connection(target_path)
    cursor = conn.cursor()

    cursor.execute("DELETE FROM students")
    cursor.execute("DELETE FROM coaches")
    # Clear stale schedule runs so old snapshots cannot overwrite new uploads
    cursor.execute("DELETE FROM schedules")
    cursor.execute("DELETE FROM active_metadata WHERE key = 'latest_schedule_id'")

    for s in students:
        cursor.execute("""
            INSERT INTO students (student_id, student_name, student_level, batch_type, region_timezone, required_classes, data_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            s["student_id"],
            s["student_name"],
            s["student_level"],
            s["batch_type"],
            s.get("region_timezone", "IST"),
            s.get("required_classes", 8),
            json.dumps(s)
        ))

    for c in coaches:
        cursor.execute("""
            INSERT INTO coaches (coach_name, levels_handled_json, monthly_capacity_min, monthly_capacity_max, data_json)
            VALUES (?, ?, ?, ?, ?)
        """, (
            c["coach_name"],
            json.dumps(c.get("levels_handled", [])),
            c.get("monthly_capacity_min", 0),
            c.get("monthly_capacity_max", 100),
            json.dumps(c)
        ))

    cursor.execute("INSERT OR REPLACE INTO active_metadata (key, value) VALUES ('parsing_errors', ?)", (json.dumps(errors or []),))
    if filename:
        cursor.execute("INSERT OR REPLACE INTO active_metadata (key, value) VALUES ('last_filename', ?)", (filename,))
    if upload_timestamp:
        cursor.execute("INSERT OR REPLACE INTO active_metadata (key, value) VALUES ('last_upload_timestamp', ?)", (upload_timestamp,))

    conn.commit()
    conn.close()

def save_single_student_db(s: Dict[str, Any], db_path: Optional[str] = None):
    target_path = db_path or get_db_path()
    init_db(target_path)
    conn = get_connection(target_path)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO students (student_id, student_name, student_level, batch_type, region_timezone, required_classes, data_json)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        s["student_id"],
        s["student_name"],
        s["student_level"],
        s["batch_type"],
        s.get("region_timezone", "IST"),
        s.get("required_classes", 8),
        json.dumps(s)
    ))
    conn.commit()
    conn.close()

def delete_single_student_db(student_id: str, db_path: Optional[str] = None):
    target_path = db_path or get_db_path()
    init_db(target_path)
    conn = get_connection(target_path)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM students WHERE student_id = ?", (student_id,))
    conn.commit()
    conn.close()

def save_single_coach_db(c: Dict[str, Any], db_path: Optional[str] = None):
    target_path = db_path or get_db_path()
    init_db(target_path)
    conn = get_connection(target_path)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO coaches (coach_name, levels_handled_json, monthly_capacity_min, monthly_capacity_max, data_json)
        VALUES (?, ?, ?, ?, ?)
    """, (
        c["coach_name"],
        json.dumps(c.get("levels_handled", [])),
        c.get("monthly_capacity_min", 0),
        c.get("monthly_capacity_max", 100),
        json.dumps(c)
    ))
    conn.commit()
    conn.close()

def delete_single_coach_db(coach_name: str, db_path: Optional[str] = None):
    target_path = db_path or get_db_path()
    init_db(target_path)
    conn = get_connection(target_path)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM coaches WHERE coach_name = ?", (coach_name,))
    conn.commit()
    conn.close()

def load_master_data_db(db_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Loads persisted master student and coach records from SQLite.
    """
    target_path = db_path or get_db_path()
    init_db(target_path)
    conn = get_connection(target_path)
    cursor = conn.cursor()

    cursor.execute("SELECT data_json FROM students")
    student_rows = cursor.fetchall()
    students = [json.loads(row["data_json"]) for row in student_rows]

    cursor.execute("SELECT data_json FROM coaches")
    coach_rows = cursor.fetchall()
    coaches = [json.loads(row["data_json"]) for row in coach_rows]

    cursor.execute("SELECT value FROM active_metadata WHERE key = 'parsing_errors'")
    err_row = cursor.fetchone()
    parsing_errors = json.loads(err_row["value"]) if err_row else []

    cursor.execute("SELECT value FROM active_metadata WHERE key = 'last_filename'")
    fn_row = cursor.fetchone()
    last_filename = fn_row["value"] if fn_row else ""

    cursor.execute("SELECT value FROM active_metadata WHERE key = 'last_upload_timestamp'")
    ts_row = cursor.fetchone()
    last_upload_timestamp = ts_row["value"] if ts_row else ""

    conn.close()
    return {
        "students": students,
        "coaches": coaches,
        "parsing_errors": parsing_errors,
        "last_filename": last_filename,
        "last_upload_timestamp": last_upload_timestamp
    }

def has_master_data_db(db_path: Optional[str] = None) -> bool:
    """
    Checks if SQLite database contains valid master student and coach records.
    """
    target_path = db_path or get_db_path()
    init_db(target_path)
    conn = get_connection(target_path)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM students")
    s_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM coaches")
    c_count = cursor.fetchone()[0]
    conn.close()
    return s_count > 0 and c_count > 0

def save_schedule_db(schedule_dict: Dict[str, Any], db_path: Optional[str] = None):
    """
    Saves generated schedule and output views in SQLite schedules table.
    Also updates latest_schedule_id pointer in active_metadata.
    """
    target_path = db_path or get_db_path()
    init_db(target_path)
    conn = get_connection(target_path)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO schedules 
        (schedule_id, status, start_date, end_date, total_students, scheduled_students, unscheduled_students, accountability_passed, data_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        schedule_dict["schedule_id"],
        schedule_dict["status"],
        schedule_dict["start_date"],
        schedule_dict["end_date"],
        schedule_dict["total_students_considered"],
        schedule_dict["successfully_scheduled_students"],
        schedule_dict["unscheduled_students_count"],
        1 if schedule_dict["accountability_passed"] else 0,
        json.dumps(schedule_dict),
        schedule_dict["created_at"]
    ))
    cursor.execute("INSERT OR REPLACE INTO active_metadata (key, value) VALUES ('latest_schedule_id', ?)", (schedule_dict["schedule_id"],))
    conn.commit()
    conn.close()

def get_schedule_db(schedule_id: str, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Retrieves saved schedule from SQLite schedules table.
    """
    target_path = db_path or get_db_path()
    init_db(target_path)
    conn = get_connection(target_path)
    cursor = conn.cursor()
    cursor.execute("SELECT data_json FROM schedules WHERE schedule_id = ?", (schedule_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return json.loads(row["data_json"])
    return None

def get_latest_schedule_db(db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Retrieves the most recent active schedule from SQLite for zero-data-loss application reloads.
    """
    target_path = db_path or get_db_path()
    init_db(target_path)
    conn = get_connection(target_path)
    cursor = conn.cursor()

    cursor.execute("SELECT value FROM active_metadata WHERE key = 'latest_schedule_id'")
    row = cursor.fetchone()
    if row:
        sched_id = row["value"]
        conn.close()
        return get_schedule_db(sched_id, target_path)

    cursor.execute("SELECT schedule_id FROM schedules ORDER BY created_at DESC LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    if row:
        return get_schedule_db(row["schedule_id"], target_path)

    return None
