"""Minimal working versions of the teammate's logic.py contract.
gui.py uses logic.py if it exists, otherwise this file. Same names, same inputs."""
from datetime import date
from db import connect


def add_student(name, email):
    with connect() as c:
        return c.execute("INSERT INTO students(name,email) VALUES (?,?)", (name, email)).lastrowid

def list_students():
    with connect() as c:
        return [tuple(r) for r in c.execute("SELECT student_id,name,email FROM students ORDER BY student_id")]

def list_courses():
    with connect() as c:
        return [tuple(r) for r in c.execute("SELECT course_id,title FROM courses ORDER BY course_id")]

def enroll(student_id, course_id):
    with connect() as c:
        c.execute("INSERT OR IGNORE INTO enrollments VALUES (?,?,?)", (student_id, course_id, date.today().isoformat()))

def is_enrolled(student_id, course_id):
    with connect() as c:
        return c.execute("SELECT 1 FROM enrollments WHERE student_id=? AND course_id=?", (student_id, course_id)).fetchone() is not None

def module_status(student_id, course_id):
    """-> [(module_id, title, score or None)]"""
    with connect() as c:
        return [tuple(r) for r in c.execute(
            "SELECT m.module_id, m.title, p.score FROM modules m "
            "LEFT JOIN progress p ON p.module_id=m.module_id AND p.student_id=? "
            "WHERE m.course_id=? ORDER BY m.module_id", (student_id, course_id))]

def mark_module_complete(student_id, module_id, score):
    with connect() as c:
        c.execute("INSERT OR REPLACE INTO progress VALUES (?,?,?,?)", (student_id, module_id, score, date.today().isoformat()))

def all_modules_done(student_id, course_id):
    rows = module_status(student_id, course_id)
    return bool(rows) and all(r[2] is not None for r in rows)
