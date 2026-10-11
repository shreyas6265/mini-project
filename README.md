# AI-Based Attendance Simulation, Excel Analysis and Prediction System

> BTech AI/ML Mini-Project | Flask · Pandas · Scikit-learn · SQLite · Chart.js

---

## Problem Statement

Traditional attendance tracking in colleges is manual, error-prone, and lacks analytical insight.  
This system automates attendance collection (via Excel upload or simulation), computes detailed analytics per subject and combined across subjects, and uses a Machine Learning model to predict student attendance risk.

---

## Objectives

1. Parse and validate real teacher-uploaded Excel attendance sheets
2. Store attendance data per subject, per student in SQLite
3. Calculate subject-wise and combined attendance with correct formulas
4. Identify students below the 75% eligibility threshold and compute classes needed
5. Train a Decision Tree classifier to predict LOW / MEDIUM / HIGH attendance risk
6. Provide an interactive dashboard with charts and filterable tables
7. Export reports as .xlsx files

---

## Features

| Feature | Description |
|---|---|
| Excel Upload | Upload .xlsx with P/A columns; validated and stored |
| Multi-subject | Different teachers upload different subjects independently |
| Subject-wise Stats | Per-student: classes, present, absent, %, grade, eligibility, risk |
| Combined Attendance | Correct formula: sum(attended) / sum(conducted) × 100 |
| Dynamic Columns | Combined table auto-adds new subject columns when uploaded |
| AI Prediction | Decision Tree predicts LOW/MEDIUM/HIGH risk from 6 features |
| 75% Calculator | Computes exact minimum classes needed to reach eligibility |
| Simulation | Generates realistic synthetic attendance (4 quality patterns) |
| Charts | 5 Chart.js charts: subject avg, risk, grade, P/A, distribution |
| Export | Download subject or combined report as .xlsx |
| Upload History | Full log of all uploads with date, teacher, filename |
| Student Profile | Full view per student: all subjects + combined + AI prediction |

---

## Technology Stack

- **Backend**: Python 3, Flask
- **Data**: Pandas, NumPy, openpyxl
- **ML**: Scikit-learn (DecisionTreeClassifier), Joblib
- **Database**: SQLite (via standard library)
- **Frontend**: HTML5, CSS3 (custom), Vanilla JavaScript, Chart.js (CDN)

---

## Project Architecture

```
attendance-ai/
├── app.py                      # Flask routes + startup init
├── config.py                   # All constants and thresholds
├── database.py                 # SQLite helpers (CRUD)
├── requirements.txt
├── README.md
├── database/
│   └── attendance.db           # Auto-created SQLite DB
├── data/
│   ├── sample_dbms.xlsx        # Auto-generated sample data
│   ├── sample_os.xlsx
│   ├── sample_cn.xlsx
│   └── sample_ai.xlsx
├── uploads/                    # Uploaded files stored here
├── exports/                    # Generated report files
├── model/
│   ├── train_model.py          # ML training script
│   └── attendance_model.pkl    # Trained model (auto-generated)
├── utils/
│   ├── attendance_calculator.py  # Grade, eligibility, risk formulas
│   ├── excel_processor.py       # Excel parse, validate, import, export
│   ├── simulator.py             # Realistic simulation engine
│   └── predictor.py             # ML inference using real DB data
├── templates/                   # Jinja2 HTML templates (12 files)
└── static/                      # CSS + JS
```

---

## Database Design

### students
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | Auto |
| student_id | TEXT UNIQUE | e.g. CSE001 |
| name | TEXT | Full name |
| department | TEXT | e.g. CSE |
| year | INTEGER | 1–4 |
| email | TEXT | Optional |

### subjects
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | Auto |
| subject_code | TEXT UNIQUE | e.g. CS401 |
| subject_name | TEXT | e.g. DBMS |
| teacher_name | TEXT | e.g. Prof. Sharma |

### attendance
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | Auto |
| student_id | TEXT FK→students | |
| subject_id | INTEGER FK→subjects | |
| attendance_date | TEXT | e.g. 01-09 |
| status | TEXT | P or A |
| source | TEXT | Excel / Simulation / Manual |

### uploads
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | Auto |
| subject_id | INTEGER FK | |
| teacher_name | TEXT | |
| filename | TEXT | |
| upload_date | TEXT | ISO timestamp |
| total_students | INTEGER | |
| total_classes | INTEGER | |
| status | TEXT | Success |

### predictions
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | Auto |
| student_id | TEXT FK | |
| prediction_date | TEXT | |
| current_attendance | REAL | |
| risk_level | TEXT | LOW/MEDIUM/HIGH |
| recommendation | TEXT | |

---

## Excel Format

```
Student ID | Student Name | 01-09 | 03-09 | 05-09 | 08-09 | 10-09
CSE001     | Aarav Sharma | P     | P     | A     | P     | P
CSE002     | Priya Patel  | A     | P     | P     | P     | A
```

**Supported status values**: `P`, `Present`, `1`, `Yes` → Present  
`A`, `Absent`, `0`, `No` → Absent

---

## Upload Process

1. Teacher selects subject and enters name
2. Selects .xlsx file (drag & drop supported)
3. System validates: extension, Student ID column, Student Name column, attendance columns, valid values
4. If duplicate: system asks to Replace or Cancel
5. On success: shows students, classes, present, absent counts

---

## Subject Attendance Formula

```
attendance_percentage = (classes_attended / total_classes) × 100

Grades:
  90–100  → A+
  80–89.99→ A
  75–79.99→ B+
  70–74.99→ B
  60–69.99→ C
  50–59.99→ D
  < 50    → F
```

---

## Combined Attendance Formula (CRITICAL)

```python
# CORRECT – ratio of sums
combined_pct = (sum_of_all_present / sum_of_all_conducted) × 100

# WRONG – simple average of percentages
# combined_pct = mean([pct_DBMS, pct_OS, pct_CN, pct_AI])
```

**Example**:
- DBMS: 24/30 = 80%
- OS: 21/30 = 70%
- CN: 27/30 = 90%
- Combined: 72/90 = **80.0%** ✓ (not (80+70+90)/3 = 80% coincidentally same here but formula is correct)

---

## 75% Eligibility Calculator

Finds minimum **x** such that:

```
(attended + x) / (conducted + x) ≥ 0.75

Solving algebraically:
  x = (0.75 × conducted − attended) / (1 − 0.75)
  x = ceil((0.75 × conducted − attended) / 0.25)
```

---

## AI/ML Model

**Algorithm**: Decision Tree Classifier (Scikit-learn)

**Features**:
1. current_attendance (%)
2. previous_attendance (%)
3. recent_attendance – last 10 classes (%)
4. classes_conducted
5. classes_attended
6. consecutive_absences

**Target classes**: `LOW`, `MEDIUM`, `HIGH`

**Training**: 1,500 synthetic samples generated with realistic distributions:
- HIGH: 30% of samples (attendance 30–64%)
- MEDIUM: 35% (attendance 60–77%)
- LOW: 35% (attendance 75–100%)

**Model saved**: `model/attendance_model.pkl`

---

## Recommendations

| Risk | Recommendation |
|---|---|
| LOW | Attendance is healthy. Maintain regular attendance. |
| MEDIUM | Attendance requires attention. Attend upcoming classes regularly. |
| HIGH | Attendance is at high risk. Attend upcoming classes regularly and avoid unnecessary absences. |

---

## Installation

```bash
cd attendance-ai
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
python app.py
```

Open: **http://127.0.0.1:5000**

---

## Running

The application auto-initialises on first run:
1. Creates required directories
2. Creates SQLite database and all tables
3. Inserts 25 sample students
4. Inserts 4 sample subjects
5. Generates sample Excel files (15 dates × 25 students × 4 subjects)
6. Imports sample Excel data into DB
7. Trains/loads ML model
8. Starts Flask

---

## Testing

```bash
# Run the Flask test suite
python -m pytest tests/ -v   # if tests/ exists

# Or manually:
python -c "
from utils.attendance_calculator import classes_needed_for_eligibility
# DBMS 24/30 + OS 21/30 + CN 27/30 = 72/90 = 80%
assert round((72/90)*100, 2) == 80.0
print('Combined % test: PASSED')
# Classes needed: attended=60, conducted=100, need x: (60+x)/(100+x)>=0.75
x = classes_needed_for_eligibility(60, 100)
assert (60+x)/(100+x) >= 0.75
print(f'Classes needed test: PASSED (x={x})')
"
```

---

## Exporting Reports

| Export | Route | Contains |
|---|---|---|
| Subject Report | `/export/subject/<id>` | Per-student stats for one subject |
| Combined Report | `/export/combined` | All subjects combined per student |
| Excel Template | `/download_template` | Blank template for teachers |

Files saved to `exports/` directory.

---

## Future Scope

1. User authentication (teacher login, HOD dashboard)
2. Email alerts for high-risk students
3. Mobile-responsive layout
4. Biometric / RFID integration
5. Deep learning models (LSTM for trend prediction)
6. SMS notifications via Twilio
7. PDF report generation
8. Multi-department / multi-batch support
9. REST API for integration with university ERP

---

## Viva Questions

**Q1. What is the formula for combined attendance?**  
A. Total present across all subjects ÷ Total conducted across all subjects × 100. NOT the average of individual percentages.

**Q2. Why Decision Tree over other algorithms?**  
A. Interpretable, handles mixed numeric features well, fast inference, suitable for small training sets.

**Q3. How does the 75% eligibility calculator work?**  
A. Solves: (attended + x)/(conducted + x) ≥ 0.75 algebraically to find minimum x.

**Q4. How do you prevent duplicate attendance records?**  
A. SQLite UNIQUE constraint on (student_id, subject_id, attendance_date). INSERT OR REPLACE is used on re-upload.

**Q5. What are the three attendance risk levels?**  
A. LOW (≥75%), MEDIUM (60–74.99%), HIGH (<60%).

**Q6. How is recent attendance calculated?**  
A. Last 10 attendance records (by date order) for that student.

**Q7. What Excel formats are accepted?**  
A. .xlsx only. Columns: Student ID, Student Name, then date columns with P/A/1/0 values.

**Q8. How does the simulation work?**  
A. Assigns each student a random pattern (excellent/good/average/poor) with weighted probabilities, then generates P/A per class with that pattern's probability ± small noise.

**Q9. What does the `source` field in attendance table store?**  
A. Whether the record came from Excel upload, Simulation, or Manual entry.

**Q10. How are grades assigned?**  
A. Thresholds defined in config.py: A+ ≥90%, A ≥80%, B+ ≥75%, B ≥70%, C ≥60%, D ≥50%, F <50%.
