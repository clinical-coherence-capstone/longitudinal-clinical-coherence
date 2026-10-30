"""Authentication helpers for the LCC web application. Uses bcrypt for password hashing. Never stores or returns plain-text passwords."""
import sqlite3
import bcrypt

try:
    from .database import create_user, get_user_by_username
except ImportError:
    from webapp.database import create_user, get_user_by_username

MIN_PASSWORD_LEN: int = 8


def hash_password(plain: str) -> str:
    """Hash a plaintext password using bcrypt and salt."""
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plaintext password against a stored bcrypt hash."""
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


def register_user(username: str, password: str) -> tuple[bool, str]:
    """Validate registration details and create user record.
    
    Returns (True, message) on success or (False, reason) on failure.
    """
    if not username or not username.strip():
        return False, "Username cannot be empty."
    clean_username = username.strip()
    if len(clean_username) > 50:
        return False, "Username must be 50 characters or fewer."
    if len(password) < MIN_PASSWORD_LEN:
        return False, f"Password must be at least {MIN_PASSWORD_LEN} characters long."

    hashed = hash_password(password)
    try:
        create_user(clean_username, hashed)
        return True, "Registration successful."
    except sqlite3.IntegrityError:
        return False, "Username already taken."
    except Exception as e:
        return False, f"Registration failed: {str(e)}"


def login_user(username: str, password: str) -> tuple[bool, str, int | None]:
    """Authenticate a user. Returns (True, message, user_id) or (False, 'Invalid credentials.', None)."""
    if not username or not password:
        return False, "Invalid credentials.", None

    clean_username = username.strip()
    user = get_user_by_username(clean_username)
    if user is None:
        return False, "Invalid credentials.", None

    if not verify_password(password, user["password_hash"]):
        return False, "Invalid credentials.", None

    return True, "Login successful.", user["id"]
