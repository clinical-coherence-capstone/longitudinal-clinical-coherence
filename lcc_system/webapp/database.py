
"""SQLite persistence layer for the LCC web application."""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB_PATH: Path = Path(__file__).parent / "lcc_webapp.db"


def _clean_text(value, required=False):
    """Safely convert a value to cleaned text."""
    if value is None:
        return "" if required else None

    cleaned = str(value).strip()

    if not cleaned:
        return "" if required else None

    return cleaned


def get_connection() -> sqlite3.Connection:
    """Open a SQLite connection to DB_PATH with row factory enabled."""
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Initialize database tables if they do not exist."""
    conn = get_connection()
    try:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS patient_profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER UNIQUE NOT NULL REFERENCES users(id),
                preferred_name TEXT NOT NULL,
                age_or_dob TEXT,
                sex_assigned_at_birth TEXT,
                gender_identity TEXT,
                medical_conditions TEXT,
                known_allergies TEXT,
                current_medications TEXT,
                medical_history TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id),
                title TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id INTEGER NOT NULL REFERENCES conversations(id),
                role TEXT NOT NULL CHECK(role IN ('user','assistant')),
                content TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS patient_states (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id INTEGER NOT NULL REFERENCES conversations(id),
                turn_number INTEGER NOT NULL,
                state_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS verification_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id INTEGER NOT NULL REFERENCES messages(id),
                flags_json TEXT NOT NULL,
                gate_decision TEXT NOT NULL,
                reasoning TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            """
        )
        conn.commit()
    finally:
        conn.close()


def create_user(username: str, password_hash: str) -> int:
    """Create a new user. Raises IntegrityError if username already exists."""
    now = datetime.now(timezone.utc).isoformat()
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO users (username, password_hash, created_at)
            VALUES (?, ?, ?)
            """,
            (username, password_hash, now),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def get_user_by_username(username: str) -> sqlite3.Row | None:
    """Retrieve user record by username."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM users WHERE username = ? LIMIT 1",
            (username,),
        )
        return cursor.fetchone()
    finally:
        conn.close()


def get_user_by_id(user_id: int) -> sqlite3.Row | None:
    """Retrieve user record by user ID."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM users WHERE id = ? LIMIT 1",
            (user_id,),
        )
        return cursor.fetchone()
    finally:
        conn.close()


def save_patient_profile(user_id: int, profile_data: dict) -> None:
    """Create or update patient profile for a user."""
    now = datetime.now(timezone.utc).isoformat()

    preferred_name = _clean_text(
        profile_data.get("preferred_name"),
        required=True,
    )

    if not preferred_name:
        raise ValueError("Preferred name cannot be empty.")

    profile_values = (
        user_id,
        preferred_name,
        _clean_text(profile_data.get("age_or_dob")),
        _clean_text(profile_data.get("sex_assigned_at_birth")),
        _clean_text(profile_data.get("gender_identity")),
        _clean_text(profile_data.get("medical_conditions")),
        _clean_text(profile_data.get("known_allergies")),
        _clean_text(profile_data.get("current_medications")),
        _clean_text(profile_data.get("medical_history")),
        now,
        now,
    )

    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO patient_profiles (
                user_id,
                preferred_name,
                age_or_dob,
                sex_assigned_at_birth,
                gender_identity,
                medical_conditions,
                known_allergies,
                current_medications,
                medical_history,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)

            ON CONFLICT(user_id) DO UPDATE SET
                preferred_name = excluded.preferred_name,
                age_or_dob = excluded.age_or_dob,
                sex_assigned_at_birth = excluded.sex_assigned_at_birth,
                gender_identity = excluded.gender_identity,
                medical_conditions = excluded.medical_conditions,
                known_allergies = excluded.known_allergies,
                current_medications = excluded.current_medications,
                medical_history = excluded.medical_history,
                updated_at = excluded.updated_at
            """,
            profile_values,
        )
        conn.commit()
    finally:
        conn.close()


def get_patient_profile(user_id: int) -> sqlite3.Row | None:
    """Retrieve patient profile for a user ID."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM patient_profiles WHERE user_id = ? LIMIT 1",
            (user_id,),
        )
        return cursor.fetchone()
    finally:
        conn.close()


def create_conversation(user_id: int, title: str) -> int:
    """Create a new conversation for a user."""
    now = datetime.now(timezone.utc).isoformat()
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO conversations (user_id, title, created_at, updated_at)
            VALUES (?, ?, ?, ?)
            """,
            (user_id, title, now, now),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def get_conversations_for_user(user_id: int, search_query: str | None = None) -> list[sqlite3.Row]:
    """Retrieve conversations ordered by most recently updated, optionally filtering by search query."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        if search_query and search_query.strip():
            pattern = f"%{search_query.strip()}%"
            cursor.execute(
                """
                SELECT DISTINCT c.* FROM conversations c
                LEFT JOIN messages m ON c.id = m.conversation_id
                WHERE c.user_id = ? AND (c.title LIKE ? OR m.content LIKE ?)
                ORDER BY c.updated_at DESC
                """,
                (user_id, pattern, pattern),
            )
        else:
            cursor.execute(
                """
                SELECT * FROM conversations
                WHERE user_id = ?
                ORDER BY updated_at DESC
                """,
                (user_id,),
            )
        return cursor.fetchall()
    finally:
        conn.close()


def delete_empty_conversations(user_id: int) -> None:
    """Delete conversations that have no messages to prevent sidebar clutter."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            DELETE FROM conversations
            WHERE user_id = ? AND id NOT IN (
                SELECT DISTINCT conversation_id FROM messages WHERE conversation_id IS NOT NULL
            )
            """,
            (user_id,),
        )
        conn.commit()
    finally:
        conn.close()


def get_conversation(
    conversation_id: int,
    user_id: int,
) -> sqlite3.Row | None:
    """Retrieve conversation by ID while enforcing user ownership."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT * FROM conversations
            WHERE id = ? AND user_id = ?
            LIMIT 1
            """,
            (conversation_id, user_id),
        )
        return cursor.fetchone()
    finally:
        conn.close()


def add_message(conversation_id: int, role: str, content: str) -> int:
    """Append a message and update the conversation timestamp."""
    now = datetime.now(timezone.utc).isoformat()
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO messages (conversation_id, role, content, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (conversation_id, role, content, now),
        )

        message_id = cursor.lastrowid

        cursor.execute(
            "UPDATE conversations SET updated_at = ? WHERE id = ?",
            (now, conversation_id),
        )

        conn.commit()
        return message_id
    finally:
        conn.close()


def get_messages(conversation_id: int) -> list[sqlite3.Row]:
    """Retrieve messages in chronological order."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT * FROM messages
            WHERE conversation_id = ?
            ORDER BY id ASC
            """,
            (conversation_id,),
        )
        return cursor.fetchall()
    finally:
        conn.close()


def save_patient_state(
    conversation_id: int,
    turn_number: int,
    state_json: str,
) -> None:
    """Save serialized patient state for a specific conversation turn."""
    now = datetime.now(timezone.utc).isoformat()
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO patient_states (
                conversation_id, turn_number, state_json, created_at
            )
            VALUES (?, ?, ?, ?)
            """,
            (conversation_id, turn_number, state_json, now),
        )
        conn.commit()
    finally:
        conn.close()


def get_latest_patient_state(conversation_id: int) -> str | None:
    """Retrieve the most recent serialized patient state JSON."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT state_json FROM patient_states
            WHERE conversation_id = ?
            ORDER BY turn_number DESC
            LIMIT 1
            """,
            (conversation_id,),
        )
        row = cursor.fetchone()
        return row["state_json"] if row is not None else None
    finally:
        conn.close()


def save_verification_result(
    message_id: int,
    flags_json: str,
    gate_decision: str,
    reasoning: str,
) -> None:
    """Save verification outcome associated with an assistant message."""
    now = datetime.now(timezone.utc).isoformat()
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO verification_results (
                message_id, flags_json, gate_decision, reasoning, created_at
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (message_id, flags_json, gate_decision, reasoning, now),
        )
        conn.commit()
    finally:
        conn.close()


def get_verification_result(message_id: int) -> sqlite3.Row | None:
    """Retrieve verification result for an assistant message ID."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT * FROM verification_results
            WHERE message_id = ?
            LIMIT 1
            """,
            (message_id,),
        )
        return cursor.fetchone()
    finally:
        conn.close()
