import sqlite3
import json
import os
import uuid
import hashlib
from datetime import datetime
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

    # Canonical resolution: prioritize populated database
    curr_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.abspath(os.path.join(curr_dir, "..", "..", "data", "chess_scheduler.db")),
        os.path.abspath(os.path.join(curr_dir, "..", "..", "..", "data", "chess_scheduler.db")),
        DEFAULT_DB_PATH
    ]
    for cand in candidates:
        if os.path.exists(cand) and os.path.getsize(cand) > 1000:
            return cand
    return candidates[0]

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

    # Rule 5: Indexes for high performance and zero table-scan latency
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_students_level_batch ON students(student_level, batch_type)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_batches_type_level ON batches(batch_type, level)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_schedules_created ON schedules(created_at)")

    # 6. Absolute Baselines table (Part E)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS absolute_baselines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            month TEXT NOT NULL,
            version INTEGER NOT NULL,
            status TEXT NOT NULL,
            file_name TEXT,
            uploaded_by TEXT DEFAULT 'Admin',
            uploaded_at TEXT,
            student_count INTEGER DEFAULT 0,
            class_count INTEGER DEFAULT 0,
            student_class_count INTEGER DEFAULT 0,
            students_data_json TEXT NOT NULL,
            classes_data_json TEXT NOT NULL,
            baseline_exceptions_json TEXT,
            validation_report_json TEXT,
            created_at TEXT NOT NULL
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_baselines_month ON absolute_baselines(month, status)")

    # 7. Exception Records table (Part D - ⓒ Overlay)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS exception_records (
            id TEXT PRIMARY KEY,
            month TEXT NOT NULL,
            date TEXT NOT NULL,
            start_time TEXT NOT NULL,
            coach_id TEXT NOT NULL,
            class_key TEXT NOT NULL,
            action_type TEXT NOT NULL,
            affected_student_ids_json TEXT NOT NULL,
            before_json TEXT,
            after_json TEXT,
            subtype TEXT NOT NULL,
            violated_rules_json TEXT,
            reason TEXT,
            created_by TEXT DEFAULT 'Admin',
            created_at TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'active',
            version INTEGER DEFAULT 1
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_exceptions_month ON exception_records(month, status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_exceptions_date ON exception_records(date, start_time)")

    # 8. Assignments Layer table (Part A2 - Layer 2)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS assignments_layer (
            id TEXT PRIMARY KEY,
            month TEXT NOT NULL,
            class_data_json TEXT NOT NULL,
            source TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_assignments_month ON assignments_layer(month)")

    # 9. Audit Logs table (Part A5)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id TEXT PRIMARY KEY,
            timestamp TEXT NOT NULL,
            user TEXT NOT NULL,
            action TEXT NOT NULL,
            entity_type TEXT NOT NULL,
            entity_id TEXT,
            before_json TEXT,
            after_json TEXT,
            violated_rules_json TEXT,
            source_page TEXT,
            month TEXT
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_month ON audit_logs(month, timestamp)")

    # 10. Deleted & Archived Records table (Output 3 Management)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS deleted_records (
            record_id TEXT PRIMARY KEY,
            record_type TEXT NOT NULL,
            record_name TEXT NOT NULL,
            deletion_scope TEXT NOT NULL,
            deleted_at TEXT NOT NULL,
            deleted_by TEXT DEFAULT 'Admin',
            affected_future_classes INTEGER DEFAULT 0,
            historical_classes_preserved INTEGER DEFAULT 0,
            notes TEXT,
            data_json TEXT
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_deleted_scope ON deleted_records(deletion_scope, record_type)")
    
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
    c_name = c["coach_name"].strip()
    cursor.execute("DELETE FROM coaches WHERE LOWER(coach_name) = LOWER(?)", (c_name,))
    cursor.execute("""
        INSERT OR REPLACE INTO coaches (coach_name, levels_handled_json, monthly_capacity_min, monthly_capacity_max, data_json)
        VALUES (?, ?, ?, ?, ?)
    """, (
        c_name,
        json.dumps(c.get("levels_handled", c.get("levels", []))),
        c.get("monthly_capacity_min") if c.get("monthly_capacity_min") is not None else 0,
        c.get("monthly_capacity_max") if c.get("monthly_capacity_max") is not None else 100,
        json.dumps(c)
    ))
    conn.commit()
    conn.close()

def delete_single_coach_db(coach_name: str, db_path: Optional[str] = None):
    target_path = db_path or get_db_path()
    init_db(target_path)
    conn = get_connection(target_path)
    cursor = conn.cursor()

    # Rule 10 & Additional Rule 5: Maintain Historical Identity in Database
    # Archive coach data before removing from active scheduling pool
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS historical_coaches (
            coach_name TEXT PRIMARY KEY,
            deleted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            data_json TEXT
        )
    """)
    cursor.execute("SELECT coach_name, data_json FROM coaches WHERE LOWER(coach_name) = LOWER(?)", (coach_name.strip(),))
    existing_c = cursor.fetchone()
    if existing_c:
        cursor.execute("""
            INSERT OR REPLACE INTO historical_coaches (coach_name, deleted_at, data_json)
            VALUES (?, CURRENT_TIMESTAMP, ?)
        """, (existing_c["coach_name"], existing_c["data_json"]))

    cursor.execute("DELETE FROM coaches WHERE LOWER(coach_name) = LOWER(?)", (coach_name.strip(),))

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
    try:
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
    except Exception:
        conn.rollback()
        raise
    finally:
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

def save_engine_settings_db(settings_dict: Dict[str, Any], db_path: Optional[str] = None):
    """
    Persists current ENGINE_SETTINGS dictionary into SQLite active_metadata table.
    """
    target_path = db_path or get_db_path()
    init_db(target_path)
    conn = get_connection(target_path)
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO active_metadata (key, value) VALUES ('engine_settings', ?)", (json.dumps(settings_dict),))
    conn.commit()
    conn.close()

def load_engine_settings_db(db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Retrieves persisted ENGINE_SETTINGS dictionary from SQLite active_metadata table.
    """
    target_path = db_path or get_db_path()
    init_db(target_path)
    conn = get_connection(target_path)
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM active_metadata WHERE key = 'engine_settings'")
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

# ==============================================================================
# ABSOLUTE BASELINES STORAGE (PART E)
# ==============================================================================

def save_baseline_db(baseline_dict: Dict[str, Any], db_path: Optional[str] = None) -> int:
    """
    Saves a baseline (Draft or Active) into absolute_baselines table.
    Returns the auto-generated id.
    """
    target_path = db_path or get_db_path()
    init_db(target_path)
    conn = get_connection(target_path)
    cursor = conn.cursor()

    month = baseline_dict["month"]
    version = baseline_dict.get("version", 1)
    status = baseline_dict.get("status", "Draft")

    # If status is Active, mark all prior baselines for this month as Superseded
    if status == "Active":
        cursor.execute("UPDATE absolute_baselines SET status = 'Superseded' WHERE month = ? AND status = 'Active'", (month,))

    cursor.execute("""
        INSERT INTO absolute_baselines (
            month, version, status, file_name, uploaded_by, uploaded_at,
            student_count, class_count, student_class_count,
            students_data_json, classes_data_json, baseline_exceptions_json,
            validation_report_json, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        month,
        version,
        status,
        baseline_dict.get("file_name", ""),
        baseline_dict.get("uploaded_by", "Admin"),
        baseline_dict.get("uploaded_at", datetime.now().strftime("%Y-%m-%d %I:%M %p")),
        baseline_dict.get("student_count", 0),
        baseline_dict.get("class_count", 0),
        baseline_dict.get("student_class_count", 0),
        json.dumps(baseline_dict.get("students_data", [])),
        json.dumps(baseline_dict.get("classes_data", [])),
        json.dumps(baseline_dict.get("baseline_exceptions", [])),
        json.dumps(baseline_dict.get("validation_report", {})),
        baseline_dict.get("created_at", "")
    ))
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return new_id

def get_active_baseline_db(month: str, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Retrieves the Active baseline for a month."""
    target_path = db_path or get_db_path()
    init_db(target_path)
    conn = get_connection(target_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM absolute_baselines
        WHERE month = ? AND status = 'Active'
        ORDER BY version DESC LIMIT 1
    """, (month,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    return _hydrate_baseline_row(row)

def get_draft_baseline_db(month: str, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Retrieves the latest Draft baseline for a month."""
    target_path = db_path or get_db_path()
    init_db(target_path)
    conn = get_connection(target_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM absolute_baselines
        WHERE month = ? AND status = 'Draft'
        ORDER BY version DESC LIMIT 1
    """, (month,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    return _hydrate_baseline_row(row)

def get_baseline_by_version_db(month: str, version: int, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Retrieves baseline by month and explicit version."""
    target_path = db_path or get_db_path()
    init_db(target_path)
    conn = get_connection(target_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM absolute_baselines WHERE month = ? AND version = ?", (month, version))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    return _hydrate_baseline_row(row)

def list_baselines_for_month_db(month: str, db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Lists all baseline versions for a month (history)."""
    target_path = db_path or get_db_path()
    init_db(target_path)
    conn = get_connection(target_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, month, version, status, file_name, uploaded_by, uploaded_at,
               student_count, class_count, student_class_count, created_at
        FROM absolute_baselines
        WHERE month = ?
        ORDER BY version DESC
    """, (month,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def activate_baseline_db(month: str, version: int, user: str = "Admin", db_path: Optional[str] = None) -> bool:
    """Activates a draft baseline version and supersedes previous active version."""
    target_path = db_path or get_db_path()
    init_db(target_path)
    conn = get_connection(target_path)
    cursor = conn.cursor()
    # Mark old active as Superseded
    cursor.execute("UPDATE absolute_baselines SET status = 'Superseded' WHERE month = ? AND status = 'Active'", (month,))
    # Activate target version
    cursor.execute("UPDATE absolute_baselines SET status = 'Active', uploaded_by = ? WHERE month = ? AND version = ?", (user, month, version))
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    return affected > 0

def discard_draft_baseline_db(month: str, db_path: Optional[str] = None) -> bool:
    """Discards the pending draft baseline for a month."""
    target_path = db_path or get_db_path()
    init_db(target_path)
    conn = get_connection(target_path)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM absolute_baselines WHERE month = ? AND status = 'Draft'", (month,))
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    return affected > 0

def _hydrate_baseline_row(row) -> Dict[str, Any]:
    return {
        "id": row["id"],
        "month": row["month"],
        "version": row["version"],
        "status": row["status"],
        "file_name": row["file_name"],
        "uploaded_by": row["uploaded_by"],
        "uploaded_at": row["uploaded_at"],
        "student_count": row["student_count"],
        "class_count": row["class_count"],
        "student_class_count": row["student_class_count"],
        "students_data": json.loads(row["students_data_json"]) if row["students_data_json"] else [],
        "classes_data": json.loads(row["classes_data_json"]) if row["classes_data_json"] else [],
        "baseline_exceptions": json.loads(row["baseline_exceptions_json"]) if row["baseline_exceptions_json"] else [],
        "validation_report": json.loads(row["validation_report_json"]) if row["validation_report_json"] else {},
        "created_at": row["created_at"]
    }

# ==============================================================================
# EXCEPTION RECORDS (ⓒ OVERLAY - PART D)
# ==============================================================================

def save_exception_record_db(rec: Dict[str, Any], db_path: Optional[str] = None):
    """Inserts or updates a single-occurrence manual ExceptionRecord (ⓒ)."""
    target_path = db_path or get_db_path()
    init_db(target_path)
    conn = get_connection(target_path)
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT OR REPLACE INTO exception_records (
                id, month, date, start_time, coach_id, class_key, action_type,
                affected_student_ids_json, before_json, after_json, subtype,
                violated_rules_json, reason, created_by, created_at, status, version
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            rec["id"],
            rec["month"],
            rec["date"],
            rec["start_time"],
            rec["coach_id"],
            rec["class_key"],
            rec["action_type"],
            json.dumps(rec.get("affected_student_ids", [])),
            json.dumps(rec.get("before", {})),
            json.dumps(rec.get("after", {})),
            rec.get("subtype", "manual"),
            json.dumps(rec.get("violated_rules", [])),
            rec.get("reason", ""),
            rec.get("created_by", "Admin"),
            rec.get("created_at", ""),
            rec.get("status", "active"),
            rec.get("version", 1)
        ))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def get_exception_records_db(month: str, status: Optional[str] = "active", db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieves ExceptionRecords for a month."""
    target_path = db_path or get_db_path()
    init_db(target_path)
    conn = get_connection(target_path)
    cursor = conn.cursor()
    if status:
        cursor.execute("SELECT * FROM exception_records WHERE month = ? AND status = ? ORDER BY created_at ASC", (month, status))
    else:
        cursor.execute("SELECT * FROM exception_records WHERE month = ? ORDER BY created_at ASC", (month,))
    rows = cursor.fetchall()
    conn.close()
    results = []
    for r in rows:
        results.append({
            "id": r["id"],
            "month": r["month"],
            "date": r["date"],
            "start_time": r["start_time"],
            "coach_id": r["coach_id"],
            "class_key": r["class_key"],
            "action_type": r["action_type"],
            "affected_student_ids": json.loads(r["affected_student_ids_json"]) if r["affected_student_ids_json"] else [],
            "before": json.loads(r["before_json"]) if r["before_json"] else {},
            "after": json.loads(r["after_json"]) if r["after_json"] else {},
            "subtype": r["subtype"],
            "violated_rules": json.loads(r["violated_rules_json"]) if r["violated_rules_json"] else [],
            "reason": r["reason"],
            "created_by": r["created_by"],
            "created_at": r["created_at"],
            "status": r["status"],
            "version": r["version"]
        })
    return results

def revert_exception_record_db(exception_id: str, db_path: Optional[str] = None) -> bool:
    """Marks an exception record as reverted."""
    target_path = db_path or get_db_path()
    init_db(target_path)
    conn = get_connection(target_path)
    cursor = conn.cursor()
    cursor.execute("UPDATE exception_records SET status = 'reverted' WHERE id = ?", (exception_id,))
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    return affected > 0

# ==============================================================================
# AUDIT LOGS (PART A5)
# ==============================================================================

def log_audit_event_db(
    user: str,
    action: str,
    entity_type: str,
    entity_id: str,
    before: Any,
    after: Any,
    violated_rules: List[Any],
    source_page: str,
    month: str,
    db_path: Optional[str] = None
):
    """Writes an entry to audit_logs table."""
    import uuid
    target_path = db_path or get_db_path()
    init_db(target_path)
    conn = get_connection(target_path)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO audit_logs (
            id, timestamp, user, action, entity_type, entity_id,
            before_json, after_json, violated_rules_json, source_page, month
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        f"AUD_{uuid.uuid4().hex[:8].upper()}",
        datetime.now().strftime("%Y-%m-%d %I:%M:%S %p"),
        user,
        action,
        entity_type,
        entity_id,
        json.dumps(before or {}),
        json.dumps(after or {}),
        json.dumps(violated_rules or []),
        source_page,
        month
    ))
    conn.commit()
    conn.close()

def get_audit_logs_db(month: Optional[str] = None, limit: int = 100, db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieves audit logs."""
    target_path = db_path or get_db_path()
    init_db(target_path)
    conn = get_connection(target_path)
    cursor = conn.cursor()
    if month:
        cursor.execute("SELECT * FROM audit_logs WHERE month = ? ORDER BY timestamp DESC LIMIT ?", (month, limit))
    else:
        cursor.execute("SELECT * FROM audit_logs ORDER BY timestamp DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [
        {
            "id": r["id"],
            "timestamp": r["timestamp"],
            "user": r["user"],
            "action": r["action"],
            "entity_type": r["entity_type"],
            "entity_id": r["entity_id"],
            "before": json.loads(r["before_json"]) if r["before_json"] else {},
            "after": json.loads(r["after_json"]) if r["after_json"] else {},
            "violated_rules": json.loads(r["violated_rules_json"]) if r["violated_rules_json"] else [],
            "source_page": r["source_page"],
            "month": r["month"]
        }
        for r in rows
    ]

# ==============================================================================
# SEED INITIAL OCTOBER 2026 BASELINE
# ==============================================================================

def seed_october_baseline_if_missing(db_path: Optional[str] = None):
    """
    Guarantees October 2026 has an Active Baseline (v1) loaded from reference schedule,
    so the app boots up immediately with the full 119-student schedule.
    """
    target_path = db_path or get_db_path()
    init_db(target_path)
    conn = get_connection(target_path)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM absolute_baselines WHERE month = '2026-10' AND status = 'Active'")
    cnt = cursor.fetchone()[0]
    conn.close()
    if cnt > 0:
        seed_september_baseline_if_missing(target_path)
        seed_november_and_december_baselines_if_missing(target_path)
        return

    # Check for pre-compiled JSON reference
    ref_json_paths = [
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "reference_oct_schedule.json"),
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "backend", "data", "reference_oct_schedule.json")
    ]
    ref_data = None
    for p in ref_json_paths:
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    ref_data = json.load(f)
                break
            except Exception:
                pass

    if not ref_data:
        return

    students_raw = ref_data.get("students_raw", [])
    classes_by_date = ref_data.get("oct_exact_classes_by_date", {})
    all_classes = []
    seat_count = 0
    for dt, cls_list in classes_by_date.items():
        for c in cls_list:
            all_classes.append(c)
            seat_count += len(c.get("student_ids", []))

    save_baseline_db({
        "month": "2026-10",
        "version": 1,
        "status": "Active",
        "file_name": "Oct'26 Schedule_FRESH-1.xlsx",
        "uploaded_by": "System Baseline Seed",
        "uploaded_at": "2026-10-01 12:00 PM",
        "student_count": len(students_raw),
        "class_count": len(all_classes),
        "student_class_count": seat_count,
        "students_data": students_raw,
        "classes_data": all_classes,
        "baseline_exceptions": [],
        "validation_report": {"blocking": [], "baseline_exceptions": [], "info": []},
        "created_at": "2026-10-01 12:00:00"
    }, target_path)

    # Ensure master batches are also seeded if missing
    conn = get_connection(target_path)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM batches")
    b_cnt = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM coaches")
    c_cnt = cursor.fetchone()[0]
    conn.close()
    if b_cnt == 0:
        from app.constants.batch_naming import allocate_students_to_subdivisions
        subdivisions, _ = allocate_students_to_subdivisions(students_raw)
        save_all_master_batches_db(subdivisions, target_path)

    if c_cnt == 0:
        from app.engine.rule_engine import COACH_REFERENCE
        for c_name, c_info in COACH_REFERENCE.items():
            save_single_coach_db({
                "coach_name": c_name,
                "levels_handled": c_info.get("levels", []),
                "monthly_capacity_min": c_info.get("monthly_min") or 30,
                "monthly_capacity_max": c_info.get("monthly_max") or 100,
                "is_active": True,
                "qualified_levels_priority": {lvl: idx + 1 for idx, lvl in enumerate(c_info.get("levels", []))}
            }, target_path)

    print(f"[BASE_SEED] Successfully seeded October 2026 Active Baseline (v1): {len(students_raw)} students, {len(all_classes)} classes, {seat_count} seats.", flush=True)

    # Ensure other months are seeded
    seed_september_baseline_if_missing(target_path)
    seed_november_and_december_baselines_if_missing(target_path)

def seed_september_baseline_if_missing(db_path: Optional[str] = None):
    target_path = db_path or get_db_path()
    init_db(target_path)
    conn = get_connection(target_path)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM absolute_baselines WHERE month = '2026-09' AND status = 'Active'")
    cnt = cursor.fetchone()[0]
    conn.close()
    if cnt > 0:
        return

    cand_paths = [
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "september_raw.txt"),
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "backend", "data", "september_raw.txt")
    ]
    raw_path = next((p for p in cand_paths if os.path.exists(p)), None)
    if not raw_path:
        return

    import re
    from collections import defaultdict, Counter

    ref_json_paths = [
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "reference_oct_schedule.json"),
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "backend", "data", "reference_oct_schedule.json")
    ]
    name_to_stu = {}
    for p in ref_json_paths:
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    oct_ref = json.load(f)
                    for s in oct_ref.get("students_raw", []):
                        name = s.get("student_name", "").strip()
                        sid = s.get("student_id", "")
                        lvl = s.get("student_level", "Basic 1")
                        btype = s.get("batch_type", "G")
                        req = s.get("required_classes", 8)
                        clean = name.lower()
                        name_to_stu[clean] = {"student_id": sid, "student_name": name, "student_level": lvl, "batch_type": btype, "required_classes": req}
                        clean_no_dot = re.sub(r'[\.\s]+', '', clean)
                        name_to_stu[clean_no_dot] = name_to_stu[clean]
                break
            except Exception:
                pass

    try:
        with open(raw_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception:
        return

    current_date = None
    current_coach = None
    current_time = None
    schedule_records = []

    date_pattern = re.compile(r'📅\s*DATE:\s*(\d{2}-[A-Za-z]{3})')
    coach_pattern = re.compile(r'♟️\s*([A-Za-z\s]+)')
    time_pattern = re.compile(r'^(\d{1,2}:\d{2}\s*(?:AM|PM)|\d{1,2}\s*(?:AM|PM)|TIME NOT PROVIDED|\d{1,2}\s*&\s*\d{1,2}\.\d{2}[a-z]+)', re.IGNORECASE)

    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith("━"):
            continue
        m_date = date_pattern.match(line)
        if m_date:
            d_str = m_date.group(1)
            day_num, month_str = d_str.split("-")
            current_date = f"2026-09-{day_num.zfill(2)}"
            current_coach = None
            current_time = None
            continue
        m_coach = coach_pattern.match(line)
        if m_coach:
            c_raw = m_coach.group(1).strip()
            current_coach = c_raw.upper()
            current_time = None
            continue
        m_time = time_pattern.match(line)
        if m_time:
            current_time = m_time.group(1).strip()
            continue
        if line.startswith("-"):
            stu_str = line[1:].strip()
            if "CANCELLED" in stu_str or "~~" in stu_str:
                continue
            clean_name = stu_str.replace("Extra", "").replace("Individual", "").replace("Trainer", "").strip()
            if not clean_name:
                continue
            if current_date and current_coach and current_time:
                try:
                    d_obj = datetime.strptime(current_date, "%Y-%m-%d")
                    day_name = d_obj.strftime("%A")
                except Exception:
                    day_name = "Monday"
                schedule_records.append({
                    "date": current_date,
                    "day": day_name,
                    "coach": current_coach,
                    "time_slot": current_time,
                    "student_name": clean_name
                })

    class_groups = defaultdict(lambda: {"student_ids": [], "student_names": []})
    student_counts = Counter()
    student_objects = {}

    for r in schedule_records:
        clean = r["student_name"].lower()
        clean_no_dot = re.sub(r'[\.\s]+', '', clean)
        matched = name_to_stu.get(clean) or name_to_stu.get(clean_no_dot)
        sid = matched["student_id"] if matched else f"STU_{abs(hash(r['student_name'])) % 10000}"
        sname = matched["student_name"] if matched else r["student_name"]
        slvl = matched["student_level"] if matched else "Basic 1"
        sbtype = matched["batch_type"] if matched else "G"
        k = (r["date"], r["day"], r["coach"], r["time_slot"])
        if sid not in class_groups[k]["student_ids"]:
            class_groups[k]["student_ids"].append(sid)
            class_groups[k]["student_names"].append(sname)
        student_counts[sid] += 1
        if sid not in student_objects:
            student_objects[sid] = {
                "student_id": sid,
                "student_name": sname,
                "student_level": slvl,
                "batch_type": sbtype,
                "required_classes": matched["required_classes"] if matched else 8,
                "scheduled_classes": 0
            }

    for sid, cnt in student_counts.items():
        if sid in student_objects:
            student_objects[sid]["scheduled_classes"] = cnt

    all_classes = []
    cls_idx = 1
    total_seats = 0
    for (dt, dy, coach, ts), grp in class_groups.items():
        s_count = len(grp["student_ids"])
        total_seats += s_count
        b_type = "I" if s_count <= 1 else ("L" if s_count <= 4 else "G")
        lvls = [student_objects.get(sid, {}).get("student_level", "Basic 1") for sid in grp["student_ids"]]
        dominant_lvl = Counter(lvls).most_common(1)[0][0] if lvls else "Basic 1"
        all_classes.append({
            "class_id": f"CLS_SEP_{str(cls_idx).zfill(4)}",
            "date": dt,
            "day": dy,
            "time_slot": ts,
            "coach_name": coach,
            "batch_name": f"{dominant_lvl} - {coach}",
            "student_level": dominant_lvl,
            "batch_type": b_type,
            "student_ids": grp["student_ids"],
            "student_names": grp["student_names"]
        })
        cls_idx += 1

    students_list = list(student_objects.values())
    save_baseline_db({
        "month": "2026-09",
        "version": 1,
        "status": "Active",
        "file_name": "september_raw.txt",
        "uploaded_by": "System Baseline Seed",
        "uploaded_at": "2026-09-01 12:00 PM",
        "student_count": len(students_list),
        "class_count": len(all_classes),
        "student_class_count": total_seats,
        "students_data": students_list,
        "classes_data": all_classes,
        "baseline_exceptions": [],
        "validation_report": {"blocking": [], "baseline_exceptions": [], "info": []},
        "created_at": "2026-09-01 12:00:00"
    }, target_path)
    print(f"[BASE_SEED] Successfully seeded September 2026 Active Baseline (v1): {len(students_list)} students, {len(all_classes)} classes, {total_seats} seats.", flush=True)

def seed_november_and_december_baselines_if_missing(db_path: Optional[str] = None):
    target_path = db_path or get_db_path()
    init_db(target_path)
    conn = get_connection(target_path)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM absolute_baselines WHERE month = '2026-11' AND status = 'Active'")
    nov_cnt = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM absolute_baselines WHERE month = '2026-12' AND status = 'Active'")
    dec_cnt = cursor.fetchone()[0]
    conn.close()

    if nov_cnt > 0 and dec_cnt > 0:
        return

    from app.engine.baseline_service import generate_next_month_draft
    
    if nov_cnt == 0:
        try:
            nov_draft = generate_next_month_draft("2026-10", 2026, 11, user="System Baseline Seed")
            nov_record = dict(nov_draft)
            nov_record["status"] = "Active"
            nov_record["file_name"] = "Nov'26 Schedule.xlsx"
            nov_record["uploaded_at"] = "2026-11-01 12:00 PM"
            save_baseline_db(nov_record, target_path)
            print(f"[BASE_SEED] Successfully seeded November 2026 Active Baseline (v1): {nov_record.get('student_count')} students, {nov_record.get('class_count')} classes, {nov_record.get('student_class_count')} seats.", flush=True)
        except Exception as e:
            print("[BASE_SEED] Notice: Could not seed November baseline:", e)

    if dec_cnt == 0:
        try:
            dec_draft = generate_next_month_draft("2026-10", 2026, 12, user="System Baseline Seed")
            dec_record = dict(dec_draft)
            dec_record["status"] = "Active"
            dec_record["file_name"] = "Dec'26 Schedule.xlsx"
            dec_record["uploaded_at"] = "2026-12-01 12:00 PM"
            save_baseline_db(dec_record, target_path)
            print(f"[BASE_SEED] Successfully seeded December 2026 Active Baseline (v1): {dec_record.get('student_count')} students, {dec_record.get('class_count')} classes, {dec_record.get('student_class_count')} seats.", flush=True)
        except Exception as e:
            print("[BASE_SEED] Notice: Could not seed December baseline:", e)

def save_deleted_record_db(record: Dict[str, Any], db_path: Optional[str] = None) -> str:
    target_path = db_path or get_db_path()
    init_db(target_path)
    conn = get_connection(target_path)
    cursor = conn.cursor()
    r_id = record.get("record_id") or f"DEL_{uuid.uuid4().hex[:8].upper()}"
    cursor.execute("""
        INSERT OR REPLACE INTO deleted_records (
            record_id, record_type, record_name, deletion_scope, deleted_at,
            deleted_by, affected_future_classes, historical_classes_preserved, notes, data_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        r_id,
        record.get("record_type", "coach"),
        record.get("record_name", ""),
        record.get("deletion_scope", "remove_from_schedule"),
        record.get("deleted_at") or datetime.now().strftime("%Y-%m-%d %I:%M %p"),
        record.get("deleted_by", "Admin"),
        record.get("affected_future_classes", 0),
        record.get("historical_classes_preserved", 0),
        record.get("notes", ""),
        json.dumps(record.get("data", {}))
    ))
    conn.commit()
    conn.close()
    return r_id

def get_deleted_records_db(db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    target_path = db_path or get_db_path()
    init_db(target_path)
    conn = get_connection(target_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM deleted_records ORDER BY deleted_at DESC")
    rows = cursor.fetchall()
    results = []
    for r in rows:
        results.append({
            "record_id": r["record_id"],
            "record_type": r["record_type"],
            "record_name": r["record_name"],
            "deletion_scope": r["deletion_scope"],
            "deleted_at": r["deleted_at"],
            "deleted_by": r["deleted_by"],
            "affected_future_classes": r["affected_future_classes"],
            "historical_classes_preserved": r["historical_classes_preserved"],
            "notes": r["notes"],
            "data": json.loads(r["data_json"]) if r["data_json"] else {}
        })
    conn.close()
    return results

def update_deleted_record_scope_db(record_id: str, new_scope: str, db_path: Optional[str] = None):
    target_path = db_path or get_db_path()
    init_db(target_path)
    conn = get_connection(target_path)
    cursor = conn.cursor()
    cursor.execute("UPDATE deleted_records SET deletion_scope = ? WHERE record_id = ?", (new_scope, record_id))
    conn.commit()
    conn.close()

def permanently_delete_record_db(record_id: str, db_path: Optional[str] = None):
    target_path = db_path or get_db_path()
    init_db(target_path)
    conn = get_connection(target_path)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM deleted_records WHERE record_id = ?", (record_id,))
    conn.commit()
    conn.close()

def load_all_coaches_db(db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    return load_master_data_db(db_path).get("coaches", [])

get_db_connection = get_connection



