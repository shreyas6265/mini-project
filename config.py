"""
Configuration file for AI Attendance System
All thresholds and constants defined here for easy modification
"""

import os

# ─── Base Directories ──────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_DIR = os.path.join(BASE_DIR, 'database')
DATA_DIR = os.path.join(BASE_DIR, 'data')
UPLOAD_DIR = os.path.join(BASE_DIR, 'uploads')
EXPORT_DIR = os.path.join(BASE_DIR, 'exports')
MODEL_DIR = os.path.join(BASE_DIR, 'model')

# ─── Database ──────────────────────────────────────────────────────────────────
DATABASE_PATH = os.path.join(DATABASE_DIR, 'attendance.db')

# ─── File Upload ───────────────────────────────────────────────────────────────
ALLOWED_EXTENSIONS = {'xlsx'}
MAX_FILE_SIZE_MB = 10
MAX_CONTENT_LENGTH = MAX_FILE_SIZE_MB * 1024 * 1024

# ─── Attendance Grade Thresholds ───────────────────────────────────────────────
# Format: (min_percentage, grade_label)
GRADE_THRESHOLDS = [
    (90, 'A+'),
    (80, 'A'),
    (75, 'B+'),
    (70, 'B'),
    (60, 'C'),
    (50, 'D'),
    (0,  'F'),
]

# ─── Eligibility ───────────────────────────────────────────────────────────────
ELIGIBILITY_THRESHOLD = 75.0  # percent

# ─── ML Model ──────────────────────────────────────────────────────────────────
MODEL_PATH = os.path.join(MODEL_DIR, 'attendance_model.pkl')
TRAINING_SAMPLES = 1500
RANDOM_STATE = 42

# ─── Risk Levels ───────────────────────────────────────────────────────────────
RISK_THRESHOLDS = {
    'HIGH': 60.0,    # below this => HIGH risk
    'MEDIUM': 75.0,  # below this => MEDIUM risk
    # at or above MEDIUM threshold => LOW risk
}

# ─── Recommendations ───────────────────────────────────────────────────────────
RECOMMENDATIONS = {
    'LOW': 'Attendance is healthy. Maintain regular attendance.',
    'MEDIUM': 'Attendance requires attention. Attend upcoming classes regularly.',
    'HIGH': 'Attendance is at high risk. Attend upcoming classes regularly and avoid unnecessary absences.',
}

# ─── Simulation Patterns ───────────────────────────────────────────────────────
SIMULATION_PATTERNS = {
    'excellent': (85, 98),
    'good':      (75, 90),
    'average':   (60, 80),
    'poor':      (40, 65),
}

# ─── Flask ─────────────────────────────────────────────────────────────────────
SECRET_KEY = 'attendance-ai-secret-2024'
DEBUG = True
HOST = '0.0.0.0'
PORT = 5000