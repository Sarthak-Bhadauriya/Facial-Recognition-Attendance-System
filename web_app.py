"""
Attend-X — Flask Web Application

Authentication model:
  COMMON_EMPLOYEE_PASSWORD  → used for: Employee Registration ONLY
  MANAGER_PASSWORD          → used for: Admin Dashboard ONLY
  Mark Attendance           → NO password; uses Unique ID + live face match
"""

from flask import Flask, render_template, request, jsonify
import base64
import threading
import webbrowser
import os
from datetime import datetime, timezone, timedelta
import pandas as pd

# Indian Standard Time = UTC + 5:30
IST = timezone(timedelta(hours=5, minutes=30))

def now_ist():
    return datetime.now(IST)

from register import perform_registration_from_frame
from attendance import process_attendance
from face_utils import recognize_frame_for_uid, reset_liveness
from dashboard import (get_today_attendance_df, search_attendance_df,
                        get_monthly_summary_df, get_monthly_detail_df)
from config import verify_manager_password, verify_employee_password
import storage

app = Flask(__name__)
app.secret_key = os.urandom(24)


# ── Utility ────────────────────────────────────────────────────────────────────

def decode_frame(frame_b64):
    """Decode a base64 JPEG string to raw bytes. Returns None on failure."""
    try:
        return base64.b64decode(frame_b64)
    except Exception:
        return None


# ── Pages ──────────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return render_template('index.html')


# ══════════════════════════════════════════════════════════════════════════════
# MARK ATTENDANCE  (Page 1)
# NO password — authenticated by Unique ID + live face match only.
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/api/check-uid', methods=['POST'])
def api_check_uid():
    """
    Check whether a Unique Employee ID exists in employees.csv
    AND has a stored face encoding.
    Called before opening the camera so we fail fast without wasting time.
    """
    data = request.get_json()
    uid  = str(data.get('uid', '')).strip()

    if not uid:
        return jsonify({'exists': False, 'message': 'Please enter your Unique Employee ID.'})

    employees_df   = storage.load_employees()
    encodings_dict = storage.load_encodings()

    in_csv  = uid in employees_df['unique_id'].astype(str).values
    has_enc = (str(uid) in encodings_dict) or (uid in encodings_dict)

    if not in_csv:
        return jsonify({'exists': False,
                        'message': 'This Unique ID is not registered. Please register first.'})
    if not has_enc:
        return jsonify({'exists': False,
                        'message': 'No face data found for this ID. Please complete registration first.'})

    return jsonify({'exists': True})


@app.route('/api/process-frame', methods=['POST'])
def api_process_frame():
    """
    Receive a single JPEG frame (base64) + target Unique ID.
    Checks if the face matches ONLY that UID's stored encoding.
    Returns result immediately — no liveness blocking.

    Response 'result' values:
        'no_face'     – no face detected, keep scanning
        'match'       – face matched, attendance marked
        'mismatch'    – face found but does NOT match this UID
        'no_encoding' – no face encoding on file for this UID
    """
    data       = request.get_json()
    target_uid = str(data.get('target_uid', '')).strip()
    frame_b64  = data.get('frame_b64', '')

    if not target_uid or not frame_b64:
        return jsonify({'result': 'no_face', 'message': ''})

    jpeg_bytes = decode_frame(frame_b64)
    if jpeg_bytes is None:
        return jsonify({'result': 'no_face', 'message': 'Invalid frame data.'})

    result, name = recognize_frame_for_uid(jpeg_bytes, target_uid)

    if result == 'no_face':
        return jsonify({'result': 'no_face', 'message': ''})

    if result == 'mismatch':
        return jsonify({
            'result':  'mismatch',
            'message': 'Face does not match the entered Unique ID. Attendance not marked.',
        })

    if result == 'spoof':
        return jsonify({
            'result':  'spoof',
            'message': 'Spoofing Detected: Please show a real face, not a photo.',
        })

    if result == 'no_encoding':
        return jsonify({
            'result':  'no_encoding',
            'message': 'No face encoding found for this ID. Please complete registration first.',
        })

    # result == 'match' — mark attendance
    msg          = process_attendance(target_uid, name)
    already_done = 'already completed' in msg.lower()

    return jsonify({
        'result':       'match',
        'name':         name,
        'message':      msg,
        'already_done': already_done,
    })


@app.route('/api/reset-liveness', methods=['POST'])
def api_reset_liveness():
    """No-op kept for JS compatibility."""
    return jsonify({'success': True})


# ══════════════════════════════════════════════════════════════════════════════
# REGISTER NEW EMPLOYEE  (Page 2)
# Requires ONLY the COMMON EMPLOYEE ACCESS CODE.
# Explicitly rejects the Manager Access Code.
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/api/verify-employee', methods=['POST'])
def api_verify_employee():
    """
    Verify the common Employee Access Code.
    Explicitly rejects the Manager Access Code with a clear message.
    """
    data = request.get_json()
    pwd  = data.get('employee_code', '')

    if verify_employee_password(pwd):
        return jsonify({'success': True})

    if verify_manager_password(pwd):
        return jsonify({'success': False,
                        'message': 'Incorrect — please enter the Employee Access Code, not the Manager code.'})

    return jsonify({'success': False, 'message': 'Incorrect Employee Access Code.'})


@app.route('/api/capture-register-frame', methods=['POST'])
def api_capture_register_frame():
    """
    Receive a JPEG frame (base64) + employee details.
    Authenticates with COMMON EMPLOYEE ACCESS CODE only.
    Extracts face encoding and saves the new employee.
    Unique ID accepts any non-empty string (numeric, alphabetic, or mixed).
    """
    data      = request.get_json()
    emp_code  = data.get('employee_code', '')
    uid       = str(data.get('uid', '')).strip()
    name      = data.get('name', '').strip()
    frame_b64 = data.get('frame_b64', '')

    # Reject manager code explicitly
    if verify_manager_password(emp_code):
        return jsonify({'success': False,
                        'message': 'Incorrect — use the Employee Access Code, not the Manager code.'})

    if not verify_employee_password(emp_code):
        return jsonify({'success': False, 'message': 'Incorrect Employee Access Code.'})

    if not uid:
        return jsonify({'success': False, 'message': 'Unique ID cannot be empty.'})

    if not name:
        return jsonify({'success': False, 'message': 'Employee name cannot be empty.'})

    if not frame_b64:
        return jsonify({'success': False, 'message': 'No image frame received.'})

    jpeg_bytes = decode_frame(frame_b64)
    if jpeg_bytes is None:
        return jsonify({'success': False, 'message': 'Invalid image data.'})

    success, msg = perform_registration_from_frame(emp_code, uid, name, jpeg_bytes)
    return jsonify({'success': success, 'message': msg})


# ══════════════════════════════════════════════════════════════════════════════
# ADMIN DASHBOARD  (Page 3)
# Requires ONLY the MANAGER ACCESS CODE (separate from Employee Access Code).
# Explicitly rejects the Employee Access Code.
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/api/dashboard/verify', methods=['POST'])
def api_dash_verify():
    """
    Gate for the Admin Dashboard.
    Only the Manager Access Code grants access.
    Employee Access Code is explicitly rejected.
    """
    data = request.get_json()
    pwd  = data.get('manager_code', '')

    if verify_manager_password(pwd):
        return jsonify({'success': True})

    # Explicitly reject the employee code
    if verify_employee_password(pwd):
        return jsonify({'success': False,
                        'message': 'Manager access required. The Employee Access Code cannot unlock this page.'})

    return jsonify({'success': False, 'message': 'Incorrect Manager Access Code.'})


@app.route('/api/dashboard/today', methods=['POST'])
def api_dash_today():
    data = request.get_json()
    if not verify_manager_password(data.get('manager_code', '')):
        return jsonify({'success': False, 'message': 'Unauthorized'})

    df        = get_today_attendance_df()
    employees = storage.load_employees()
    leaves_df = storage.load_leaves()

    total_emp = len(employees)
    present   = 0
    late      = 0
    on_leave  = 0

    today_str    = now_ist().strftime("%Y-%m-%d")
    leaves_today = (
        leaves_df[leaves_df['date'] == today_str]['unique_id'].astype(str).tolist()
        if not leaves_df.empty else []
    )

    if not df.empty:
        present = int(len(df[df['status'].isin(['Present', 'Late'])]))
        late    = int(len(df[df['status'] == 'Late']))

        for _, row in employees.iterrows():
            uid = str(row['unique_id'])
            if uid not in df['unique_id'].astype(str).values:
                if uid in leaves_today:
                    on_leave += 1
                    df = pd.concat([df, pd.DataFrame([{
                        'unique_id': uid, 'name': row['name'], 'date': today_str,
                        'time_in': '-', 'time_out': '-', 'status': 'On Leave', 'overtime_hours': 0
                    }])], ignore_index=True)
                else:
                    df = pd.concat([df, pd.DataFrame([{
                        'unique_id': uid, 'name': row['name'], 'date': today_str,
                        'time_in': '-', 'time_out': '-', 'status': 'Absent', 'overtime_hours': 0
                    }])], ignore_index=True)
    else:
        for _, row in employees.iterrows():
            uid    = str(row['unique_id'])
            status = 'On Leave' if uid in leaves_today else 'Absent'
            if status == 'On Leave':
                on_leave += 1
            df = pd.concat([df, pd.DataFrame([{
                'unique_id': uid, 'name': row['name'], 'date': today_str,
                'time_in': '-', 'time_out': '-', 'status': status, 'overtime_hours': 0
            }])], ignore_index=True)

    absent  = total_emp - present - on_leave
    records = [] if df.empty else df.fillna('').to_dict(orient='records')

    return jsonify({
        'success': True,
        'metrics': {'total': total_emp, 'present': present, 'late': late,
                    'absent': absent, 'on_leave': on_leave},
        'records': records,
    })


@app.route('/api/dashboard/search', methods=['POST'])
def api_dash_search():
    data = request.get_json()
    if not verify_manager_password(data.get('manager_code', '')):
        return jsonify({'success': False, 'message': 'Unauthorized'})

    df = search_attendance_df(
        data.get('search_type'),
        data.get('search_val', ''),
        data.get('start_date', ''),
        data.get('end_date',   ''),
    )
    return jsonify({'success': True,
                    'records': [] if df.empty else df.fillna('').to_dict(orient='records')})


@app.route('/api/dashboard/monthly', methods=['POST'])
def api_dash_monthly():
    data = request.get_json()
    if not verify_manager_password(data.get('manager_code', '')):
        return jsonify({'success': False, 'message': 'Unauthorized'})

    df      = get_monthly_summary_df(data.get('month', ''))
    records = [] if df.empty else df.fillna('').to_dict(orient='records')
    return jsonify({'success': True, 'records': records})


@app.route('/api/dashboard/monthly-detail', methods=['POST'])
def api_dash_monthly_detail():
    """Return day-by-day attendance breakdown for every employee in a month."""
    data = request.get_json()
    if not verify_manager_password(data.get('manager_code', '')):
        return jsonify({'success': False, 'message': 'Unauthorized'})

    rows, all_days = get_monthly_detail_df(data.get('month', ''))
    return jsonify({'success': True, 'rows': rows, 'days': all_days})


# ── Manage Employees ──────────────────────────────────────────────────────────

@app.route('/api/dashboard/employees', methods=['POST'])
def api_dash_employees():
    data = request.get_json()
    if not verify_manager_password(data.get('manager_code', '')):
        return jsonify({'success': False, 'message': 'Unauthorized'})
    df      = storage.load_employees()
    records = [] if df.empty else df.fillna('').to_dict(orient='records')
    return jsonify({'success': True, 'records': records})


@app.route('/api/dashboard/employees/update', methods=['POST'])
def api_dash_employees_update():
    data = request.get_json()
    if not verify_manager_password(data.get('manager_code', '')):
        return jsonify({'success': False, 'message': 'Unauthorized'})
    success = storage.update_employee_name(data.get('uid'), data.get('new_name'))
    return jsonify({'success': success})


@app.route('/api/dashboard/employees/delete', methods=['POST'])
def api_dash_employees_delete():
    data = request.get_json()
    if not verify_manager_password(data.get('manager_code', '')):
        return jsonify({'success': False, 'message': 'Unauthorized'})
    success = storage.delete_employee(data.get('uid'))
    return jsonify({'success': success})


# ── Leave Management ──────────────────────────────────────────────────────────

@app.route('/api/dashboard/leaves', methods=['POST'])
def api_dash_leaves():
    data = request.get_json()
    if not verify_manager_password(data.get('manager_code', '')):
        return jsonify({'success': False, 'message': 'Unauthorized'})
    df      = storage.load_leaves()
    records = [] if df.empty else df.fillna('').to_dict(orient='records')
    return jsonify({'success': True, 'records': records})


@app.route('/api/dashboard/leaves/add', methods=['POST'])
def api_dash_leaves_add():
    data = request.get_json()
    if not verify_manager_password(data.get('manager_code', '')):
        return jsonify({'success': False, 'message': 'Unauthorized'})
    storage.add_leave(data.get('uid'), data.get('date'), data.get('leave_type', 'On Leave'))
    return jsonify({'success': True})


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    port = 5000
    threading.Timer(1.2, lambda: webbrowser.open(f'http://localhost:{port}')).start()
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
