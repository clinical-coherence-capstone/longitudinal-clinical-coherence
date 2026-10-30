"""
test_evidence_retriever.py — Unit tests for EvidenceRetriever.
"""
from __future__ import annotations

import pytest
from dataset_loader import DatasetLoader
from medication_normalizer import MedicationNormalizer
from evidence_retriever import EvidenceRetriever
from models import PatientState
from datetime import datetime, timezone


@pytest.fixture(scope="module")
def retriever():
    loader = DatasetLoader()
    norm = MedicationNormalizer(loader)
    return EvidenceRetriever(loader, norm)


def _make_state(medications: list[str]) -> PatientState:
    return PatientState(
        case_id="TEST",
        version=1,
        turn_number=1,
        timestamp=datetime.now(timezone.utc).isoformat(),
        facts={},
        revealed_evidence_ids=[],
        medications=medications,
    )


# ---------------------------------------------------------------------------
# Test 1: retrieve('metformin') returns list with first record.section_name=='BOXED WARNING'
# ---------------------------------------------------------------------------

def test_retrieve_metformin_boxed_warning_first(retriever):
    results = retriever.retrieve("metformin")
    assert len(results) > 0, "Expected results for metformin"
    assert results[0].section_name == "BOXED WARNING", (
        f"Expected BOXED WARNING first, got {results[0].section_name}"
    )


# ---------------------------------------------------------------------------
# Test 2: retrieve('aspirin') returns []
# ---------------------------------------------------------------------------

def test_retrieve_aspirin_returns_empty(retriever):
    results = retriever.retrieve("aspirin")
    assert results == [], f"Expected [] for aspirin, got {len(results)} records"


# ---------------------------------------------------------------------------
# Test 3: retrieve_for_state with state.medications=['metformin'] returns non-empty list
# ---------------------------------------------------------------------------

def test_retrieve_for_state_metformin(retriever):
    state = _make_state(["metformin"])
    results = retriever.retrieve_for_state(state)
    assert len(results) > 0, "Expected evidence records for metformin in state"


# ---------------------------------------------------------------------------
# Test 4: retrieve('alogliptin') returns non-empty list
# ---------------------------------------------------------------------------

def test_retrieve_alogliptin_returns_records(retriever):
    results = retriever.retrieve("alogliptin")
    assert len(results) > 0, "Expected evidence records for alogliptin"


# ---------------------------------------------------------------------------
# Test 5: max_results is respected
# ---------------------------------------------------------------------------

def test_retrieve_respects_max_results(retriever):
    results = retriever.retrieve("metformin", max_results=2)
    assert len(results) <= 2, f"Expected at most 2 results, got {len(results)}"


# ---------------------------------------------------------------------------
# Test 6: retrieve_for_state with empty medications returns []
# ---------------------------------------------------------------------------

def test_retrieve_for_state_empty_medications(retriever):
    state = _make_state([])
    results = retriever.retrieve_for_state(state)
    assert results == [], f"Expected [] for empty medications, got {len(results)}"


# ---------------------------------------------------------------------------
# Test 7: retrieve('unresolved_drug_xyz') returns []
# ---------------------------------------------------------------------------

def test_retrieve_unknown_drug_returns_empty(retriever):
    results = retriever.retrieve("unresolved_drug_xyz_12345")
    assert results == []


# ---------------------------------------------------------------------------
# Test 8: retrieve_for_state with 'Medication: metformin' description prefix
# ---------------------------------------------------------------------------

def test_retrieve_for_state_with_medication_prefix(retriever):
    # State medications may contain "Medication: metformin" from StateExtractor
    state = _make_state(["Medication: metformin"])
    results = retriever.retrieve_for_state(state)
    assert len(results) > 0, (
        "Expected evidence records when state has 'Medication: metformin'"
    )


# ---------------------------------------------------------------------------
# Test 9: results are sorted by section priority (BOXED WARNING before others)
# ---------------------------------------------------------------------------

def test_results_sorted_by_priority(retriever):
    results = retriever.retrieve("metformin", max_results=5)
    if len(results) >= 2:
        from evidence_retriever import SECTION_PRIORITY
        first_priority = SECTION_PRIORITY.get(results[0].section_name, 9)
        second_priority = SECTION_PRIORITY.get(results[1].section_name, 9)
        assert first_priority <= second_priority, (
            f"Results not sorted: {results[0].section_name} > {results[1].section_name}"
        )
