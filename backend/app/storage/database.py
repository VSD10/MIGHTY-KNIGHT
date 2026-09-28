import sqlite3
import json
import os
import hashlib
from typing import Dict, Any, List, Optional

# Local SQLite Database Path inside data/ folder
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(BASE_DIR, "data")
DEFAULT_DB_PATH = os.path.join(DATA_DIR, "chess_scheduler.db")

def get_db_path() -> str:
    env_path = os.environ.get("CHESS_DB_PATH")
    if env_path:
        return os.path.abspath(env_path)
    # Vercel serverless environment: root filesystem is read-only, copy to /tmp for write access
    if os.environ.get("VERCEL"):
        tmp_db = "/tmp/chess_scheduler.db"
        if not os.path.exists(tmp_db) and os.path.exists(DEFAULT_DB_PATH):
            import shutil
            try:
                shutil.copy2(DEFAULT_DB_PATH, tmp_db)
            except Exception as e:
                print("Notice: Could not copy DB to /tmp:", e)
        return tmp_db
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

    # 4. Master Batches table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS batches (
            batch_id TEXT PRIMARY KEY,
            batch_name TEXT NOT NULL,
            level TEXT NOT NULL,
            batch_type TEXT NOT NULL,
            fixed_trainer TEXT,
            schedule_timings TEXT,
            student_ids_json TEXT,
            data_json TEXT NOT NULL
        )
    """)

    # 5. Active metadata table
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

    # Sanitize batches: remove any student IDs that do not exist in the newly uploaded student list
    new_student_ids = {s["student_id"] for s in students}
    cursor.execute("SELECT batch_id, data_json FROM batches")
    rows = cursor.fetchall()
    for row in rows:
        try:
            b = json.loads(row["data_json"])
            old_s_ids = b.get("student_ids", [])
            filtered_s_ids = [sid for sid in old_s_ids if sid in new_student_ids]
            if len(filtered_s_ids) != len(old_s_ids):
                b["student_ids"] = filtered_s_ids
                if "students" in b and isinstance(b["students"], list):
                    b["students"] = [st for st in b["students"] if isinstance(st, dict) and st.get("student_id") in new_student_ids]
                    b["student_count"] = len(b["students"])
                cursor.execute("UPDATE batches SET student_ids_json = ?, data_json = ? WHERE batch_id = ?",
                               (json.dumps(filtered_s_ids), json.dumps(b), row["batch_id"]))
        except Exception:
            pass

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
    cursor.execute("DELETE FROM active_metadata WHERE key = 'master_cleared'")
    cursor.execute("""
        INSERT OR REPLACE INTO students (student_id, student_name, student_level, batch_type, region_timezone, required_classes, data_json)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        s.get("student_id", ""),
        s.get("student_name", ""),
        s.get("student_level", "Basic 1"),
        s.get("batch_type", "G"),
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
    
    # Cascade: Unlink student from any master batches
    cursor.execute("SELECT batch_id, data_json FROM batches")
    rows = cursor.fetchall()
    for row in rows:
        try:
            b = json.loads(row["data_json"])
            s_ids = b.get("student_ids", [])
            students_list = b.get("students", [])
            modified = False
            if student_id in s_ids:
                b["student_ids"] = [sid for sid in s_ids if sid != student_id]
                modified = True
            if any(s.get("student_id") == student_id for s in students_list):
                b["students"] = [s for s in students_list if s.get("student_id") != student_id]
                b["student_count"] = len(b["students"])
                modified = True
            if modified:
                cursor.execute("UPDATE batches SET student_ids_json = ?, data_json = ? WHERE batch_id = ?",
                               (json.dumps(b.get("student_ids", [])), json.dumps(b), row["batch_id"]))
        except Exception:
            pass

    conn.commit()
    conn.close()

def save_single_coach_db(c: Dict[str, Any], db_path: Optional[str] = None):
    target_path = db_path or get_db_path()
    init_db(target_path)
    conn = get_connection(target_path)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM active_metadata WHERE key = 'master_cleared'")
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

    # Cascade: Unassign coach from master batches
    cursor.execute("SELECT batch_id, data_json FROM batches")
    rows = cursor.fetchall()
    for row in rows:
        try:
            b = json.loads(row["data_json"])
            if b.get("fixed_trainer", "").strip().lower() == coach_name.strip().lower():
                b["fixed_trainer"] = "Unassigned"
                cursor.execute("UPDATE batches SET fixed_trainer = 'Unassigned', data_json = ? WHERE batch_id = ?",
                               (json.dumps(b), row["batch_id"]))
        except Exception:
            pass

    conn.commit()
    conn.close()

def get_master_statistics_db(db_path: Optional[str] = None) -> Dict[str, int]:
    """
    Computes real-time master data statistics directly from SQLite.
    """
    target_path = db_path or get_db_path()
    init_db(target_path)
    conn = get_connection(target_path)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM batches")
    total_batches = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM students")
    total_students = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM coaches")
    total_coaches = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM batches WHERE batch_type = 'G'")
    group_batches = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM batches WHERE batch_type = 'L'")
    limited_batches = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM batches WHERE batch_type = 'I'")
    individual_batches = cursor.fetchone()[0]
    conn.close()
    return {
        "total_batches": total_batches,
        "total_students": total_students,
        "total_coaches": total_coaches,
        "group_batches": group_batches,
        "limited_batches": limited_batches,
        "individual_batches": individual_batches
    }


def save_single_batch_db(b: Dict[str, Any], db_path: Optional[str] = None):
    target_path = db_path or get_db_path()
    init_db(target_path)
    conn = get_connection(target_path)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM active_metadata WHERE key = 'master_cleared'")
    cursor.execute("""
        INSERT OR REPLACE INTO batches (batch_id, batch_name, level, batch_type, fixed_trainer, schedule_timings, student_ids_json, data_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        b["batch_id"],
        b.get("batch_name", b["batch_id"]),
        b.get("level", "Beginner 1"),
        b.get("batch_type", "G"),
        b.get("fixed_trainer", "Unassigned"),
        b.get("schedule_timings", ""),
        json.dumps(b.get("student_ids", [])),
        json.dumps(b)
    ))
    conn.commit()
    conn.close()

def delete_single_batch_db(batch_id: str, db_path: Optional[str] = None):
    target_path = db_path or get_db_path()
    init_db(target_path)
    conn = get_connection(target_path)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM batches WHERE batch_id = ?", (batch_id,))
    conn.commit()
    conn.close()

def load_master_batches_db(db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    target_path = db_path or get_db_path()
    init_db(target_path)
    conn = get_connection(target_path)
    cursor = conn.cursor()
    cursor.execute("SELECT data_json FROM batches")
    rows = cursor.fetchall()
    batches = [json.loads(row["data_json"]) for row in rows]
    conn.close()
    return batches

def save_all_master_batches_db(batches: List[Dict[str, Any]], db_path: Optional[str] = None):
    target_path = db_path or get_db_path()
    init_db(target_path)
    conn = get_connection(target_path)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM batches")
    for b in batches:
        cursor.execute("""
            INSERT INTO batches (batch_id, batch_name, level, batch_type, fixed_trainer, schedule_timings, student_ids_json, data_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            b["batch_id"],
            b.get("batch_name", b["batch_id"]),
            b.get("level", "Beginner 1"),
            b.get("batch_type", "G"),
            b.get("fixed_trainer", "Unassigned"),
            b.get("schedule_timings", ""),
            json.dumps(b.get("student_ids", [])),
            json.dumps(b)
        ))
    conn.commit()
    conn.close()

def clear_all_master_data_db(db_path: Optional[str] = None):
    """
    Completely wipes all students, coaches, batches, schedules, and active metadata from the SQLite DB.
    Sets master_cleared flag in active_metadata so empty state is respected across restarts.
    """
    target_path = db_path or get_db_path()
    init_db(target_path)
    conn = get_connection(target_path)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM students")
    cursor.execute("DELETE FROM coaches")
    cursor.execute("DELETE FROM batches")
    cursor.execute("DELETE FROM schedules")
    cursor.execute("DELETE FROM active_metadata")
    cursor.execute("INSERT INTO active_metadata (key, value) VALUES ('master_cleared', 'true')")
    conn.commit()
    conn.close()

def is_master_cleared_db(db_path: Optional[str] = None) -> bool:
    target_path = db_path or get_db_path()
    init_db(target_path)
    conn = get_connection(target_path)
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM active_metadata WHERE key = 'master_cleared'")
    row = cursor.fetchone()
    conn.close()
    return bool(row and row["value"] == "true")


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

    cursor.execute("SELECT data_json FROM batches")
    batch_rows = cursor.fetchall()
    batches = [json.loads(row["data_json"]) for row in batch_rows]

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
        "batches": batches,
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

def compute_master_data_fingerprint(config_dict: Optional[Dict[str, Any]] = None, db_path: Optional[str] = None) -> str:
    """
    Computes a deterministic SHA256 fingerprint representing the entire master data state:
    students, trainers, batches, and system configuration.
    Used for schedule cache invalidation and detecting stale finalized schedules.
    """
    target_path = db_path or get_db_path()
    init_db(target_path)
    conn = get_connection(target_path)
    cursor = conn.cursor()

    cursor.execute("SELECT student_id, student_level, batch_type, required_classes FROM students ORDER BY student_id ASC")
    student_rows = cursor.fetchall()
    stu_repr = [(r["student_id"], r["student_level"], r["batch_type"], r["required_classes"]) for r in student_rows]

    cursor.execute("SELECT coach_name, levels_handled_json, monthly_capacity_min, monthly_capacity_max FROM coaches ORDER BY coach_name ASC")
    coach_rows = cursor.fetchall()
    coach_repr = [(r["coach_name"], r["levels_handled_json"], r["monthly_capacity_min"], r["monthly_capacity_max"]) for r in coach_rows]

    cursor.execute("SELECT batch_id, level, batch_type, fixed_trainer, schedule_timings, student_ids_json FROM batches ORDER BY batch_id ASC")
    batch_rows = cursor.fetchall()
    batch_repr = [(r["batch_id"], r["level"], r["batch_type"], r["fixed_trainer"], r["schedule_timings"], r["student_ids_json"]) for r in batch_rows]

    cfg_val = config_dict
    if cfg_val is None:
        cursor.execute("SELECT value FROM active_metadata WHERE key = 'system_config'")
        cfg_row = cursor.fetchone()
        cfg_val = json.loads(cfg_row["value"]) if cfg_row else {}

    conn.close()

    raw_payload = json.dumps({
        "students": stu_repr,
        "coaches": coach_repr,
        "batches": batch_repr,
        "config": cfg_val
    }, sort_keys=True)

    return hashlib.sha256(raw_payload.encode("utf-8")).hexdigest()

def save_schedule_db(schedule_dict: Dict[str, Any], db_path: Optional[str] = None):
    """
    Saves generated schedule and output views in SQLite schedules table.
    Also updates latest_schedule_id pointer and master_data_fingerprint in active_metadata.
    """
    target_path = db_path or get_db_path()
    init_db(target_path)

    if not schedule_dict.get("master_data_fingerprint"):
        schedule_dict["master_data_fingerprint"] = compute_master_data_fingerprint(db_path=target_path)

    conn = get_connection(target_path)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO schedules 
        (schedule_id, status, start_date, end_date, total_students, scheduled_students, unscheduled_students, accountability_passed, data_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        schedule_dict["schedule_id"],
        schedule_dict.get("status", "Draft"),
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
    cursor.execute("INSERT OR REPLACE INTO active_metadata (key, value) VALUES ('latest_schedule_fingerprint', ?)", (schedule_dict["master_data_fingerprint"],))
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

def save_system_config_db(config_dict: Dict[str, Any], db_path: Optional[str] = None):
    """
    Persists current SystemConfig dictionary into SQLite active_metadata table.
    """
    target_path = db_path or get_db_path()
    init_db(target_path)
    conn = get_connection(target_path)
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO active_metadata (key, value) VALUES ('system_config', ?)", (json.dumps(config_dict),))
    conn.commit()
    conn.close()

def load_system_config_db(db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Retrieves persisted SystemConfig dictionary from SQLite active_metadata table.
    """
    target_path = db_path or get_db_path()
    init_db(target_path)
    conn = get_connection(target_path)
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM active_metadata WHERE key = 'system_config'")
    row = cursor.fetchone()
    conn.close()
    if row:
        try:
            return json.loads(row["value"])
        except Exception:
            return None
    return None

def clear_all_master_data_db(db_path: Optional[str] = None):
    """
    Wipes all students, coaches, batches, and schedules from the SQLite database,
    and marks master_cleared flag as true so server restarts don't auto-reload sample data.
    """
    target_path = db_path or get_db_path()
    init_db(target_path)
    conn = get_connection(target_path)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM students")
    cursor.execute("DELETE FROM coaches")
    cursor.execute("DELETE FROM batches")
    cursor.execute("DELETE FROM schedules")
    cursor.execute("DELETE FROM active_metadata WHERE key = 'latest_schedule_id'")
    cursor.execute("INSERT OR REPLACE INTO active_metadata (key, value) VALUES ('master_cleared', 'true')")
    conn.commit()
    conn.close()
    log_db_status("POST_CLEAR_ALL_MASTER_DATA", target_path)

def is_master_cleared_db(db_path: Optional[str] = None) -> bool:
    """
    Returns True if master data was explicitly cleared by the user.
    """
    target_path = db_path or get_db_path()
    if not os.path.exists(target_path):
        return False
    try:
        conn = get_connection(target_path)
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM active_metadata WHERE key = 'master_cleared'")
        row = cursor.fetchone()
        conn.close()
        return bool(row and row["value"] == "true")
    except Exception:
        return False

