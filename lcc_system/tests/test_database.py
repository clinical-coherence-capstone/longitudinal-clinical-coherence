"""Tests for webapp/database.py."""
import sys
import os
import sqlite3
import pytest

# Ensure src/ and webapp parent are on sys.path
SRC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from webapp import database


@pytest.fixture(autouse=True)
def setup_test_db(tmp_path, monkeypatch):
    """Set up an isolated temporary database for each test."""
    test_db = tmp_path / "test_lcc_webapp.db"
    monkeypatch.setattr(database, "DB_PATH", test_db)
    database.init_db()
    return test_db


def test_init_db_creates_tables():
    conn = database.get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row["name"] for row in cursor.fetchall()}
        expected_tables = {
            "users",
            "conversations",
            "messages",
            "patient_states",
            "verification_results",
        }
        assert expected_tables.issubset(tables)
    finally:
        conn.close()


def test_create_and_get_user():
    uid = database.create_user("testuser", "hashed_pw_123")
    assert uid > 0

    user = database.get_user_by_username("testuser")
    assert user is not None
    assert user["id"] == uid
    assert user["username"] == "testuser"
    assert user["password_hash"] == "hashed_pw_123"

    user_by_id = database.get_user_by_id(uid)
    assert user_by_id is not None
    assert user_by_id["username"] == "testuser"


def test_duplicate_username_raises():
    database.create_user("alice", "hash1")
    with pytest.raises(sqlite3.IntegrityError):
        database.create_user("alice", "hash2")


def test_create_and_get_conversation():
    uid = database.create_user("bob", "hash")
    cid = database.create_conversation(uid, "First Chat")
    assert cid > 0

    convs = database.get_conversations_for_user(uid)
    assert len(convs) == 1
    assert convs[0]["id"] == cid
    assert convs[0]["title"] == "First Chat"


def test_conversation_ownership_enforced():
    user1_id = database.create_user("user1", "hash1")
    user2_id = database.create_user("user2", "hash2")

    conv_id = database.create_conversation(user1_id, "User1 Chat")

    assert database.get_conversation(conv_id, user1_id) is not None
    assert database.get_conversation(conv_id, user2_id) is None


def test_add_and_get_messages():
    uid = database.create_user("carol", "hash")
    cid = database.create_conversation(uid, "Chat")

    m1_id = database.add_message(cid, "user", "Hello doctor")
    m2_id = database.add_message(cid, "assistant", "Hello patient")

    assert m1_id > 0
    assert m2_id > m1_id

    messages = database.get_messages(cid)
    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == "Hello doctor"
    assert messages[1]["role"] == "assistant"
    assert messages[1]["content"] == "Hello patient"


def test_save_and_get_patient_state():
    uid = database.create_user("david", "hash")
    cid = database.create_conversation(uid, "Chat")

    assert database.get_latest_patient_state(cid) is None

    database.save_patient_state(cid, 0, '{"version": 1, "facts": {}}')
    database.save_patient_state(cid, 1, '{"version": 2, "facts": {"E_91": "fatigue"}}')

    latest = database.get_latest_patient_state(cid)
    assert latest == '{"version": 2, "facts": {"E_91": "fatigue"}}'


def test_save_and_get_verification_result():
    uid = database.create_user("eve", "hash")
    cid = database.create_conversation(uid, "Chat")
    mid = database.add_message(cid, "assistant", "Response text")

    database.save_verification_result(mid, '{"flags": []}', "PASS", "No issues")

    ver = database.get_verification_result(mid)
    assert ver is not None
    assert ver["message_id"] == mid
    assert ver["gate_decision"] == "PASS"
    assert ver["reasoning"] == "No issues"


def test_save_and_get_patient_profile():
    uid = database.create_user("profile_user", "hash")
    assert database.get_patient_profile(uid) is None

    profile_data = {
        "preferred_name": "Alex",
        "age_or_dob": "42",
        "sex_assigned_at_birth": "Female",
        "gender_identity": "Woman",
        "medical_conditions": "Type 2 Diabetes",
        "known_allergies": "Penicillin",
        "current_medications": "Metformin 500mg",
        "medical_history": "Appendectomy 2015",
    }
    database.save_patient_profile(uid, profile_data)

    prof = database.get_patient_profile(uid)
    assert prof is not None
    assert prof["user_id"] == uid
    assert prof["preferred_name"] == "Alex"
    assert prof["age_or_dob"] == "42"
    assert prof["medical_conditions"] == "Type 2 Diabetes"
    assert prof["current_medications"] == "Metformin 500mg"


def test_update_patient_profile():
    uid = database.create_user("profile_updater", "hash")
    database.save_patient_profile(uid, {"preferred_name": "Sam"})
    prof1 = database.get_patient_profile(uid)
    assert prof1["preferred_name"] == "Sam"
    assert prof1["medical_conditions"] is None

    # Update
    database.save_patient_profile(
        uid,
        {
            "preferred_name": "Samantha",
            "medical_conditions": "Asthma",
            "current_medications": "Albuterol",
        },
    )
    prof2 = database.get_patient_profile(uid)
    assert prof2["preferred_name"] == "Samantha"
    assert prof2["medical_conditions"] == "Asthma"
    assert prof2["current_medications"] == "Albuterol"


def test_patient_profile_optional_fields_none():
    uid = database.create_user("minimal_user", "hash")
    database.save_patient_profile(uid, {"preferred_name": "Jordan"})
    prof = database.get_patient_profile(uid)
    assert prof["preferred_name"] == "Jordan"
    assert prof["age_or_dob"] is None
    assert prof["known_allergies"] is None

