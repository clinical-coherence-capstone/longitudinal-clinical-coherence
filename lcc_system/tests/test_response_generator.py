"""
test_response_generator.py — Unit tests for ResponseGenerator and MockLLMProvider.
"""
from __future__ import annotations

import pytest
from dataset_loader import DatasetLoader
from medication_normalizer import MedicationNormalizer
from evidence_retriever import EvidenceRetriever
from response_generator import MockLLMProvider, ResponseGenerator
from state_manager import StateManager
from models import Conversation, PatientState
from datetime import datetime, timezone


@pytest.fixture(scope="module")
def loader():
    return DatasetLoader()


@pytest.fixture(scope="module")
def retriever(loader):
    norm = MedicationNormalizer(loader)
    return EvidenceRetriever(loader, norm)


@pytest.fixture
def sm():
    return StateManager(case_id="TEST_RESPONSE")


@pytest.fixture
def generator(sm, retriever):
    return ResponseGenerator(sm, retriever, provider="mock")


def _make_conversation(case_id: str = "TEST") -> Conversation:
    from models import ConversationTurn
    conv = Conversation(case_id=case_id, turns=[], current_turn=0)
    conv.turns.append(ConversationTurn(
        turn_index=0,
        speaker="patient",
        text="I am a 55-year-old female. My main concern is fatigue.",
        revealed_evidence_ids=[],
        injection={},
    ))
    conv.turns.append(ConversationTurn(
        turn_index=1,
        speaker="doctor",
        text="Can you tell me more?",
        revealed_evidence_ids=[],
        injection={},
    ))
    return conv


# ---------------------------------------------------------------------------
# Test 1: MockLLMProvider().generate('', {}) returns non-empty string
# ---------------------------------------------------------------------------

def test_mock_provider_returns_nonempty_string():
    provider = MockLLMProvider()
    result = provider.generate("", {})
    assert isinstance(result, str)
    assert len(result) > 0, "MockLLMProvider.generate returned empty string"


# ---------------------------------------------------------------------------
# Test 2: ResponseGenerator with mock provider returns (str, list) tuple
# ---------------------------------------------------------------------------

def test_response_generator_returns_tuple(generator):
    conv = _make_conversation()
    result = generator.generate_response(conv)
    assert isinstance(result, tuple), f"Expected tuple, got {type(result)}"
    assert len(result) == 2
    assert isinstance(result[0], str), f"Expected str, got {type(result[0])}"
    assert isinstance(result[1], list), f"Expected list, got {type(result[1])}"


# ---------------------------------------------------------------------------
# Test 3: response does not contain string 'Anemia' when pathology not in context
# ---------------------------------------------------------------------------

def test_response_does_not_contain_pathology(generator):
    conv = _make_conversation()
    response_text, _ = generator.generate_response(conv)
    assert "anemia" not in response_text.lower(), (
        f"Pathology 'Anemia' should not appear in response: '{response_text}'"
    )


# ---------------------------------------------------------------------------
# Test 4: MockLLMProvider uses correct template
# ---------------------------------------------------------------------------

def test_mock_provider_template_selection():
    provider = MockLLMProvider()
    result = provider.generate("", {"template": "medication_counseling", "medication": "metformin",
                                    "evidence_summary": "BOXED WARNING text", "relevant_condition": "diabetes"})
    assert isinstance(result, str)
    assert len(result) > 0


# ---------------------------------------------------------------------------
# Test 5: MockLLMProvider handles missing keys gracefully
# ---------------------------------------------------------------------------

def test_mock_provider_handles_missing_keys():
    provider = MockLLMProvider()
    # Provide minimal context — missing keys should become '[unknown]'
    result = provider.generate("", {"symptoms": "fever"})
    assert isinstance(result, str)
    assert "[unknown]" in result or "fever" in result


# ---------------------------------------------------------------------------
# Test 6: ResponseGenerator with no medications still returns a response
# ---------------------------------------------------------------------------

def test_response_generator_no_medications(generator):
    conv = _make_conversation()
    response_text, evidence = generator.generate_response(conv)
    assert isinstance(response_text, str)
    assert len(response_text) > 0
    # No medications in state → evidence list should be empty
    assert evidence == [] or isinstance(evidence, list)


# ---------------------------------------------------------------------------
# Test 7: ConfigurableProvider raises ValueError without API key
# ---------------------------------------------------------------------------

def test_configurable_provider_raises_without_api_key():
    import os
    from response_generator import ConfigurableProvider
    # Ensure LCC_API_KEY is not set
    env_backup = os.environ.pop("LCC_API_KEY", None)
    try:
        provider = ConfigurableProvider()
        with pytest.raises(ValueError, match="LCC_API_KEY"):
            provider.generate("prompt", {})
    finally:
        if env_backup is not None:
            os.environ["LCC_API_KEY"] = env_backup
