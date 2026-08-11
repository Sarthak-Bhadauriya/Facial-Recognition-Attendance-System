"""
face_utils.py — Face recognition helpers for the Attend-X web application.

Only browser-based frame processing is used.
No cv2.imshow / VideoCapture / desktop GUI calls.
"""

import cv2
import face_recognition
import numpy as np
from storage import load_encodings, load_employees


def recognize_frame_for_uid(jpeg_bytes, target_uid):
    """
    Check whether the face in jpeg_bytes matches the encoding stored
    specifically for target_uid. Does NOT compare against all employees.

    Returns one of:
        ('no_face',    '')         – no face detected in frame
        ('no_encoding','')         – target_uid has no stored encoding
        ('mismatch',   '')         – face found but doesn't match target_uid
        ('match',      name:str)   – face matches, attendance should be marked
    """
    nparr = np.frombuffer(jpeg_bytes, np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if frame is None:
        return 'no_face', ''

    rgb   = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    # Downscale for faster recognition
    small = cv2.resize(rgb, (0, 0), fx=0.5, fy=0.5)

    face_locs = face_recognition.face_locations(small)
    if not face_locs:
        return 'no_face', ''

    # Basic Liveness Heuristic (Blur/Texture check)
    # Replaces heavy ML models which are incompatible with Python 3.14
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    variance = cv2.Laplacian(gray, cv2.CV_64F).var()
    
    # A very low variance usually indicates a printed photo or screen
    if variance < 30.0:
        return 'spoof', ''

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
    is_match = face_recognition.compare_faces(
        [stored_enc], detected_enc, tolerance=0.55
    )[0]

    if is_match:
        row  = employees_df[employees_df['unique_id'].astype(str) == str(target_uid)]
        name = row.iloc[0]['name'] if not row.empty else str(target_uid)
        return 'match', name

    return 'mismatch', ''


# Kept for any future use; not called by web routes
def reset_liveness(uid):
    """No-op: liveness check removed. Kept for import compatibility."""
    pass
