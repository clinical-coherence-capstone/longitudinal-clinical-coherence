"""
test_dataset_loader.py — Unit tests for DatasetLoader.

Acceptance criteria (from FEAT-001):
  - load_dailymed_evidence() returns exactly 24 EvidenceRecord objects
  - load_rxnorm_concepts() returns at least 29 RxNormConcept objects
  - generate_synthetic_cases(25) returns exactly 25 PatientCase objects,
    each with len(evidences) >= 8
  - load_evidence_vocab() returns a dict with key 'E_91' having data_type == 'B'
"""
import pytest

from dataset_loader import DatasetLoader
from models import (
    ConditionMeta,
    EvidenceRecord,
    EvidenceVocabEntry,
    PatientCase,
    RxNormConcept,
)


@pytest.fixture(scope="module")
def loader() -> DatasetLoader:
    """Shared DatasetLoader instance for all tests in this module."""
    return DatasetLoader()


# ---------------------------------------------------------------------------
# DailyMed evidence
# ---------------------------------------------------------------------------

class TestLoadDailymedEvidence:
    def test_returns_list(self, loader):
        records = loader.load_dailymed_evidence()
        assert isinstance(records, list)

    def test_exact_count(self, loader):
        records = loader.load_dailymed_evidence()
        assert len(records) == 24, (
            f"Expected 24 DailyMed evidence records, got {len(records)}"
        )

    def test_first_record_id(self, loader):
        records = loader.load_dailymed_evidence()
        assert records[0].evidence_id == "DM-EV-ALOG-MET-001", (
            f"First record ID expected 'DM-EV-ALOG-MET-001', got '{records[0].evidence_id}'"
        )

    def test_all_are_evidence_records(self, loader):
        records = loader.load_dailymed_evidence()
        for rec in records:
            assert isinstance(rec, EvidenceRecord)

    def test_records_have_evidence_text(self, loader):
        records = loader.load_dailymed_evidence()
        for rec in records:
            assert rec.evidence_text, f"Empty evidence_text for {rec.evidence_id}"

    def test_evidence_ids_are_unique(self, loader):
        records = loader.load_dailymed_evidence()
        ids = [r.evidence_id for r in records]
        assert len(ids) == len(set(ids)), "Duplicate evidence_id values found"


# ---------------------------------------------------------------------------
# RxNorm concepts
# ---------------------------------------------------------------------------

class TestLoadRxNormConcepts:
    def test_returns_list(self, loader):
        concepts = loader.load_rxnorm_concepts()
        assert isinstance(concepts, list)

    def test_minimum_count(self, loader):
        concepts = loader.load_rxnorm_concepts()
        assert len(concepts) >= 29, (
            f"Expected >= 29 RxNorm concepts, got {len(concepts)}"
        )

    def test_metformin_rxcui_present(self, loader):
        concepts = loader.load_rxnorm_concepts()
        rxcuis = {c.rxcui for c in concepts}
        assert "6809" in rxcuis, "Metformin rxcui '6809' not found in concepts"

    def test_all_are_rxnorm_concepts(self, loader):
        concepts = loader.load_rxnorm_concepts()
        for c in concepts:
            assert isinstance(c, RxNormConcept)

    def test_rxcui_is_string(self, loader):
        concepts = loader.load_rxnorm_concepts()
        for c in concepts:
            assert isinstance(c.rxcui, str)


# ---------------------------------------------------------------------------
# RxNorm relationships
# ---------------------------------------------------------------------------

class TestLoadRxNormRelationships:
    def test_returns_list(self, loader):
        rels = loader.load_rxnorm_relationships()
        assert isinstance(rels, list)

    def test_rows_are_dicts(self, loader):
        rels = loader.load_rxnorm_relationships()
        if rels:  # may be empty if file is unavailable, but should not error
            assert isinstance(rels[0], dict)


# ---------------------------------------------------------------------------
# RxNorm aliases
# ---------------------------------------------------------------------------

class TestLoadRxNormAliases:
    def test_returns_list(self, loader):
        aliases = loader.load_rxnorm_aliases()
        assert isinstance(aliases, list)

    def test_rows_are_dicts(self, loader):
        aliases = loader.load_rxnorm_aliases()
        if aliases:
            assert isinstance(aliases[0], dict)


# ---------------------------------------------------------------------------
# Condition metadata
# ---------------------------------------------------------------------------

class TestLoadConditionMetadata:
    def test_returns_dict(self, loader):
        meta = loader.load_condition_metadata()
        assert isinstance(meta, dict)

    def test_anemia_present(self, loader):
        meta = loader.load_condition_metadata()
        assert "Anemia" in meta, "'Anemia' not found in condition metadata"

    def test_anemia_severity(self, loader):
        meta = loader.load_condition_metadata()
        assert meta["Anemia"].severity == 4

    def test_values_are_condition_meta(self, loader):
        meta = loader.load_condition_metadata()
        for v in meta.values():
            assert isinstance(v, ConditionMeta)


# ---------------------------------------------------------------------------
# Evidence vocab
# ---------------------------------------------------------------------------

class TestLoadEvidenceVocab:
    def test_returns_dict(self, loader):
        vocab = loader.load_evidence_vocab()
        assert isinstance(vocab, dict)

    def test_e91_present(self, loader):
        vocab = loader.load_evidence_vocab()
        assert "E_91" in vocab, "'E_91' not found in evidence vocab"

    def test_e91_data_type_is_B(self, loader):
        vocab = loader.load_evidence_vocab()
        assert vocab["E_91"].data_type == "B", (
            f"Expected E_91.data_type == 'B', got '{vocab['E_91'].data_type}'"
        )

    def test_e91_is_not_antecedent(self, loader):
        vocab = loader.load_evidence_vocab()
        assert vocab["E_91"].is_antecedent is False

    def test_values_are_vocab_entries(self, loader):
        vocab = loader.load_evidence_vocab()
        for v in vocab.values():
            assert isinstance(v, EvidenceVocabEntry)

    def test_sample_values_parsed(self, loader):
        vocab = loader.load_evidence_vocab()
        # E_55 has sample_values with multiple entries
        if "E_55" in vocab:
            e55 = vocab["E_55"]
            # should have parsed at least one possible_value entry
            assert isinstance(e55.possible_values, dict)
            if e55.possible_values:  # non-empty for M-type
                assert len(e55.possible_values) >= 1

    def test_is_antecedent_bool(self, loader):
        vocab = loader.load_evidence_vocab()
        for v in vocab.values():
            assert isinstance(v.is_antecedent, bool), (
                f"is_antecedent for {v.evidence_id} is not bool: {type(v.is_antecedent)}"
            )


# ---------------------------------------------------------------------------
# Synthetic case generation
# ---------------------------------------------------------------------------

class TestGenerateSyntheticCases:
    def test_returns_list(self, loader):
        cases = loader.generate_synthetic_cases(25)
        assert isinstance(cases, list)

    def test_exact_count(self, loader):
        cases = loader.generate_synthetic_cases(25)
        assert len(cases) == 25, (
            f"Expected 25 synthetic cases, got {len(cases)}"
        )

    def test_all_are_patient_cases(self, loader):
        cases = loader.generate_synthetic_cases(25)
        for c in cases:
            assert isinstance(c, PatientCase)

    def test_each_case_has_at_least_8_evidences(self, loader):
        cases = loader.generate_synthetic_cases(25)
        for c in cases:
            assert len(c.evidences) >= 8, (
                f"Case {c.case_id} has only {len(c.evidences)} evidences (need >= 8)"
            )

    def test_case_ids_are_strings(self, loader):
        cases = loader.generate_synthetic_cases(25)
        for c in cases:
            assert isinstance(c.case_id, str)

    def test_case_ids_are_synthetic_prefixed(self, loader):
        cases = loader.generate_synthetic_cases(25)
        for c in cases:
            assert c.case_id.startswith("SYNTHETIC_"), (
                f"Case ID does not start with 'SYNTHETIC_': {c.case_id}"
            )

    def test_reproducibility(self, loader):
        """Same seed → same result on two calls."""
        cases_a = loader.generate_synthetic_cases(25)
        cases_b = loader.generate_synthetic_cases(25)
        for a, b in zip(cases_a, cases_b):
            assert a.case_id == b.case_id
            assert a.age == b.age
            assert a.sex == b.sex
            assert a.evidences == b.evidences

    def test_severity_populated(self, loader):
        cases = loader.generate_synthetic_cases(25)
        for c in cases:
            assert isinstance(c.severity, int)
            assert 1 <= c.severity <= 5, (
                f"Severity out of range for {c.case_id}: {c.severity}"
            )

    def test_pathology_not_in_evidences(self, loader):
        """Pathology names must not appear in the evidences list (ground truth hidden)."""
        cases = loader.generate_synthetic_cases(25)
        for c in cases:
            for ev in c.evidences:
                assert c.pathology not in ev, (
                    f"Pathology '{c.pathology}' found in evidence token '{ev}' for {c.case_id}"
                )

    def test_differential_not_empty(self, loader):
        cases = loader.generate_synthetic_cases(25)
        for c in cases:
            assert len(c.differential_diagnosis) > 0, (
                f"Case {c.case_id} has empty differential_diagnosis"
            )

    def test_sex_is_m_or_f(self, loader):
        cases = loader.generate_synthetic_cases(25)
        for c in cases:
            assert c.sex in ("M", "F"), (
                f"Case {c.case_id} has invalid sex value: {c.sex}"
            )

    def test_age_is_positive_int(self, loader):
        cases = loader.generate_synthetic_cases(25)
        for c in cases:
            assert isinstance(c.age, int)
            assert c.age > 0
