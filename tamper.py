import sys, db
name = sys.argv[1] if len(sys.argv) > 1 else "Hacker"
with db.connect() as c:
    c.execute("UPDATE certificates SET student_name=? WHERE cert_id=1", (name,))
print("certificate 1 name is now:", name)
