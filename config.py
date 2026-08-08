import hashlib

# ── Generative AI (Gemini) ──────────────────────────────────────────────────
# Get your free API key at: https://aistudio.google.com/app/apikey
GEMINI_API_KEY = "AQ.Ab8RN6JWryMw66CRtqR-G8BZmsBXMrp1AEbWp4PeP9GDk2jrqQ"

# Default Passwords (In a real application, these should be loaded from environment variables)
# We store them as hashes.
# Manager Password Default: admin123
# Employee Password Default: emp123

MANAGER_PASSWORD_HASH = hashlib.sha256("admin123".encode()).hexdigest()
COMMON_EMPLOYEE_PASSWORD_HASH = hashlib.sha256("emp123".encode()).hexdigest()

def hash_password(password):
    """Returns the SHA-256 hash of the given password string."""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_manager_password(input_password):
    return hash_password(input_password) == MANAGER_PASSWORD_HASH

def verify_employee_password(input_password):
    return hash_password(input_password) == COMMON_EMPLOYEE_PASSWORD_HASH

# ── Attendance & Shift Rules ────────────────────────────────────────────────
# Configurable settings for attendance calculation.
# SHIFT_START_TIME: Time after which an employee is considered "Late" (plus grace period).
# SHIFT_END_TIME: Time after which an employee starts accumulating "Overtime".

SHIFT_START_TIME = "10:00:00"
LATE_GRACE_MINS  = 15          # Employees checking in before 10:15 AM are "Present", not "Late".
SHIFT_END_TIME   = "19:00:00"
