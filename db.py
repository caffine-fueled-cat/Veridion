"""Database setup. SQLite file lives next to this script."""
import os
import sqlite3
from contextlib import contextmanager

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "elearning.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS students (
    student_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name  TEXT NOT NULL,
    email TEXT
);
CREATE TABLE IF NOT EXISTS courses (
    course_id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS modules (
    module_id INTEGER PRIMARY KEY AUTOINCREMENT,
    course_id INTEGER NOT NULL REFERENCES courses(course_id),
    title TEXT NOT NULL,
    notes TEXT            -- the AI reads this to build quizzes
);
CREATE TABLE IF NOT EXISTS enrollments (
    student_id  INTEGER NOT NULL REFERENCES students(student_id),
    course_id   INTEGER NOT NULL REFERENCES courses(course_id),
    enrolled_on TEXT,
    PRIMARY KEY (student_id, course_id)
);
CREATE TABLE IF NOT EXISTS progress (
    student_id   INTEGER NOT NULL REFERENCES students(student_id),
    module_id    INTEGER NOT NULL REFERENCES modules(module_id),
    score        INTEGER,
    completed_on TEXT,
    PRIMARY KEY (student_id, module_id)
);
CREATE TABLE IF NOT EXISTS certificates (
    cert_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id     INTEGER NOT NULL,
    course_id      INTEGER NOT NULL,
    student_name   TEXT NOT NULL,   -- snapshot, so editing it breaks the hash
    course_title   TEXT NOT NULL,
    issued_on      TEXT NOT NULL,
    last_proven_on TEXT NOT NULL,
    expires_on     TEXT NOT NULL,
    summary        TEXT NOT NULL,   -- AI proof summary
    prev_hash      TEXT NOT NULL,   -- cert_hash of the previous certificate
    cert_hash      TEXT NOT NULL,   -- fixed at issue time (identity + chain link)
    proof_hash     TEXT NOT NULL    -- changes on renewal (dates + summary)
);
CREATE TABLE IF NOT EXISTS reproof_attempts (
    attempt_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    cert_id        INTEGER NOT NULL REFERENCES certificates(cert_id),
    score          INTEGER,
    total          INTEGER,
    passed         INTEGER,
    taken_on       TEXT,
    questions_json TEXT
);
"""


@contextmanager
def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with connect() as conn:
        conn.executescript(SCHEMA)
