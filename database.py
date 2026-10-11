import sqlite3
import os
import json
from datetime import datetime, timedelta
from config import DATABASE_PATH

def get_db_connection():
    """Returns a thread-safe connection with sqlite3.Row row factory."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db():
    """Initializes the SQLite schema."""
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.executescript("""
    CREATE TABLE IF NOT EXISTS exams (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        subject TEXT NOT NULL,
        duration_minutes INTEGER NOT NULL DEFAULT 15,
        passing_score INTEGER NOT NULL DEFAULT 50,
        instructions TEXT,
        is_active INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS questions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        exam_id INTEGER NOT NULL,
        question_text TEXT NOT NULL,
        option_a TEXT NOT NULL,
        option_b TEXT NOT NULL,
        option_c TEXT NOT NULL,
        option_d TEXT NOT NULL,
        correct_option TEXT NOT NULL,
        points INTEGER DEFAULT 1,
        FOREIGN KEY (exam_id) REFERENCES exams (id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        full_name TEXT NOT NULL,
        roll_number TEXT UNIQUE NOT NULL,
        email TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS submissions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        exam_id INTEGER NOT NULL,
        student_id INTEGER NOT NULL,
        start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        submit_time TIMESTAMP,
        score REAL DEFAULT 0.0,
        total_points REAL DEFAULT 0.0,
        answers_json TEXT DEFAULT '{}',
        status TEXT DEFAULT 'IN_PROGRESS',
        integrity_score REAL DEFAULT 100.0,
        total_violations INTEGER DEFAULT 0,
        FOREIGN KEY (exam_id) REFERENCES exams (id) ON DELETE CASCADE,
        FOREIGN KEY (student_id) REFERENCES students (id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS violations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        submission_id INTEGER NOT NULL,
        exam_id INTEGER NOT NULL,
        student_id INTEGER NOT NULL,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        violation_type TEXT NOT NULL,
        severity TEXT NOT NULL,
        details TEXT,
        evidence_path TEXT,
        FOREIGN KEY (submission_id) REFERENCES submissions (id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS activity_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        submission_id INTEGER NOT NULL,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        event_type TEXT NOT NULL,
        details TEXT,
        FOREIGN KEY (submission_id) REFERENCES submissions (id) ON DELETE CASCADE
    );
    """)

    conn.commit()
    conn.close()

def seed_sample_data():
    """Seeds sample exams, questions, and an audit demo if the database is empty."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Check if exams already exist
    cursor.execute("SELECT COUNT(*) as count FROM exams")
    if cursor.fetchone()["count"] > 0:
        conn.close()
        return

    print("[Database] Seeding initial exams and benchmark curriculum...")

    # Exam 1: Cybersecurity & Operating Systems
    cursor.execute("""
    INSERT INTO exams (title, subject, duration_minutes, passing_score, instructions)
    VALUES (?, ?, ?, ?, ?)
    """, (
        "Computer Systems & Network Security",
        "Cybersecurity & Distributed Systems",
        15,
        60,
        "Proctored Examination Instructions: Webcam and microphone access are strictly required. Do not look away from the screen, switch browser tabs, or attempt copy-pasting. AI vision monitors gaze, head pose, and candidate presence in real time."
    ))
    exam1_id = cursor.lastrowid

    questions_exam1 = [
        (
            exam1_id,
            "Which symmetric cryptographic cipher operates on 128-bit blocks using substitution-permutation networks?",
            "DES (Data Encryption Standard)",
            "AES (Advanced Encryption Standard)",
            "RSA Public Key Algorithm",
            "Diffie-Hellman Key Exchange",
            "B", 2
        ),
        (
            exam1_id,
            "In TCP three-way handshake connection establishment, what flags are transmitted in the second segment?",
            "SYN only",
            "ACK only",
            "SYN-ACK",
            "FIN-ACK",
            "C", 2
        ),
        (
            exam1_id,
            "Which memory protection mechanism marks memory regions (like the stack) as non-executable to prevent code injection?",
            "Address Space Layout Randomization (ASLR)",
            "Data Execution Prevention (DEP / NX Bit)",
            "Stack Canary Protection",
            "Virtual Memory Paging",
            "B", 2
        ),
        (
            exam1_id,
            "Which transport layer protocol is connectionless, minimizes latency, and is preferred for real-time video streaming?",
            "TCP",
            "UDP",
            "SCTP",
            "BGP",
            "B", 2
        ),
        (
            exam1_id,
            "What type of attack involves an attacker tricking a victim's browser into executing malicious JavaScript inside the session?",
            "SQL Injection (SQLi)",
            "Cross-Site Scripting (XSS)",
            "Buffer Overflow",
            "Man-in-the-Middle (MitM)",
            "B", 2
        ),
        (
            exam1_id,
            "Which consensus algorithm relies on cryptographic puzzles and computational work to secure distributed ledgers?",
            "Proof of Stake (PoS)",
            "Proof of Authority (PoA)",
            "Proof of Work (PoW)",
            "Raft Consensus",
            "C", 2
        )
    ]

    for q in questions_exam1:
        cursor.execute("""
        INSERT INTO questions (exam_id, question_text, option_a, option_b, option_c, option_d, correct_option, points)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, q)

    # Exam 2: AI & Data Structures
    cursor.execute("""
    INSERT INTO exams (title, subject, duration_minutes, passing_score, instructions)
    VALUES (?, ?, ?, ?, ?)
    """, (
        "Algorithms & Computer Vision Fundamentals",
        "Artificial Intelligence & Software Engineering",
        20,
        50,
        "Proctored Examination Instructions: AI Vision Proctoring is active. Looking away, dual monitors, or leaving the screen will incur penalties on your Integrity Index."
    ))
    exam2_id = cursor.lastrowid

    questions_exam2 = [
        (
            exam2_id,
            "What is the average time complexity of searching for an element in a balanced Binary Search Tree (AVL or Red-Black)?",
            "O(1)",
            "O(log N)",
            "O(N)",
            "O(N log N)",
            "B", 2
        ),
        (
            exam2_id,
            "In Computer Vision, which algorithm is commonly used for estimating 3D object pose from known 3D-to-2D point correspondences?",
            "Perspective-n-Point (PnP / solvePnP)",
            "K-Means Clustering",
            "Dijkstra Shortest Path",
            "Fast Fourier Transform (FFT)",
            "A", 2
        ),
        (
            exam2_id,
            "Which activation function suffers from vanishing gradient problems when inputs are large positive or negative values?",
            "Rectified Linear Unit (ReLU)",
            "Sigmoid Function",
            "Leaky ReLU",
            "Linear",
            "B", 2
        ),
        (
            exam2_id,
            "Which graph traversal algorithm explores the deepest nodes first and can be implemented using a Stack?",
            "Breadth-First Search (BFS)",
            "Depth-First Search (DFS)",
            "Prim's Algorithm",
            "Kruskal's Algorithm",
            "B", 2
        ),
        (
            exam2_id,
            "What facial landmark index typically corresponds to the nose tip in the canonical 468/478 MediaPipe Face Mesh model?",
            "Landmark 0",
            "Landmark 1",
            "Landmark 33",
            "Landmark 152",
            "B", 2
        )
    ]

    for q in questions_exam2:
        cursor.execute("""
        INSERT INTO questions (exam_id, question_text, option_a, option_b, option_c, option_d, correct_option, points)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, q)

    # Seed Sample Students
    cursor.execute("""
    INSERT INTO students (full_name, roll_number, email)
    VALUES (?, ?, ?)
    """, ("Alex Mercer", "ENG-2026-081", "alex.mercer@engineering.edu"))
    student1_id = cursor.lastrowid

    cursor.execute("""
    INSERT INTO students (full_name, roll_number, email)
    VALUES (?, ?, ?)
    """, ("Samantha Reed", "ENG-2026-104", "samantha.reed@engineering.edu"))
    student2_id = cursor.lastrowid

    # Seed a Completed Audit Submission for Student 1 to showcase the Proctoring Report
    start_time = datetime.now() - timedelta(minutes=45)
    submit_time = start_time + timedelta(minutes=14, seconds=20)

    cursor.execute("""
    INSERT INTO submissions (
        exam_id, student_id, start_time, submit_time, score, total_points,
        answers_json, status, integrity_score, total_violations
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        exam1_id,
        student1_id,
        start_time.strftime("%Y-%m-%d %H:%M:%S"),
        submit_time.strftime("%Y-%m-%d %H:%M:%S"),
        10.0,
        12.0,
        json.dumps({"1": "B", "2": "C", "3": "B", "4": "B", "5": "B", "6": "A"}),
        "SUBMITTED",
        73.0,  # Moderate risk due to violations
        4
    ))
    submission1_id = cursor.lastrowid

    # Seed realistic violations for student 1
    sample_violations = [
        (
            submission1_id, exam1_id, student1_id,
            (start_time + timedelta(minutes=3, seconds=12)).strftime("%Y-%m-%d %H:%M:%S"),
            "LOOKING_AWAY", "MEDIUM",
            "Head turned right (Yaw: 28.4°) sustained for 2.4s", None
        ),
        (
            submission1_id, exam1_id, student1_id,
            (start_time + timedelta(minutes=7, seconds=45)).strftime("%Y-%m-%d %H:%M:%S"),
            "TAB_SWITCH", "HIGH",
            "Switched browser tab / active window lost focus", None
        ),
        (
            submission1_id, exam1_id, student1_id,
            (start_time + timedelta(minutes=11, seconds=20)).strftime("%Y-%m-%d %H:%M:%S"),
            "FACE_MISSING", "HIGH",
            "Candidate face not detected for >3.0 seconds", None
        ),
        (
            submission1_id, exam1_id, student1_id,
            (start_time + timedelta(minutes=12, seconds=50)).strftime("%Y-%m-%d %H:%M:%S"),
            "SUSPICIOUS_GAZE", "LOW",
            "Gaze shifted down towards desk surface", None
        )
    ]

    for v in sample_violations:
        cursor.execute("""
        INSERT INTO violations (submission_id, exam_id, student_id, timestamp, violation_type, severity, details, evidence_path)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, v)

    # Seed Activity Logs
    cursor.execute("""
    INSERT INTO activity_logs (submission_id, timestamp, event_type, details)
    VALUES (?, ?, ?, ?)
    """, (submission1_id, start_time.strftime("%Y-%m-%d %H:%M:%S"), "EXAM_STARTED", "Exam session initiated in full screen mode"))

    conn.commit()
    conn.close()
    print("[Database] Database initialized and seeded successfully.")
