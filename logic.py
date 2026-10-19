"""Business logic for Living Certificates e-learning platform."""
from datetime import date
from db import connect


# Add a new student record with name and email, returns the new student_id
def add_student(name, email):
    with connect() as conn:
        # Insert student record into students table
        cursor = conn.execute("INSERT INTO students (name, email) VALUES (?, ?)", (name, email))
        return cursor.lastrowid


# Return all students as (student_id, name, email) tuples ordered by id
def list_students():
    with connect() as conn:
        # Select all student records in ascending order of their ID
        cursor = conn.execute("SELECT student_id, name, email FROM students ORDER BY student_id")
        return [tuple(row) for row in cursor.fetchall()]


# Return all courses as (course_id, title) tuples ordered by id
def list_courses():
    with connect() as conn:
        # Select all course records in ascending order of their ID
        cursor = conn.execute("SELECT course_id, title FROM courses ORDER BY course_id")
        return [tuple(row) for row in cursor.fetchall()]


# Enroll a student in a course; ignores duplicates and records today's date
def enroll(student_id, course_id):
    today = date.today().isoformat()
    with connect() as conn:
        # Insert enrollment with today's date, ignoring if already enrolled
        conn.execute("INSERT OR IGNORE INTO enrollments (student_id, course_id, enrolled_on) VALUES (?, ?, ?)",
                     (student_id, course_id, today))


# Check if a student is enrolled in a specific course, returns bool
def is_enrolled(student_id, course_id):
    with connect() as conn:
        # Query for matching enrollment record
        cursor = conn.execute("SELECT 1 FROM enrollments WHERE student_id = ? AND course_id = ?",
                              (student_id, course_id))
        return cursor.fetchone() is not None


# Return list of (module_id, title, score_or_None) for all modules in a course
def module_status(student_id, course_id):
    with connect() as conn:
        # Left join modules with student progress to show module details and score (or None if not done)
        cursor = conn.execute(
            "SELECT m.module_id, m.title, p.score FROM modules m "
            "LEFT JOIN progress p ON p.module_id = m.module_id AND p.student_id = ? "
            "WHERE m.course_id = ? ORDER BY m.module_id",
            (student_id, course_id)
        )
        return [tuple(row) for row in cursor.fetchall()]


# Mark a module as complete with a score and today's date (insert or replace)
def mark_module_complete(student_id, module_id, score):
    today = date.today().isoformat()
    with connect() as conn:
        # Insert or update progress record with module score and completion date
        conn.execute(
            "INSERT OR REPLACE INTO progress (student_id, module_id, score, completed_on) VALUES (?, ?, ?, ?)",
            (student_id, module_id, score, today)
        )


# Check if a student has completed every module in a course (False if course has no modules)
def all_modules_done(student_id, course_id):
    rows = module_status(student_id, course_id)
    return bool(rows) and all(r[2] is not None for r in rows)


# Update a student's name and email
def update_student(student_id, name, email):
    with connect() as conn:
        # Update name and email for the student with matching ID
        conn.execute("UPDATE students SET name = ?, email = ? WHERE student_id = ?",
                     (name, email, student_id))


# Delete a student and their associated progress and enrollment rows
def delete_student(student_id):
    with connect() as conn:
        # Delete student's progress rows first to respect foreign key constraints
        conn.execute("DELETE FROM progress WHERE student_id = ?", (student_id,))
        # Delete student's enrollment rows
        conn.execute("DELETE FROM enrollments WHERE student_id = ?", (student_id,))
        # Delete the student record
        conn.execute("DELETE FROM students WHERE student_id = ?", (student_id,))


# Add a new course with a title, returns the new course_id
def add_course(title):
    with connect() as conn:
        # Insert course record into courses table
        cursor = conn.execute("INSERT INTO courses (title) VALUES (?)", (title,))
        return cursor.lastrowid


# Add a new module to a course with title and study notes, returns module_id
def add_module(course_id, title, notes):
    with connect() as conn:
        # Insert module record into modules table
        cursor = conn.execute("INSERT INTO modules (course_id, title, notes) VALUES (?, ?, ?)",
                              (course_id, title, notes))
        return cursor.lastrowid
