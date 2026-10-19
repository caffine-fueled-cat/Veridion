"""Living Certificates: SHA-256 hash chain + expiry + re-proof.

Two hashes per certificate:
  cert_hash  = SHA256(identity fields + prev_hash)      -> never changes, forms the chain
  proof_hash = SHA256(cert_hash + dates + AI summary)   -> changes on every renewal
Status is never stored. It is recomputed on every check.
"""
import hashlib
import json
from datetime import date, timedelta
from db import connect

EXPIRY_DAYS = 180     # certificate lifetime
PASS_MARK = 0.6       # fixed rule: the AI never decides pass/fail


def _sha(*parts):
    return hashlib.sha256("|".join(str(p) for p in parts).encode()).hexdigest()

def _core_hash(c):
    return _sha(c["cert_id"], c["student_id"], c["student_name"], c["course_id"],
                c["course_title"], c["issued_on"], c["prev_hash"])

def _proof_hash(c):
    return _sha(c["cert_hash"], c["last_proven_on"], c["expires_on"], c["summary"])


def get_certificate(cert_id):
    with connect() as conn:
        row = conn.execute("SELECT * FROM certificates WHERE cert_id=?", (cert_id,)).fetchone()
    return dict(row) if row else None


def issue_certificate(student_id, course_id):
    """Issue only if every module of the course is complete. Returns cert_id."""
    with connect() as conn:
        old = conn.execute("SELECT cert_id FROM certificates WHERE student_id=? AND course_id=?",
                           (student_id, course_id)).fetchone()
        if old:
            return old["cert_id"]
        total = conn.execute("SELECT COUNT(*) FROM modules WHERE course_id=?", (course_id,)).fetchone()[0]
        done = conn.execute(
            "SELECT COUNT(*) FROM progress p JOIN modules m ON m.module_id=p.module_id "
            "WHERE p.student_id=? AND m.course_id=?", (student_id, course_id)).fetchone()[0]
        if total == 0 or done < total:
            raise ValueError(f"Only {done} of {total} modules completed. Finish all modules first.")
        stu = conn.execute("SELECT name FROM students WHERE student_id=?", (student_id,)).fetchone()
        crs = conn.execute("SELECT title FROM courses WHERE course_id=?", (course_id,)).fetchone()
        prev = conn.execute("SELECT cert_hash FROM certificates ORDER BY cert_id DESC LIMIT 1").fetchone()
        prev_hash = prev["cert_hash"] if prev else "GENESIS"

        today = date.today()
        cert_id = conn.execute(
            "INSERT INTO certificates(student_id,course_id,student_name,course_title,issued_on,"
            "last_proven_on,expires_on,summary,prev_hash,cert_hash,proof_hash) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (student_id, course_id, stu["name"], crs["title"], today.isoformat(), today.isoformat(),
             (today + timedelta(days=EXPIRY_DAYS)).isoformat(), "Completed all course modules.",
             prev_hash, "", "")).lastrowid
        c = dict(conn.execute("SELECT * FROM certificates WHERE cert_id=?", (cert_id,)).fetchone())
        c["cert_hash"] = _core_hash(c)
        c["proof_hash"] = _proof_hash(c)
        conn.execute("UPDATE certificates SET cert_hash=?, proof_hash=? WHERE cert_id=?",
                     (c["cert_hash"], c["proof_hash"], cert_id))
    return cert_id


def check(cert_id):
    """Returns {'status': VALID|EXPIRED|TAMPERED|NOT_FOUND, 'reason': str}."""
    c = get_certificate(cert_id)
    if c is None:
        return {"status": "NOT_FOUND", "reason": "No certificate with this ID."}
    if _core_hash(c) != c["cert_hash"]:
        return {"status": "TAMPERED", "reason": "Certificate details do not match their hash."}
    if _proof_hash(c) != c["proof_hash"]:
        return {"status": "TAMPERED", "reason": "Proof dates or summary were altered."}
    with connect() as conn:
        prev = conn.execute("SELECT cert_hash FROM certificates WHERE cert_id<? ORDER BY cert_id DESC LIMIT 1",
                            (cert_id,)).fetchone()
    expected_prev = prev["cert_hash"] if prev else "GENESIS"
    if c["prev_hash"] != expected_prev:
        return {"status": "TAMPERED", "reason": "Chain link broken: an earlier certificate was changed or removed."}
    if date.today() > date.fromisoformat(c["expires_on"]):
        return {"status": "EXPIRED", "reason": f"Genuine, but expired on {c['expires_on']}. Re-proof needed."}
    return {"status": "VALID", "reason": f"Genuine and proven on {c['last_proven_on']}. Valid until {c['expires_on']}."}


def verify_certificate(cert_id):
    return check(cert_id)["status"]


def renew_certificate(cert_id, score, total, summary, questions=None):
    """Log the attempt. If score/total >= PASS_MARK, extend expiry and re-hash. Returns True if passed."""
    if check(cert_id)["status"] in ("TAMPERED", "NOT_FOUND"):
        return False
    passed = total > 0 and score / total >= PASS_MARK
    today = date.today()
    with connect() as conn:
        conn.execute("INSERT INTO reproof_attempts(cert_id,score,total,passed,taken_on,questions_json) VALUES (?,?,?,?,?,?)",
                     (cert_id, score, total, int(passed), today.isoformat(), json.dumps(questions or [])))
        if passed:
            c = dict(conn.execute("SELECT * FROM certificates WHERE cert_id=?", (cert_id,)).fetchone())
            c["last_proven_on"] = today.isoformat()
            c["expires_on"] = (today + timedelta(days=EXPIRY_DAYS)).isoformat()
            c["summary"] = summary
            conn.execute("UPDATE certificates SET last_proven_on=?, expires_on=?, summary=?, proof_hash=? WHERE cert_id=?",
                         (c["last_proven_on"], c["expires_on"], summary, _proof_hash(c), cert_id))
    return passed


def simulate_expiry(cert_id):
    """DEMO ONLY: moves expiry to yesterday as a legitimate update (re-hashes), so status becomes EXPIRED, not TAMPERED."""
    with connect() as conn:
        c = dict(conn.execute("SELECT * FROM certificates WHERE cert_id=?", (cert_id,)).fetchone())
        c["expires_on"] = (date.today() - timedelta(days=1)).isoformat()
        conn.execute("UPDATE certificates SET expires_on=?, proof_hash=? WHERE cert_id=?",
                     (c["expires_on"], _proof_hash(c), cert_id))


def list_certificates():
    with connect() as conn:
        ids = [r[0] for r in conn.execute("SELECT cert_id FROM certificates ORDER BY cert_id")]
    out = []
    for i in ids:
        c = get_certificate(i)
        c["status"] = check(i)["status"]
        out.append(c)
    return out
