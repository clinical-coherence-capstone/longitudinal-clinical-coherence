"""
test_models.py — Unit tests for all 12 dataclasses in models.py.

Each dataclass must be importable, instantiatable with minimal valid arguments,
and enforce documented invariants.
"""
import pytest
from datetime import datetime, timezone

from models import (
    CoherenceFlag,
    ClinicalFact,
    ConditionMeta,
    Conversation,
    ConversationTurn,
    EvidenceRecord,
    EvidenceVocabEntry,
    MedicationNormResult,
    PatientCase,
    PatientState,
    RxNormConcept,
    StateVersion,
    VerificationResult,
)


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# EvidenceVocabEntry
# ---------------------------------------------------------------------------

class TestEvidenceVocabEntry:
    def test_instantiation_minimal(self):
        entry = EvidenceVocabEntry(
            evidence_id="E_91",
            name="E_91",
            data_type="B",
            is_antecedent=False,
            question_en="Do you have a fever?",
            default_value="",
            possible_values={},
        )
        assert entry.evidence_id == "E_91"
        assert entry.data_type == "B"
        assert entry.is_antecedent is False

    def test_possible_values_dict(self):
        entry = EvidenceVocabEntry(
            evidence_id="E_55",
            name="E_55",
            data_type="M",
            is_antecedent=False,
            question_en="Do you feel pain somewhere?",
            default_value="V_123",
            possible_values={"V_123": "nowhere", "V_14": "iliac wing(R)"},
        )
        assert entry.possible_values["V_123"] == "nowhere"


# ---------------------------------------------------------------------------
# ConditionMeta
# ---------------------------------------------------------------------------

class TestConditionMeta:
    def test_instantiation(self):
        meta = ConditionMeta(
            condition_id="Anemia",
            icd10_id="D64.9",
            severity=4,
            symptom_count=16,
            antecedent_count=8,
        )
        assert meta.condition_id == "Anemia"
        assert meta.severity == 4
        assert isinstance(meta.symptom_count, int)


# ---------------------------------------------------------------------------
# PatientCase
# ---------------------------------------------------------------------------

class TestPatientCase:
    def test_instantiation(self):
        case = PatientCase(
            case_id="SYNTHETIC_000",
            age=55,
            sex="F",
            initial_evidence="E_154",
            evidences=["E_154", "E_76", "E_82"],
            pathology="Anemia",
            differential_diagnosis=[("Anemia", 0.35), ("Atrial fibrillation", 0.15)],
            severity=4,
        )
        assert case.case_id == "SYNTHETIC_000"
        assert isinstance(case.case_id, str)
        assert case.sex in ("M", "F")

    def test_case_id_is_string(self):
        case = PatientCase(
            case_id="SYNTHETIC_001",
            age=62,
            sex="M",
            initial_evidence="E_53",
            evidences=["E_53"],
            pathology="Possible NSTEMI / STEMI",
            differential_diagnosis=[],
            severity=1,
        )
        assert isinstance(case.case_id, str)


# ---------------------------------------------------------------------------
# ClinicalFact — status must be one of {positive, negative, unknown}
# ---------------------------------------------------------------------------

class TestClinicalFact:
    def _make_fact(self, status: str) -> ClinicalFact:
        return ClinicalFact(
            fact_id="E_91",
            description="Fever",
            status=status,
            source_turn=1,
            timestamp=iso_now(),
            confidence=0.9,
            is_antecedent=False,
        )

    def test_status_positive(self):
        fact = self._make_fact("positive")
        assert fact.status == "positive"

    def test_status_negative(self):
        fact = self._make_fact("negative")
        assert fact.status == "negative"

    def test_status_unknown(self):
        fact = self._make_fact("unknown")
        assert fact.status == "unknown"

    def test_all_valid_statuses(self):
        for status in ("positive", "negative", "unknown"):
            fact = self._make_fact(status)
            assert fact.status in {"positive", "negative", "unknown"}

    def test_fact_id_is_string(self):
        fact = self._make_fact("positive")
        assert isinstance(fact.fact_id, str)


# ---------------------------------------------------------------------------
# PatientState
# ---------------------------------------------------------------------------

class TestPatientState:
    def test_instantiation_defaults(self):
        state = PatientState(
            case_id="SYNTHETIC_000",
            version=0,
            turn_number=0,
            timestamp=iso_now(),
        )
        assert state.facts == {}
        assert state.revealed_evidence_ids == []
        assert state.medications == []

    def test_instantiation_with_data(self):
        fact = ClinicalFact(
            fact_id="E_91",
            description="Fever",
            status="positive",
            source_turn=1,
            timestamp=iso_now(),
            confidence=0.9,
            is_antecedent=False,
        )
        state = PatientState(
            case_id="CASE_01",
            version=1,
            turn_number=2,
            timestamp=iso_now(),
            facts={"E_91": fact},
            revealed_evidence_ids=["E_91"],
            medications=["metformin"],
        )
        assert "E_91" in state.facts
        assert state.version == 1


# ---------------------------------------------------------------------------
# StateVersion
# ---------------------------------------------------------------------------

class TestStateVersion:
    def test_instantiation(self):
        state = PatientState(
            case_id="CASE_01",
            version=0,
            turn_number=0,
            timestamp=iso_now(),
        )
        sv = StateVersion(
            version=0,
            turn_number=0,
            snapshot=state,
            change_summary="Initial state.",
        )
        assert sv.version == 0
        assert sv.snapshot.case_id == "CASE_01"


# ---------------------------------------------------------------------------
# ConversationTurn
# ---------------------------------------------------------------------------

class TestConversationTurn:
    def test_instantiation_defaults(self):
        turn = ConversationTurn(
            turn_index=0,
            speaker="patient",
            text="I have been feeling tired.",
        )
        assert turn.speaker == "patient"
        assert turn.revealed_evidence_ids == []
        assert turn.injection == {}

    def test_instantiation_with_injection(self):
        turn = ConversationTurn(
            turn_index=1,
            speaker="doctor",
            text="Can you tell me more?",
            revealed_evidence_ids=["E_91"],
            injection={"is_injected": False, "error_type": "", "content": ""},
        )
        assert turn.injection["is_injected"] is False


# ---------------------------------------------------------------------------
# Conversation
# ---------------------------------------------------------------------------

class TestConversation:
    def test_instantiation_defaults(self):
        conv = Conversation(case_id="SYNTHETIC_000")
        assert conv.turns == []
        assert conv.current_turn == 0

    def test_with_turns(self):
        t = ConversationTurn(turn_index=0, speaker="patient", text="Hello.")
        conv = Conversation(case_id="CASE_01", turns=[t], current_turn=1)
        assert len(conv.turns) == 1


# ---------------------------------------------------------------------------
# RxNormConcept
# ---------------------------------------------------------------------------

class TestRxNormConcept:
    def test_instantiation(self):
        c = RxNormConcept(
            rxcui="6809",
            rxnorm_name="metformin",
            tty="IN",
            concept_type="ingredient",
            ingredient_names="metformin",
            ingredient_rxcuis="6809",
        )
        assert c.rxcui == "6809"
        assert c.tty == "IN"


# ---------------------------------------------------------------------------
# MedicationNormResult
# ---------------------------------------------------------------------------

class TestMedicationNormResult:
    def test_resolved(self):
        r = MedicationNormResult(
            input_text="metformin",
            rxcui="6809",
            rxnorm_name="metformin",
            tty="IN",
            match_method="exact",
            confidence=1.0,
        )
        assert r.rxcui == "6809"
        assert r.match_method == "exact"

    def test_unresolved_none_fields(self):
        r = MedicationNormResult(
            input_text="aspirin",
            rxcui=None,
            rxnorm_name=None,
            tty=None,
            match_method="unresolved",
            confidence=0.0,
        )
        assert r.rxcui is None
        assert r.rxnorm_name is None
        assert r.tty is None


# ---------------------------------------------------------------------------
# EvidenceRecord
# ---------------------------------------------------------------------------

class TestEvidenceRecord:
    def test_instantiation(self):
        rec = EvidenceRecord(
            evidence_id="DM-EV-ALOG-MET-001",
            active_ingredient="Metformin hydrochloride",
            product_name="ALOGLIPTIN AND METFORMIN HYDROCHLORIDE tablet",
            all_active_ingredients="Alogliptin benzoate; Metformin hydrochloride",
            section_name="BOXED WARNING",
            evidence_text="WARNING: LACTIC ACIDOSIS.",
            source_url="https://dailymed.nlm.nih.gov/",
            evidence_scope="Single ingredient (Metformin component)",
            verification_status="verified",
            notes="Boxed warning driven by metformin.",
        )
        assert rec.evidence_id == "DM-EV-ALOG-MET-001"
        assert rec.verification_status == "verified"


# ---------------------------------------------------------------------------
# CoherenceFlag
# ---------------------------------------------------------------------------

class TestCoherenceFlag:
    def test_instantiation(self):
        flag = CoherenceFlag(
            check_id="FACT_CONTRADICTION",
            severity="ERROR",
            description="Status changed from positive to negative without explanation.",
            turn_index=3,
            evidence="E_91 was positive in turn 1, now negative.",
        )
        assert flag.check_id == "FACT_CONTRADICTION"
        assert flag.severity == "ERROR"


# ---------------------------------------------------------------------------
# VerificationResult
# ---------------------------------------------------------------------------

class TestVerificationResult:
    def test_instantiation_defaults(self):
        vr = VerificationResult(pass_through=True)
        assert vr.pass_through is True
        assert vr.flags == []
        assert vr.gate_decision == "PASS"
        assert vr.reasoning == ""

    def test_with_flags(self):
        flag = CoherenceFlag(
            check_id="MED_TARGET_MISMATCH",
            severity="WARNING",
            description="Medication does not match patient's condition.",
            turn_index=2,
            evidence="Patient has type 1 diabetes; alogliptin+metformin contraindicated.",
        )
        vr = VerificationResult(
            pass_through=False,
            flags=[flag],
            gate_decision="WARN",
            reasoning="Medication mismatch detected.",
        )
        assert vr.gate_decision == "WARN"
        assert len(vr.flags) == 1
