"""
Database initialization and helper functions
Handles all SQLite operations for the attendance system
"""

import sqlite3
import os
from datetime import datetime
from config import DATABASE_PATH, DATABASE_DIR


def get_connection():
    """Return a thread-safe SQLite connection with foreign keys enabled."""
    os.makedirs(DATABASE_DIR, exist_ok=True)
    conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Create all tables if they do not exist."""
    conn = get_connection()
    cur = conn.cursor()

    # Students table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id  TEXT    NOT NULL UNIQUE,
            name        TEXT    NOT NULL,
            department  TEXT    NOT NULL DEFAULT 'CSE',
            year        INTEGER NOT NULL DEFAULT 3,
            email       TEXT
        )
    """)

    # Subjects table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS subjects (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            subject_code TEXT    NOT NULL UNIQUE,
            subject_name TEXT    NOT NULL,
            teacher_name TEXT    NOT NULL
        )
    """)

    # Attendance table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id      TEXT    NOT NULL,
            subject_id      INTEGER NOT NULL,
            attendance_date TEXT    NOT NULL,
            status          TEXT    NOT NULL CHECK(status IN ('P','A')),
            source          TEXT    NOT NULL DEFAULT 'Manual'
                            CHECK(source IN ('Excel','Simulation','Manual')),
            FOREIGN KEY (student_id)  REFERENCES students(student_id)  ON DELETE CASCADE,
            FOREIGN KEY (subject_id)  REFERENCES subjects(id)          ON DELETE CASCADE,
            UNIQUE(student_id, subject_id, attendance_date)
        )
    """)

    # Uploads table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS uploads (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            subject_id     INTEGER NOT NULL,
            teacher_name   TEXT    NOT NULL,
            filename       TEXT    NOT NULL,
            upload_date    TEXT    NOT NULL,
            total_students INTEGER DEFAULT 0,
            total_classes  INTEGER DEFAULT 0,
            status         TEXT    DEFAULT 'Success',
            FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE
        )
    """)

    # Predictions table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS predictions (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id          TEXT    NOT NULL,
            prediction_date     TEXT    NOT NULL,
            current_attendance  REAL    NOT NULL,
            risk_level          TEXT    NOT NULL,
            recommendation      TEXT,
            FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE
        )
    """)

    conn.commit()
    conn.close()
    print("[DB] Tables created / verified.")


# ─── Student helpers ────────────────────────────────────────────────────────────

def insert_student(student_id, name, department='CSE', year=3, email=''):
    conn = get_connection()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO students (student_id, name, department, year, email) VALUES (?,?,?,?,?)",
            (student_id, name, department, year, email)
        )
        conn.commit()
    finally:
        conn.close()


def get_all_students():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM students ORDER BY student_id").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_student(student_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM students WHERE student_id=?", (student_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def search_students(query):
    conn = get_connection()
    q = f"%{query}%"
    rows = conn.execute(
        "SELECT * FROM students WHERE student_id LIKE ? OR name LIKE ? ORDER BY student_id",
        (q, q)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ─── Subject helpers ────────────────────────────────────────────────────────────

def insert_subject(subject_code, subject_name, teacher_name):
    conn = get_connection()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO subjects (subject_code, subject_name, teacher_name) VALUES (?,?,?)",
            (subject_code, subject_name, teacher_name)
        )
        conn.commit()
    finally:
        conn.close()


def get_all_subjects():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM subjects ORDER BY id").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_subject(subject_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM subjects WHERE id=?", (subject_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_subject_by_code(code):
    conn = get_connection()
    row = conn.execute("SELECT * FROM subjects WHERE subject_code=?", (code,)).fetchone()
    conn.close()
    return dict(row) if row else None


# ─── Attendance helpers ─────────────────────────────────────────────────────────

def insert_attendance_record(student_id, subject_id, date, status, source='Excel'):
    conn = get_connection()
    try:
        conn.execute(
            """INSERT OR REPLACE INTO attendance
               (student_id, subject_id, attendance_date, status, source)
               VALUES (?,?,?,?,?)""",
            (student_id, subject_id, date, status, source)
        )
        conn.commit()
    finally:
        conn.close()


def bulk_insert_attendance(records):
    """Insert many records at once. records = list of (student_id, subject_id, date, status, source)."""
    conn = get_connection()
    try:
        conn.executemany(
            """INSERT OR REPLACE INTO attendance
               (student_id, subject_id, attendance_date, status, source)
               VALUES (?,?,?,?,?)""",
            records
        )
        conn.commit()
    finally:
        conn.close()


def delete_subject_attendance(subject_id):
    """Remove all attendance records for a subject (before re-upload)."""
    conn = get_connection()
    try:
        conn.execute("DELETE FROM attendance WHERE subject_id=?", (subject_id,))
        conn.execute("DELETE FROM uploads WHERE subject_id=?", (subject_id,))
        conn.commit()
    finally:
        conn.close()


def get_attendance_for_subject(subject_id):
    conn = get_connection()
    rows = conn.execute(
        """SELECT a.*, s.name as student_name
           FROM attendance a
           JOIN students s ON a.student_id = s.student_id
           WHERE a.subject_id=?
           ORDER BY a.student_id, a.attendance_date""",
        (subject_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_attendance_for_student(student_id):
    conn = get_connection()
    rows = conn.execute(
        """SELECT a.*, sub.subject_name, sub.subject_code, sub.teacher_name
           FROM attendance a
           JOIN subjects sub ON a.subject_id = sub.id
           WHERE a.student_id=?
           ORDER BY sub.id, a.attendance_date""",
        (student_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_all_attendance(subject_id=None, student_id=None, date_filter=None):
    conn = get_connection()
    query = """
        SELECT a.*, s.name as student_name, sub.subject_name, sub.subject_code
        FROM attendance a
        JOIN students s ON a.student_id = s.student_id
        JOIN subjects sub ON a.subject_id = sub.id
        WHERE 1=1
    """
    params = []
    if subject_id:
        query += " AND a.subject_id=?"
        params.append(subject_id)
    if student_id:
        query += " AND a.student_id LIKE ?"
        params.append(f"%{student_id}%")
    if date_filter:
        query += " AND a.attendance_date=?"
        params.append(date_filter)
    query += " ORDER BY a.attendance_date DESC, a.student_id LIMIT 500"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def subject_has_attendance(subject_id):
    """Return True if any attendance records exist for this subject."""
    conn = get_connection()
    count = conn.execute(
        "SELECT COUNT(*) FROM attendance WHERE subject_id=?", (subject_id,)
    ).fetchone()[0]
    conn.close()
    return count > 0


# ─── Upload helpers ─────────────────────────────────────────────────────────────

def insert_upload(subject_id, teacher_name, filename, total_students, total_classes):
    conn = get_connection()
    try:
        conn.execute(
            """INSERT INTO uploads
               (subject_id, teacher_name, filename, upload_date, total_students, total_classes, status)
               VALUES (?,?,?,?,?,?,'Success')""",
            (subject_id, teacher_name, filename,
             datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
             total_students, total_classes)
        )
        conn.commit()
    finally:
        conn.close()


def get_all_uploads():
    conn = get_connection()
    rows = conn.execute(
        """SELECT u.*, sub.subject_name, sub.subject_code
           FROM uploads u
           JOIN subjects sub ON u.subject_id = sub.id
           ORDER BY u.upload_date DESC"""
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ─── Prediction helpers ─────────────────────────────────────────────────────────

def insert_prediction(student_id, current_attendance, risk_level, recommendation):
    conn = get_connection()
    try:
        conn.execute(
            """INSERT INTO predictions
               (student_id, prediction_date, current_attendance, risk_level, recommendation)
               VALUES (?,?,?,?,?)""",
            (student_id, datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
             current_attendance, risk_level, recommendation)
        )
        conn.commit()
    finally:
        conn.close()


# ─── Analytics helpers ──────────────────────────────────────────────────────────

def get_dashboard_stats():
    """Return aggregate statistics for the dashboard."""
    conn = get_connection()

    total_students = conn.execute("SELECT COUNT(*) FROM students").fetchone()[0]
    total_subjects = conn.execute("SELECT COUNT(*) FROM subjects").fetchone()[0]
    total_teachers = conn.execute(
        "SELECT COUNT(DISTINCT teacher_name) FROM subjects"
    ).fetchone()[0]
    total_classes_conducted = conn.execute(
        "SELECT COUNT(DISTINCT subject_id || '-' || attendance_date) FROM attendance"
    ).fetchone()[0]

    conn.close()
    return {
        'total_students': total_students,
        'total_subjects': total_subjects,
        'total_teachers': total_teachers,
        'total_classes': total_classes_conducted,
    }


def get_subject_stats(subject_id):
    """
    Return per-student stats for a subject:
    classes, present, absent, percentage.
    """
    conn = get_connection()
    rows = conn.execute(
        """SELECT
               a.student_id,
               s.name            as student_name,
               COUNT(*)          as total_classes,
               SUM(CASE WHEN a.status='P' THEN 1 ELSE 0 END) as present,
               SUM(CASE WHEN a.status='A' THEN 1 ELSE 0 END) as absent
           FROM attendance a
           JOIN students s ON a.student_id = s.student_id
           WHERE a.subject_id=?
           GROUP BY a.student_id
           ORDER BY a.student_id""",
        (subject_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_combined_stats():
    """
    Return combined attendance across ALL subjects per student.
    Uses SUM of attended / SUM of conducted.
    """
    conn = get_connection()
    # Per student per subject
    rows = conn.execute(
        """SELECT
               a.student_id,
               s.name            as student_name,
               a.subject_id,
               sub.subject_name,
               sub.subject_code,
               COUNT(*)          as total_classes,
               SUM(CASE WHEN a.status='P' THEN 1 ELSE 0 END) as present
           FROM attendance a
           JOIN students s   ON a.student_id  = s.student_id
           JOIN subjects sub ON a.subject_id  = sub.id
           GROUP BY a.student_id, a.subject_id
           ORDER BY a.student_id, a.subject_id"""
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_dates_for_subject(subject_id):
    """Return sorted list of dates that have attendance records for a subject."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT DISTINCT attendance_date FROM attendance WHERE subject_id=? ORDER BY attendance_date",
        (subject_id,)
    ).fetchall()
    conn.close()
    return [r[0] for r in rows]