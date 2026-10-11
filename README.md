# Intelligent Online Examination & AI Proctoring System

An engineering-grade online examination platform equipped with automated artificial intelligence proctoring, real-time computer vision cheat detection, and full-stack event tracking.

---

## 📌 Executive Summary

* **Project Title:** Intelligent Online Examination & Proctoring System
* **Level:** Engineering / Capstone
* **Tech Stack:** Python 3.13, OpenCV (`cv2`), MediaPipe (`FaceLandmarker`), Flask, SQLite, Vanilla JS, HTML5/CSS3, Chart.js
* **Core Concepts:** Face Detection, 3D Head Pose Estimation, Iris Gaze Tracking, Client Security Traps, Integrity Scoring, Forensic Evidence Archival
* **Engineering Value:** Computer Vision, System Security, Event Tracking & Forensic Auditing

---

## 🏛️ System Architecture

```
+-----------------------------------------------------------------------------------------+
|                                    CANDIDATE CLIENT                                     |
|  - WebRTC Video Stream Capture (640x480 @ 1.5s intervals)                               |
|  - Mandatory Enforced Fullscreen Mode API                                               |
|  - Page Visibility API & Window Blur (Tab Switch Traps)                                 |
|  - Keystroke & DevTools Interceptors (F12, Ctrl+Shift+I, Copy/Paste Prevention)         |
+-----------------------------------------------------------------------------------------+
                                      │  Base64 Frames & Security Events
                                      ▼
+-----------------------------------------------------------------------------------------+
|                                  FLASK CONTROLLER & REST API                            |
|  - /api/proctor/analyze_frame   : Dispatches frames to Computer Vision pipeline         |
|  - /api/proctor/log_activity    : Receives client security violation events             |
|  - /api/student/submit_exam     : Evaluates academic score & finalizes integrity        |
+-----------------------------------------------------------------------------------------+
                                      │
            ┌─────────────────────────┴────────────────────────┐
            ▼                                                  ▼
+------------------------------------+  +-------------------------------------------------+
|      COMPUTER VISION PIPELINE      |  |             SQLITE EVENT LEDGER                 |
|  1. MediaPipe FaceLandmarker:      |  |  - `exams`       : Catalog & benchmarks         |
|     - 478 3D Landmarks             |  |  - `questions`   : Multi-choice items & scoring |
|     - Iris Landmarks (468, 473)    |  |  - `students`    : Roll numbers & identities    |
|     - Multi-Face Presence Count    |  |  - `submissions` : Academic scores & integrity  |
|  2. OpenCV solvePnP:               |  |  - `violations`  : Timestamped forensic log     |
|     - Anthropometric 3D Head Model |  |  - `activity_logs`: Chronological telemetry     |
|     - Euler Angles (Yaw/Pitch/Roll)|  +-------------------------------------------------+
|  3. Temporal Streak Filter:        |                         │
|     - Suppresses momentary blinks  |                         │
|  4. Forensic Evidence Snapshots:   |                         ▼
|     - Saves JPEG frames on alert   |  +-------------------------------------------------+
+------------------------------------+  |           PROCTOR AUDIT & LIVE MONITOR          |
                                        |  - Real-Time Multi-Candidate Proctor Wall       |
                                        |  - Chart.js Violation Breakdown Analytics       |
                                        |  - Forensic Audit Report & Evidence Gallery     |
                                        +-------------------------------------------------+
```

---

## 🔬 Core Engineering Concepts

### 1. 3D Head Pose Estimation (`cv2.solvePnP`)
To determine if a candidate is looking away from their screen or down at unauthorized materials (such as a mobile phone or printed notes), the system establishes 3D-to-2D correspondences between an anthropometric 3D head model and 2D facial landmarks:
- **Nose Tip:** Landmark 1
- **Chin:** Landmark 152
- **Left Eye Outer Corner:** Landmark 33
- **Right Eye Outer Corner:** Landmark 263
- **Left Mouth Corner:** Landmark 61
- **Right Mouth Corner:** Landmark 291

Using `cv2.solvePnP(model_points, image_points, camera_matrix, dist_coeffs)`:
$$\mathbf{R}, \mathbf{t} = \text{solvePnP}(P_{3D}, p_{2D}, K)$$

The rotation vector $\mathbf{R}$ is transformed into a rotation matrix using the Rodrigues transformation (`cv2.Rodrigues`), which is then decomposed into Euler angles using `cv2.RQDecomp3x3`:
* **Yaw ($Y$):** Horizontal head turn (threshold: $|Y| > 22^\circ$)
* **Pitch ($P$):** Vertical head tilt (threshold: $P < -18^\circ$ for looking down, $P > 22^\circ$ for looking up)
* **Roll ($R$):** Side-to-side head tilt

### 2. Iris Gaze Tracking
When a candidate attempts to look sideways at notes or another monitor without turning their head, the **Iris Gaze Tracker** computes the horizontal iris displacement relative to the inner and outer eye corners:
$$\text{Iris Ratio} = \frac{x_{\text{iris}} - \min(x_{\text{inner}}, x_{\text{outer}})}{|x_{\text{inner}} - x_{\text{outer}}|}$$
* $\text{Ratio} < 0.35$: Suspicious eye gaze shifted to the left (`GAZE_LEFT`)
* $\text{Ratio} > 0.65$: Suspicious eye gaze shifted to the right (`GAZE_RIGHT`)

### 3. Face Count & Presence Verification
* **Face Count = 0 (`FACE_MISSING`):** Candidate left the camera's field of view.
* **Face Count > 1 (`MULTIPLE_FACES`):** Unauthorized secondary person detected in the test environment.
* **Face Count = 1 (`NORMAL`):** Single authenticated candidate verified.

### 4. Client-Side Security Enforcements
* **Enforced Fullscreen:** Mandatory `requestFullscreen()` barrier before questions unlock. If fullscreen is exited, questions are blocked and a `FULLSCREEN_EXIT` violation is logged.
* **Page Visibility & Window Blur:** Traps `document.onvisibilitychange` and `window.onblur` to intercept tab switching or minimizing the browser (`TAB_SWITCH`).
* **Keystroke Interceptor:** Disables developer tools shortcuts (`F12`, `Ctrl+Shift+I`, `Ctrl+Shift+J`, `Ctrl+U`), and clipboard commands (`Ctrl+C`, `Ctrl+V`, `Ctrl+X`).
* **Right-Click Context Menu Suppression:** Prevents inspect element or external search.

### 5. Dynamic Integrity Index
Every candidate begins with a **100% Integrity Score**. Violations deduct points based on severity:

| Violation Code | Severity | Penalty | Description |
| :--- | :---: | :---: | :--- |
| `MULTIPLE_FACES` | HIGH | -15% | Additional unauthorized face in frame |
| `FACE_MISSING` | HIGH | -12% | Candidate absent from webcam feed |
| `TAB_SWITCH` | HIGH | -12% | Browser tab switched or window blurred |
| `FULLSCREEN_EXIT` | HIGH | -10% | Exited enforced full-screen mode |
| `DEVTOOLS_ATTEMPT` | HIGH | -15% | Attempted inspect element or F12 |
| `LOOKING_AWAY` | MEDIUM | -5% | Head turned beyond threshold angles |
| `SUSPICIOUS_GAZE` | MEDIUM | -4% | Eyes averted from monitor |
| `COPY_PASTE_ATTEMPT`| MEDIUM | -5% | Attempted clipboard action |

**Integrity Classifications:**
* **85% - 100%:** High Integrity (Verified Clean)
* **65% - 84%:** Moderate Risk (Discretionary Manual Review)
* **Below 65%:** High Risk / Disqualified (Integrity Breach)

---

## 📂 Project Directory Structure

```
Intelligent-Online-Proctoring-System/
├── app.py                      # Flask Application Controller & REST API
├── config.py                   # System thresholds, penalties & paths
├── database.py                 # SQLite schema creation & benchmark seed data
├── models.py                   # Data queries, score calculations & analytics
├── requirements.txt            # Python dependencies
├── run.bat                     # Windows 1-click startup script
├── models_cache/
│   └── face_landmarker.task    # Google MediaPipe 478 FaceLandmarker model
├── proctoring/
│   ├── __init__.py
│   ├── model_loader.py         # Singleton model manager with auto-download
│   ├── face_detector.py        # Face count & presence analysis
│   ├── gaze_tracker.py         # 3D Head Pose (PnP) & Iris gaze tracking
│   └── frame_analyzer.py       # Computer Vision orchestrator & HUD renderer
├── static/
│   ├── css/
│   │   ├── main.css            # Dark theme styles, cards, tables, badges
│   │   └── exam.css            # Exam room layout, HUD sidebar, modals
│   ├── js/
│   │   └── exam_proctor.js     # WebRTC capture, event traps & frame dispatch
│   └── uploads/
│       └── evidence/           # Violation snapshot JPEG storage
└── templates/
    ├── base.html               # Base layout with navbar and alerts
    ├── index.html              # Landing page and architectural summary
    ├── student/
    │   ├── portal.html         # Candidate registration & exam selection
    │   ├── exam_room.html      # Proctored exam room with live HUD & questions
    │   └── exam_result.html    # Post-exam scorecard & integrity audit
    └── admin/
        ├── dashboard.html      # Proctor overview, KPI metrics & charts
        ├── exams.html          # Exam catalog & candidate tallies
        ├── create_exam.html    # Interactive exam & question builder
        ├── student_report.html # Forensic candidate audit & evidence gallery
        └── live_monitor.html   # Live multi-candidate proctoring wall
```

---

## 🚀 Getting Started

### 1. Prerequisites
Ensure you have Python 3.10+ installed (Tested and verified on **Python 3.13**).

### 2. Installation
Open your terminal/command prompt and navigate into the project directory:
```bash
cd "Intelligent-Online-Proctoring-System"
pip install -r requirements.txt
```

### 3. Run the Application
Start the Flask web server:
```bash
python app.py
```
*Or on Windows, simply double-click `run.bat`.*

The server will launch at:
```
http://127.0.0.1:5000
```

---

## 🧪 Demonstration & Testing Walkthrough

1. **Visit the Landing Page:** Navigate to `http://127.0.0.1:5000` to review system architecture and features.
2. **Access the Proctor Dashboard:** Click **"Proctor Dashboard"** or visit `http://127.0.0.1:5000/admin`.
   - View seeded candidate records (e.g. Alex Mercer).
   - Click **"Audit Report"** on any candidate to inspect the forensic timeline, integrity gauge, and snapshots.
3. **Simulate Candidate Examination:**
   - Click **"Student Exam Portal"** (`/student/portal`).
   - Enter your name and roll number, select an exam (e.g. *Computer Systems & Network Security*), and click **"Authenticate & Enter Exam Room"**.
   - Click **"Enter Fullscreen & Begin Exam"**.
   - Allow camera access. Your live feed will immediately display the Computer Vision HUD showing:
     - Real-time 3D Head Pose orientation vector line.
     - Face count badge (`Faces: 1`).
     - Real-time Euler angles (Yaw and Pitch).
     - Gaze direction indicator (`CENTER`).
4. **Test Cheat Detection Mechanisms:**
   - **Test Looking Away:** Turn your head left or right, or look down at your desk. The HUD will turn amber/red (`WARNING: HEAD TURNED LEFT`), an audible warning chime will trigger, and your Integrity Score will decrease.
   - **Test Candidate Absence:** Step out of the camera's view for 3 seconds. The HUD will flag `CANDIDATE FACE MISSING` and snapshot evidence.
   - **Test Tab Switching:** Switch to another browser tab or application. Return to the exam tab to see `Tab switch detected! Event logged.`
   - **Test Exiting Fullscreen:** Press `Esc`. An alert overlay will appear blocking questions until you return to full-screen mode.
   - **Test DevTools / Shortcuts:** Press `F12` or attempt `Ctrl+C` / `Ctrl+V`. The incident is trapped and penalized.
5. **Submit & Review Results:**
   - Answer the multiple-choice questions and click **"Finalize & Submit Examination"**.
   - View your Academic Score, Questions Review, and official **Proctoring Integrity Verification**.
   - Return to the **Proctor Dashboard** to see your session and violation analytics updated in real time!

---

## 🛡️ License & Academic Integrity
Developed for engineering demonstration and educational research in automated computer vision and event security.
