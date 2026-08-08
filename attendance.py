import pandas as pd
from datetime import datetime
from storage import get_today_record, save_attendance_record, update_today_record, load_attendance, ATTENDANCE_FILE
from config import SHIFT_START_TIME, LATE_GRACE_MINS, SHIFT_END_TIME
from datetime import timedelta

def process_attendance(unique_id, name):
    """
    Core logic applied to a recognized face.
    Returns a string message describing what happened.
    """
    if unique_id == "Unknown":
        return "Face not registered. Please register first using your Unique ID and password before marking attendance."
        
    today_date = datetime.now().strftime("%Y-%m-%d")
    current_time_str = datetime.now().strftime("%H:%M:%S")
    current_time_obj = datetime.now().time()
    
    record = get_today_record(unique_id)
    
    if record is None:
        status = "Present"
        # Calculate Late threshold
        shift_start_dt = datetime.strptime(SHIFT_START_TIME, "%H:%M:%S")
        late_threshold_dt = shift_start_dt + timedelta(minutes=LATE_GRACE_MINS)
        late_threshold_time = late_threshold_dt.time()
        
        if current_time_obj > late_threshold_time:
            status = "Late"
            
        new_record = {
            'unique_id': unique_id,
            'name': name,
            'date': today_date,
            'time_in': current_time_str,
            'time_out': "",
            'status': status,
            'overtime_hours': 0.0
        }
        
        save_attendance_record(new_record)
        return f"Time-In marked successfully for {name} at {current_time_str}."
        
    else:
        time_out_val = str(record.get('time_out', "")).strip()
        
        if time_out_val != "" and time_out_val != "nan" and time_out_val != "None":
            return f"Attendance already completed for {name} today. Only one Time-In and one Time-Out allowed per day."
        else:
            shift_end_time_obj = datetime.strptime(SHIFT_END_TIME, "%H:%M:%S").time()
            overtime = 0.0
            
            if current_time_obj > shift_end_time_obj:
                end_of_regular = datetime.strptime(SHIFT_END_TIME, "%H:%M:%S")
                current_dt = datetime.strptime(current_time_str, "%H:%M:%S")
                diff = current_dt - end_of_regular
                overtime = round(diff.total_seconds() / 3600.0, 2)
                
            updated_data = {
                'time_out': current_time_str,
                'overtime_hours': overtime
            }
            
            update_today_record(unique_id, updated_data)
            msg = f"Time-Out marked successfully for {name} at {current_time_str}."
            if overtime > 0:
                msg += f" Overtime logged: {overtime} hours."
            return msg

def finalize_incomplete_attendance():
    """
    End-of-day script: 
    marks "Incomplete" for anyone who clocked in but never clocked out.
    """
    df = load_attendance()
    today_date = datetime.now().strftime("%Y-%m-%d")
    
    mask = (df['date'] == today_date) & (df['time_out'].isna() | (df['time_out'] == ""))
    
    if mask.any():
        df.loc[mask, 'status'] = "Incomplete"
        df.to_excel(ATTENDANCE_FILE, index=False, engine='openpyxl')
        return f"Marked {mask.sum()} incomplete attendances."
    else:
        return "No incomplete attendances found for today."
