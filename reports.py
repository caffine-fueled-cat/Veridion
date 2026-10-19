"""Reports module for Living Certificates e-learning platform."""
from db import connect

# Column headings used by the GUI to display report tables
STUDENT_PERFORMANCE_COLUMNS = ["Student", "Courses Enrolled", "Modules Completed", "Average Score"]
COURSE_COMPLETION_COLUMNS = ["Course", "Students Enrolled", "Certificates Issued", "Completion %"]


# Report showing student name, courses enrolled, modules completed, and average score
def student_performance():
    with connect() as conn:
        # Left join students with enrollments and progress to include students without activity
        cursor = conn.execute("""
            SELECT
                s.name,
                COUNT(DISTINCT e.course_id) AS courses_enrolled,
                COUNT(DISTINCT p.module_id) AS modules_completed,
                COALESCE(ROUND(AVG(p.score), 1), 0) AS average_score
            FROM students s
            LEFT JOIN enrollments e ON s.student_id = e.student_id
            LEFT JOIN progress p ON s.student_id = p.student_id
            GROUP BY s.student_id, s.name
            ORDER BY average_score DESC
        """)
        return [tuple(row) for row in cursor.fetchall()]


# Report showing course title, students enrolled, certificates issued, and completion percentage
def course_completion():
    with connect() as conn:
        # Left join courses with enrollments and certificates to compute completion rate per course
        cursor = conn.execute("""
            SELECT
                c.title,
                COUNT(DISTINCT e.student_id) AS students_enrolled,
                COUNT(DISTINCT cert.cert_id) AS certificates_issued,
                CASE
                    WHEN COUNT(DISTINCT e.student_id) = 0 THEN 0
                    ELSE ROUND(COUNT(DISTINCT cert.cert_id) * 100.0 / COUNT(DISTINCT e.student_id), 1)
                END AS completion_percent
            FROM courses c
            LEFT JOIN enrollments e ON c.course_id = e.course_id
            LEFT JOIN certificates cert ON c.course_id = cert.course_id
            GROUP BY c.course_id, c.title
            ORDER BY c.course_id
        """)
        return [tuple(row) for row in cursor.fetchall()]
