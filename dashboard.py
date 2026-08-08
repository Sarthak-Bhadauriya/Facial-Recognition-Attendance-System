import pandas as pd
from datetime import datetime
from storage import load_attendance

def get_today_attendance_df():
    df = load_attendance()
    today_date = datetime.now().strftime("%Y-%m-%d")
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
        total_late = len(group[group['status'] == 'Late'])
        total_overtime = pd.to_numeric(group['overtime_hours'], errors='coerce').fillna(0.0).sum()
        
        summary.append({
            'Unique ID': uid,
            'Name': name,
            'Total Days Present': total_present,
            'Total Late Days': total_late,
            'Total Overtime (hrs)': round(total_overtime, 2)
        })
        
    return pd.DataFrame(summary)
