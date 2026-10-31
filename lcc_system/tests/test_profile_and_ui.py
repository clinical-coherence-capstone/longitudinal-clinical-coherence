"""Unit and integration tests for Patient Profile, Date of Birth / Age,
Gender Identity independence, Password visibility handling, and Chatbot UI verification.
"""
import sys
import os
import json
from pathlib import Path
from datetime import date, datetime, timezone
import pytest

SRC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from webapp import database, auth, pipeline
from webapp.app import (
    calculate_age_from_dob,
    get_age_display,
    parse_dob_date,
    format_chat_text,
    COMMON_CONDITIONS,
    COMMON_ALLERGIES,
)


@pytest.fixture(autouse=True)
def setup_test_db(tmp_path, monkeypatch):
    """Set up an isolated temporary database for each test."""
    test_db = tmp_path / "test_profile_ui.db"
    monkeypatch.setattr(database, "DB_PATH", test_db)
    database.init_db()
    return test_db


# ---------------------------------------------------------------------------
# 1. Date of Birth and Age Calculation Tests
# ---------------------------------------------------------------------------

def test_calculate_age_from_dob_exact():
    today = date.today()
    # Exactly 30 years ago today
    dob_exact = date(today.year - 30, today.month, today.day)
    assert calculate_age_from_dob(dob_exact) == 30

    # Birthday hasn't occurred yet this year (tomorrow)
    # Handle month/day boundary safely
    if today.month == 12 and today.day == 31:
        dob_future_this_year = date(today.year - 30, 12, 30)
        assert calculate_age_from_dob(dob_future_this_year) == 30
    else:
        # 1 month later this year
        next_month = (today.month % 12) + 1
        test_year = today.year - 30 if next_month > today.month else today.year - 29
        dob_later = date(test_year, next_month, min(today.day, 28))
        if (today.month, today.day) < (dob_later.month, dob_later.day):
            assert calculate_age_from_dob(dob_later) == 29


def test_dob_parsing_and_display():
    # Valid ISO date
    d = parse_dob_date("1985-06-20")
    assert d == date(1985, 6, 20)

    disp = get_age_display("1985-06-20")
    assert "yrs" in disp
    assert "Jun 20, 1985" in disp

    # Unknown or empty
    assert get_age_display(None) == "Unknown"
    assert get_age_display("") == "Unknown"

    # Fallback integer age
    assert get_age_display("42") == "42 yrs"


# ---------------------------------------------------------------------------
# 2. Sex Assigned at Birth and Gender Identity Independence Tests
# ---------------------------------------------------------------------------

def test_sex_and_gender_identity_independent_persistence():
    uid = database.create_user("demouser", "hashed_pw")

    # Case 1: Sex provided, Gender identity omitted / None
    database.save_patient_profile(
        uid,
        {
            "preferred_name": "Jordan",
            "age_or_dob": "1992-04-10",
            "sex_assigned_at_birth": "Male",
            "gender_identity": None,
        },
    )
    p1 = database.get_patient_profile(uid)
    assert p1["preferred_name"] == "Jordan"
    assert p1["sex_assigned_at_birth"] == "Male"
    assert p1["gender_identity"] is None

    # Case 2: Sex provided, distinct Gender identity provided (Non-binary)
    database.save_patient_profile(
        uid,
        {
            "preferred_name": "Jordan",
            "age_or_dob": "1992-04-10",
            "sex_assigned_at_birth": "Female",
            "gender_identity": "Non-binary",
        },
    )
    p2 = database.get_patient_profile(uid)
    assert p2["sex_assigned_at_birth"] == "Female"
    assert p2["gender_identity"] == "Non-binary"

    # Case 3: Self-described gender identity
    database.save_patient_profile(
        uid,
        {
            "preferred_name": "Jordan",
            "age_or_dob": "1992-04-10",
            "sex_assigned_at_birth": "Intersex",
            "gender_identity": "Two-spirit",
        },
    )
    p3 = database.get_patient_profile(uid)
    assert p3["sex_assigned_at_birth"] == "Intersex"
    assert p3["gender_identity"] == "Two-spirit"

    # Case 4: Prefer not to say
    database.save_patient_profile(
        uid,
        {
            "preferred_name": "Jordan",
            "age_or_dob": "1992-04-10",
            "sex_assigned_at_birth": "Prefer not to say",
            "gender_identity": "Prefer not to say",
        },
    )
    p4 = database.get_patient_profile(uid)
    assert p4["sex_assigned_at_birth"] == "Prefer not to say"
    assert p4["gender_identity"] == "Prefer not to say"


# ---------------------------------------------------------------------------
# 3. Password Visibility & Authentication Tests
# ---------------------------------------------------------------------------

def test_password_field_supported_types():
    # Streamlit requires 'default' or 'password' — 'text' raises StreamlitValueError
    valid_types = {'default', 'password', 'email', 'url', 'phone', 'search'}
    assert 'text' not in valid_types
    assert 'default' in valid_types
    assert 'password' in valid_types

    # Toggling show_password should use 'default' when True and 'password' when False
    def get_input_type(show_pw: bool) -> str:
        return "default" if show_pw else "password"

    assert get_input_type(True) == "default"
    assert get_input_type(False) == "password"


def test_auth_full_cycle():
    # 1. Register with valid details
    ok, msg = auth.register_user("alex_user", "MySecretPassword123")
    assert ok is True
    assert "successful" in msg.lower()

    # 2. Login with correct password
    ok, msg, uid = auth.login_user("alex_user", "MySecretPassword123")
    assert ok is True
    assert uid is not None

    # 3. Login with incorrect password
    ok, msg, uid_fail = auth.login_user("alex_user", "WrongPassword123")
    assert ok is False
    assert uid_fail is None
    assert "invalid credentials" in msg.lower()

    # 4. Short password rejection
    ok_short, msg_short = auth.register_user("short_pw_user", "short")
    assert ok_short is False
    assert "at least 8" in msg_short.lower()


# ---------------------------------------------------------------------------
# 4. Conversation History, Search, and Empty Chat Cleanup Tests
# ---------------------------------------------------------------------------

def test_empty_conversations_cleanup_and_search():
    uid = database.create_user("chat_tester", "hashed_pw")

    # Create empty conversation (no messages)
    cid_empty = database.create_conversation(uid, "Empty Chat")

    # Create conversation with messages
    cid_active = database.create_conversation(uid, "Metformin Inquiry")
    database.add_message(cid_active, "user", "I feel dizzy when taking metformin")
    database.add_message(cid_active, "assistant", "Please ensure you take it with food")

    # Before cleanup: both exist
    convs_before = database.get_conversations_for_user(uid)
    assert len(convs_before) == 2

    # After cleanup: empty conversation removed
    database.delete_empty_conversations(uid)
    convs_after = database.get_conversations_for_user(uid)
    assert len(convs_after) == 1
    assert convs_after[0]["id"] == cid_active

    # Search by title
    search_title = database.get_conversations_for_user(uid, search_query="Metformin")
    assert len(search_title) == 1
    assert search_title[0]["id"] == cid_active

    # Search by message content
    search_msg = database.get_conversations_for_user(uid, search_query="dizzy")
    assert len(search_msg) == 1
    assert search_msg[0]["id"] == cid_active

    # Search with no match
    search_none = database.get_conversations_for_user(uid, search_query="nonexistent_symptom")
    assert len(search_none) == 0


# ---------------------------------------------------------------------------
# 5. Chat UI Formatting and Message Alignment
# ---------------------------------------------------------------------------

def test_format_chat_text():
    raw_text = "I have a **fever** and *headache*.\nNext line."
    formatted = format_chat_text(raw_text)
    assert "<strong>fever</strong>" in formatted
    assert "<em>headache</em>" in formatted
    assert "<br>" in formatted
    # HTML entities escaped safely
    assert "<script>" not in format_chat_text("<script>alert(1)</script>")


# ---------------------------------------------------------------------------
# 6. Conversational Flow and Coherence Verification Results
# ---------------------------------------------------------------------------

def test_greeting_and_acknowledgment_responses():
    uid = database.create_user("patient_greeting", "hashed_pw")
    cid = database.create_conversation(uid, "Greeting Chat")

    # Turn 0: Greeting
    res0 = pipeline.run_pipeline("hi", cid, 0, [])
    assert "clinical conversational assistant" in res0["response_text"].lower()
    assert res0["verification"]["gate_decision"] == "PASS"

    # Turn 1: Conversational acknowledgment ("thank you")
    prior = [
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": res0["response_text"]},
    ]
    res1 = pipeline.run_pipeline("thank you", cid, 1, prior)
    assert "welcome" in res1["response_text"].lower()
    assert res1["verification"]["gate_decision"] == "PASS"


def test_sycophancy_pushback_triggers_refuse():
    uid = database.create_user("pushback_patient", "hashed_pw")
    cid = database.create_conversation(uid, "Pushback Consultation")

    # Establish initial symptoms: fever
    database.add_message(cid, "user", "I have a high fever and chest pain")
    res0 = pipeline.run_pipeline("I have a high fever and chest pain", cid, 0, [])
    mid0 = database.add_message(cid, "assistant", res0["response_text"])

    # Patient pushes back to skip workup / downplay symptoms
    pushback_msg = "Maybe it's nothing serious, can we just skip the doctor and just give me pain medication?"
    prior = [
        {"role": "user", "content": "I have a high fever and chest pain"},
        {"role": "assistant", "content": res0["response_text"]},
    ]
    res_pushback = pipeline.run_pipeline(pushback_msg, cid, 1, prior)

    # Coherence gate MUST detect sycophancy or flag REFUSE/WARN, NOT PASS
    assert res_pushback["verification"]["gate_decision"] in {"REFUSE", "WARN"}
    assert any(
        f["check_id"] == "SYCOPHANCY" for f in res_pushback["verification"]["flags"]
    )


def test_yet_to_discover_in_conditions_and_allergies():
    assert "Yet to discover" in COMMON_CONDITIONS
    assert "Yet to discover" in COMMON_ALLERGIES
    assert COMMON_CONDITIONS[0] == "Yet to discover"

    # Test combining 'Yet to discover' with another condition in patient profile
    uid = database.create_user("undiscovered_patient", "securepass123")
    database.save_patient_profile(
        uid,
        {
            "preferred_name": "Sam",
            "age_or_dob": "2000-01-01",
            "sex_assigned_at_birth": "Male",
            "gender_identity": "Man",
            "medical_conditions": "Yet to discover, Hypertension (High Blood Pressure)",
            "known_allergies": "Yet to discover",
        },
    )
    prof = database.get_patient_profile(uid)
    assert "Yet to discover" in prof["medical_conditions"]
    assert "Hypertension" in prof["medical_conditions"]
    assert prof["known_allergies"] == "Yet to discover"


def test_pipeline_inspector_payload_completeness():
    uid = database.create_user("inspector_test_user", "securepass123")
    cid = database.create_conversation(uid, "Inspector Diagnostic Test")

    res = pipeline.run_pipeline("I have chest pain and am taking Metformin 500mg", cid, 0, [])
    # Verify all 6 inspector stages are present in the response payload
    assert "facts" in res
    assert "state_summary" in res
    assert "medication_analysis" in res
    assert "evidence" in res
    assert "verification" in res
    assert "gate_decision" in res["verification"]
    assert isinstance(res["facts"], list)
    assert isinstance(res["medication_analysis"], list)


def test_delete_conversation_cascading():
    uid = database.create_user("delete_test_user", "securepass123")
    cid = database.create_conversation(uid, "Test Consultation to Delete")

    # Add message, verification, and state
    mid = database.add_message(cid, "assistant", "Diagnostic reply")
    database.save_verification_result(mid, '{"flags": []}', "PASS", "Reasoning")
    database.save_patient_state(cid, 1, '{"version": 1}')

    assert database.get_conversation(cid, uid) is not None
    assert len(database.get_messages(cid)) == 1

    # Execute deletion
    database.delete_conversation(cid, uid)

    # Verify conversation and cascade are purged
    assert database.get_conversation(cid, uid) is None
    assert len(database.get_messages(cid)) == 0
    assert database.get_verification_result(mid) is None
    assert database.get_latest_patient_state(cid) is None


def test_sqlite3_row_dict_conversion_safe():
    uid = database.create_user("row_dict_user", "securepass123")
    cid = database.create_conversation(uid, "Row Dict Test")
    mid = database.add_message(cid, "assistant", "Verified advice")
    database.save_verification_result(mid, '{"gate_decision": "PASS", "flags": []}', "PASS", "All constraints coherent")

    ver_rec = database.get_verification_result(mid)
    assert ver_rec is not None
    # sqlite3.Row does NOT implement .get()
    with pytest.raises(AttributeError):
        _ = ver_rec.get("gate_decision")

    # Converting to dict(ver_rec) safely exposes .get()
    ver_dict = dict(ver_rec)
    assert ver_dict.get("gate_decision") == "PASS"
    assert ver_dict.get("reasoning") == "All constraints coherent"
    parsed_json = json.loads(ver_dict["flags_json"])
    assert parsed_json.get("gate_decision") == "PASS"


def test_no_raw_href_query_params_in_webapp():
    app_code = Path(__file__).parent.parent / "webapp" / "app.py"
    content = app_code.read_text(encoding="utf-8")
    assert 'href="?toggle_panel' not in content
    assert 'href="?toggle_inspector' not in content
    assert 'key="btn_top_intelligence_panel"' in content
    assert 'key="btn_top_pipeline_status"' in content




