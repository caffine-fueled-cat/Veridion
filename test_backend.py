"""Unit and integration tests for logic.py and reports.py on a temporary database."""
import os
import tempfile
import db

# Redirect database to a temporary file before any other module imports connect
temp_dir = tempfile.mkdtemp()
db.DB_PATH = os.path.join(temp_dir, "test_backend.db")

import seed
import logic
import reports
import certificate
from db import connect


def run_tests():
    print("Initializing test database with seed data...")
    assert seed.seed() is True
    print("Seed completed successfully.")

    # 1. Test list_students and list_courses
    students = logic.list_students()
    courses = logic.list_courses()
    print("Initial students count:", len(students))
    print("Initial courses count:", len(courses))
    assert len(students) == 10
    assert len(courses) == 2
    assert isinstance(students[0], tuple)
    assert isinstance(courses[0], tuple)

    # 2. Test add_student
    new_sid = logic.add_student("Temp Student", "temp@example.com")
    print("Added student with ID:", new_sid)
    assert new_sid == 11
    assert any(s[0] == new_sid and s[1] == "Temp Student" for s in logic.list_students())

    # 3. Test update_student
    logic.update_student(new_sid, "Updated Student", "updated@example.com")
    updated_stu = next(s for s in logic.list_students() if s[0] == new_sid)
    print("Updated student:", updated_stu)
    assert updated_stu == (new_sid, "Updated Student", "updated@example.com")

    # 4. Test add_course and add_module
    new_cid = logic.add_course("Cloud Computing")
    print("Added course with ID:", new_cid)
    assert new_cid == 3
    # A course with no modules should return False for all_modules_done
    assert logic.all_modules_done(new_sid, new_cid) is False

    new_mid = logic.add_module(new_cid, "Virtual Machines", "Basics of VMs.")
    print("Added module with ID:", new_mid)
    assert new_mid == 7

    # 5. Test enroll and is_enrolled
    assert logic.is_enrolled(new_sid, new_cid) is False
    logic.enroll(new_sid, new_cid)
    assert logic.is_enrolled(new_sid, new_cid) is True
    print("Enrolled student", new_sid, "in course", new_cid)

    # Test duplicate enroll is ignored
    logic.enroll(new_sid, new_cid)
    with connect() as conn:
        enroll_count = conn.execute(
            "SELECT COUNT(*) FROM enrollments WHERE student_id = ? AND course_id = ?",
            (new_sid, new_cid)
        ).fetchone()[0]
    assert enroll_count == 1
    print("OK: duplicate enroll ignored.")

    # 6. Test all_modules_done before completion
    assert logic.all_modules_done(new_sid, new_cid) is False
    status_before = logic.module_status(new_sid, new_cid)
    print("Module status before completion:", status_before)
    assert status_before == [(new_mid, "Virtual Machines", None)]

    # 7. Test mark_module_complete and all_modules_done after completion
    logic.mark_module_complete(new_sid, new_mid, 95)
    status_after = logic.module_status(new_sid, new_cid)
    print("Module status after completion:", status_after)
    assert status_after == [(new_mid, "Virtual Machines", 95)]
    assert logic.all_modules_done(new_sid, new_cid) is True
    print("OK: all_modules_done is False before and True after completion.")

    # 8. Test delete_student removes progress and enrollments
    logic.delete_student(new_sid)
    with connect() as conn:
        prog_rows = conn.execute("SELECT COUNT(*) FROM progress WHERE student_id = ?", (new_sid,)).fetchone()[0]
        enr_rows = conn.execute("SELECT COUNT(*) FROM enrollments WHERE student_id = ?", (new_sid,)).fetchone()[0]
        stu_rows = conn.execute("SELECT COUNT(*) FROM students WHERE student_id = ?", (new_sid,)).fetchone()[0]
    assert prog_rows == 0
    assert enr_rows == 0
    assert stu_rows == 0
    print("OK: delete_student removes progress, enrollment, and student rows.")

    # 9. Test reports with a small known setup
    # Student 1 (Aarav): enroll in course 1, complete 3 modules with 80, 90, 100 (avg 90.0)
    logic.enroll(1, 1)
    logic.mark_module_complete(1, 1, 80)
    logic.mark_module_complete(1, 2, 90)
    logic.mark_module_complete(1, 3, 100)
    assert logic.all_modules_done(1, 1) is True
    # Issue certificate for student 1 in course 1
    cert_id = certificate.issue_certificate(1, 1)
    assert cert_id is not None

    # Student 2 (Diya): enroll in course 1, complete 1 module with score 75
    logic.enroll(2, 1)
    logic.mark_module_complete(2, 1, 75)

    # Call student_performance
    perf = reports.student_performance()
    print("\n--- Student Performance Report ---")
    for row in perf:
        print(row)
    assert len(perf) == 10
    # Top student is Aarav with avg 90.0
    assert perf[0] == ("Aarav", 1, 3, 90.0)
    # Second student is Diya with avg 75.0
    assert perf[1] == ("Diya", 1, 1, 75.0)
    # Remaining students should have 0 activity and 0 avg score
    for row in perf[2:]:
        assert row[1] == 0
        assert row[2] == 0
        assert row[3] == 0
    print("OK: student_performance report returned expected numbers.")

    # Call course_completion
    comp = reports.course_completion()
    print("\n--- Course Completion Report ---")
    for row in comp:
        print(row)
    assert len(comp) == 3
    # Course 1: "Programming in C", 2 enrolled, 1 cert, 50.0% completion
    assert comp[0] == ("Programming in C", 2, 1, 50.0)
    # Course 2: "Database Systems", 0 enrolled, 0 certs, 0%
    assert comp[1] == ("Database Systems", 0, 0, 0)
    # Course 3: "Cloud Computing", 0 enrolled, 0 certs, 0%
    assert comp[2] == ("Cloud Computing", 0, 0, 0)
    print("OK: course_completion report returned expected numbers.")

    print("\nALL BACKEND TESTS PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    run_tests()
