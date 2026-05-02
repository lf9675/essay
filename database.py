import sqlite3
import json
from datetime import datetime

DB_PATH = "essay_grader.db"

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            exam_level TEXT NOT NULL DEFAULT 'HCL',
            genre TEXT NOT NULL,
            prompt TEXT NOT NULL,
            requirements TEXT,
            rubric TEXT,
            focus_areas TEXT,
            created_at TEXT,
            is_active INTEGER DEFAULT 1
        )
    """)
    try:
        c.execute("ALTER TABLE assignments ADD COLUMN focus_areas TEXT")
    except:
        pass
    try:
        c.execute("ALTER TABLE assignments ADD COLUMN exam_level TEXT DEFAULT 'HCL'")
    except:
        pass

    c.execute("""
        CREATE TABLE IF NOT EXISTS submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            assignment_id INTEGER,
            student_id TEXT NOT NULL,
            student_name TEXT NOT NULL,
            submitted_at TEXT,
            image_data BLOB,
            ocr_text TEXT,
            feedback_json TEXT,
            viewed_at TEXT,
            FOREIGN KEY (assignment_id) REFERENCES assignments(id)
        )
    """)
    try:
        c.execute("ALTER TABLE submissions ADD COLUMN ocr_text TEXT")
    except:
        pass

    conn.commit()
    conn.close()

def save_assignment(title, exam_level, genre, prompt, requirements, rubric, focus_areas=None):
    conn = get_conn()
    c = conn.cursor()
    focus_json = json.dumps(focus_areas or [], ensure_ascii=False)
    c.execute("""
        INSERT INTO assignments (title, exam_level, genre, prompt, requirements, rubric, focus_areas, created_at, is_active)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
    """, (title, exam_level, genre, prompt, requirements, rubric, focus_json, datetime.now().isoformat()))
    assignment_id = c.lastrowid
    conn.commit()
    conn.close()
    return assignment_id

def get_active_assignments():
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM assignments WHERE is_active=1 ORDER BY created_at DESC")
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_all_assignments():
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM assignments ORDER BY created_at DESC")
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def toggle_assignment(assignment_id, is_active):
    conn = get_conn()
    c = conn.cursor()
    c.execute("UPDATE assignments SET is_active=? WHERE id=?", (is_active, assignment_id))
    conn.commit()
    conn.close()

def delete_assignment(assignment_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("DELETE FROM assignments WHERE id=?", (assignment_id,))
    conn.commit()
    conn.close()

def save_submission(assignment_id, student_id, student_name, image_bytes, ocr_text, feedback_json):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        INSERT INTO submissions (assignment_id, student_id, student_name, submitted_at, image_data, ocr_text, feedback_json)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (assignment_id, student_id, student_name, datetime.now().isoformat(),
          image_bytes, ocr_text, json.dumps(feedback_json, ensure_ascii=False)))
    sid = c.lastrowid
    conn.commit()
    conn.close()
    return sid

def get_all_submissions():
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        SELECT s.*, a.title as assignment_title, a.genre
        FROM submissions s
        JOIN assignments a ON s.assignment_id = a.id
        ORDER BY s.submitted_at DESC
    """)
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_submissions_for_assignment(assignment_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        SELECT s.*, a.title as assignment_title
        FROM submissions s
        JOIN assignments a ON s.assignment_id = a.id
        WHERE s.assignment_id = ?
        ORDER BY s.submitted_at DESC
    """, (assignment_id,))
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def mark_viewed(submission_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("UPDATE submissions SET viewed_at=? WHERE id=? AND viewed_at IS NULL",
              (datetime.now().isoformat(), submission_id))
    conn.commit()
    conn.close()

init_db()
