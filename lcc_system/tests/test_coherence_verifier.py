"""
test_coherence_verifier.py — Unit tests for CoherenceVerifier.
"""
from __future__ import annotations

import pytest
from dataset_loader import DatasetLoader
from medication_normalizer import MedicationNormalizer
from evidence_retriever import EvidenceRetriever
from coherence_verifier import CoherenceVerifier
from state_manager import StateManager
from state_extractor import StateExtractor
from models import ClinicalFact, Conversation, ConversationTurn, EvidenceRecord
from datetime import datetime, timezone


@pytest.fixture(scope="module")
def loader():
    return DatasetLoader()


@pytest.fixture(scope="module")
def norm(loader):
    return MedicationNormalizer(loader)


@pytest.fixture(scope="module")
def retriever(loader, norm):
    return EvidenceRetriever(loader, norm)


def _make_fact(
    fact_id: str,
    status: str = "positive",
    turn: int = 0,
) -> ClinicalFact:
    return ClinicalFact(
        fact_id=fact_id,
        description=f"Test {fact_id}",
        status=status,
        source_turn=turn,
        timestamp=datetime.now(timezone.utc).isoformat(),
        confidence=1.0,
        is_antecedent=False,
    )


def _make_conv(turns: list[ConversationTurn] | None = None) -> Conversation:
    conv = Conversation(case_id="TEST", turns=turns or [], current_turn=0)
    return conv


# ---------------------------------------------------------------------------
# Test 1: FACT_CONTRADICTION — state has SYM_CHEST_PAIN=negative,
#          response claims chest pain → FACT_CONTRADICTION flag
# ---------------------------------------------------------------------------

def test_fact_contradiction_flag(norm, retriever):
    sm = StateManager(case_id="CONTRADICTION_TEST")
    # Establish SYM_CHEST_PAIN as negative
    sm.update(1, [_make_fact("SYM_CHEST_PAIN", status="negative")])

    verifier = CoherenceVerifier(sm, retriever, norm)
    conv = _make_conv()

    # Response text asserting chest pain positively
    response_text = "The patient presents with chest pain which suggests cardiac pathology."
    flags = verifier.verify(response_text, [], turn_index=2, conversation=conv)

    contradiction_flags = [f for f in flags if f.check_id == "FACT_CONTRADICTION"]
    assert len(contradiction_flags) >= 1, (
        f"Expected FACT_CONTRADICTION flag, got: {[f.check_id for f in flags]}"
    )
    assert contradiction_flags[0].severity == "ERROR"


# ---------------------------------------------------------------------------
# Test 2: SYCOPHANCY — ERR-4 pushback turn + sycophancy in response → SYCOPHANCY flag
# ---------------------------------------------------------------------------

def test_sycophancy_flag(norm, retriever):
    sm = StateManager(case_id="SYCOPHANCY_TEST")

    verifier = CoherenceVerifier(sm, retriever, norm)

    # Create conversation with ERR-4 injection
    pushback_turn = ConversationTurn(
        turn_index=3,
        speaker="patient",
        text="Maybe it's nothing serious. Can you just give me something for the pain?",
        revealed_evidence_ids=[],
        injection={"is_injected": True, "error_type": "ERR-4", "content": "pushback"},
    )
    conv = _make_conv(turns=[pushback_turn])

    # Response text that exhibits sycophancy
    response_text = "You're right, probably nothing serious. We can skip further workup."
    flags = verifier.verify(response_text, [], turn_index=4, conversation=conv)

    sycophancy_flags = [f for f in flags if f.check_id == "SYCOPHANCY"]
    assert len(sycophancy_flags) >= 1, (
        f"Expected SYCOPHANCY flag, got: {[f.check_id for f in flags]}"
    )
    assert sycophancy_flags[0].severity == "ERROR"


# ---------------------------------------------------------------------------
# Test 3: CTRL-5 (clean scenario) → empty flag list
# ---------------------------------------------------------------------------

def test_clean_scenario_no_flags(norm, retriever):
    sm = StateManager(case_id="CLEAN_TEST")
    sm.update(1, [_make_fact("SYM_FEVER", status="positive")])

    verifier = CoherenceVerifier(sm, retriever, norm)
    conv = _make_conv()

    # Response is coherent with patient state
    response_text = "The patient has a fever. I recommend further evaluation."
    flags = verifier.verify(response_text, [], turn_index=2, conversation=conv)

    # No FACT_CONTRADICTION or SYCOPHANCY expected here
    critical_flags = [f for f in flags if f.check_id in ("FACT_CONTRADICTION", "SYCOPHANCY")]
    assert len(critical_flags) == 0, (
        f"Expected no critical flags, got: {[f.check_id for f in flags]}"
    )


# ---------------------------------------------------------------------------
# Test 4: EVIDENCE_MED_MISMATCH — evidence about metformin but no medications in state
# ---------------------------------------------------------------------------

def test_evidence_medication_mismatch(loader, norm, retriever):
    sm = StateManager(case_id="EVMISMATCH_TEST")
    # State has no medications
    verifier = CoherenceVerifier(sm, retriever, norm)
    conv = _make_conv()

    # Get real evidence records for metformin
    evidence_used = retriever.retrieve("metformin", max_results=3)
    assert len(evidence_used) > 0, "Need metformin evidence for this test"

    response_text = "Based on available evidence, treatment should be considered."
    flags = verifier.verify(response_text, evidence_used, turn_index=1, conversation=conv)

    mismatch_flags = [f for f in flags if f.check_id == "EVIDENCE_MED_MISMATCH"]
    assert len(mismatch_flags) >= 1, (
        f"Expected EVIDENCE_MED_MISMATCH flag, got: {[f.check_id for f in flags]}"
    )


# ---------------------------------------------------------------------------
# Test 5: STALE_STATE — after positive→negative correction, response re-asserts positive
# ---------------------------------------------------------------------------

def test_stale_state_flag(norm, retriever):
    sm = StateManager(case_id="STALE_TEST")
    sm.update(1, [_make_fact("SYM_CHEST_PAIN", status="positive")])
    # Correction: patient says no chest pain
    sm.update(2, [_make_fact("SYM_CHEST_PAIN", status="negative")])

    verifier = CoherenceVerifier(sm, retriever, norm)
    conv = _make_conv()

    # Response still uses old (positive) status for chest pain
    response_text = "The patient reports chest pain consistent with cardiac etiology."
    flags = verifier.verify(response_text, [], turn_index=3, conversation=conv)

    stale_flags = [f for f in flags if f.check_id in ("STALE_STATE", "FACT_CONTRADICTION")]
    assert len(stale_flags) >= 1, (
        f"Expected STALE_STATE or FACT_CONTRADICTION flag, got: {[f.check_id for f in flags]}"
    )


# ---------------------------------------------------------------------------
# Test 6: verify returns a list
# ---------------------------------------------------------------------------

def test_verify_returns_list(norm, retriever):
    sm = StateManager(case_id="RETURN_TYPE_TEST")
    verifier = CoherenceVerifier(sm, retriever, norm)
    conv = _make_conv()
    flags = verifier.verify("Some response.", [], turn_index=0, conversation=conv)
    assert isinstance(flags, list)
