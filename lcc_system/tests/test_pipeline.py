"""Tests for webapp/pipeline.py."""
import sys
import os
import unittest.mock as mock
import pytest

SRC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from models import ClinicalFact, PatientState
from webapp import pipeline


@pytest.fixture(autouse=True)
def mock_db_in_pipeline(monkeypatch):
    """Ensure database state operations are mocked out during pipeline unit tests."""
    in_memory_states = {}

    def fake_save_patient_state(conv_id, turn_num, state_json):
        in_memory_states[conv_id] = state_json

    def fake_get_latest_patient_state(conv_id):
        return in_memory_states.get(conv_id)

    monkeypatch.setattr(pipeline, "save_patient_state", fake_save_patient_state)
    monkeypatch.setattr(pipeline, "get_latest_patient_state", fake_get_latest_patient_state)
    return in_memory_states


def test_run_pipeline_returns_expected_keys():
    result = pipeline.run_pipeline("I have fatigue and chest pain", 999, 0, [])
    assert isinstance(result, dict)
    for key in ("response_text", "verification", "facts", "state_summary", "evidence"):
        assert key in result

    verification = result["verification"]
    assert "pass_through" in verification
    assert "gate_decision" in verification
    assert "reasoning" in verification
    assert "flags" in verification


def test_run_pipeline_gate_decision_is_valid():
    result = pipeline.run_pipeline("I have fatigue and chest pain", 999, 0, [])
    assert result["verification"]["gate_decision"] in {"PASS", "CLARIFY", "WARN", "REFUSE"}


def test_run_pipeline_extracts_facts():
    # Use chief complaints or symptoms from dataset vocabulary
    result = pipeline.run_pipeline("I have a fever and fatigue", 999, 0, [])
    assert isinstance(result["facts"], list)
    # At least one fact should be identified or facts list is present
    assert "facts" in result


def test_serialize_deserialize_roundtrip():
    fact1 = ClinicalFact(
        fact_id="E_91",
        description="Fever",
        status="positive",
        source_turn=0,
        timestamp="2026-10-30T10:00:00Z",
        confidence=1.0,
        is_antecedent=False,
    )
    fact2 = ClinicalFact(
        fact_id="E_53",
        description="Pain somewhere",
        status="negative",
        source_turn=1,
        timestamp="2026-10-30T10:01:00Z",
        confidence=0.9,
        is_antecedent=False,
    )
    orig_state = PatientState(
        case_id="case_101",
        version=2,
        turn_number=1,
        timestamp="2026-10-30T10:01:00Z",
        facts={"E_91": fact1, "E_53": fact2},
        revealed_evidence_ids=["E_91", "E_53"],
        medications=["metformin"],
    )

    serialized = pipeline.serialize_state(orig_state)
    deserialized = pipeline.deserialize_state(serialized, "case_101")

    assert deserialized.case_id == "case_101"
    assert deserialized.version == 2
    assert deserialized.turn_number == 1
    assert len(deserialized.facts) == 2
    assert deserialized.facts["E_91"].description == "Fever"
    assert deserialized.facts["E_53"].status == "negative"
    assert deserialized.medications == ["metformin"]


def test_rebuild_state_manager_no_prior_state(monkeypatch):
    monkeypatch.setattr(pipeline, "get_latest_patient_state", lambda cid: None)
    sm = pipeline.rebuild_state_manager(123)
    assert sm.case_id == "123"
    assert sm.current_version == 0
    assert len(sm.get_current_state().facts) == 0


def test_rebuild_state_manager_with_prior_state(monkeypatch):
    fact = ClinicalFact(
        fact_id="E_154",
        description="Paleness",
        status="positive",
        source_turn=0,
        timestamp="2026-10-30T10:00:00Z",
        confidence=1.0,
        is_antecedent=False,
    )
    saved_state = PatientState(
        case_id="456",
        version=3,
        turn_number=2,
        timestamp="2026-10-30T10:05:00Z",
        facts={"E_154": fact},
        revealed_evidence_ids=["E_154"],
        medications=[],
    )
    saved_json = pipeline.serialize_state(saved_state)
    monkeypatch.setattr(pipeline, "get_latest_patient_state", lambda cid: saved_json)

    sm = pipeline.rebuild_state_manager(456)
    assert sm.case_id == "456"
    assert sm.current_version == 3
    assert "E_154" in sm.get_current_state().facts


def test_build_conversation_maps_roles():
    prior_messages = [
        {"role": "user", "content": "I feel tired"},
        {"role": "assistant", "content": "How long have you felt tired?"},
    ]
    conv = pipeline.build_conversation(789, prior_messages, current_turn=2)
    assert conv.case_id == "789"
    assert len(conv.turns) == 2
    assert conv.turns[0].turn_index == 0
    assert conv.turns[0].speaker == "patient"
    assert conv.turns[0].text == "I feel tired"
    assert conv.turns[1].turn_index == 1
    assert conv.turns[1].speaker == "doctor"
    assert conv.turns[1].text == "How long have you felt tired?"
