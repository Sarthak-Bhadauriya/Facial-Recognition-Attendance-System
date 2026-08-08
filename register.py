import cv2
import face_recognition
import numpy as np
import os
from storage import load_employees, save_employee, save_encoding
from config import verify_manager_password, verify_employee_password

KNOWN_FACES_DIR = 'known_faces'

def check_duplicate_id(unique_id):
    df = load_employees()
    return str(unique_id) in df['unique_id'].astype(str).values


def perform_registration_from_frame(emp_pwd, unique_id, name, jpeg_bytes):
    """
    Register a new employee using a JPEG frame captured by the browser.
    Requires the COMMON EMPLOYEE ACCESS CODE (not the manager code).
    No cv2.imshow / VideoCapture required.

    Args:
        emp_pwd:    Common Employee Access Code string.
        unique_id:  Unique employee identifier string.
        name:       Employee full name string.
        jpeg_bytes: Raw JPEG bytes from the browser canvas.

    Returns:
        (True, success_message) or (False, error_message)
    """
    if not verify_employee_password(emp_pwd):
        return False, "Error: Incorrect Employee Access Code."

    if not unique_id or not name:
        return False, "Error: Unique ID and Name cannot be empty."

    if check_duplicate_id(unique_id):
        return False, f"Error: Employee with ID '{unique_id}' already exists."

    nparr = np.frombuffer(jpeg_bytes, np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if frame is None:
        return False, "Error: Could not decode the captured image."

    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    face_locs = face_recognition.face_locations(rgb)

    if len(face_locs) == 0:
        return False, "No face detected in the image. Please position your face clearly and try again."
    if len(face_locs) > 1:
        return False, "Multiple faces detected. Please ensure only one person is in frame."

    encs = face_recognition.face_encodings(rgb, face_locs)
    if not encs:
        return False, "Could not extract face encoding. Please try again with better lighting."

    face_encoding = encs[0]

    try:
        os.makedirs(KNOWN_FACES_DIR, exist_ok=True)
        img_path = os.path.join(KNOWN_FACES_DIR, f"{unique_id}.jpg")
        cv2.imwrite(img_path, frame)
        save_encoding(unique_id, face_encoding)
        save_employee(unique_id, name)
        return True, f"Employee {name} (ID: {unique_id}) registered successfully."
    except Exception as e:
        return False, f"Error saving data: {e}"


# ── Legacy CLI method (kept for backward compatibility) ─────────────────────
def perform_registration(admin_pwd, unique_id, name):
    """
    Original OpenCV-window-based registration (for CLI use only).
    The web UI uses perform_registration_from_frame() instead.
    """
    if not verify_manager_password(admin_pwd):
        return False, "Error: Incorrect Manager Access Code."

    if not unique_id or not name:
        return False, "Error: Unique ID and Name cannot be empty."

    if check_duplicate_id(unique_id):
        return False, f"Error: Employee with ID {unique_id} already exists."

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        return False, "Error: Could not access the webcam."

    face_encoding = None
    captured_frame = None

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        cv2.imshow("Registration - Press 'c' to capture, 'q' to quit", frame)
        key = cv2.waitKey(1) & 0xFF
        if key == ord('c'):
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            face_locations = face_recognition.face_locations(rgb_frame)
            if len(face_locations) == 0:
                print("No face detected. Try again.")
            elif len(face_locations) > 1:
                print("Multiple faces detected.")
            else:
                encodings = face_recognition.face_encodings(rgb_frame, face_locations)
                if encodings:
                    face_encoding = encodings[0]
                    captured_frame = frame
                    break
        elif key == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

    if face_encoding is not None:
        try:
            os.makedirs(KNOWN_FACES_DIR, exist_ok=True)
            image_path = os.path.join(KNOWN_FACES_DIR, f"{unique_id}.jpg")
            cv2.imwrite(image_path, captured_frame)
            save_encoding(unique_id, face_encoding)
            save_employee(unique_id, name)
            return True, f"Employee {name} (ID: {unique_id}) registered successfully."
        except Exception as e:
            return False, f"An error occurred while saving data: {e}"

    return False, "Registration cancelled or face not captured clearly."
