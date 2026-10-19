"""Tkinter GUI. Talks only to logic (or stubs), certificate and ai_examiner."""
import tkinter as tk
from tkinter import ttk, messagebox

try:
    import logic                      # teammate's real backend, once it exists
except ImportError:
    import stubs as logic             # same function names, minimal versions
import certificate
import ai_examiner
import reports

COLORS = {"VALID": "#1a7f37", "EXPIRED": "#b36b00", "TAMPERED": "#c62828", "NOT_FOUND": "#555555"}


def pick_id(text):
    return int(text.split(" - ")[0])


def make_tree(parent, cols, height=12):
    tree = ttk.Treeview(parent, columns=[c[0] for c in cols], show="headings", height=height)
    for name, width in cols:
        tree.heading(name, text=name.replace("_", " ").title())
        tree.column(name, width=width, anchor="w")
    tree.pack(fill="both", expand=True, pady=8)
    return tree


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Living Certificates - E-Learning Platform")
        self.geometry("860x560")
        style = ttk.Style(self)
        if "clam" in style.theme_names():
            style.theme_use("clam")
        def fixed_map(option):
            return [elm for elm in style.map("Treeview", query_opt=option)
                    if elm[:2] != ("!disabled", "!selected")]
        style.map("Treeview",
                  foreground=fixed_map("foreground"),
                  background=fixed_map("background"))
        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True, padx=8, pady=8)
        self.combos = []              # every student/course combobox, refreshed together
        self.build_students()
        self.build_progress()
        self.build_certs()
        self.build_verify()
        self.build_reports()
        self.refresh_all()

    # ---------- shared helpers ----------
    def student_values(self):
        return [f"{s[0]} - {s[1]}" for s in logic.list_students()]

    def course_values(self):
        return [f"{c[0]} - {c[1]}" for c in logic.list_courses()]

    def combo(self, parent, kind, col, width=28):
        cb = ttk.Combobox(parent, state="readonly", width=width)
        cb.grid(row=0, column=col, padx=4)
        self.combos.append((cb, kind))
        return cb

    def refresh_all(self):
        for cb, kind in self.combos:
            cb["values"] = self.student_values() if kind == "student" else self.course_values()
        self.refresh_students()
        self.refresh_certs()

    # ---------- Students tab ----------
    def build_students(self):
        f = ttk.Frame(self.nb, padding=10)
        self.nb.add(f, text="Students")
        form = ttk.Frame(f)
        form.pack(fill="x")
        self.s_name, self.s_email = tk.StringVar(), tk.StringVar()
        ttk.Label(form, text="Name").grid(row=0, column=0)
        ttk.Entry(form, textvariable=self.s_name, width=22).grid(row=0, column=1, padx=4)
        ttk.Label(form, text="Email").grid(row=0, column=2)
        ttk.Entry(form, textvariable=self.s_email, width=26).grid(row=0, column=3, padx=4)
        ttk.Button(form, text="Add student", command=self.add_student).grid(row=0, column=4, padx=4)
        self.s_tree = make_tree(f, [("id", 60), ("name", 220), ("email", 280)], 16)

    def add_student(self):
        name = self.s_name.get().strip()
        if not name:
            messagebox.showwarning("Missing name", "Enter the student's name.")
            return
        logic.add_student(name, self.s_email.get().strip())
        self.s_name.set("")
        self.s_email.set("")
        self.refresh_all()

    def refresh_students(self):
        self.s_tree.delete(*self.s_tree.get_children())
        for s in logic.list_students():
            self.s_tree.insert("", "end", values=(s[0], s[1], s[2]))

    # ---------- Enrollment & Progress tab ----------
    def build_progress(self):
        f = ttk.Frame(self.nb, padding=10)
        self.nb.add(f, text="Enrollment & Progress")
        top = ttk.Frame(f)
        top.pack(fill="x")
        self.p_student = self.combo(top, "student", 0)
        self.p_course = self.combo(top, "course", 1)
        self.p_student.bind("<<ComboboxSelected>>", lambda _e: self._on_progress_combo_select())
        self.p_course.bind("<<ComboboxSelected>>", lambda _e: self._on_progress_combo_select())
        ttk.Button(top, text="Enroll", command=self.do_enroll).grid(row=0, column=2, padx=4)
        ttk.Button(top, text="Show modules", command=self.refresh_modules).grid(row=0, column=3)
        self.m_tree = make_tree(f, [("module_id", 80), ("module", 320), ("status", 120), ("score", 80)], 10)
        bottom = ttk.Frame(f)
        bottom.pack(fill="x")
        ttk.Label(bottom, text="Score").pack(side="left")
        self.score_var = tk.StringVar(value="80")
        ttk.Entry(bottom, textvariable=self.score_var, width=6).pack(side="left", padx=4)
        ttk.Button(bottom, text="Mark selected complete", command=self.mark_selected).pack(side="left", padx=4)
        ttk.Button(bottom, text="Complete all modules (demo shortcut)", command=self.complete_all).pack(side="left", padx=4)

    def _on_progress_combo_select(self):
        if self.p_student.get() and self.p_course.get():
            self.refresh_modules()

    def _sel_ids(self):
        if not self.p_student.get() or not self.p_course.get():
            messagebox.showwarning("Select first", "Choose a student and a course.")
            return None
        return pick_id(self.p_student.get()), pick_id(self.p_course.get())

    def do_enroll(self):
        ids = self._sel_ids()
        if ids:
            logic.enroll(*ids)
            self.refresh_modules()
            messagebox.showinfo("Enrolled", "Student enrolled in course.")

    def refresh_modules(self):
        self.m_tree.delete(*self.m_tree.get_children())
        ids = self._sel_ids()
        if not ids:
            return
        for mid, title, score in logic.module_status(*ids):
            self.m_tree.insert("", "end", values=(mid, title, "Done" if score is not None else "Pending",
                                                  "" if score is None else score))

    def _score(self):
        try:
            s = int(self.score_var.get())
            if 0 <= s <= 100:
                return s
        except ValueError:
            pass
        messagebox.showwarning("Bad score", "Score must be a number from 0 to 100.")
        return None

    def mark_selected(self):
        ids, score = self._sel_ids(), self._score()
        if not ids or score is None:
            return
        sel = self.m_tree.selection()
        if not sel:
            messagebox.showwarning("Select first", "Select a module in the list to mark complete.")
            return
        logic.mark_module_complete(ids[0], int(self.m_tree.item(sel[0])["values"][0]), score)
        self.refresh_modules()

    def complete_all(self):
        ids, score = self._sel_ids(), self._score()
        if not ids or score is None:
            return
        for mid, _, _ in logic.module_status(*ids):
            logic.mark_module_complete(ids[0], mid, score)
        self.refresh_modules()

    # ---------- Certificates tab ----------
    def build_certs(self):
        f = ttk.Frame(self.nb, padding=10)
        self.nb.add(f, text="Certificates")
        top = ttk.Frame(f)
        top.pack(fill="x")
        self.c_student = self.combo(top, "student", 0)
        self.c_course = self.combo(top, "course", 1)
        ttk.Button(top, text="Issue certificate", command=self.issue).grid(row=0, column=2, padx=4)
        cols = [("id", 50), ("student", 130), ("course", 160), ("issued", 90), ("expires", 90), ("status", 90)]
        self.c_tree = make_tree(f, cols, 12)
        for st, col in COLORS.items():
            self.c_tree.tag_configure(st, foreground=col)
        bottom = ttk.Frame(f)
        bottom.pack(fill="x")
        ttk.Button(bottom, text="Renew (AI re-proof quiz)", command=self.renew).pack(side="left", padx=4)
        ttk.Button(bottom, text="Refresh", command=self.refresh_certs).pack(side="left", padx=4)
        ttk.Button(bottom, text="Demo: simulate expiry", command=self.expire).pack(side="left", padx=4)
        self.c_summary = ttk.Label(f, text="", wraplength=780, justify="left")
        self.c_summary.pack(fill="x", pady=6)
        self.c_tree.bind("<<TreeviewSelect>>", self.show_summary)

    def issue(self):
        if not self.c_student.get() or not self.c_course.get():
            messagebox.showwarning("Select first", "Choose a student and a course.")
            return
        try:
            cid = certificate.issue_certificate(pick_id(self.c_student.get()), pick_id(self.c_course.get()))
        except ValueError as e:
            messagebox.showerror("Cannot issue", str(e))
            return
        self.refresh_certs()
        messagebox.showinfo("Issued", f"Certificate ID: {cid}")

    def refresh_certs(self, sel_id=None):
        self.c_tree.delete(*self.c_tree.get_children())
        select_item = None
        for c in certificate.list_certificates():
            item = self.c_tree.insert("", "end", values=(c["cert_id"], c["student_name"], c["course_title"],
                                                  c["issued_on"], c["expires_on"], c["status"]),
                               tags=(c["status"],))
            if sel_id is not None and c["cert_id"] == sel_id:
                select_item = item
        if select_item:
            self.c_tree.selection_set(select_item)
            self.show_summary()

    def _sel_cert(self):
        sel = self.c_tree.selection()
        if not sel:
            messagebox.showwarning("Select first", "Select a certificate in the list.")
            return None
        return int(self.c_tree.item(sel[0])["values"][0])

    def show_summary(self, _event=None):
        sel = self.c_tree.selection()
        if sel:
            c = certificate.get_certificate(int(self.c_tree.item(sel[0])["values"][0]))
            self.c_summary.config(text="Proof summary: " + (c["summary"] if c else ""))
        else:
            self.c_summary.config(text="")

    def renew(self):
        cid = self._sel_cert()
        if cid is None:
            return
        status = certificate.verify_certificate(cid)
        if status == "TAMPERED":
            messagebox.showerror("Tampered", "This certificate failed verification and cannot be renewed.")
            return
        if status == "NOT_FOUND":
            messagebox.showerror("Not found", "Certificate does not exist.")
            return
        QuizWindow(self, cid)

    def expire(self):
        cid = self._sel_cert()
        if cid is not None:
            certificate.simulate_expiry(cid)
            self.refresh_certs(sel_id=cid)

    # ---------- Verify tab ----------
    def build_verify(self):
        f = ttk.Frame(self.nb, padding=20)
        self.nb.add(f, text="Verify")
        ttk.Label(f, text="Certificate ID").pack()
        self.v_id = tk.StringVar()
        e = ttk.Entry(f, textvariable=self.v_id, width=12, justify="center")
        e.pack(pady=6)
        e.bind("<Return>", lambda _e: self.verify())
        ttk.Button(f, text="Verify", command=self.verify).pack()
        self.v_result = tk.Label(f, text="", font=("Segoe UI", 32, "bold"))
        self.v_result.pack(pady=18)
        self.v_reason = ttk.Label(f, text="", wraplength=700, justify="center")
        self.v_reason.pack()
        self.v_detail = ttk.Label(f, text="", wraplength=700, justify="left")
        self.v_detail.pack(pady=12)

    def verify(self):
        try:
            cid = int(self.v_id.get())
        except ValueError:
            messagebox.showwarning("Bad ID", "Enter a numeric certificate ID.")
            return
        r = certificate.check(cid)
        self.v_result.config(text=r["status"], fg=COLORS.get(r["status"], "#000000"))
        self.v_reason.config(text=r["reason"])
        c = certificate.get_certificate(cid)
        self.v_detail.config(text="" if not c else
                             f"{c['student_name']} | {c['course_title']}\nIssued {c['issued_on']}  |  "
                             f"Last proven {c['last_proven_on']}\nProof summary: {c['summary']}\n"
                             f"Hash: {c['cert_hash'][:24]}...  Previous: {c['prev_hash'][:24]}...")

    # ---------- Reports tab ----------
    def build_reports(self):
        f = ttk.Frame(self.nb, padding=10)
        self.nb.add(f, text="Reports")
        top = ttk.Frame(f)
        top.pack(fill="x")
        ttk.Button(top, text="Student performance", command=self.show_student_performance).pack(side="left", padx=4)
        ttk.Button(top, text="Course completion", command=self.show_course_completion).pack(side="left", padx=4)
        cols = [(c, 160) for c in reports.STUDENT_PERFORMANCE_COLUMNS]
        self.r_tree = make_tree(f, cols, 14)

    def _display_report(self, columns, rows):
        self.r_tree.delete(*self.r_tree.get_children())
        self.r_tree["columns"] = columns
        for c in columns:
            self.r_tree.heading(c, text=c)
            self.r_tree.column(c, width=160, anchor="w")
        for row in rows:
            self.r_tree.insert("", "end", values=row)

    def show_student_performance(self):
        self._display_report(reports.STUDENT_PERFORMANCE_COLUMNS, reports.student_performance())

    def show_course_completion(self):
        self._display_report(reports.COURSE_COMPLETION_COLUMNS, reports.course_completion())


class QuizWindow(tk.Toplevel):
    """Re-proof quiz: one question at a time, then renew."""
    def __init__(self, app, cert_id):
        super().__init__(app)
        self.app, self.cert_id = app, cert_id
        self.cert = certificate.get_certificate(cert_id)
        self.title("Re-proof Quiz")
        self.geometry("660x420")
        self.transient(app)
        self.grab_set()
        self.head = ttk.Label(self, text="Generating quiz...", font=("Segoe UI", 11, "bold"))
        self.head.pack(pady=10)
        self.update()
        self.questions, self.source = ai_examiner.generate_quiz(self.cert["course_id"])
        if not self.questions:
            messagebox.showerror("No questions", "No questions available for this course.")
            self.destroy()
            return
        self.i, self.picked = 0, []
        self.choice = tk.IntVar(value=-1)
        self.qlabel = ttk.Label(self, wraplength=600, font=("Segoe UI", 11))
        self.qlabel.pack(pady=8, padx=20, anchor="w")
        self.opts = ttk.Frame(self)
        self.opts.pack(anchor="w", padx=30)
        self.btn = ttk.Button(self, command=self.next)
        self.btn.pack(pady=16)
        self.show()

    def show(self):
        q = self.questions[self.i]
        self.head.config(text=f"{self.cert['course_title']}  -  Question {self.i + 1} of {len(self.questions)}"
                              f"   [{self.source}]")
        self.qlabel.config(text=q["question"])
        for w in self.opts.winfo_children():
            w.destroy()
        self.choice.set(-1)
        for idx, text in enumerate(q["options"]):
            ttk.Radiobutton(self.opts, text=text, value=idx, variable=self.choice).pack(anchor="w", pady=2)
        self.btn.config(text="Submit" if self.i == len(self.questions) - 1 else "Next")

    def next(self):
        if self.choice.get() < 0:
            messagebox.showwarning("Pick one", "Select an answer first.")
            return
        self.picked.append(self.choice.get())
        self.i += 1
        if self.i < len(self.questions):
            self.show()
        else:
            self.finish()

    def finish(self):
        score = sum(p == q["answer"] for p, q in zip(self.picked, self.questions))
        missed = [q["question"] for p, q in zip(self.picked, self.questions) if p != q["answer"]]
        total = len(self.questions)
        self.head.config(text="Writing proof summary...")
        self.update()
        summary = ai_examiner.write_summary(self.cert["student_name"], self.cert["course_title"], score, total, missed)
        passed = certificate.renew_certificate(self.cert_id, score, total, summary, self.questions)
        if passed:
            messagebox.showinfo("Passed", f"Score {score}/{total}. Certificate renewed.\n\n{summary}")
        else:
            messagebox.showwarning("Not passed", f"Score {score}/{total}. Pass mark is "
                                   f"{int(certificate.PASS_MARK * 100)}%. Certificate not renewed.")
        self.app.refresh_certs(sel_id=self.cert_id)
        if self.winfo_exists():
            self.destroy()
