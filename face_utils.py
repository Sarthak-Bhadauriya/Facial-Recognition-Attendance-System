import cv2
import face_recognition
import numpy as np
from storage import load_encodings, load_employees


def recognize_single_frame(jpeg_bytes):
    """
    Process a single JPEG frame from the browser (no GUI window).

    Args:
        jpeg_bytes: Raw JPEG bytes (from browser canvas capture).

    Returns:
        (unique_id, name)  – matched employee
        ("Unknown", "Unknown") – face found but not in database
        (None, None)           – no face detected in the frame
    """
    nparr = np.frombuffer(jpeg_bytes, np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if frame is None:
        return None, None

    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    # Downscale for faster recognition
    small = cv2.resize(rgb, (0, 0), fx=0.5, fy=0.5)

    face_locs = face_recognition.face_locations(small)
    if not face_locs:
        return None, None

    face_encs = face_recognition.face_encodings(small, face_locs)
    if not face_encs:
        return None, None

    encodings_dict = load_encodings()
    employees_df   = load_employees()

    known_encs = list(encodings_dict.values())
    known_ids  = list(encodings_dict.keys())

    if not known_encs:
        return "Unknown", "Unknown"

    face_enc  = face_encs[0]
    matches   = face_recognition.compare_faces(known_encs, face_enc, tolerance=0.55)
    distances = face_recognition.face_distance(known_encs, face_enc)

    best = int(np.argmin(distances))
    if matches[best]:
        uid = known_ids[best]
        row = employees_df[employees_df['unique_id'].astype(str) == str(uid)]
        name = row.iloc[0]['name'] if not row.empty else str(uid)
        return uid, name

    return "Unknown", "Unknown"


import math

# Global state for liveness tracking (uid -> dict)
liveness_state = {}

def calculate_ear(eye_points):
    """Calculate Eye Aspect Ratio (EAR) given 6 (x,y) eye landmarks."""
    A = math.dist(eye_points[1], eye_points[5])
    B = math.dist(eye_points[2], eye_points[4])
    C = math.dist(eye_points[0], eye_points[3])
    return (A + B) / (2.0 * C) if C != 0 else 0

def recognize_frame_for_uid(jpeg_bytes, target_uid):
    """
    Check whether the face in jpeg_bytes matches the encoding stored
    specifically for target_uid. Does NOT compare against all employees —
    Process a single JPEG frame and check if it matches target_uid.
    Also implements Liveness Detection (Blink tracking).
    """
    nparr = np.frombuffer(jpeg_bytes, np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if frame is None:
        return 'no_face', ''

    rgb   = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    small = cv2.resize(rgb, (0, 0), fx=0.5, fy=0.5)

    face_locs = face_recognition.face_locations(small)
    if not face_locs:
        return 'no_face', ''

    face_encs = face_recognition.face_encodings(small, face_locs)
    if not face_encs:
        return 'no_face', ''

    encodings_dict = load_encodings()
    employees_df   = load_employees()

    # Keys may be str or original type — try both
    stored_enc = encodings_dict.get(str(target_uid))
    if stored_enc is None:
        stored_enc = encodings_dict.get(target_uid)
    if stored_enc is None:
        return 'no_encoding', ''

    detected_enc = face_encs[0]
    is_match     = face_recognition.compare_faces([stored_enc], detected_enc, tolerance=0.55)[0]

    if is_match:
        # Liveness Detection: Check EAR for blinks
        landmarks = face_recognition.face_landmarks(small, face_locations=face_locs)
        if landmarks:
            left_eye = landmarks[0].get('left_eye')
            right_eye = landmarks[0].get('right_eye')
            if left_eye and right_eye:
                ear = (calculate_ear(left_eye) + calculate_ear(right_eye)) / 2.0
                state = liveness_state.get(str(target_uid), {'blinks': 0, 'eyes_closed_frames': 0})
                
                if ear < 0.22:
                    state['eyes_closed_frames'] += 1
                else:
                    if state['eyes_closed_frames'] >= 1:
                        state['blinks'] += 1
                    state['eyes_closed_frames'] = 0
                
                liveness_state[str(target_uid)] = state
                
                if state['blinks'] == 0:
                    return 'liveness_pending', 'Please blink to verify...'
                
                # Clear state on success
                del liveness_state[str(target_uid)]
        
        row  = employees_df[employees_df['unique_id'].astype(str) == str(target_uid)]
        name = row.iloc[0]['name'] if not row.empty else str(target_uid)
        return 'match', name

    return 'mismatch', ''


def recognize_faces_continuous():
    """
    Opens the webcam, continuously scans for faces, and yields the detected 
    faces against stored encodings until the user presses 'q'.
    
    Yields:
        tuple: (unique_id, name) or ("Unknown", "Unknown")
    """
    encodings_dict = load_encodings()
    employees_df = load_employees()
    
    # Prepare lists of known encodings and their corresponding IDs
    known_face_encodings = list(encodings_dict.values())
    known_face_ids = list(encodings_dict.keys())

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: Could not access the webcam.")
        return

    print("\nScanning for faces...")
    print("Please look at the camera. Press 'q' to cancel.")

    process_this_frame = True

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Failed to grab frame from webcam.")
            break

        # Resize frame of video to 1/4 size for faster face recognition processing
        small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
        # Convert BGR (OpenCV format) to RGB (face_recognition format)
        rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)

        if process_this_frame:
            # Find all the faces in the current frame of video
            face_locations = face_recognition.face_locations(rgb_small_frame)
            
            if face_locations:
                face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)
                
                # For simplicity, we process the first face found in the frame
                face_encoding = face_encodings[0]
                
                matched_id = "Unknown"
                matched_name = "Unknown"
                
                if len(known_face_encodings) > 0:
                    matches = face_recognition.compare_faces(known_face_encodings, face_encoding)
                    face_distances = face_recognition.face_distance(known_face_encodings, face_encoding)
                    
                    if len(face_distances) > 0:
                        best_match_index = np.argmin(face_distances)
                        if matches[best_match_index]:
                            matched_id = known_face_ids[best_match_index]
                            
                            # Retrieve the name from employees.csv
                            emp_record = employees_df[employees_df['unique_id'].astype(str) == str(matched_id)]
                            if not emp_record.empty:
                                matched_name = emp_record.iloc[0]['name']

                # Draw a box around the face and display it briefly
                top, right, bottom, left = face_locations[0]
                top *= 4; right *= 4; bottom *= 4; left *= 4
                
                color = (0, 255, 0) if matched_id != "Unknown" else (0, 0, 255)
                cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
                
                label = f"{matched_name} ({matched_id})" if matched_id != "Unknown" else "Unknown"
                cv2.rectangle(frame, (left, bottom - 35), (right, bottom), color, cv2.FILLED)
                cv2.putText(frame, label, (left + 6, bottom - 6), cv2.FONT_HERSHEY_DUPLEX, 0.6, (255, 255, 255), 1)
                
                cv2.imshow("Face Scanner", frame)
                cv2.waitKey(1000) # Display the result for 1 second to provide feedback
                
                # Yield the detected face to the attendance processor
                yield matched_id, matched_name
                
                # Skip the standard waitKey below for this iteration so we don't delay twice
                continue

        # Toggle process_this_frame to skip the next frame for efficiency
        process_this_frame = not process_this_frame

        cv2.imshow("Face Scanner", frame)
        
        # Hit 'q' on the keyboard to quit!
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # Clean up resources
    cap.release()
    cv2.destroyAllWindows()
