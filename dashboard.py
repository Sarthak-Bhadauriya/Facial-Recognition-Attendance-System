import pandas as pd
from datetime import datetime, timezone, timedelta
from storage import load_attendance, load_employees
import calendar

# Indian Standard Time = UTC + 5:30
IST = timezone(timedelta(hours=5, minutes=30))

def now_ist():
    return datetime.now(IST)


def get_today_attendance_df():
    df = load_attendance()
    today_date = now_ist().strftime("%Y-%m-%d")
    df['date_str'] = df['date'].astype(str)
    today_records = df[df['date_str'].str.startswith(today_date)].copy()
    today_records.drop(columns=['date_str'], inplace=True, errors='ignore')
    return today_records


def search_attendance_df(search_type, search_val=None, start_date=None, end_date=None):
    df = load_attendance()
    df['date_str'] = df['date'].astype(str).str.split(' ').str[0]

    filtered_df = pd.DataFrame()

    if search_type == "uid":
        filtered_df = df[df['unique_id'].astype(str) == str(search_val)]
    elif search_type == "name":
        filtered_df = df[df['name'].astype(str).str.contains(str(search_val), case=False, na=False)]
    elif search_type == "date":
        filtered_df = df[(df['date_str'] >= start_date) & (df['date_str'] <= end_date)]

    filtered_df = filtered_df.drop(columns=['date_str'], errors='ignore')
    return filtered_df


def get_monthly_summary_df(month_str):
    """Aggregate totals per employee for a given month (YYYY-MM)."""
    df = load_attendance()
    df['date_str'] = df['date'].astype(str)
    df['month'] = df['date_str'].str[0:7]

    monthly_data = df[df['month'] == month_str]
    if monthly_data.empty:
        return pd.DataFrame()

    summary = []
    grouped = monthly_data.groupby(['unique_id', 'name'])
    for (uid, name), group in grouped:
        total_present = len(group[group['status'].isin(['Present', 'Late'])])
        total_late    = len(group[group['status'] == 'Late'])
        total_absent  = len(group[group['status'] == 'Absent'])
        total_incomplete = len(group[group['status'] == 'Incomplete'])
        total_overtime = pd.to_numeric(group['overtime_hours'], errors='coerce').fillna(0.0).sum()

        summary.append({
            'Unique ID':              uid,
            'Name':                   name,
            'Total Present':          total_present,
            'Total Late':             total_late,
            'Total Absent':           total_absent,
            'Total Incomplete':       total_incomplete,
            'Total Overtime (hrs)':   round(total_overtime, 2),
        })

    return pd.DataFrame(summary)


def get_monthly_detail_df(month_str):
    """
    Day-by-day breakdown for every employee in the given month (YYYY-MM).

    Returns a list of dicts, one per employee:
        {
          'uid':   str,
          'name':  str,
          'days':  { 'YYYY-MM-DD': status_char, ... },   # status P/L/A/I/-
          'totals':{ 'present': n, 'late': n, 'absent': n, 'incomplete': n }
        }
    Also returns a sorted list of all calendar days in the month.
    """
    df = load_attendance()
    employees = load_employees()

    if employees.empty:
        return [], []

    # Parse month
    try:
        year, month = int(month_str[:4]), int(month_str[5:7])
    except Exception:
        return [], []

    # All days in the month
    num_days = calendar.monthrange(year, month)[1]
    all_days = [f"{year}-{month:02d}-{d:02d}" for d in range(1, num_days + 1)]

    # Filter attendance to this month
    df['date_str'] = df['date'].astype(str).str[:10]
    df['month']    = df['date_str'].str[:7]
    monthly        = df[df['month'] == month_str].copy()

    # Build lookup: uid -> { date_str -> status }
    lookup = {}
    for _, row in monthly.iterrows():
        uid  = str(row['unique_id'])
        date = str(row['date_str'])
        stat = str(row.get('status', ''))
        lookup.setdefault(uid, {})[date] = stat

    STATUS_MAP = {
        'Present':    'P',
        'Late':       'L',
        'Absent':     'A',
        'Incomplete': 'I',
        'On Leave':   'OL',
    }

    result = []
    for _, emp in employees.iterrows():
        uid  = str(emp['unique_id'])
        name = str(emp['name'])
        emp_days = lookup.get(uid, {})

        days    = {}
        totals  = {'present': 0, 'late': 0, 'absent': 0, 'incomplete': 0, 'on_leave': 0}
        for day in all_days:
            raw = emp_days.get(day, '')
            char = STATUS_MAP.get(raw, '-')
            days[day] = char
            if char == 'P':  totals['present']    += 1
            elif char == 'L': totals['late']       += 1
            elif char == 'A': totals['absent']     += 1
            elif char == 'I': totals['incomplete'] += 1
            elif char == 'OL': totals['on_leave']  += 1

        result.append({'uid': uid, 'name': name, 'days': days, 'totals': totals})

    return result, all_days
