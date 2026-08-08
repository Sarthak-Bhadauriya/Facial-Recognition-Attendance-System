import sys
from register import register_new_employee
from attendance import start_attendance_scanner
from dashboard import run_dashboard

def main_menu():
    while True:
        print("\n" + "*"*55)
        print("   FACE RECOGNITION ATTENDANCE SYSTEM - MAIN MENU   ")
        print("*"*55)
        print("1. Register New Employee")
        print("2. Mark Attendance")
        print("3. Open Admin Dashboard")
        print("4. Exit")
        
        choice = input("\nEnter your choice (1-4): ").strip()
        
        if choice == '1':
            register_new_employee()
        elif choice == '2':
            start_attendance_scanner()
        elif choice == '3':
            run_dashboard()
        elif choice == '4':
            print("\nExiting the system. Have a great day!")
            sys.exit(0)
        else:
            print("\nInvalid choice. Please enter a number between 1 and 4.")

if __name__ == "__main__":
    main_menu()
