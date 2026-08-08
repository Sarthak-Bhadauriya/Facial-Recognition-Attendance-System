import sys
import os
import unittest
from unittest.mock import patch, MagicMock
import numpy as np
import pandas as pd
from io import StringIO
import cv2

# Clean up any existing files to start fresh for testing
for f in ['employees.csv', 'face_encodings.pkl', 'attendance.xlsx', 'export_test.xlsx']:
    if os.path.exists(f):
        os.remove(f)

# Import local modules
import storage
import register
import face_utils
import attendance
import dashboard
import main

class SystemTest(unittest.TestCase):
    def setUp(self):
        # Redirect stdout to capture print statements
        self.held, sys.stdout = sys.stdout, StringIO()
        
    def tearDown(self):
        sys.stdout = self.held

    def get_output(self):
        return sys.stdout.getvalue()

    @patch('builtins.input')
    @patch('cv2.VideoCapture')
    @patch('cv2.imshow')
    @patch('cv2.waitKey')
    @patch('cv2.destroyAllWindows')
    @patch('face_recognition.face_locations')
    @patch('face_recognition.face_encodings')
    def test_01_register_new_employee(self, mock_encodings, mock_locations, mock_destroy, mock_waitkey, mock_imshow, mock_videocapture, mock_input):
        mock_input.side_effect = ["admin123", "101", "Test User", "password"]
        
        # Mock Camera
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        dummy_frame = np.zeros((100, 100, 3), dtype=np.uint8)
        mock_cap.read.return_value = (True, dummy_frame)
        mock_videocapture.return_value = mock_cap
        
        # Mock key presses: 'c' to capture
        mock_waitkey.side_effect = [ord('c')]
        
        # Mock face recognition
        mock_locations.return_value = [(0, 10, 10, 0)]
        mock_encodings.return_value = [np.array([0.1, 0.2, 0.3])]
        
        register.register_new_employee()
        
        output = self.get_output()
        self.assertIn("Employee Test User (ID: 101) registered successfully", output)
        
        # Check files
        df = pd.read_csv('employees.csv')
        self.assertEqual(len(df), 1)
        self.assertEqual(str(df.iloc[0]['unique_id']), "101")
        
        encodings = storage.load_encodings()
        self.assertIn("101", encodings)

    @patch('builtins.input')
    def test_02_duplicate_registration(self, mock_input):
        mock_input.side_effect = ["admin123", "101"]
        register.register_new_employee()
        
        output = self.get_output()
        self.assertIn("Error: Employee with ID 101 already exists.", output)

    @patch('attendance.recognize_faces_continuous')
    def test_03_mark_attendance_time_in(self, mock_recognize):
        mock_recognize.return_value = iter([("101", "Test User")])
        attendance.start_attendance_scanner()
        
        output = self.get_output()
        self.assertIn("Time-In marked successfully for Test User", output)
        
        df = pd.read_excel('attendance.xlsx')
        self.assertEqual(len(df), 1)
        self.assertEqual(str(df.iloc[0]['unique_id']), "101")
        self.assertFalse(pd.isna(df.iloc[0]['time_in']))
        # In pandas, empty string might be read as nan or empty string depending on engine
        self.assertTrue(pd.isna(df.iloc[0]['time_out']) or str(df.iloc[0]['time_out']).strip() == "nan" or df.iloc[0]['time_out'] == "")

    @patch('attendance.recognize_faces_continuous')
    def test_04_mark_attendance_time_out(self, mock_recognize):
        mock_recognize.return_value = iter([("101", "Test User")])
        attendance.start_attendance_scanner()
        
        output = self.get_output()
        self.assertIn("Time-Out marked successfully for Test User", output)
        
        df = pd.read_excel('attendance.xlsx')
        val = str(df.iloc[0]['time_out']).strip()
        self.assertTrue(val != "" and val != "nan" and val != "None")

    @patch('attendance.recognize_faces_continuous')
    def test_05_mark_attendance_third_time(self, mock_recognize):
        mock_recognize.return_value = iter([("101", "Test User")])
        attendance.start_attendance_scanner()
        
        output = self.get_output()
        self.assertIn("Attendance already completed for Test User today", output)

    @patch('attendance.recognize_faces_continuous')
    def test_06_unregistered_face(self, mock_recognize):
        mock_recognize.return_value = iter([("Unknown", "Unknown")])
        attendance.start_attendance_scanner()
        
        output = self.get_output()
        self.assertIn("Face not registered.", output)

    @patch('builtins.input')
    def test_07_admin_dashboard_view(self, mock_input):
        mock_input.side_effect = ["admin123", "1", "n", "4"]
        dashboard.run_dashboard()
        
        output = self.get_output()
        self.assertIn("Today's Attendance", output)
        self.assertIn("Test User", output)

    @patch('builtins.input')
    def test_08_admin_dashboard_export(self, mock_input):
        mock_input.side_effect = ["admin123", "1", "y", "export_test.xlsx", "4"]
        dashboard.run_dashboard()
        
        output = self.get_output()
        self.assertIn("Data successfully exported to export_test.xlsx", output)
        self.assertTrue(os.path.exists("export_test.xlsx"))

if __name__ == '__main__':
    unittest.main(verbosity=2)
