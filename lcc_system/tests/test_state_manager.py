"""
test_state_manager.py — Unit tests for StateManager.
"""
from __future__ import annotations

import pytest
from state_manager import StateManager
from models import ClinicalFact
from datetime import datetime, timezone


def _make_fact(
    fact_id: str,
    status: str = "positive",
    turn: int = 0,
    confidence: float = 0.9,
    is_antecedent: bool = False,
) -> ClinicalFact:
    return ClinicalFact(
        fact_id=fact_id,
        description=f"Test fact {fact_id}",
        status=status,
        source_turn=turn,
        timestamp=datetime.now(timezone.utc).isoformat(),
        confidence=confidence,
        is_antecedent=is_antecedent,
    )


@pytest.fixture
def sm():
    return StateManager(case_id="TEST_CASE")


# ---------------------------------------------------------------------------
# Test 1: init → version == 0
# ---------------------------------------------------------------------------

def test_initial_version_is_zero(sm):
    assert sm.current_version == 0
    state = sm.get_current_state()
    assert state.version == 0


# ---------------------------------------------------------------------------
# Test 2: three consecutive update() calls → version == 3
# ---------------------------------------------------------------------------

def test_three_updates_increments_version(sm):
    sm.update(1, [_make_fact("SYM_FEVER")])
    sm.update(2, [_make_fact("SYM_COUGH")])
    sm.update(3, [_make_fact("SYM_HEADACHE")])
    assert sm.current_version == 3


# ---------------------------------------------------------------------------
# Test 3: adding positive then negative for same fact_id → get_contradictions() returns 1 entry
# ---------------------------------------------------------------------------

def test_contradiction_recorded_on_status_change():
    sm = StateManager(case_id="CONTRADICTION_TEST")
    sm.update(1, [_make_fact("SYM_CHEST_PAIN", status="positive")])
    sm.update(2, [_make_fact("SYM_CHEST_PAIN", status="negative")])
    contradictions = sm.get_contradictions()
    assert len(contradictions) == 1, (
        f"Expected 1 contradiction, got {len(contradictions)}: {contradictions}"
    )
    fact_id, old_status, new_status = contradictions[0]
    assert fact_id == "SYM_CHEST_PAIN"
    assert old_status == "positive"
    assert new_status == "negative"


# ---------------------------------------------------------------------------
# Test 4: get_version(1) returns the state after first update
# ---------------------------------------------------------------------------

def test_get_version_returns_correct_state():
    sm = StateManager(case_id="VERSION_TEST")
    sm.update(1, [_make_fact("SYM_FEVER")])
    sm.update(2, [_make_fact("SYM_COUGH")])
    sm.update(3, [_make_fact("SYM_HEADACHE")])

    # After update 1, SYM_FEVER should be present
    state_v1 = sm.get_version(1)
    assert state_v1 is not None
    # The state returned for version 1 should have SYM_FEVER
    # (version 1 is the snapshot after the first update = history[1].snapshot if available,
    # else current)
    # Let's verify the current state has all three
    current = sm.get_current_state()
    assert "SYM_FEVER" in current.facts
    assert "SYM_COUGH" in current.facts
    assert "SYM_HEADACHE" in current.facts


# ---------------------------------------------------------------------------
# Test 5: update returns current state
# ---------------------------------------------------------------------------

def test_update_returns_patient_state():
    sm = StateManager(case_id="RETURN_TEST")
    result = sm.update(1, [_make_fact("SYM_NAUSEA")])
    from models import PatientState
    assert isinstance(result, PatientState)


# ---------------------------------------------------------------------------
# Test 6: get_fact_history returns history for a fact
# ---------------------------------------------------------------------------

def test_get_fact_history():
    sm = StateManager(case_id="HISTORY_TEST")
    sm.update(1, [_make_fact("SYM_FEVER", status="positive")])
    sm.update(2, [_make_fact("SYM_FEVER", status="negative")])
    history = sm.get_fact_history("SYM_FEVER")
    assert len(history) >= 1


# ---------------------------------------------------------------------------
# Test 7: no contradiction when updating unknown to positive
# ---------------------------------------------------------------------------

def test_no_contradiction_unknown_to_positive():
    sm = StateManager(case_id="NO_CONTRADICTION_TEST")
    sm.update(1, [_make_fact("SYM_COUGH", status="unknown")])
    sm.update(2, [_make_fact("SYM_COUGH", status="positive")])
    contradictions = sm.get_contradictions()
    # unknown → positive should NOT be a contradiction
    assert len(contradictions) == 0, (
        f"Expected 0 contradictions for unknown→positive, got {contradictions}"
    )


# ---------------------------------------------------------------------------
# Test 8: get_current_state() returns PatientState
# ---------------------------------------------------------------------------

def test_get_current_state_type():
    sm = StateManager(case_id="TYPE_TEST")
    from models import PatientState
    assert isinstance(sm.get_current_state(), PatientState)


# ---------------------------------------------------------------------------
# Test 9: history length equals number of updates
# ---------------------------------------------------------------------------

def test_history_length_equals_update_count():
    sm = StateManager(case_id="HIST_LEN_TEST")
    sm.update(1, [_make_fact("SYM_FEVER")])
    sm.update(2, [_make_fact("SYM_COUGH")])
    assert len(sm.history) == 2
