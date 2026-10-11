import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# Database configuration
DATABASE_PATH = os.path.join(BASE_DIR, "data", "proctoring.db")

# Model configuration
MODEL_CACHE_DIR = os.path.join(BASE_DIR, "models_cache")
FACE_LANDMARKER_MODEL_PATH = os.path.join(MODEL_CACHE_DIR, "face_landmarker.task")
MODEL_URL = "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task"

# File upload and evidence storage
EVIDENCE_UPLOAD_DIR = os.path.join(BASE_DIR, "static", "uploads", "evidence")

# Secret key for Flask session
SECRET_KEY = os.environ.get("SECRET_KEY", "proctor-secure-key-2026-x99b1a")

# Proctoring computer vision thresholds
PROCTOR_THRESHOLDS = {
    # Head Pose (Degrees)
    "YAW_THRESHOLD_LEFT": -22.0,       # Turn head left
    "YAW_THRESHOLD_RIGHT": 22.0,       # Turn head right
    "PITCH_THRESHOLD_DOWN": -18.0,     # Looking down (notes / phone)
    "PITCH_THRESHOLD_UP": 22.0,        # Looking up at ceiling
    "ROLL_THRESHOLD": 25.0,            # Extreme tilt

    # Eye Gaze / Iris Position (Normalized ratio [0, 1] across eye socket width)
    "IRIS_LEFT_RATIO": 0.35,           # Looking towards left
    "IRIS_RIGHT_RATIO": 0.65,          # Looking towards right
    "IRIS_VERTICAL_UP_RATIO": 0.35,    # Looking up
    "IRIS_VERTICAL_DOWN_RATIO": 0.65,  # Looking down

    # Temporal Smoothing
    "CONSECUTIVE_FRAMES_TRIGGER": 2,   # Require violation in 2 consecutive frames to prevent momentary noise
    "MAX_WARNINGS_BEFORE_FLAG": 5      # Maximum allowable warnings before high-risk escalation
}

# Integrity Score Deductions (Base score 100)
INTEGRITY_PENALTIES = {
    "MULTIPLE_FACES": 15,              # Another person in frame
    "FACE_MISSING": 12,                # Candidate left webcam
    "LOOKING_AWAY": 5,                 # Head turned away
    "SUSPICIOUS_GAZE": 4,              # Eye gaze shifted without head movement
    "TAB_SWITCH": 12,                  # Browser tab/app switched
    "FULLSCREEN_EXIT": 10,             # Exited full screen
    "DEVTOOLS_ATTEMPT": 15,            # Attempted F12 / inspect element
    "COPY_PASTE_ATTEMPT": 5            # Attempted copy or paste
}
