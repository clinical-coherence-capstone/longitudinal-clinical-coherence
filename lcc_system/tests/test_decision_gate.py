"""
test_decision_gate.py — Unit tests for DecisionGate.
"""
from __future__ import annotations

import pytest
from decision_gate import DecisionGate
from models import CoherenceFlag
from datetime import datetime, timezone


@pytest.fixture
def gate():
    return DecisionGate()


def _make_flag(
    check_id: str,
    severity: str,
    description: str = "Test flag",
    turn_index: int = 0,
    evidence: str = "",
) -> CoherenceFlag:
    return CoherenceFlag(
        check_id=check_id,
        severity=severity,
        description=description,
        turn_index=turn_index,
        evidence=evidence,
    )


# ---------------------------------------------------------------------------
# Test 1: [] → ('PASS', ...)
# ---------------------------------------------------------------------------

def test_empty_flags_returns_pass(gate):
    decision, reasoning = gate.evaluate([])
    assert decision == "PASS", f"Expected PASS, got {decision}"
    assert isinstance(reasoning, str)
    assert len(reasoning) > 0


# ---------------------------------------------------------------------------
# Test 2: [CoherenceFlag('SYCOPHANCY', 'ERROR', ...)] → ('REFUSE', ...)
# ---------------------------------------------------------------------------

def test_sycophancy_error_returns_refuse(gate):
    flags = [_make_flag("SYCOPHANCY", "ERROR", "Patient exhibited sycophancy")]
    decision, reasoning = gate.evaluate(flags)
    assert decision == "REFUSE", f"Expected REFUSE, got {decision}"


# ---------------------------------------------------------------------------
# Test 3: [CoherenceFlag('FACT_CONTRADICTION', 'ERROR', ...)] → ('WARN', ...)
# ---------------------------------------------------------------------------

def test_fact_contradiction_error_returns_warn(gate):
    flags = [_make_flag("FACT_CONTRADICTION", "ERROR", "Response contradicts patient facts")]
    decision, reasoning = gate.evaluate(flags)
    assert decision == "WARN", f"Expected WARN, got {decision}"


# ---------------------------------------------------------------------------
# Test 4: [CoherenceFlag('X', 'WARNING', ...)] → ('CLARIFY', ...)
# ---------------------------------------------------------------------------

def test_warning_flag_returns_clarify(gate):
    flags = [_make_flag("EVIDENCE_MED_MISMATCH", "WARNING", "Evidence mismatch")]
    decision, reasoning = gate.evaluate(flags)
    assert decision == "CLARIFY", f"Expected CLARIFY, got {decision}"


# ---------------------------------------------------------------------------
# Test 5: MED_TARGET_MISMATCH ERROR → REFUSE
# ---------------------------------------------------------------------------

def test_med_target_mismatch_error_returns_refuse(gate):
    flags = [_make_flag("MED_TARGET_MISMATCH", "ERROR", "Wrong medication target")]
    decision, reasoning = gate.evaluate(flags)
    assert decision == "REFUSE", f"Expected REFUSE, got {decision}"


# ---------------------------------------------------------------------------
# Test 6: STALE_STATE ERROR → WARN
# ---------------------------------------------------------------------------

def test_stale_state_error_returns_warn(gate):
    flags = [_make_flag("STALE_STATE", "ERROR", "State is stale")]
    decision, reasoning = gate.evaluate(flags)
    assert decision == "WARN", f"Expected WARN, got {decision}"


# ---------------------------------------------------------------------------
# Test 7: REFUSE takes priority over WARN when both present
# ---------------------------------------------------------------------------

def test_refuse_takes_priority_over_warn(gate):
    flags = [
        _make_flag("FACT_CONTRADICTION", "ERROR", "Contradiction"),
        _make_flag("SYCOPHANCY", "ERROR", "Sycophancy"),
    ]
    decision, reasoning = gate.evaluate(flags)
    assert decision == "REFUSE", f"Expected REFUSE over WARN, got {decision}"


# ---------------------------------------------------------------------------
# Test 8: reasoning string is non-empty for all decisions
# ---------------------------------------------------------------------------

def test_reasoning_always_nonempty(gate):
    test_cases = [
        [],
        [_make_flag("SYCOPHANCY", "ERROR")],
        [_make_flag("FACT_CONTRADICTION", "ERROR")],
        [_make_flag("SOMETHING", "WARNING")],
    ]
    for flags in test_cases:
        decision, reasoning = gate.evaluate(flags)
        assert isinstance(reasoning, str) and len(reasoning) > 0, (
            f"Empty reasoning for flags: {[f.check_id for f in flags]}, decision: {decision}"
        )


# ---------------------------------------------------------------------------
# Test 9: evaluate returns (str, str) tuple
# ---------------------------------------------------------------------------

def test_evaluate_returns_tuple(gate):
    result = gate.evaluate([])
    assert isinstance(result, tuple)
    assert len(result) == 2
    assert isinstance(result[0], str)
    assert isinstance(result[1], str)


# ---------------------------------------------------------------------------
# Test 10: unknown ERROR check_id → CLARIFY (unclassified)
# ---------------------------------------------------------------------------

def test_unknown_error_check_id_returns_clarify(gate):
    flags = [_make_flag("UNKNOWN_CHECK", "ERROR", "Unclassified issue")]
    decision, reasoning = gate.evaluate(flags)
    assert decision == "CLARIFY", f"Expected CLARIFY for unknown check_id, got {decision}"
