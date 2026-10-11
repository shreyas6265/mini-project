"""
test_system.py
Quick integration test for the AI Attendance System.
Run: python test_system.py
"""

import sys, os
sys.path.insert(0, r'c:\Users\PANKAJ\Desktop\attendance-ai')
os.chdir(r'c:\Users\PANKAJ\Desktop\attendance-ai')

import database as db
import config

print("=" * 50)
print("AI Attendance System - Integration Tests")
print("=" * 50)

# ── 1. DB init ───────────────────────────────────────
if os.path.exists(config.DATABASE_PATH):
    os.remove(config.DATABASE_PATH)
db.init_db()
print("[1] DB init: PASSED")

# ── 2. Sample data ───────────────────────────────────
from app import insert_sample_students, insert_sample_subjects
from app import generate_sample_excel_files, load_sample_excel_to_db

insert_sample_students()
insert_sample_subjects()
generate_sample_excel_files()
load_sample_excel_to_db()

students = db.get_all_students()
subjects = db.get_all_subjects()
assert len(students) == 25, f"Expected 25 students, got {len(students)}"
assert len(subjects) == 4, f"Expected 4 subjects, got {len(subjects)}"
print(f"[2] Sample data: PASSED ({len(students)} students, {len(subjects)} subjects)")

# ── 3. Attendance records ────────────────────────────
conn = db.get_connection()
count = conn.execute("SELECT COUNT(*) FROM attendance").fetchone()[0]
conn.close()
assert count > 0, "No attendance records!"
print(f"[3] Attendance records: PASSED ({count} records)")

# ── 4. Combined % formula ────────────────────────────
from utils.attendance_calculator import compute_combined_stats, classes_needed_for_eligibility
result = compute_combined_stats([
    {"total_classes": 30, "present": 24},
    {"total_classes": 30, "present": 21},
    {"total_classes": 30, "present": 27},
])
assert result["combined_pct"] == 80.0, f"Combined % FAIL: {result['combined_pct']}"
print(f"[4] Combined % (72/90=80%): PASSED -> {result['combined_pct']}%")

# ── 5. Classes needed for 75% ────────────────────────
x = classes_needed_for_eligibility(60, 100)
assert (60 + x) / (100 + x) >= 0.75, f"Classes needed FAIL: x={x}"
print(f"[5] Classes needed (60/100): PASSED -> x={x}, result={(60+x)/(100+x)*100:.1f}%")

x2 = classes_needed_for_eligibility(24, 30)
assert x2 == 0, f"Already eligible but got x={x2}"
print(f"[6] Classes needed (24/30=eligible): PASSED -> x=0")

# ── 6. Grade calculation ─────────────────────────────
from utils.attendance_calculator import get_grade
assert get_grade(95) == "A+", f"Grade 95 FAIL: {get_grade(95)}"
assert get_grade(82) == "A",  f"Grade 82 FAIL: {get_grade(82)}"
assert get_grade(77) == "B+", f"Grade 77 FAIL: {get_grade(77)}"
assert get_grade(72) == "B",  f"Grade 72 FAIL: {get_grade(72)}"
assert get_grade(65) == "C",  f"Grade 65 FAIL: {get_grade(65)}"
assert get_grade(55) == "D",  f"Grade 55 FAIL: {get_grade(55)}"
assert get_grade(40) == "F",  f"Grade 40 FAIL: {get_grade(40)}"
print("[7] Grade calculation: PASSED (A+/A/B+/B/C/D/F)")

# ── 7. Risk levels ───────────────────────────────────
from utils.attendance_calculator import get_risk_level
assert get_risk_level(80) == "LOW"
assert get_risk_level(70) == "MEDIUM"
assert get_risk_level(55) == "HIGH"
print("[8] Risk levels (LOW/MEDIUM/HIGH): PASSED")

# ── 8. ML prediction ────────────────────────────────
from utils.predictor import predict_risk
res_high = predict_risk(55.0, 60.0, 50.0, 40, 22, 4)
res_low  = predict_risk(88.0, 85.0, 90.0, 40, 35, 0)
assert res_high["risk_level"] in ("HIGH", "MEDIUM"), f"Expected HIGH/MEDIUM, got {res_high['risk_level']}"
assert res_low["risk_level"] == "LOW", f"Expected LOW, got {res_low['risk_level']}"
print(f"[9] ML prediction: PASSED (55%={res_high['risk_level']}, 88%={res_low['risk_level']})")

# ── 9. Excel validation ──────────────────────────────
from utils.excel_processor import validate_excel
_, _, err = validate_excel(os.path.join(config.DATA_DIR, "sample_dbms.xlsx"))
assert err is None, f"Excel validation FAIL: {err}"
print("[10] Excel validation: PASSED")

# ── 10. Dashboard stats ──────────────────────────────
stats = db.get_dashboard_stats()
assert stats["total_students"] == 25
assert stats["total_subjects"] == 4
print(f"[11] Dashboard stats: PASSED ({stats})")

# ── 11. Subject stats ────────────────────────────────
sub1_stats = db.get_subject_stats(1)
assert len(sub1_stats) > 0
print(f"[12] Subject stats (DBMS): PASSED ({len(sub1_stats)} students)")

# ── 12. Flask test client ────────────────────────────
from app import app
app.config["TESTING"] = True
client = app.test_client()

routes = ["/", "/students", "/subjects", "/combined",
          "/attendance", "/prediction", "/analytics",
          "/uploads", "/upload"]
for route in routes:
    resp = client.get(route)
    assert resp.status_code == 200, f"Route {route} returned {resp.status_code}"
    print(f"[13] GET {route}: {resp.status_code} OK")

# API chart endpoints
for api in ["/api/chart/subjects", "/api/chart/risk",
            "/api/chart/grades", "/api/chart/present_absent",
            "/api/chart/combined_distribution"]:
    resp = client.get(api)
    assert resp.status_code == 200, f"API {api} returned {resp.status_code}"
    print(f"[14] GET {api}: 200 OK")

print()
print("=" * 50)
print("ALL TESTS PASSED")
print("=" * 50)
