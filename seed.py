"""Sample data: 10 students, 2 courses, 3 modules each (with notes)."""
from db import connect, init_db

COURSES = {
    "Programming in C": [
        ("Variables and Data Types",
         "C variables must be declared with a type. int stores whole numbers (usually 4 bytes), "
         "char stores one character, float and double store decimals. sizeof gives the size of a type."),
        ("Pointers",
         "A pointer stores the memory address of another variable. &x gives the address of x. "
         "The * operator (dereference) reads or writes the value at the address a pointer holds."),
        ("Arrays and Strings",
         "Arrays hold several values of one type and are indexed from 0. An array of size 5 has "
         "valid indexes 0 to 4. A C string is a char array that ends with the null character '\\0'."),
    ],
    "Database Systems": [
        ("SQL Basics",
         "SELECT reads rows, INSERT adds rows, UPDATE changes rows, DELETE removes rows. "
         "The WHERE clause filters which rows are affected."),
        ("Joins",
         "A JOIN combines rows from two tables using a condition written after ON. INNER JOIN keeps "
         "only matching rows. LEFT JOIN keeps every row of the left table, matched or not."),
        ("Normalization",
         "Normalization reduces redundancy by splitting data into related tables. 1NF needs atomic "
         "values and no repeating groups. A primary key must be unique and not null."),
    ],
}
STUDENTS = ["Aarav", "Diya", "Karthik", "Meera", "Rohan", "Sneha", "Vikram", "Ananya", "Arjun", "Priya"]


def seed():
    init_db()
    with connect() as conn:
        if conn.execute("SELECT COUNT(*) FROM students").fetchone()[0]:
            return False
        for n in STUDENTS:
            conn.execute("INSERT INTO students(name, email) VALUES (?,?)", (n, n.lower() + "@example.com"))
        for title, mods in COURSES.items():
            cid = conn.execute("INSERT INTO courses(title) VALUES (?)", (title,)).lastrowid
            for mt, notes in mods:
                conn.execute("INSERT INTO modules(course_id,title,notes) VALUES (?,?,?)", (cid, mt, notes))
    return True


if __name__ == "__main__":
    print("seeded" if seed() else "already has data")
