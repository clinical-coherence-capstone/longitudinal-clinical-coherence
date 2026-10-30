"""
test_state_extractor.py — Unit tests for StateExtractor.
"""
from __future__ import annotations

import pytest
from state_extractor import StateExtractor
from models import ClinicalFact, ConversationTurn


@pytest.fixture
def extractor():
    return StateExtractor()


def _make_turn(text: str, turn_index: int = 0, revealed_ids: list | None = None) -> ConversationTurn:
    return ConversationTurn(
        turn_index=turn_index,
        speaker="patient",
        text=text,
        revealed_evidence_ids=revealed_ids or [],
        injection={},
    )


# ---------------------------------------------------------------------------
# Test 1: 'No chest pain at all' → ClinicalFact(fact_id='SYM_CHEST_PAIN', status='negative')
# ---------------------------------------------------------------------------

def test_negated_chest_pain(extractor):
    turn = _make_turn("No chest pain at all.")
    facts = extractor.extract_from_turn(turn, turn_index=1)
    chest_pain_facts = [f for f in facts if f.fact_id == "SYM_CHEST_PAIN"]
    assert len(chest_pain_facts) == 1, f"Expected SYM_CHEST_PAIN fact, got: {facts}"
    assert chest_pain_facts[0].status == "negative", (
        f"Expected negative, got: {chest_pain_facts[0].status}"
    )


# ---------------------------------------------------------------------------
# Test 2: 'I have a fever' → ClinicalFact(fact_id='SYM_FEVER', status='positive')
# ---------------------------------------------------------------------------

def test_positive_fever(extractor):
    turn = _make_turn("I have a fever.")
    facts = extractor.extract_from_turn(turn, turn_index=0)
    fever_facts = [f for f in facts if f.fact_id == "SYM_FEVER"]
    assert len(fever_facts) == 1, f"Expected SYM_FEVER fact, got: {facts}"
    assert fever_facts[0].status == "positive", (
        f"Expected positive, got: {fever_facts[0].status}"
    )


# ---------------------------------------------------------------------------
# Test 3: empty string → empty list
# ---------------------------------------------------------------------------

def test_empty_text_returns_empty_list(extractor):
    turn = _make_turn("")
    facts = extractor.extract_from_turn(turn, turn_index=0)
    assert facts == [], f"Expected [], got: {facts}"


# ---------------------------------------------------------------------------
# Test 4: revealed_evidence_ids non-empty → len(facts) == len(revealed_ids), status='positive'
# ---------------------------------------------------------------------------

def test_revealed_evidence_ids_path(extractor):
    revealed = ["E_91", "E_53", "E_76"]
    turn = _make_turn("", revealed_ids=revealed)
    facts = extractor.extract_from_turn(turn, turn_index=2)
    assert len(facts) == len(revealed), (
        f"Expected {len(revealed)} facts, got {len(facts)}"
    )
    for fact in facts:
        assert fact.status == "positive", (
            f"Expected all revealed facts to be positive, got {fact.status} for {fact.fact_id}"
        )


# ---------------------------------------------------------------------------
# Test 5: 'denies shortness of breath' → negative status
# ---------------------------------------------------------------------------

def test_denies_negation(extractor):
    turn = _make_turn("Patient denies shortness of breath.")
    facts = extractor.extract_from_turn(turn, turn_index=0)
    dyspnea_facts = [f for f in facts if f.fact_id == "SYM_DYSPNEA"]
    assert dyspnea_facts, f"Expected SYM_DYSPNEA, got: {facts}"
    assert dyspnea_facts[0].status == "negative"


# ---------------------------------------------------------------------------
# Test 6: unmentioned facts are not created
# ---------------------------------------------------------------------------

def test_unmentioned_facts_not_created(extractor):
    turn = _make_turn("I feel fine today.")
    facts = extractor.extract_from_turn(turn, turn_index=0)
    # "fine" is not in KEYWORD_MAP, so no facts should be created
    assert facts == [], f"Expected no facts for 'I feel fine today.', got: {facts}"


# ---------------------------------------------------------------------------
# Test 7: keyword-matched facts have confidence=0.7
# ---------------------------------------------------------------------------

def test_keyword_confidence_is_07(extractor):
    turn = _make_turn("I have a headache.")
    facts = extractor.extract_from_turn(turn, turn_index=0)
    headache_facts = [f for f in facts if f.fact_id == "SYM_HEADACHE"]
    assert headache_facts, "Expected SYM_HEADACHE fact"
    assert headache_facts[0].confidence == 0.7


# ---------------------------------------------------------------------------
# Test 8: revealed_evidence_ids have confidence=1.0
# ---------------------------------------------------------------------------

def test_revealed_evidence_confidence_is_10(extractor):
    revealed = ["E_91"]
    turn = _make_turn("", revealed_ids=revealed)
    facts = extractor.extract_from_turn(turn, turn_index=0)
    assert facts[0].confidence == 1.0


# ---------------------------------------------------------------------------
# Test 9: classify_fact_type returns correct types
# ---------------------------------------------------------------------------

def test_classify_fact_type():
    assert StateExtractor.classify_fact_type("SYM_FEVER") == "symptom"
    assert StateExtractor.classify_fact_type("MED_METFORMIN") == "medication"
    assert StateExtractor.classify_fact_type("ANT_DIABETES") == "antecedent"
