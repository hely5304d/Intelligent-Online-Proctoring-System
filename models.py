import json
from datetime import datetime
from database import get_db_connection
from config import INTEGRITY_PENALTIES

def get_active_exams():
    conn = get_db_connection()
    exams = conn.execute("""
        SELECT e.*, COUNT(q.id) as question_count 
        FROM exams e
        LEFT JOIN questions q ON e.id = q.exam_id
        WHERE e.is_active = 1
        GROUP BY e.id
        ORDER BY e.id DESC
    """).fetchall()
    conn.close()
    return [dict(e) for e in exams]

def get_all_exams():
    conn = get_db_connection()
    exams = conn.execute("""
        SELECT e.*, COUNT(q.id) as question_count,
        (SELECT COUNT(*) FROM submissions s WHERE s.exam_id = e.id) as candidate_count
        FROM exams e
        LEFT JOIN questions q ON e.id = q.exam_id
        GROUP BY e.id
        ORDER BY e.id DESC
    """).fetchall()
    conn.close()
    return [dict(e) for e in exams]

def get_exam_by_id(exam_id):
    conn = get_db_connection()
    exam = conn.execute("SELECT * FROM exams WHERE id = ?", (exam_id,)).fetchone()
    conn.close()
    return dict(exam) if exam else None

def get_questions_by_exam(exam_id):
    conn = get_db_connection()
    questions = conn.execute("""
        SELECT * FROM questions WHERE exam_id = ? ORDER BY id ASC
    """, (exam_id,)).fetchall()
    conn.close()
    return [dict(q) for q in questions]

def get_or_create_student(full_name, roll_number, email):
    conn = get_db_connection()
    cursor = conn.cursor()
    student = cursor.execute("SELECT * FROM students WHERE roll_number = ?", (roll_number,)).fetchone()
    if not student:
        cursor.execute("""
            INSERT INTO students (full_name, roll_number, email) VALUES (?, ?, ?)
        """, (full_name, roll_number, email))
        conn.commit()
        student_id = cursor.lastrowid
        student = cursor.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone()
    conn.close()
    return dict(student)

def create_submission(exam_id, student_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    # Check for existing in-progress session
    existing = cursor.execute("""
        SELECT * FROM submissions 
        WHERE exam_id = ? AND student_id = ? AND status = 'IN_PROGRESS'
        ORDER BY id DESC LIMIT 1
    """, (exam_id, student_id)).fetchone()
    
    if existing:
        conn.close()
        return dict(existing)

    cursor.execute("""
        INSERT INTO submissions (exam_id, student_id, start_time, status, integrity_score, total_violations)
        VALUES (?, ?, CURRENT_TIMESTAMP, 'IN_PROGRESS', 100.0, 0)
    """, (exam_id, student_id))
    conn.commit()
    sub_id = cursor.lastrowid
    sub = cursor.execute("SELECT * FROM submissions WHERE id = ?", (sub_id,)).fetchone()
    conn.close()
    return dict(sub)

def get_submission(submission_id):
    conn = get_db_connection()
    sub = conn.execute("""
        SELECT s.*, e.title as exam_title, e.duration_minutes, e.passing_score,
               st.full_name as student_name, st.roll_number, st.email as student_email
        FROM submissions s
        JOIN exams e ON s.exam_id = e.id
        JOIN students st ON s.student_id = st.id
        WHERE s.id = ?
    """, (submission_id,)).fetchone()
    conn.close()
    return dict(sub) if sub else None

def record_violation(submission_id, exam_id, student_id, violation_type, severity, details, evidence_path=None):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO violations (submission_id, exam_id, student_id, timestamp, violation_type, severity, details, evidence_path)
        VALUES (?, ?, ?, CURRENT_TIMESTAMP, ?, ?, ?, ?)
    """, (submission_id, exam_id, student_id, violation_type, severity, details, evidence_path))

    # Calculate deduction
    penalty = INTEGRITY_PENALTIES.get(violation_type, 5)

    cursor.execute("""
        UPDATE submissions 
        SET total_violations = total_violations + 1,
            integrity_score = MAX(0.0, integrity_score - ?)
        WHERE id = ?
    """, (penalty, submission_id))

    conn.commit()
    conn.close()

def record_activity_log(submission_id, event_type, details):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO activity_logs (submission_id, timestamp, event_type, details)
        VALUES (?, CURRENT_TIMESTAMP, ?, ?)
    """, (submission_id, event_type, details))
    conn.commit()
    conn.close()

def submit_exam(submission_id, answers_dict):
    conn = get_db_connection()
    cursor = conn.cursor()

    submission = cursor.execute("SELECT * FROM submissions WHERE id = ?", (submission_id,)).fetchone()
    if not submission:
        conn.close()
        return None

    exam_id = submission["exam_id"]
    questions = cursor.execute("SELECT * FROM questions WHERE exam_id = ?", (exam_id,)).fetchall()

    total_points = 0.0
    scored_points = 0.0

    for q in questions:
        q_id = str(q["id"])
        total_points += q["points"]
        student_ans = answers_dict.get(q_id, "").strip().upper()
        if student_ans == q["correct_option"].strip().upper():
            scored_points += q["points"]

    cursor.execute("""
        UPDATE submissions
        SET submit_time = CURRENT_TIMESTAMP,
            score = ?,
            total_points = ?,
            answers_json = ?,
            status = 'SUBMITTED'
        WHERE id = ?
    """, (scored_points, total_points, json.dumps(answers_dict), submission_id))

    conn.commit()
    updated = cursor.execute("SELECT * FROM submissions WHERE id = ?", (submission_id,)).fetchone()
    conn.close()
    return dict(updated)

def get_submission_report(submission_id):
    sub = get_submission(submission_id)
    if not sub:
        return None

    conn = get_db_connection()
    violations = conn.execute("""
        SELECT * FROM violations WHERE submission_id = ? ORDER BY id ASC
    """, (submission_id,)).fetchall()

    logs = conn.execute("""
        SELECT * FROM activity_logs WHERE submission_id = ? ORDER BY id ASC
    """, (submission_id,)).fetchall()

    questions = conn.execute("""
        SELECT * FROM questions WHERE exam_id = ? ORDER BY id ASC
    """, (sub["exam_id"],)).fetchall()

    conn.close()

    answers = json.loads(sub["answers_json"] or "{}")

    # Group violations by type
    violation_summary = {}
    for v in violations:
        v_type = v["violation_type"]
        violation_summary[v_type] = violation_summary.get(v_type, 0) + 1

    return {
        "submission": sub,
        "violations": [dict(v) for v in violations],
        "violation_summary": violation_summary,
        "activity_logs": [dict(l) for l in logs],
        "questions": [dict(q) for q in questions],
        "answers": answers
    }

def get_admin_dashboard_metrics():
    conn = get_db_connection()
    total_exams = conn.execute("SELECT COUNT(*) as c FROM exams").fetchone()["c"]
    total_candidates = conn.execute("SELECT COUNT(*) as c FROM students").fetchone()["c"]
    total_submissions = conn.execute("SELECT COUNT(*) as c FROM submissions").fetchone()["c"]
    total_violations = conn.execute("SELECT COUNT(*) as c FROM violations").fetchone()["c"]
    
    avg_integrity_row = conn.execute("SELECT AVG(integrity_score) as avg_score FROM submissions").fetchone()
    avg_integrity = round(avg_integrity_row["avg_score"] or 100.0, 1)

    recent_submissions = conn.execute("""
        SELECT s.*, e.title as exam_title, st.full_name, st.roll_number
        FROM submissions s
        JOIN exams e ON s.exam_id = e.id
        JOIN students st ON s.student_id = st.id
        ORDER BY s.id DESC LIMIT 8
    """).fetchall()

    recent_violations = conn.execute("""
        SELECT v.*, e.title as exam_title, st.full_name
        FROM violations v
        JOIN exams e ON v.exam_id = e.id
        JOIN students st ON v.student_id = st.id
        ORDER BY v.id DESC LIMIT 10
    """).fetchall()

    # Violation types breakdown
    v_breakdown = conn.execute("""
        SELECT violation_type, COUNT(*) as count
        FROM violations
        GROUP BY violation_type
        ORDER BY count DESC
    """).fetchall()

    conn.close()

    return {
        "total_exams": total_exams,
        "total_candidates": total_candidates,
        "total_submissions": total_submissions,
        "total_violations": total_violations,
        "avg_integrity": avg_integrity,
        "recent_submissions": [dict(s) for s in recent_submissions],
        "recent_violations": [dict(v) for v in recent_violations],
        "violation_breakdown": {r["violation_type"]: r["count"] for r in v_breakdown}
    }

def get_live_active_sessions():
    conn = get_db_connection()
    active = conn.execute("""
        SELECT s.*, e.title as exam_title, st.full_name, st.roll_number
        FROM submissions s
        JOIN exams e ON s.exam_id = e.id
        JOIN students st ON s.student_id = st.id
        WHERE s.status = 'IN_PROGRESS'
        ORDER BY s.id DESC
    """).fetchall()
    conn.close()
    return [dict(a) for a in active]
