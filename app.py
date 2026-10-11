import os
import json
import logging
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
from config import SECRET_KEY, EVIDENCE_UPLOAD_DIR
from database import init_db, seed_sample_data, get_db_connection
import models
from proctoring.frame_analyzer import FrameAnalyzer

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = SECRET_KEY

# Ensure evidence directory exists
os.makedirs(EVIDENCE_UPLOAD_DIR, exist_ok=True)

# Initialize Computer Vision frame analyzer singleton
analyzer = FrameAnalyzer()

# Initialize database schema and benchmark seed data
init_db()
seed_sample_data()


# ==========================================
# PUBLIC & STUDENT ROUTES
# ==========================================

@app.route("/")
def index():
    """Landing Page"""
    return render_template("index.html")


@app.route("/student/portal")
def student_portal():
    """Student entrance: select active exam and enter details."""
    exams = models.get_active_exams()
    return render_template("student/portal.html", exams=exams)


@app.route("/student/start", methods=["POST"])
def start_student_session():
    """Validates student roll number/name, creates or fetches submission, redirects to exam room."""
    full_name = request.form.get("full_name", "").strip()
    roll_number = request.form.get("roll_number", "").strip().upper()
    email = request.form.get("email", "").strip()
    exam_id = request.form.get("exam_id")

    if not full_name or not roll_number or not exam_id:
        flash("Please provide your full name, roll number, and select an exam.", "danger")
        return redirect(url_for("student_portal"))

    # Register or fetch student
    student = models.get_or_create_student(full_name, roll_number, email or f"{roll_number.lower()}@exam.edu")
    
    # Create or resume submission session
    sub = models.create_submission(int(exam_id), student["id"])

    # If exam already completed, redirect to results
    if sub["status"] == "SUBMITTED":
        flash("You have already completed this examination.", "info")
        return redirect(url_for("exam_result", submission_id=sub["id"]))

    session["student_id"] = student["id"]
    session["submission_id"] = sub["id"]

    return redirect(url_for("exam_room", submission_id=sub["id"]))


@app.route("/student/exam/<int:submission_id>")
def exam_room(submission_id):
    """The proctored exam hall interface."""
    sub = models.get_submission(submission_id)
    if not sub:
        flash("Exam session not found.", "danger")
        return redirect(url_for("student_portal"))

    if sub["status"] == "SUBMITTED":
        return redirect(url_for("exam_result", submission_id=submission_id))

    exam = models.get_exam_by_id(sub["exam_id"])
    questions = models.get_questions_by_exam(sub["exam_id"])

    # Calculate remaining time if needed
    duration_minutes = exam["duration_minutes"]

    return render_template(
        "student/exam_room.html",
        submission=sub,
        exam=exam,
        questions=questions,
        duration_minutes=duration_minutes
    )


@app.route("/student/result/<int:submission_id>")
def exam_result(submission_id):
    """Post-submission scorecard and integrity review."""
    report_data = models.get_submission_report(submission_id)
    if not report_data:
        flash("Submission report not found.", "danger")
        return redirect(url_for("student_portal"))

    return render_template("student/exam_result.html", data=report_data)


# ==========================================
# PROCTOR / ADMIN ROUTES
# ==========================================

@app.route("/admin")
def admin_dashboard():
    """Executive Proctoring Dashboard with violation breakdown and statistics."""
    metrics = models.get_admin_dashboard_metrics()
    return render_template("admin/dashboard.html", metrics=metrics)


@app.route("/admin/exams")
def admin_exams():
    """List all exams and candidate counts."""
    exams = models.get_all_exams()
    return render_template("admin/exams.html", exams=exams)


@app.route("/admin/exams/create", methods=["GET", "POST"])
def admin_create_exam():
    """Create new proctored exam and questions."""
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        subject = request.form.get("subject", "").strip()
        duration = int(request.form.get("duration_minutes", 15))
        passing_score = int(request.form.get("passing_score", 50))
        instructions = request.form.get("instructions", "").strip()

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO exams (title, subject, duration_minutes, passing_score, instructions)
            VALUES (?, ?, ?, ?, ?)
        """, (title, subject, duration, passing_score, instructions))
        exam_id = cursor.lastrowid

        # Insert question items
        q_count = int(request.form.get("question_count", 0))
        for i in range(1, q_count + 1):
            q_text = request.form.get(f"q_text_{i}", "").strip()
            if not q_text:
                continue
            opt_a = request.form.get(f"opt_a_{i}", "").strip()
            opt_b = request.form.get(f"opt_b_{i}", "").strip()
            opt_c = request.form.get(f"opt_c_{i}", "").strip()
            opt_d = request.form.get(f"opt_d_{i}", "").strip()
            correct = request.form.get(f"correct_{i}", "A").strip().upper()
            points = int(request.form.get(f"points_{i}", 1))

            cursor.execute("""
                INSERT INTO questions (exam_id, question_text, option_a, option_b, option_c, option_d, correct_option, points)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (exam_id, q_text, opt_a, opt_b, opt_c, opt_d, correct, points))

        conn.commit()
        conn.close()
        flash("Exam created successfully!", "success")
        return redirect(url_for("admin_exams"))

    return render_template("admin/create_exam.html")


@app.route("/admin/report/<int:submission_id>")
def admin_student_report(submission_id):
    """Detailed candidate audit report with computer vision evidence gallery."""
    report_data = models.get_submission_report(submission_id)
    if not report_data:
        flash("Report not found.", "danger")
        return redirect(url_for("admin_dashboard"))

    return render_template("admin/student_report.html", data=report_data)


@app.route("/admin/live")
def admin_live_monitor():
    """Live multi-candidate proctoring view."""
    active_sessions = models.get_live_active_sessions()
    return render_template("admin/live_monitor.html", active_sessions=active_sessions)


# ==========================================
# REST API (CV & SECURITY)
# ==========================================

@app.route("/api/proctor/analyze_frame", methods=["POST"])
def api_analyze_frame():
    """
    Receives webcam frame in Base64 from client, executes FaceLandmarker CV pipeline,
    records any violations in SQLite, and returns HUD overlay frame + telemetry.
    """
    try:
        data = request.get_json(silent=True) or {}
        image_b64 = data.get("image")
        submission_id = data.get("submission_id")

        if not image_b64 or not submission_id:
            return jsonify({"status": "ERROR", "message": "Missing image or submission_id"}), 400

        sub = models.get_submission(submission_id)
        if not sub:
            return jsonify({"status": "ERROR", "message": "Submission session not found"}), 404

        # Decode BGR image
        bgr_frame = analyzer.decode_base64_image(image_b64)
        if bgr_frame is None:
            return jsonify({"status": "ERROR", "message": "Could not decode image"}), 400

        # Run Computer Vision analysis
        cv_result = analyzer.analyze_frame(bgr_frame, session_id=str(submission_id))

        # If violations occurred, persist them to database
        if cv_result.get("violations"):
            for v in cv_result["violations"]:
                models.record_violation(
                    submission_id=sub["id"],
                    exam_id=sub["exam_id"],
                    student_id=sub["student_id"],
                    violation_type=v["type"],
                    severity=v["severity"],
                    details=v["details"],
                    evidence_path=cv_result.get("evidence_path")
                )

        # Re-fetch updated submission stats
        updated_sub = models.get_submission(submission_id)

        return jsonify({
            "status": cv_result["status"],
            "face_count": cv_result["face_count"],
            "head_pose": cv_result["head_pose"],
            "gaze_direction": cv_result["gaze_direction"],
            "gaze_reason": cv_result["gaze_reason"],
            "violations": cv_result["violations"],
            "annotated_frame": cv_result["annotated_frame"],
            "integrity_score": updated_sub["integrity_score"],
            "total_violations": updated_sub["total_violations"]
        })

    except Exception as e:
        logger.error(f"Error in api_analyze_frame: {e}", exc_info=True)
        return jsonify({"status": "ERROR", "message": str(e)}), 500


@app.route("/api/proctor/log_activity", methods=["POST"])
def api_log_activity():
    """
    Receives system security violation events from student browser
    (Tab switch, exiting full screen, developer tools attempt, copy/paste).
    """
    try:
        data = request.get_json(silent=True) or {}
        submission_id = data.get("submission_id")
        event_type = data.get("event_type", "SECURITY_ALERT")
        details = data.get("details", "")

        if not submission_id:
            return jsonify({"status": "ERROR", "message": "Missing submission_id"}), 400

        sub = models.get_submission(submission_id)
        if not sub:
            return jsonify({"status": "ERROR", "message": "Submission session not found"}), 404

        # Map event type to violation severity
        severity_map = {
            "TAB_SWITCH": ("HIGH", "Browser tab or window lost focus"),
            "FULLSCREEN_EXIT": ("HIGH", "Exited enforced full screen mode"),
            "DEVTOOLS_ATTEMPT": ("HIGH", "Attempted to inspect page or open developer console"),
            "COPY_PASTE_ATTEMPT": ("MEDIUM", "Attempted clipboard action (copy / paste)")
        }

        sev, default_desc = severity_map.get(event_type, ("LOW", "Suspicious client activity"))
        actual_details = details if details else default_desc

        models.record_violation(
            submission_id=sub["id"],
            exam_id=sub["exam_id"],
            student_id=sub["student_id"],
            violation_type=event_type,
            severity=sev,
            details=actual_details,
            evidence_path=None
        )

        models.record_activity_log(submission_id, event_type, actual_details)
        updated_sub = models.get_submission(submission_id)

        return jsonify({
            "status": "OK",
            "integrity_score": updated_sub["integrity_score"],
            "total_violations": updated_sub["total_violations"]
        })

    except Exception as e:
        logger.error(f"Error in api_log_activity: {e}", exc_info=True)
        return jsonify({"status": "ERROR", "message": str(e)}), 500


@app.route("/api/student/submit_exam", methods=["POST"])
def api_submit_exam():
    """Receives candidate's final submitted answers and computes exam score."""
    try:
        data = request.get_json(silent=True) or {}
        submission_id = data.get("submission_id")
        answers = data.get("answers", {})

        if not submission_id:
            return jsonify({"status": "ERROR", "message": "Missing submission_id"}), 400

        sub = models.submit_exam(submission_id, answers)
        if not sub:
            return jsonify({"status": "ERROR", "message": "Submission not found"}), 404

        return jsonify({
            "status": "SUCCESS",
            "score": sub["score"],
            "total_points": sub["total_points"],
            "integrity_score": sub["integrity_score"],
            "redirect_url": url_for("exam_result", submission_id=submission_id)
        })

    except Exception as e:
        logger.error(f"Error in api_submit_exam: {e}", exc_info=True)
        return jsonify({"status": "ERROR", "message": str(e)}), 500


@app.route("/api/admin/metrics")
def api_admin_metrics():
    """Returns analytics data for real-time dashboard charts."""
    metrics = models.get_admin_dashboard_metrics()
    return jsonify(metrics)


if __name__ == "__main__":
    print("\n=======================================================")
    print("   INTELLIGENT ONLINE EXAMINATION & PROCTORING SYSTEM   ")
    print("   Tech Stack: Python, OpenCV, MediaPipe, Flask, SQLite ")
    print("=======================================================")
    print("Server starting at http://127.0.0.1:5000 ...\n")
    app.run(host="0.0.0.0", port=5000, debug=True)
