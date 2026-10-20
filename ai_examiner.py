"""AI Re-proof Examiner: LLM generates the quiz and the proof summary.
If there is no API key or the call fails, a built-in question bank takes over,
so the demo never breaks. Pass/fail is NOT decided here (see certificate.PASS_MARK)."""
import json
import os
import random
import urllib.request
from db import connect

MODEL = "gemini-3.5-flash"
API_URL = "https://generativelanguage.googleapis.com/v1beta/models"

# ---- Fallback bank: module title -> [(question, options, correct_index)] ----
BANK = {
    "Variables and Data Types": [
        ("Which C type normally stores a single character?", ["int", "char", "float", "double"], 1),
        ("What does sizeof(int) return on most modern systems?", ["1", "2", "4", "8"], 2),
        ("Which declaration is valid in C?", ["int 2x = 5;", "int x = 5;", "integer x = 5;", "x int = 5;"], 1),
    ],
    "Pointers": [
        ("What does a pointer variable store?", ["A float value", "A memory address", "A file name", "A loop counter"], 1),
        ("Which operator reads the value at the address a pointer holds?", ["&", "*", "#", "@"], 1),
        ("What does &x give you?", ["The value of x", "The address of x", "The size of x", "The type of x"], 1),
    ],
    "Arrays and Strings": [
        ("In C, array indexing starts at:", ["0", "1", "-1", "Any number you choose"], 0),
        ("Which character ends a C string?", ["'\\n'", "'\\0'", "' '", "'.'"], 1),
        ("For int a[5], the last valid index is:", ["5", "4", "6", "0"], 1),
    ],
    "SQL Basics": [
        ("Which statement reads rows from a table?", ["INSERT", "SELECT", "UPDATE", "DROP"], 1),
        ("Which clause filters rows?", ["WHERE", "ORDER BY", "GROUP BY", "LIMIT"], 0),
        ("Which statement removes rows?", ["DELETE", "SELECT", "CREATE", "ALTER"], 0),
    ],
    "Joins": [
        ("INNER JOIN returns:", ["All rows of both tables", "Only rows that match in both tables",
                                 "Only unmatched rows", "Rows of the left table only"], 1),
        ("Which keyword introduces the join condition?", ["ON", "IF", "WHEN", "BY"], 0),
        ("LEFT JOIN keeps every row from which table?", ["The right table", "The left table", "Neither", "Both"], 1),
    ],
    "Normalization": [
        ("The main goal of normalization is to:", ["Reduce redundancy", "Increase redundancy", "Delete tables", "Speed up the network"], 0),
        ("First normal form (1NF) requires:", ["Atomic values, no repeating groups", "Every column is a key",
                                               "No primary key", "Only one table"], 0),
        ("A primary key must be:", ["Unique and not null", "Always text", "Duplicated", "Optional"], 0),
    ],
}


def _call_llm(prompt, max_tokens=8000):
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key:
        raise RuntimeError("GEMINI_API_KEY not set")
    url = f"{API_URL}/{MODEL}:generateContent"
    body = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"maxOutputTokens": max_tokens}
    }).encode()
    req = urllib.request.Request(
        url, data=body,
        headers={"content-type": "application/json", "x-goog-api-key": key}
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = json.load(resp)
    candidates = data.get("candidates", [])
    if not candidates:
        return ""
    parts = candidates[0].get("content", {}).get("parts", [])
    return "".join(p.get("text", "") for p in parts)


def _course_modules(course_id):
    with connect() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT title, notes FROM modules WHERE course_id=? ORDER BY module_id", (course_id,))]


def _valid(q):
    return (isinstance(q, dict) and isinstance(q.get("question"), str)
            and isinstance(q.get("options"), list) and len(q["options"]) == 4
            and isinstance(q.get("answer"), int) and 0 <= q["answer"] <= 3)


def _ai_quiz(modules, n):
    notes = "\n\n".join(f"## {m['title']}\n{m['notes']}" for m in modules)
    prompt = (f"You are a strict examiner. Using ONLY the course notes below, write {n} multiple-choice "
              "questions that test understanding, spread across the modules. Each has exactly 4 options and "
              "one correct answer. Respond with JSON only, no markdown, in this shape: "
              '[{"question": "...", "options": ["a","b","c","d"], "answer": 0}] '
              "where answer is the index (0-3) of the correct option.\n\n" + notes)
    text = _call_llm(prompt).strip()
    text = text[text.find("["): text.rfind("]") + 1]       # drop any stray text/fences
    qs = [q for q in json.loads(text) if _valid(q)]
    if len(qs) < n:
        raise ValueError("AI returned too few valid questions")
    return qs[:n]


def _bank_quiz(modules, n):
    pool = [(q, o, a) for m in modules for (q, o, a) in BANK.get(m["title"], [])]
    random.shuffle(pool)
    return [{"question": q, "options": o, "answer": a} for q, o, a in pool[:n]]


def generate_quiz(course_id, n=5):
    """-> (questions, source) where source is 'AI' or 'Question bank'.
    Each question: {'question': str, 'options': [4 str], 'answer': int index}."""
    modules = _course_modules(course_id)
    try:
        return _ai_quiz(modules, n), "AI"
    except Exception:
        return _bank_quiz(modules, n), "Question bank"


def write_summary(student_name, course_title, score, total, missed):
    """Two-sentence proof summary that goes into the certificate hash."""
    try:
        prompt = (f"Write a 2-sentence proof summary (max 40 words, no markdown) for a certificate. "
                  f"Student {student_name} re-took the {course_title} exam and scored {score}/{total}. "
                  f"Questions they missed: {missed if missed else 'none'}. "
                  "Say what they demonstrated and any weak area. Do not use quotation marks.")
        text = _call_llm(prompt, 8000).strip()
        if text:
            return text
    except Exception:
        pass
    weak = f" Review needed on {len(missed)} topic(s)." if missed else " No weak areas found."
    return f"Re-proved {course_title} with a score of {score}/{total}.{weak}"
