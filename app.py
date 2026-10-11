"""
app.py
Main Flask application for AI Attendance System.
Handles all routes, auto-initialises DB, sample data, and ML model on startup.
"""

import os
import io
import json
import random
from datetime import datetime

from flask import (Flask, render_template, request, redirect, url_for,
                   flash, send_file, jsonify, abort)
from werkzeug.utils import secure_filename

import config
import database as db
from utils.attendance_calculator import (
    get_grade, get_risk_level, get_eligibility,
    classes_needed_for_eligibility, get_recommendation,
    compute_student_subject_stats, compute_combined_stats,
)
from utils.excel_processor import (
    validate_excel, process_excel, generate_template,
    export_subject_report, export_combined_report,
)
from utils.simulator import simulate_attendance
from utils.predictor import predict_risk, predict_for_student

# ─── App Setup ─────────────────────────────────────────────────────────────────

app = Flask(__name__)
app.secret_key = config.SECRET_KEY
app.config['MAX_CONTENT_LENGTH'] = config.MAX_CONTENT_LENGTH


# ─── Startup Initialisation ────────────────────────────────────────────────────

def create_directories():
    for d in [config.DATABASE_DIR, config.DATA_DIR, config.UPLOAD_DIR,
              config.EXPORT_DIR, config.MODEL_DIR]:
        os.makedirs(d, exist_ok=True)


def insert_sample_students():
    names = [
        'Aarav Sharma', 'Priya Patel', 'Rohan Mehta', 'Sneha Joshi', 'Arjun Singh',
        'Nisha Gupta', 'Vikram Rao', 'Ananya Das', 'Ravi Kumar', 'Pooja Verma',
        'Aditya Nair', 'Kavya Reddy', 'Manish Tiwari', 'Deepika Iyer', 'Saurabh Yadav',
        'Lakshmi Pillai', 'Karan Malhotra', 'Swati Bose', 'Nikhil Choudhary', 'Divya Pandey',
        'Rahul Saxena', 'Priti Agarwal', 'Amit Srivastava', 'Neha Bhatt', 'Suresh Desai',
    ]
    for i, name in enumerate(names, 1):
        sid = f'CSE{i:03d}'
        email = f'{sid.lower()}@college.edu'
        db.insert_student(sid, name, 'CSE', 3, email)
    print(f"[SETUP] {len(names)} sample students inserted.")


def insert_sample_subjects():
    subjects = [
        ('CS401', 'Database Management Systems', 'Prof. Sharma'),
        ('CS402', 'Operating Systems', 'Prof. Patil'),
        ('CS403', 'Computer Networks', 'Prof. Mehta'),
        ('CS404', 'Artificial Intelligence', 'Prof. Reddy'),
    ]
    for code, name, teacher in subjects:
        db.insert_subject(code, name, teacher)
    print("[SETUP] Sample subjects inserted.")


def generate_sample_excel_files():
    """Create data/sample_*.xlsx files if they don't exist."""
    import pandas as pd

    dates = ['01-09', '03-09', '05-09', '08-09', '10-09',
             '12-09', '15-09', '17-09', '19-09', '22-09',
             '24-09', '26-09', '29-09', '01-10', '03-10']

    students = db.get_all_students()
    if not students:
        return

    subjects_map = {
        'sample_dbms': 'CS401',
        'sample_os':   'CS402',
        'sample_cn':   'CS403',
        'sample_ai':   'CS404',
    }

    rng = random.Random(42)
    patterns = ['excellent', 'good', 'average', 'poor']
    weights  = [0.20, 0.40, 0.30, 0.10]
    prob_map = {'excellent': 0.92, 'good': 0.82, 'average': 0.70, 'poor': 0.50}

    for fname, code in subjects_map.items():
        fpath = os.path.join(config.DATA_DIR, f'{fname}.xlsx')
        if os.path.exists(fpath):
            continue
        rows = []
        for stu in students:
            pat = rng.choices(patterns, weights=weights, k=1)[0]
            prob = prob_map[pat]
            row = {'Student ID': stu['student_id'], 'Student Name': stu['name']}
            for d in dates:
                adj = min(0.98, max(0.02, prob + rng.uniform(-0.07, 0.07)))
                row[d] = 'P' if rng.random() < adj else 'A'
            rows.append(row)
        df = pd.DataFrame(rows)
        df.to_excel(fpath, index=False)
        print(f"[SETUP] Generated {fpath}")


def load_sample_excel_to_db():
    """Import sample Excel files into the DB if attendance table is empty."""
    subjects = {
        'CS401': os.path.join(config.DATA_DIR, 'sample_dbms.xlsx'),
        'CS402': os.path.join(config.DATA_DIR, 'sample_os.xlsx'),
        'CS403': os.path.join(config.DATA_DIR, 'sample_cn.xlsx'),
        'CS404': os.path.join(config.DATA_DIR, 'sample_ai.xlsx'),
    }
    for code, fpath in subjects.items():
        if not os.path.exists(fpath):
            continue
        sub = db.get_subject_by_code(code)
        if not sub:
            continue
        if db.subject_has_attendance(sub['id']):
            continue  # already loaded
        result = process_excel(fpath, sub['id'], source='Excel')
        if result['success']:
            db.insert_upload(
                sub['id'], sub['teacher_name'],
                os.path.basename(fpath),
                result['total_students'],
                result['total_classes'],
            )
            print(f"[SETUP] Loaded {os.path.basename(fpath)} -> subject {code}")
        else:
            print(f"[SETUP] Error loading {fpath}: {result.get('error')}")


def ensure_model():
    """Train model if .pkl not found."""
    if not os.path.exists(config.MODEL_PATH):
        print("[SETUP] Training ML model...")
        from model.train_model import train_and_save
        train_and_save()
    else:
        print(f"[SETUP] ML model found at {config.MODEL_PATH}")


def initialise():
    """Full startup sequence."""
    print("[SETUP] Initialising AI Attendance System...")
    create_directories()
    db.init_db()

    students = db.get_all_students()
    if not students:
        insert_sample_students()

    subjects = db.get_all_subjects()
    if not subjects:
        insert_sample_subjects()

    generate_sample_excel_files()
    load_sample_excel_to_db()
    ensure_model()
    print("[SETUP] Initialisation complete. Starting Flask...")


# ─── Template Context ──────────────────────────────────────────────────────────

@app.context_processor
def inject_subjects():
    """Make subjects list available to all templates (for sidebar/nav)."""
    return {'nav_subjects': db.get_all_subjects()}


# ─── Dashboard ─────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    base = db.get_dashboard_stats()

    # Build per-subject summaries
    subjects = db.get_all_subjects()
    subject_cards = []
    all_below_75 = 0
    all_eligible = 0
    all_high_risk = 0
    total_pct_sum = 0
    total_pct_count = 0

    for sub in subjects:
        stats = db.get_subject_stats(sub['id'])
        if not stats:
            subject_cards.append({**sub, 'avg': 0, 'below_75': 0, 'students': 0})
            continue
        total_p = sum(s['present'] for s in stats)
        total_c = sum(s['total_classes'] for s in stats)
        avg = round((total_p / total_c) * 100, 1) if total_c else 0
        below = 0
        for s in stats:
            pct = round((s['present'] / s['total_classes']) * 100, 2) if s['total_classes'] else 0
            if pct < 75:
                below += 1
                all_below_75 += 1
            else:
                all_eligible += 1
            if get_risk_level(pct) == 'HIGH':
                all_high_risk += 1
        total_pct_sum += total_p
        total_pct_count += total_c
        subject_cards.append({**sub, 'avg': avg, 'below_75': below, 'students': len(stats)})

    avg_combined = round((total_pct_sum / total_pct_count) * 100, 1) if total_pct_count else 0

    stats_summary = {
        **base,
        'avg_combined': avg_combined,
        'below_75': all_below_75,
        'eligible': all_eligible,
        'high_risk': all_high_risk,
    }
    return render_template('index.html', stats=stats_summary, subject_cards=subject_cards)


# ─── Students ──────────────────────────────────────────────────────────────────

@app.route('/students')
def students():
    query = request.args.get('q', '').strip()
    if query:
        student_list = db.search_students(query)
    else:
        student_list = db.get_all_students()
    return render_template('students.html', students=student_list, query=query)


@app.route('/student/<student_id>')
def student_profile(student_id):
    stu = db.get_student(student_id)
    if not stu:
        abort(404)

    subjects = db.get_all_subjects()
    subject_stats = []
    combined_inputs = []

    for sub in subjects:
        records = [r for r in db.get_attendance_for_student(student_id) if r['subject_id'] == sub['id']]
        if not records:
            continue
        stats = compute_student_subject_stats(student_id, records)
        stats['subject_name'] = sub['subject_name']
        stats['subject_code'] = sub['subject_code']
        stats['teacher_name'] = sub['teacher_name']
        subject_stats.append(stats)
        combined_inputs.append({'total_classes': stats['total_classes'], 'present': stats['present']})

    combined = compute_combined_stats(combined_inputs) if combined_inputs else None

    # AI prediction using real data
    prediction = predict_for_student(student_id)

    return render_template('student_profile.html',
                           student=stu,
                           subject_stats=subject_stats,
                           combined=combined,
                           prediction=prediction)


# ─── Upload ────────────────────────────────────────────────────────────────────

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    subjects = db.get_all_subjects()
    if request.method == 'POST':
        subject_id = request.form.get('subject_id', '').strip()
        teacher_name = request.form.get('teacher_name', '').strip()
        replace = request.form.get('replace', '0')
        file = request.files.get('file')

        if not subject_id or not teacher_name:
            flash('Subject and teacher name are required.', 'error')
            return render_template('upload.html', subjects=subjects)

        if not file or file.filename == '':
            flash('Please select an Excel file to upload.', 'error')
            return render_template('upload.html', subjects=subjects)

        fname = secure_filename(file.filename)
        if not fname.lower().endswith('.xlsx'):
            flash('Only .xlsx files are allowed.', 'error')
            return render_template('upload.html', subjects=subjects)

        # Save file temporarily
        save_path = os.path.join(config.UPLOAD_DIR, fname)
        file.save(save_path)

        subject_id = int(subject_id)

        # Check for existing data
        if db.subject_has_attendance(subject_id) and replace != '1':
            sub = db.get_subject(subject_id)
            return render_template('upload.html', subjects=subjects,
                                   duplicate_warning=True, subject=sub,
                                   pending_subject_id=subject_id,
                                   pending_teacher=teacher_name,
                                   pending_file=fname)

        # Replace mode: delete old data
        if replace == '1':
            db.delete_subject_attendance(subject_id)

        # Process
        result = process_excel(save_path, subject_id, source='Excel')
        if not result['success']:
            flash(f"Upload failed: {result['error']}", 'error')
            return render_template('upload.html', subjects=subjects)

        sub = db.get_subject(subject_id)
        db.insert_upload(subject_id, teacher_name, fname,
                         result['total_students'], result['total_classes'])
        flash('Upload successful!', 'success')
        return render_template('upload.html', subjects=subjects,
                               upload_result=result, subject=sub,
                               teacher_name=teacher_name)

    return render_template('upload.html', subjects=subjects)


@app.route('/download_template')
def download_template():
    buf = generate_template()
    return send_file(buf, as_attachment=True,
                     download_name='attendance_template.xlsx',
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


# ─── Subjects ──────────────────────────────────────────────────────────────────

@app.route('/subjects')
def subjects_page():
    subjects = db.get_all_subjects()
    subject_list = []
    for sub in subjects:
        stats = db.get_subject_stats(sub['id'])
        if not stats:
            subject_list.append({**sub, 'avg': 0, 'below_75': 0, 'students': 0, 'total_classes': 0})
            continue
        total_p = sum(s['present'] for s in stats)
        total_c = sum(s['total_classes'] for s in stats)
        avg = round((total_p / total_c) * 100, 1) if total_c else 0
        below = sum(1 for s in stats
                    if s['total_classes'] and (s['present'] / s['total_classes']) * 100 < 75)
        # Distinct class dates
        dates = db.get_dates_for_subject(sub['id'])
        subject_list.append({
            **sub,
            'avg': avg,
            'below_75': below,
            'students': len(stats),
            'total_classes': len(dates),
        })
    return render_template('subjects.html', subjects=subject_list)


@app.route('/subject/<int:subject_id>')
def subject_detail(subject_id):
    sub = db.get_subject(subject_id)
    if not sub:
        abort(404)
    filter_type = request.args.get('filter', 'all')
    stats = db.get_subject_stats(subject_id)
    rows = []
    for s in stats:
        total = s['total_classes']
        present = s['present']
        pct = round((present / total) * 100, 2) if total else 0
        risk = get_risk_level(pct)
        needed = classes_needed_for_eligibility(present, total)
        rows.append({
            'student_id': s['student_id'],
            'student_name': s['student_name'],
            'total_classes': total,
            'present': present,
            'absent': s['absent'],
            'percentage': pct,
            'grade': get_grade(pct),
            'eligibility': get_eligibility(pct),
            'risk': risk,
            'classes_needed': needed,
        })

    # Apply filter
    if filter_type == 'above75':
        rows = [r for r in rows if r['percentage'] >= 75]
    elif filter_type == 'below75':
        rows = [r for r in rows if r['percentage'] < 75]
    elif filter_type == 'high_risk':
        rows = [r for r in rows if r['risk'] == 'HIGH']
    elif filter_type in ('A+', 'A', 'B+', 'B', 'C', 'D', 'F'):
        rows = [r for r in rows if r['grade'] == filter_type]

    dates = db.get_dates_for_subject(subject_id)
    return render_template('subject.html', subject=sub, rows=rows,
                           filter_type=filter_type, total_dates=len(dates))


# ─── Combined Attendance ───────────────────────────────────────────────────────

@app.route('/combined')
def combined():
    raw = db.get_combined_stats()
    subjects = db.get_all_subjects()

    # Build: {student_id -> {subject_id -> {present, total}}}
    from collections import defaultdict
    student_data = defaultdict(lambda: {'name': '', 'subjects': {}})
    for r in raw:
        sid = r['student_id']
        student_data[sid]['name'] = r['student_name']
        student_data[sid]['subjects'][r['subject_id']] = {
            'present': r['present'],
            'total': r['total_classes'],
        }

    table_rows = []
    for sid, info in sorted(student_data.items()):
        row = {'student_id': sid, 'student_name': info['name'], 'subject_data': {}}
        total_p = 0
        total_c = 0
        for sub in subjects:
            sub_info = info['subjects'].get(sub['id'], {'present': 0, 'total': 0})
            pct = round((sub_info['present'] / sub_info['total']) * 100, 1) if sub_info['total'] else 0
            row['subject_data'][sub['id']] = {'pct': pct, **sub_info}
            total_p += sub_info['present']
            total_c += sub_info['total']
        combined_pct = round((total_p / total_c) * 100, 2) if total_c else 0
        risk = get_risk_level(combined_pct)
        needed = classes_needed_for_eligibility(total_p, total_c)
        row.update({
            'total_classes': total_c,
            'total_present': total_p,
            'total_absent': total_c - total_p,
            'combined_pct': combined_pct,
            'grade': get_grade(combined_pct),
            'eligibility': get_eligibility(combined_pct),
            'risk': risk,
            'classes_needed': needed,
        })
        table_rows.append(row)

    return render_template('combined.html', subjects=subjects, rows=table_rows)


# ─── Attendance Records ────────────────────────────────────────────────────────

@app.route('/attendance', methods=['GET', 'POST'])
def attendance():
    subjects = db.get_all_subjects()

    # Handle simulation POST
    sim_result = None
    if request.method == 'POST' and request.form.get('action') == 'simulate':
        subject_id = int(request.form.get('subject_id', 0))
        num_students = int(request.form.get('num_students', 20))
        num_classes = int(request.form.get('num_classes', 30))
        sim_result = simulate_attendance(subject_id, num_students, num_classes)
        if sim_result['success']:
            flash(f"Simulation complete: {num_students} students × {num_classes} classes", 'success')
        else:
            flash(sim_result.get('error', 'Simulation failed.'), 'error')

    # Handle manual entry
    if request.method == 'POST' and request.form.get('action') == 'manual':
        student_id = request.form.get('student_id', '').strip()
        subject_id = int(request.form.get('subject_id', 0))
        date = request.form.get('attendance_date', '').strip()
        status = request.form.get('status', 'P').strip()
        if student_id and subject_id and date and status in ('P', 'A'):
            db.insert_attendance_record(student_id, subject_id, date, status, 'Manual')
            flash(f'Attendance recorded for {student_id} on {date}.', 'success')
        else:
            flash('Invalid manual attendance input.', 'error')

    # Filters
    f_subject = request.args.get('subject_id', '')
    f_student = request.args.get('student_id', '')
    f_date    = request.args.get('date', '')

    records = db.get_all_attendance(
        subject_id=int(f_subject) if f_subject else None,
        student_id=f_student if f_student else None,
        date_filter=f_date if f_date else None,
    )

    return render_template('attendance.html',
                           subjects=subjects,
                           records=records,
                           sim_result=sim_result,
                           f_subject=f_subject,
                           f_student=f_student,
                           f_date=f_date)


# ─── AI Prediction ─────────────────────────────────────────────────────────────

@app.route('/prediction', methods=['GET', 'POST'])
def prediction():
    result = None
    form_data = {}

    if request.method == 'POST':
        try:
            form_data = {
                'current_attendance':   float(request.form.get('current_attendance', 0)),
                'previous_attendance':  float(request.form.get('previous_attendance', 0)),
                'recent_attendance':    float(request.form.get('recent_attendance', 0)),
                'classes_conducted':    int(request.form.get('classes_conducted', 0)),
                'classes_attended':     int(request.form.get('classes_attended', 0)),
                'consecutive_absences': int(request.form.get('consecutive_absences', 0)),
            }
            result = predict_risk(**form_data)
        except Exception as e:
            flash(f'Prediction error: {e}', 'error')

    return render_template('prediction.html', result=result, form_data=form_data)


# ─── Analytics ─────────────────────────────────────────────────────────────────

@app.route('/analytics')
def analytics():
    subjects = db.get_all_subjects()
    analytics_data = []
    grade_totals = {}
    risk_totals  = {'LOW': 0, 'MEDIUM': 0, 'HIGH': 0}

    for sub in subjects:
        stats = db.get_subject_stats(sub['id'])
        if not stats:
            continue
        pcts = []
        for s in stats:
            pct = round((s['present'] / s['total_classes']) * 100, 2) if s['total_classes'] else 0
            pcts.append(pct)
            grade = get_grade(pct)
            grade_totals[grade] = grade_totals.get(grade, 0) + 1
            risk_totals[get_risk_level(pct)] += 1
        total_p = sum(s['present'] for s in stats)
        total_c = sum(s['total_classes'] for s in stats)
        avg = round((total_p / total_c) * 100, 1) if total_c else 0
        analytics_data.append({
            'subject_name': sub['subject_name'],
            'subject_code': sub['subject_code'],
            'avg': avg,
            'highest': round(max(pcts), 1) if pcts else 0,
            'lowest': round(min(pcts), 1) if pcts else 0,
            'below_75': sum(1 for p in pcts if p < 75),
            'students': len(stats),
            'total_present': total_p,
            'total_absent': total_c - total_p,
        })

    return render_template('analytics.html',
                           analytics_data=analytics_data,
                           grade_totals=grade_totals,
                           risk_totals=risk_totals)


# ─── Upload History ────────────────────────────────────────────────────────────

@app.route('/uploads')
def uploads_history():
    uploads = db.get_all_uploads()
    return render_template('uploads.html', uploads=uploads)


# ─── Export Routes ─────────────────────────────────────────────────────────────

@app.route('/export/subject/<int:subject_id>')
def export_subject(subject_id):
    sub = db.get_subject(subject_id)
    if not sub:
        abort(404)
    os.makedirs(config.EXPORT_DIR, exist_ok=True)
    fname = f"subject_{sub['subject_code']}_{datetime.now().strftime('%Y%m%d%H%M%S')}.xlsx"
    fpath = os.path.join(config.EXPORT_DIR, fname)
    export_subject_report(subject_id, fpath)
    return send_file(fpath, as_attachment=True, download_name=fname)


@app.route('/export/combined')
def export_combined():
    os.makedirs(config.EXPORT_DIR, exist_ok=True)
    fname = f"combined_report_{datetime.now().strftime('%Y%m%d%H%M%S')}.xlsx"
    fpath = os.path.join(config.EXPORT_DIR, fname)
    export_combined_report(fpath)
    return send_file(fpath, as_attachment=True, download_name=fname)


# ─── API Endpoints for Charts ──────────────────────────────────────────────────

@app.route('/api/chart/subjects')
def api_chart_subjects():
    """Subject-wise average attendance for Chart.js."""
    subjects = db.get_all_subjects()
    labels, values = [], []
    for sub in subjects:
        stats = db.get_subject_stats(sub['id'])
        if not stats:
            continue
        total_p = sum(s['present'] for s in stats)
        total_c = sum(s['total_classes'] for s in stats)
        avg = round((total_p / total_c) * 100, 1) if total_c else 0
        labels.append(sub['subject_code'])
        values.append(avg)
    return jsonify({'labels': labels, 'values': values})


@app.route('/api/chart/risk')
def api_chart_risk():
    """Risk distribution across all students."""
    raw = db.get_combined_stats()
    from collections import defaultdict
    student_totals = defaultdict(lambda: {'p': 0, 'c': 0})
    for r in raw:
        student_totals[r['student_id']]['p'] += r['present']
        student_totals[r['student_id']]['c'] += r['total_classes']
    risk_counts = {'LOW': 0, 'MEDIUM': 0, 'HIGH': 0}
    for sid, d in student_totals.items():
        pct = (d['p'] / d['c']) * 100 if d['c'] else 0
        risk_counts[get_risk_level(pct)] += 1
    return jsonify(risk_counts)


@app.route('/api/chart/grades')
def api_chart_grades():
    """Grade distribution across all students (combined %)."""
    raw = db.get_combined_stats()
    from collections import defaultdict
    student_totals = defaultdict(lambda: {'p': 0, 'c': 0})
    for r in raw:
        student_totals[r['student_id']]['p'] += r['present']
        student_totals[r['student_id']]['c'] += r['total_classes']
    grade_counts = {}
    for sid, d in student_totals.items():
        pct = (d['p'] / d['c']) * 100 if d['c'] else 0
        g = get_grade(pct)
        grade_counts[g] = grade_counts.get(g, 0) + 1
    return jsonify(grade_counts)


@app.route('/api/chart/present_absent')
def api_chart_present_absent():
    """Total present vs absent across all subjects."""
    subjects = db.get_all_subjects()
    labels, present_vals, absent_vals = [], [], []
    for sub in subjects:
        stats = db.get_subject_stats(sub['id'])
        if not stats:
            continue
        tp = sum(s['present'] for s in stats)
        ta = sum(s['absent'] for s in stats)
        labels.append(sub['subject_code'])
        present_vals.append(tp)
        absent_vals.append(ta)
    return jsonify({'labels': labels, 'present': present_vals, 'absent': absent_vals})


@app.route('/api/chart/combined_distribution')
def api_chart_combined_distribution():
    """Distribution of combined attendance percentages (histogram buckets)."""
    raw = db.get_combined_stats()
    from collections import defaultdict
    student_totals = defaultdict(lambda: {'p': 0, 'c': 0})
    for r in raw:
        student_totals[r['student_id']]['p'] += r['present']
        student_totals[r['student_id']]['c'] += r['total_classes']
    buckets = {'0-50': 0, '50-60': 0, '60-75': 0, '75-85': 0, '85-100': 0}
    for sid, d in student_totals.items():
        pct = (d['p'] / d['c']) * 100 if d['c'] else 0
        if pct < 50:
            buckets['0-50'] += 1
        elif pct < 60:
            buckets['50-60'] += 1
        elif pct < 75:
            buckets['60-75'] += 1
        elif pct < 85:
            buckets['75-85'] += 1
        else:
            buckets['85-100'] += 1
    return jsonify(buckets)


# ─── Entry Point ───────────────────────────────────────────────────────────────

if __name__ == '__main__':
    initialise()
    app.run(host=config.HOST, port=config.PORT, debug=config.DEBUG)