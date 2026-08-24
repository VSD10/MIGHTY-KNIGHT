import sqlite3
import json
import os
from typing import Dict, Any, Optional

DB_PATH = "mighty_knight.db"

def init_db(db_path: str = DB_PATH):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Schedules table
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
    
    # Active data session (students & coaches uploaded)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS active_sessions (
            session_id TEXT PRIMARY KEY,
            students_json TEXT NOT NULL,
            coaches_json TEXT NOT NULL,
            errors_json TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    
    conn.commit()
    conn.close()

def save_schedule_db(schedule_dict: Dict[str, Any], db_path: str = DB_PATH):
    init_db(db_path)
    conn = sqlite3.connect(db_path)
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
    conn.commit()
    conn.close()

def get_schedule_db(schedule_id: str, db_path: str = DB_PATH) -> Optional[Dict[str, Any]]:
    init_db(db_path)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT data_json FROM schedules WHERE schedule_id = ?", (schedule_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return json.loads(row[0])
    return None
