"""
test_conversation_generator.py — Unit tests for ConversationGenerator.
"""
from __future__ import annotations

import pytest
from dataset_loader import DatasetLoader
from conversation_generator import ConversationGenerator
from models import ConversationTurn


@pytest.fixture(scope="module")
def loader():
    return DatasetLoader()


@pytest.fixture(scope="module")
def generator(loader):
    return ConversationGenerator(loader)


@pytest.fixture(scope="module")
def anemia_case(loader):
    cases = loader.generate_synthetic_cases(25)
    # SYNTHETIC_000 is Anemia
    return cases[0]


# ---------------------------------------------------------------------------
# Test 1: gradual_reveal produces >= 4 turns
# ---------------------------------------------------------------------------

def test_gradual_reveal_produces_at_least_4_turns(generator, anemia_case):
    conv = generator.generate_conversation(anemia_case, form="gradual_reveal")
    assert len(conv.turns) >= 4, (
        f"Expected >= 4 turns, got {len(conv.turns)}"
    )


# ---------------------------------------------------------------------------
# Test 2: no turn text contains the pathology string 'Anemia'
# ---------------------------------------------------------------------------

def test_no_pathology_leakage_in_gradual_reveal(generator, anemia_case):
    conv = generator.generate_conversation(anemia_case, form="gradual_reveal")
    for turn in conv.turns:
        assert "anemia" not in turn.text.lower(), (
            f"Pathology 'Anemia' leaked in turn {turn.turn_index}: '{turn.text[:80]}'"
        )


# ---------------------------------------------------------------------------
# Test 3: verbalize('E_91') returns a string containing 'fever'
# ---------------------------------------------------------------------------

def test_verbalize_e91_contains_fever(generator):
    result = generator.verbalize("E_91")
    assert isinstance(result, str)
    assert "fever" in result.lower(), (
        f"Expected 'fever' in verbalize('E_91'), got: '{result}'"
    )


# ---------------------------------------------------------------------------
# Test 4: pushback form adds a turn with injection.error_type == 'ERR-4'
# ---------------------------------------------------------------------------

def test_pushback_form_adds_err4_injection(generator, anemia_case):
    conv = generator.generate_conversation(anemia_case, form="pushback")
    injected_turns = [
        t for t in conv.turns
        if isinstance(t.injection, dict) and t.injection.get("error_type") == "ERR-4"
    ]
    assert len(injected_turns) >= 1, (
        "Expected at least one turn with injection error_type='ERR-4' in pushback form"
    )


# ---------------------------------------------------------------------------
# Test 5: all turns are ConversationTurn instances
# ---------------------------------------------------------------------------

def test_all_turns_are_conversation_turn_instances(generator, anemia_case):
    conv = generator.generate_conversation(anemia_case, form="gradual_reveal")
    for turn in conv.turns:
        assert isinstance(turn, ConversationTurn), (
            f"Expected ConversationTurn, got {type(turn)}"
        )


# ---------------------------------------------------------------------------
# Test 6: conversation case_id matches the patient case
# ---------------------------------------------------------------------------

def test_conversation_case_id_matches(generator, anemia_case):
    conv = generator.generate_conversation(anemia_case, form="gradual_reveal")
    assert conv.case_id == anemia_case.case_id


# ---------------------------------------------------------------------------
# Test 7: verbalize with unknown token returns a fallback string
# ---------------------------------------------------------------------------

def test_verbalize_unknown_token_returns_fallback(generator):
    result = generator.verbalize("E_99999_NONEXISTENT")
    assert isinstance(result, str)
    assert len(result) > 0


# ---------------------------------------------------------------------------
# Test 8: pushback form still has no pathology leakage
# ---------------------------------------------------------------------------

def test_pushback_no_pathology_leakage(generator, anemia_case):
    conv = generator.generate_conversation(anemia_case, form="pushback")
    for turn in conv.turns:
        assert "anemia" not in turn.text.lower(), (
            f"Pathology leaked in pushback turn {turn.turn_index}: '{turn.text[:80]}'"
        )
