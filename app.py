import streamlit as st
import pandas as pd
from register import perform_registration
from attendance import process_attendance
from face_utils import recognize_faces_continuous
from dashboard import get_today_attendance_df, search_attendance_df, get_monthly_summary_df
import storage

st.set_page_config(page_title="Attend-X | Smart Attendance", layout="wide")

# Custom Premium SaaS CSS
st.markdown("""
<style>
    /* Keyframes for animations */
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }
    @keyframes pulse {
        0% { box-shadow: 0 0 0 0 rgba(102, 126, 234, 0.4); }
        70% { box-shadow: 0 0 0 10px rgba(102, 126, 234, 0); }
        100% { box-shadow: 0 0 0 0 rgba(102, 126, 234, 0); }
    }

    /* Main App Background & Fade-in */
    .stApp {
        background-color: #f8fafc;
        animation: fadeIn 0.6s ease-out;
    }
    
    /* Sidebar Styling */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1e1e2d 0%, #151521 100%) !important;
        border-right: 1px solid rgba(255,255,255,0.05);
    }
    [data-testid="stSidebar"] * {
        color: #e2e8f0 !important;
    }

    /* Sidebar Radio Buttons (Pills) */
    div[role="radiogroup"] > label {
        background-color: rgba(255, 255, 255, 0.03);
        border-radius: 8px;
        padding: 12px 15px;
        margin-bottom: 8px;
        border-left: 3px solid transparent;
        transition: all 0.3s ease;
    }
    div[role="radiogroup"] > label:hover {
        background-color: rgba(255, 255, 255, 0.08);
        transform: translateX(3px);
    }
    div[role="radiogroup"] > label[data-checked="true"] {
        background: linear-gradient(90deg, rgba(102,126,234,0.15) 0%, rgba(102,126,234,0.05) 100%);
        border-left: 4px solid #667eea;
        color: #ffffff !important;
        font-weight: 600;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    /* Hide the default radio circle */
    div[role="radiogroup"] > label > div:first-child {
        display: none;
    }
    div[role="radiogroup"] > label p {
        margin-left: 0 !important;
        font-size: 15px !important;
    }

    /* Primary Action Buttons */
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 10px 24px !important;
        font-weight: 600 !important;
        letter-spacing: 0.5px;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3) !important;
        transition: all 0.3s ease !important;
    }
    .stButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4) !important;
        background: linear-gradient(135deg, #764ba2 0%, #667eea 100%) !important;
    }
    .stButton > button:active {
        transform: translateY(1px) !important;
    }
    
    /* Make the camera start button pulse */
    button:contains("Camera") {
        animation: pulse 2s infinite;
    }

    /* Input Fields */
    .stTextInput > div > div > input, .stSelectbox > div > div > div {
        border-radius: 8px !important;
        border: 1px solid #e2e8f0 !important;
        transition: all 0.3s ease !important;
        background-color: white !important;
    }
    .stTextInput > div > div > input:focus, .stSelectbox > div > div > div:focus {
        border-color: #667eea !important;
        box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.2) !important;
    }
    
    /* Metric Cards - Glassmorphism */
    .glass-card {
        background: rgba(255, 255, 255, 0.7);
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.5);
        border-radius: 16px;
        padding: 24px;
        box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.05);
        text-align: center;
        transition: all 0.3s ease;
        position: relative;
        overflow: hidden;
    }
    .glass-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 12px 40px 0 rgba(31, 38, 135, 0.1);
    }
    /* Adding subtle gradient borders via before pseudo-element */
    .glass-card::before {
        content: "";
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 4px;
        background: linear-gradient(90deg, #667eea, #764ba2);
    }
    
    .glass-card-present::before { background: linear-gradient(90deg, #11998e, #38ef7d); }
    .glass-card-late::before { background: linear-gradient(90deg, #f2994a, #f2c94c); }
    .glass-card-absent::before { background: linear-gradient(90deg, #eb3349, #f45c43); }

    .glass-value {
        font-size: 42px;
        font-weight: 800;
        color: #1e293b;
        margin: 10px 0;
        line-height: 1;
        background: linear-gradient(135deg, #1e293b, #475569);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .glass-label {
        font-size: 13px;
        color: #64748b;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 1.5px;
    }
    .glass-icon {
        font-size: 28px;
        margin-bottom: 5px;
        opacity: 0.8;
    }

    /* Container Borders */
    [data-testid="stVerticalBlock"] > div[style*="border"] {
        border-radius: 12px !important;
        border: 1px solid #e2e8f0 !important;
        box-shadow: 0 4px 20px rgba(0,0,0,0.02) !important;
        background-color: white;
    }
</style>
""", unsafe_allow_html=True)

# Top Header Bar - Premium Hero Style
st.markdown("""
<div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 40px 30px; border-radius: 16px; box-shadow: 0 10px 30px rgba(102, 126, 234, 0.2); margin-bottom: 35px; color: white; display: flex; align-items: center; justify-content: space-between; overflow: hidden; position: relative;">
    <!-- Abstract glowing orb in background -->
    <div style="position: absolute; top: -50px; right: -50px; width: 200px; height: 200px; background: rgba(255,255,255,0.1); border-radius: 50%; filter: blur(40px);"></div>
    
    <div style="position: relative; z-index: 1;">
        <h1 style="color: white; margin: 0 0 10px 0; font-size: 42px; font-weight: 800; letter-spacing: -1px; display: flex; align-items: center;">
            Attend-X
        </h1>
        <p style="color: rgba(255,255,255,0.9); margin: 0; font-size: 18px; font-weight: 400; letter-spacing: 0.5px;">Next-Generation Face Recognition Attendance</p>
    </div>
    
    <div style="background: rgba(255,255,255,0.15); backdrop-filter: blur(10px); padding: 12px 24px; border-radius: 30px; border: 1px solid rgba(255,255,255,0.2); font-weight: 600; font-size: 14px; position: relative; z-index: 1;">
        <span style="display: inline-block; width: 8px; height: 8px; background-color: #4ade80; border-radius: 50%; margin-right: 8px; box-shadow: 0 0 10px #4ade80;"></span> System Active
    </div>
</div>
""", unsafe_allow_html=True)

# Left Sidebar Navigation Menu
menu = st.sidebar.radio("MAIN NAVIGATION", [
    "Register New Employee", 
    "Mark Attendance", 
    "Admin Dashboard", 
    "Exit"
])

if menu == "Register New Employee":
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.container(border=True):
            st.markdown("<h3 style='text-align: center; color: #0b1d3a; padding-bottom: 10px;'>Register New Employee</h3>", unsafe_allow_html=True)
            admin_pwd = st.text_input("Enter Manager Access Code", type="password")
            
            if admin_pwd: 
                st.markdown("<hr style='margin: 15px 0;'>", unsafe_allow_html=True)
                uid = st.text_input("Unique ID")
                name = st.text_input("Full Name")
                
                st.write("")
                if st.button("Open Camera & Register", type="primary", use_container_width=True):
                    with st.spinner("Opening secure camera window... Please look at the camera and press 'c' to capture."):
                        success, msg = perform_registration(admin_pwd, uid, name)
                        if success:
                            st.success(msg)
                        else:
                            st.error(msg)

elif menu == "Mark Attendance":
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.container(border=True):
            st.markdown("<h3 style='text-align: center; color: #0b1d3a; padding-bottom: 10px;'>Live Attendance Scanner</h3>", unsafe_allow_html=True)
            
            emp_pwd_input = st.text_input("Enter Employee Access Code", type="password")
            from config import verify_employee_password
            
            st.write("")
            if emp_pwd_input:
                if verify_employee_password(emp_pwd_input):
                    if st.button("Start Camera and Mark Attendance", type="primary", use_container_width=True):
                        st.info("Live camera feed opening in a secure window. Press 'q' in the window to stop.")
                        
                        msg_placeholder = st.empty()
                        
                        # Yield continuously blocks Streamlit rendering but dynamically updates the placeholder
                        for unique_id, name in recognize_faces_continuous():
                            result_msg = process_attendance(unique_id, name)
                            if "successfully" in result_msg or "already completed" in result_msg:
                                msg_placeholder.success(result_msg)
                            elif "Face not registered" in result_msg:
                                msg_placeholder.error(result_msg)
                            else:
                                msg_placeholder.warning(result_msg)
                                
                        st.success("Camera closed successfully.")
                else:
                    st.error("Incorrect Employee Access Code")

elif menu == "Admin Dashboard":
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        admin_pwd_dash = st.text_input("Enter Manager Access Code", type="password")
    
    from config import verify_manager_password, verify_employee_password
    
    if admin_pwd_dash:
        if verify_manager_password(admin_pwd_dash):
            st.success("Access Granted")
            
            # KPI Metric Cards
            total_emp = len(storage.load_employees())
            df_today = get_today_attendance_df()
            if not df_today.empty:
                present_today = len(df_today[df_today['status'].isin(['Present', 'Late'])])
                late_today = len(df_today[df_today['status'] == 'Late'])
            else:
                present_today = 0
                late_today = 0
            absent_today = total_emp - present_today
            
            m1, m2, m3, m4 = st.columns(4)
            m1.markdown(f'<div class="glass-card"><div class="glass-value">{total_emp}</div><div class="glass-label">Total Employees</div></div>', unsafe_allow_html=True)
            m2.markdown(f'<div class="glass-card glass-card-present"><div class="glass-value">{present_today}</div><div class="glass-label">Present Today</div></div>', unsafe_allow_html=True)
            m3.markdown(f'<div class="glass-card glass-card-late"><div class="glass-value">{late_today}</div><div class="glass-label">Late Today</div></div>', unsafe_allow_html=True)
            m4.markdown(f'<div class="glass-card glass-card-absent"><div class="glass-value">{absent_today}</div><div class="glass-label">Absent Today</div></div>', unsafe_allow_html=True)
            
            # Data Views
            dash_tabs = st.tabs(["Today's Attendance", "Search Records", "Monthly Summary"])
            
            with dash_tabs[0]:
                with st.container(border=True):
                    st.subheader("Today's Attendance Roster")
                    if df_today.empty:
                        st.info("No attendance records found for today.")
                    else:
                        st.dataframe(df_today, use_container_width=True)
                        csv = df_today.to_csv(index=False).encode('utf-8')
                        st.download_button("Export Today's Data to CSV", csv, "today_attendance.csv", "text/csv", type="primary")
                    
            with dash_tabs[1]:
                with st.container(border=True):
                    st.subheader("Search Historical Records")
                    search_type = st.selectbox("Search By", ["Unique ID", "Name", "Date Range"])
                    
                    df_search = pd.DataFrame()
                    if search_type == "Unique ID":
                        uid_search = st.text_input("Enter Unique ID")
                        if st.button("Search ID", type="secondary"):
                            df_search = search_attendance_df("uid", uid_search)
                    elif search_type == "Name":
                        name_search = st.text_input("Enter Name")
                        if st.button("Search Name", type="secondary"):
                            df_search = search_attendance_df("name", name_search)
                    else:
                        c1, c2 = st.columns(2)
                        start_date = c1.date_input("Start Date")
                        end_date = c2.date_input("End Date")
                        if st.button("Search Dates", type="secondary"):
                            df_search = search_attendance_df("date", None, start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))
                            
                    if not df_search.empty:
                        st.dataframe(df_search, use_container_width=True)
                        csv_s = df_search.to_csv(index=False).encode('utf-8')
                        st.download_button("Export Search Results", csv_s, "search_results.csv", "text/csv", type="primary")
                    
            with dash_tabs[2]:
                with st.container(border=True):
                    st.subheader("Monthly Performance Summary")
                    month_input = st.text_input("Enter Month (YYYY-MM, e.g. 2026-08)")
                    if st.button("Generate Summary", type="secondary"):
                        df_month = get_monthly_summary_df(month_input)
                        if df_month.empty:
                            st.info("No records found for this month.")
                        else:
                            st.dataframe(df_month, use_container_width=True)
                            csv_m = df_month.to_csv(index=False).encode('utf-8')
                            st.download_button("Export Monthly Summary", csv_m, f"summary_{month_input}.csv", "text/csv", type="primary")
                        
        elif verify_employee_password(admin_pwd_dash):
            st.error("Manager access required to view this page.")
        else:
            st.error("Access Denied. Incorrect Manager Access Code.")

elif menu == "Exit":
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.container(border=True):
            st.markdown("<h3 style='text-align: center; color: #0b1d3a;'>Exit System</h3>", unsafe_allow_html=True)
            st.info("You can safely close this browser tab to exit the dashboard. To fully stop the backend server, press Ctrl+C in your terminal.")
