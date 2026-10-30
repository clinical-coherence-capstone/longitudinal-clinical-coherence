"""Integration tests for patient onboarding, user isolation, multi-turn clinical chat,
medication normalization, DailyMed evidence retrieval, and verification persistence.
"""
import sys
import os
import json
import pytest

SRC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from webapp import database, auth, pipeline


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    """Ensure database operations run in a fresh temporary SQLite file."""
    test_db = tmp_path / "test_integration.db"
    monkeypatch.setattr(database, "DB_PATH", test_db)
    database.init_db()
    return test_db


def test_patient_profile_registration_and_editing():
    ok, _ = auth.register_user("patient_clara", "SecurePass123!")
    assert ok is True
    _, _, uid = auth.login_user("patient_clara", "SecurePass123!")

    # 1. Baseline profile registration
    profile_data = {
        "preferred_name": "Clara Oswald",
        "age_or_dob": "29",
        "sex_assigned_at_birth": "Female",
        "gender_identity": "Woman",
        "medical_conditions": "Mild asthma",
        "known_allergies": "Sulfa drugs",
        "current_medications": "Albuterol inhaler",
        "medical_history": "Childhood appendectomy",
    }
    database.save_patient_profile(uid, profile_data)

    prof = database.get_patient_profile(uid)
    assert prof is not None
    assert prof["preferred_name"] == "Clara Oswald"
    assert prof["medical_conditions"] == "Mild asthma"
    assert prof["known_allergies"] == "Sulfa drugs"

    # 2. Profile editing
    updated_data = {
        "preferred_name": "Clara",
        "age_or_dob": "30",
        "sex_assigned_at_birth": "Female",
        "gender_identity": "Woman",
        "medical_conditions": "Mild asthma, Seasonal rhinitis",
        "known_allergies": "Sulfa drugs, Pollen",
        "current_medications": "Albuterol inhaler, Cetirizine",
        "medical_history": "Childhood appendectomy",
    }
    database.save_patient_profile(uid, updated_data)

    prof_updated = database.get_patient_profile(uid)
    assert prof_updated["preferred_name"] == "Clara"
    assert prof_updated["age_or_dob"] == "30"
    assert "Seasonal rhinitis" in prof_updated["medical_conditions"]
    assert "Cetirizine" in prof_updated["current_medications"]


def test_patient_profile_optional_fields_unknown():
    ok, _ = auth.register_user("patient_anon", "SecurePass123!")
    assert ok is True
    _, _, uid = auth.login_user("patient_anon", "SecurePass123!")

    # Only preferred_name provided
    database.save_patient_profile(uid, {"preferred_name": "Anon"})
    prof = database.get_patient_profile(uid)
    assert prof["preferred_name"] == "Anon"
    assert prof["age_or_dob"] is None
    assert prof["sex_assigned_at_birth"] is None
    assert prof["medical_conditions"] is None
    assert prof["current_medications"] is None


def test_user_data_isolation():
    # User 1: Alice
    auth.register_user("alice_smith", "Password123!")
    _, _, uid_alice = auth.login_user("alice_smith", "Password123!")
    database.save_patient_profile(uid_alice, {"preferred_name": "Alice"})
    cid_alice = database.create_conversation(uid_alice, "Alice Chat")
    database.add_message(cid_alice, "user", "I have chest pain")

    # User 2: Bob
    auth.register_user("bob_jones", "Password456!")
    _, _, uid_bob = auth.login_user("bob_jones", "Password456!")
    database.save_patient_profile(uid_bob, {"preferred_name": "Bob"})
    cid_bob = database.create_conversation(uid_bob, "Bob Chat")
    database.add_message(cid_bob, "user", "I have a rash")

    # Isolation checks
    # 1. Conversation ownership
    assert database.get_conversation(cid_alice, uid_alice) is not None
    assert database.get_conversation(cid_alice, uid_bob) is None
    assert database.get_conversation(cid_bob, uid_bob) is not None
    assert database.get_conversation(cid_bob, uid_alice) is None

    # 2. Profile isolation
    prof_alice = database.get_patient_profile(uid_alice)
    prof_bob = database.get_patient_profile(uid_bob)
    assert prof_alice["preferred_name"] == "Alice"
    assert prof_bob["preferred_name"] == "Bob"

    # 3. Message isolation
    alice_convs = database.get_conversations_for_user(uid_alice)
    bob_convs = database.get_conversations_for_user(uid_bob)
    assert len(alice_convs) == 1 and alice_convs[0]["id"] == cid_alice
    assert len(bob_convs) == 1 and bob_convs[0]["id"] == cid_bob


def test_multi_turn_patient_conversation():
    auth.register_user("turn_patient", "Password123!")
    _, _, uid = auth.login_user("turn_patient", "Password123!")
    profile = {
        "preferred_name": "Taylor",
        "medical_conditions": "Type 2 Diabetes",
        "current_medications": "Metformin",
    }
    database.save_patient_profile(uid, profile)
    cid = database.create_conversation(uid, "Longitudinal Consultation")

    # --- Turn 0: "I have fever" ---
    msg0 = "I have a fever"
    database.add_message(cid, "user", msg0)
    res0 = pipeline.run_pipeline(msg0, cid, 0, [], patient_profile=profile)

    assert any(f["fact_id"] == "SYM_FEVER" and f["status"] == "positive" for f in res0["facts"])
    assert res0["state_summary"]["version"] >= 1
    assert "SYM_FEVER" in [f["fact_id"] for f in res0["state_summary"]["facts_list"]]
    mid0 = database.add_message(cid, "assistant", res0["response_text"])
    database.save_verification_result(
        mid0, json.dumps(res0), res0["verification"]["gate_decision"], res0["verification"]["reasoning"]
    )

    # --- Turn 1: "I am taking Dolo 650" ---
    prior1 = [{"role": "user", "content": msg0}, {"role": "assistant", "content": res0["response_text"]}]
    msg1 = "I am taking Dolo 650"
    database.add_message(cid, "user", msg1)
    res1 = pipeline.run_pipeline(msg1, cid, 1, prior1, patient_profile=profile)

    # Verify Dolo 650 normalization ran without inventing RxCUI
    assert len(res1["medication_analysis"]) >= 1
    dolo_norm = next((m for m in res1["medication_analysis"] if "dolo" in m["mention"].lower()), None)
    assert dolo_norm is not None
    assert dolo_norm["rxcui"] is None
    assert dolo_norm["match_method"] == "unresolved"
    assert "No RxCUI was invented" in dolo_norm["explanation"]
    assert res1["state_summary"]["version"] > res0["state_summary"]["version"]

    mid1 = database.add_message(cid, "assistant", res1["response_text"])
    database.save_verification_result(
        mid1, json.dumps(res1), res1["verification"]["gate_decision"], res1["verification"]["reasoning"]
    )

    # --- Turn 2: "I do not have a cough" ---
    prior2 = prior1 + [{"role": "user", "content": msg1}, {"role": "assistant", "content": res1["response_text"]}]
    msg2 = "I do not have a cough"
    database.add_message(cid, "user", msg2)
    res2 = pipeline.run_pipeline(msg2, cid, 2, prior2, patient_profile=profile)

    cough_fact = next((f for f in res2["facts"] if f["fact_id"] == "SYM_COUGH"), None)
    assert cough_fact is not None
    assert cough_fact["status"] == "negative"
    assert "SYM_COUGH" in res2["state_summary"]["changes_from_prior_turn"]
    assert res2["verification"]["gate_decision"] in {"PASS", "CLARIFY", "WARN", "REFUSE"}


def test_medication_normalization_resolved_and_unresolved():
    loader, normalizer, _, _ = pipeline._get_shared_resources()

    # Dolo 650 -> unresolved, no RxCUI
    analyses_dolo = pipeline.analyze_medications(["Dolo 650"], normalizer)
    assert len(analyses_dolo) == 1
    assert analyses_dolo[0]["mention"] == "Dolo 650"
    assert analyses_dolo[0]["rxcui"] is None
    assert analyses_dolo[0]["resolved"] is False

    # Metformin -> resolved to RxCUI 6809
    analyses_met = pipeline.analyze_medications(["metformin"], normalizer)
    assert len(analyses_met) == 1
    assert analyses_met[0]["rxcui"] == "6809"
    assert analyses_met[0]["normalized_name"] == "metformin"
    assert analyses_met[0]["resolved"] is True


def test_evidence_retrieval_and_corpus_explanation():
    # 1. Unresolved med (Dolo 650) -> 0 evidence records + explicit limitation explanation
    res_dolo = pipeline.run_pipeline("I have fever and taking Dolo 650", 7001, 0, [])
    assert len(res_dolo["evidence"]) == 0
    assert "limited to the Alogliptin / Metformin combination product" in res_dolo["evidence_explanation"]

    # 2. Resolved DailyMed med (metformin) -> retrieves records
    res_met = pipeline.run_pipeline("I am taking metformin for my sugar", 7002, 0, [])
    assert len(res_met["evidence"]) > 0
    assert any("metformin" in e["active_ingredient"].lower() for e in res_met["evidence"])


def test_verification_panel_persistence_and_accuracy():
    uid = database.create_user("verify_user", "hash123")
    cid = database.create_conversation(uid, "Check Panel")
    msg_id = database.add_message(cid, "assistant", "Clinical response")

    sample_payload = {
        "verification": {
            "pass_through": True,
            "gate_decision": "PASS",
            "reasoning": "All checks passed cleanly.",
            "flags": [],
        },
        "facts": [
            {
                "fact_id": "SYM_FEVER",
                "description": "Fever",
                "status": "positive",
                "confidence": 0.7,
                "is_antecedent": False,
            }
        ],
        "state_summary": {
            "version": 1,
            "turn_number": 0,
            "medications": ["dolo 650"],
            "facts_count": 1,
            "contradictions": [],
            "changes_from_prior_turn": "Added: SYM_FEVER (Fever) = positive",
        },
        "evidence": [],
        "evidence_explanation": "Corpus limited to Alogliptin / Metformin.",
        "medication_analysis": [
            {
                "mention": "dolo 650",
                "rxcui": None,
                "normalized_name": None,
                "match_method": "unresolved",
                "resolved": False,
                "explanation": "No RxCUI invented.",
            }
        ],
    }

    database.save_verification_result(
        message_id=msg_id,
        flags_json=json.dumps(sample_payload),
        gate_decision="PASS",
        reasoning="All checks passed cleanly.",
    )

    row = database.get_verification_result(msg_id)
    assert row is not None
    unpacked = json.loads(row["flags_json"])

    assert len(unpacked["facts"]) == 1
    assert unpacked["facts"][0]["fact_id"] == "SYM_FEVER"
    assert unpacked["state_summary"]["facts_count"] == 1
    assert "Added: SYM_FEVER" in unpacked["state_summary"]["changes_from_prior_turn"]
    assert unpacked["medication_analysis"][0]["rxcui"] is None
    assert unpacked["verification"]["gate_decision"] == "PASS"
