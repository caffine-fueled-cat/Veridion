"""Terminal test of the full certificate lifecycle on a temporary database."""
import os, tempfile
import db
db.DB_PATH = os.path.join(tempfile.mkdtemp(), "test.db")
import seed, stubs, certificate as cert, ai_examiner
from db import connect

seed.seed()
for sid in (1, 2):
    for mid, _, _ in stubs.module_status(sid, 1):
        stubs.mark_module_complete(sid, mid, 80)

try:
    cert.issue_certificate(3, 1); print("FAIL: issued without completion")
except ValueError as e:
    print("OK  blocked early issue:", e)

a, b = cert.issue_certificate(1, 1), cert.issue_certificate(2, 1)
assert cert.verify_certificate(a) == "VALID" and cert.verify_certificate(b) == "VALID"
print("OK  two certs issued and VALID, chained:", cert.get_certificate(b)["prev_hash"] == cert.get_certificate(a)["cert_hash"])

with connect() as c: c.execute("UPDATE certificates SET student_name='Hacker' WHERE cert_id=?", (a,))
print("OK  name edit ->", cert.verify_certificate(a), "| next cert ->", cert.verify_certificate(b))
with connect() as c: c.execute("UPDATE certificates SET student_name='Aarav' WHERE cert_id=?", (a,))
assert cert.verify_certificate(a) == "VALID"

with connect() as c: c.execute("UPDATE certificates SET expires_on='2099-01-01' WHERE cert_id=?", (b,))
print("OK  date edit ->", cert.verify_certificate(b))
with connect() as c: c.execute("UPDATE certificates SET expires_on=date('now','+180 day') WHERE cert_id=?", (b,))

cert.simulate_expiry(b)
print("OK  simulated expiry ->", cert.verify_certificate(b))
qs, src = ai_examiner.generate_quiz(1)
print("OK  quiz source:", src, "| questions:", len(qs))
print("OK  fail attempt renewed?", cert.renew_certificate(b, 1, 5, "x", qs), "->", cert.verify_certificate(b))
summ = ai_examiner.write_summary("Diya", "Programming in C", 4, 5, [qs[0]["question"]])
print("OK  pass attempt renewed?", cert.renew_certificate(b, 4, 5, summ, qs), "->", cert.verify_certificate(b))
print("    summary:", cert.get_certificate(b)["summary"])
