import os
import pandas as pd
import pickle
from datetime import datetime

EMPLOYEES_FILE = 'employees.csv'
ENCODINGS_FILE = 'face_encodings.pkl'
ATTENDANCE_FILE = 'attendance.xlsx'
LEAVES_FILE = 'leaves.csv'

def _init_files():
    # Initialize employees.csv
    if not os.path.exists(EMPLOYEES_FILE):
        df = pd.DataFrame(columns=['unique_id', 'name', 'registered_on'])
        df.to_csv(EMPLOYEES_FILE, index=False)
        
    # Initialize face_encodings.pkl
    if not os.path.exists(ENCODINGS_FILE):
        with open(ENCODINGS_FILE, 'wb') as f:
            pickle.dump({}, f)
            
    # Initialize attendance.xlsx
    if not os.path.exists(ATTENDANCE_FILE):
        df = pd.DataFrame(columns=['unique_id', 'name', 'date', 'time_in', 'time_out', 'status', 'overtime_hours'])
        df.to_excel(ATTENDANCE_FILE, index=False)

    # Initialize leaves.csv
    if not os.path.exists(LEAVES_FILE):
        df = pd.DataFrame(columns=['unique_id', 'date', 'leave_type'])
        df.to_csv(LEAVES_FILE, index=False)

# Initialize files on module import
_init_files()

def load_employees():
    return pd.read_csv(EMPLOYEES_FILE)

def save_employee(unique_id, name):
    df = load_employees()
    if unique_id in df['unique_id'].astype(str).values or unique_id in df['unique_id'].values:
        raise ValueError(f"Employee with ID {unique_id} already exists.")
    
    registered_on = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    new_employee = pd.DataFrame([{
        'unique_id': unique_id, 
        'name': name, 
        'registered_on': registered_on
    }])
    df = pd.concat([df, new_employee], ignore_index=True)
    df.to_csv(EMPLOYEES_FILE, index=False)

def update_employee_name(unique_id, new_name):
    df = load_employees()
    mask = df['unique_id'].astype(str) == str(unique_id)
    if mask.any():
        df.loc[mask, 'name'] = new_name
        df.to_csv(EMPLOYEES_FILE, index=False)
        return True
    return False

def delete_employee(unique_id):
    # 1. Delete from employees.csv
    df = load_employees()
    mask = df['unique_id'].astype(str) == str(unique_id)
    if mask.any():
        df = df[~mask]
        df.to_csv(EMPLOYEES_FILE, index=False)
        
    # 2. Delete encoding
    encodings = load_encodings()
    if str(unique_id) in encodings:
        del encodings[str(unique_id)]
    elif unique_id in encodings:
        del encodings[unique_id]
    with open(ENCODINGS_FILE, 'wb') as f:
        pickle.dump(encodings, f)
    
    return True

def load_encodings():
    with open(ENCODINGS_FILE, 'rb') as f:
        return pickle.load(f)

def save_encoding(unique_id, encoding):
    encodings = load_encodings()
    encodings[unique_id] = encoding
    with open(ENCODINGS_FILE, 'wb') as f:
        pickle.dump(encodings, f)

def load_attendance():
    return pd.read_excel(ATTENDANCE_FILE)

def save_attendance_record(row):
    """
    row is a dictionary containing:
    unique_id, name, date, time_in, time_out, status, overtime_hours
    """
    df = load_attendance()
    new_record = pd.DataFrame([row])
    df = pd.concat([df, new_record], ignore_index=True)
    df.to_excel(ATTENDANCE_FILE, index=False, engine='openpyxl')

def get_today_record(unique_id):
    df = load_attendance()
    today_date = datetime.now().strftime("%Y-%m-%d")
    
    # Filter by unique_id and today's date
    df['unique_id'] = df['unique_id'].astype(str)
    record = df[(df['unique_id'] == str(unique_id)) & (df['date'] == today_date)]
    
    if not record.empty:
        record = record.fillna("")
        return record.iloc[-1].to_dict()
    return None

def update_today_record(unique_id, updated_data):
    df = load_attendance()
    today_date = datetime.now().strftime("%Y-%m-%d")
    df['unique_id'] = df['unique_id'].astype(str)
    
    mask = (df['unique_id'] == str(unique_id)) & (df['date'] == today_date)
    
    if mask.any():
        for key, value in updated_data.items():
            df[key] = df[key].astype(object)
            df.loc[mask, key] = value
        
        df.to_excel(ATTENDANCE_FILE, index=False, engine='openpyxl')

# ── Leave Management ──────────────────────────────────────────────────────────
def load_leaves():
    return pd.read_csv(LEAVES_FILE)

def add_leave(unique_id, date, leave_type):
    df = load_leaves()
    # Check if already exists for that date
    mask = (df['unique_id'].astype(str) == str(unique_id)) & (df['date'] == str(date))
    if mask.any():
        df.loc[mask, 'leave_type'] = leave_type
    else:
        new_leave = pd.DataFrame([{'unique_id': str(unique_id), 'date': str(date), 'leave_type': leave_type}])
        df = pd.concat([df, new_leave], ignore_index=True)
    df.to_csv(LEAVES_FILE, index=False)

def get_leave(unique_id, date):
    df = load_leaves()
    mask = (df['unique_id'].astype(str) == str(unique_id)) & (df['date'] == str(date))
    if mask.any():
        return df.loc[mask, 'leave_type'].values[0]
    return None
