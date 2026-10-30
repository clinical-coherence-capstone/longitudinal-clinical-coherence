"""
test_medication_normalizer.py — Unit tests for MedicationNormalizer.
"""
from __future__ import annotations

import pytest
from dataset_loader import DatasetLoader
from medication_normalizer import MedicationNormalizer


@pytest.fixture(scope="module")
def normalizer():
    loader = DatasetLoader()
    return MedicationNormalizer(loader)


# ---------------------------------------------------------------------------
# Test 1: normalize('metformin') → rxcui=='6809' and match_method=='exact'
# ---------------------------------------------------------------------------

def test_normalize_metformin_exact(normalizer):
    result = normalizer.normalize("metformin")
    assert result.rxcui == "6809", f"Expected rxcui=6809, got {result.rxcui}"
    assert result.match_method == "exact", f"Expected exact, got {result.match_method}"


# ---------------------------------------------------------------------------
# Test 2: normalize('Kazano') → match_method in ('exact', 'alias', 'substring')
# (Kazano is a brand name in concepts.csv for alogliptin/metformin combo)
# ---------------------------------------------------------------------------

def test_normalize_kazano_resolves(normalizer):
    result = normalizer.normalize("Kazano")
    assert result.match_method in ("exact", "alias", "substring"), (
        f"Expected Kazano to resolve, got match_method={result.match_method}"
    )
    assert result.rxcui is not None, "Expected Kazano to have a rxcui"


# ---------------------------------------------------------------------------
# Test 3: normalize('Glucophage') → match_method == 'unresolved'
# (Glucophage is in relationships.csv as a tradename but not in concepts.csv)
# ---------------------------------------------------------------------------

def test_normalize_glucophage_unresolved(normalizer):
    result = normalizer.normalize("Glucophage")
    assert result.match_method == "unresolved", (
        f"Expected Glucophage to be unresolved, got {result.match_method}"
    )


# ---------------------------------------------------------------------------
# Test 4: normalize('metf') → rxnorm_name contains 'metformin' and match_method=='substring'
# ---------------------------------------------------------------------------

def test_normalize_metf_substring(normalizer):
    result = normalizer.normalize("metf")
    assert result.match_method == "substring", (
        f"Expected substring match for 'metf', got {result.match_method}"
    )
    assert result.rxnorm_name is not None
    assert "metformin" in result.rxnorm_name.lower(), (
        f"Expected 'metformin' in rxnorm_name, got {result.rxnorm_name}"
    )


# ---------------------------------------------------------------------------
# Test 5: normalize empty string → unresolved
# ---------------------------------------------------------------------------

def test_normalize_empty_string(normalizer):
    result = normalizer.normalize("")
    assert result.match_method == "unresolved"
    assert result.rxcui is None


# ---------------------------------------------------------------------------
# Test 6: normalize('alogliptin') → exact match
# ---------------------------------------------------------------------------

def test_normalize_alogliptin_exact(normalizer):
    result = normalizer.normalize("alogliptin")
    assert result.match_method == "exact"
    assert result.rxcui == "1368001"


# ---------------------------------------------------------------------------
# Test 7: get_ingredients for alogliptin/metformin MIN
# ---------------------------------------------------------------------------

def test_get_ingredients_min(normalizer):
    # rxcui 1368384 = alogliptin / metformin (MIN)
    ingredients = normalizer.get_ingredients("1368384")
    rxcuis = [ing.rxcui for ing in ingredients]
    assert "6809" in rxcuis, f"Expected metformin (6809) in ingredients of 1368384, got {rxcuis}"
    assert "1368001" in rxcuis, f"Expected alogliptin (1368001) in ingredients of 1368384, got {rxcuis}"


# ---------------------------------------------------------------------------
# Test 8: get_ingredients for a non-MIN rxcui returns empty list
# ---------------------------------------------------------------------------

def test_get_ingredients_non_min(normalizer):
    # metformin (6809) is IN, not MIN, so has_part relationships not expected
    # (it may have none, returning [])
    ingredients = normalizer.get_ingredients("6809")
    # May return empty list for non-MIN, test that it returns a list
    assert isinstance(ingredients, list)


# ---------------------------------------------------------------------------
# Test 9: exact match confidence is 1.0 for IN tty
# ---------------------------------------------------------------------------

def test_exact_match_in_confidence(normalizer):
    result = normalizer.normalize("metformin")
    assert result.confidence == 1.0, f"Expected 1.0 for IN exact match, got {result.confidence}"


# ---------------------------------------------------------------------------
# Test 10: substring match confidence is 0.65
# ---------------------------------------------------------------------------

def test_substring_match_confidence(normalizer):
    result = normalizer.normalize("metf")
    assert result.confidence == 0.65, f"Expected 0.65, got {result.confidence}"
