"""
test_fix_evidence_mismatch_and_correction.py

Targeted acceptance tests for:
  Fix 1 — evidence/medication mismatch detection (paracetamol → no DailyMed evidence)
  Fix 2 — explicit medication correction (ibuprofen → cetirizine)

These tests exercise the pipeline end-to-end using run_pipeline() with mocked DB
to avoid requiring a live database.
"""
from __future__ import annotations

import sys
import os
import pytest

SRC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
for d in [SRC_DIR, PROJECT_ROOT]:
    if d not in sys.path:
        sys.path.insert(0, d)

from webapp import pipeline
from webapp.pipeline import detect_medication_correction, extract_medication_mentions


# ---------------------------------------------------------------------------
# Shared DB mock (same as test_pipeline.py)
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def mock_db(monkeypatch):
    store = {}

    def fake_save(conv_id, turn_num, state_json):
        store[conv_id] = state_json

    def fake_get(conv_id):
        return store.get(conv_id)

    monkeypatch.setattr(pipeline, "save_patient_state", fake_save)
    monkeypatch.setattr(pipeline, "get_latest_patient_state", fake_get)
    return store


# ===========================================================================
# FIX 1 — Paracetamol evidence mismatch
# ===========================================================================

class TestFix1EvidenceMismatch:
    """
    Acceptance test: asking about paracetamol must NOT return PASS.
    The DailyMed corpus covers only Alogliptin/Metformin, so no evidence
    can match paracetamol.  The verifier must raise EVIDENCE_MED_MISMATCH
    and the gate must return CLARIFY (not PASS).
    """

    def test_paracetamol_gate_is_not_pass(self):
        result = pipeline.run_pipeline(
            "I want information about paracetamol. What is it generally used for?",
            conversation_id=1001,
            turn_index=0,
            prior_messages=[],
        )
        gate = result["verification"]["gate_decision"]
        assert gate != "PASS", (
            f"Gate returned PASS for paracetamol query with no matching evidence. "
            f"Expected CLARIFY or WARN. Flags: {result['verification']['flags']}"
        )

    def test_paracetamol_mismatch_flag_raised(self):
        result = pipeline.run_pipeline(
            "I want information about paracetamol. What is it generally used for?",
            conversation_id=1002,
            turn_index=0,
            prior_messages=[],
        )
        flags = result["verification"]["flags"]
        mismatch_flags = [f for f in flags if f["check_id"] == "EVIDENCE_MED_MISMATCH"]
        assert len(mismatch_flags) >= 1, (
            f"Expected EVIDENCE_MED_MISMATCH flag for paracetamol, got: "
            f"{[f['check_id'] for f in flags]}"
        )

    def test_paracetamol_evidence_panel_empty_or_unrelated_not_verified(self):
        """
        Evidence retrieved for a paracetamol query must NOT be Metformin evidence
        presented as 'active medication evidence'.
        The evidence display should be empty (no matching records), OR the
        mismatch flag must exist.
        """
        result = pipeline.run_pipeline(
            "I want information about paracetamol.",
            conversation_id=1003,
            turn_index=0,
            prior_messages=[],
        )
        evidence = result["evidence"]
        flags = result["verification"]["flags"]
        mismatch_flags = [f for f in flags if f["check_id"] == "EVIDENCE_MED_MISMATCH"]

        # If any Metformin evidence appears, the mismatch flag must be raised
        metformin_ev_present = any(
            "metformin" in (e.get("active_ingredient", "") or "").lower()
            for e in evidence
        )
        if metformin_ev_present:
            assert len(mismatch_flags) >= 1, (
                "Metformin evidence shown for paracetamol query, but no "
                "EVIDENCE_MED_MISMATCH flag was raised."
            )

    def test_metformin_query_still_passes(self):
        """Regression: asking about metformin (which IS in DailyMed) should not break."""
        result = pipeline.run_pipeline(
            "I take metformin for diabetes.",
            conversation_id=1004,
            turn_index=0,
            prior_messages=[],
        )
        # metformin IS in the corpus — may PASS or CLARIFY but must not ERROR out
        gate = result["verification"]["gate_decision"]
        assert gate in {"PASS", "CLARIFY", "WARN", "REFUSE"}, (
            f"Unexpected gate value: {gate}"
        )
        # And evidence should relate to metformin/alogliptin, not be a mismatch
        evidence = result["evidence"]
        flags = result["verification"]["flags"]
        mismatch_flags = [f for f in flags if f["check_id"] == "EVIDENCE_MED_MISMATCH"]
        # If evidence was retrieved for metformin, there should be no mismatch flag
        if evidence:
            assert len(mismatch_flags) == 0, (
                f"False EVIDENCE_MED_MISMATCH raised for metformin. Flags: {flags}"
            )


# ===========================================================================
# FIX 2 — Explicit medication correction
# ===========================================================================

class TestFix2MedicationCorrection:
    """
    Acceptance test for the 4-turn correction scenario:
      Turn 1: paracetamol
      Turn 2: ibuprofen
      Turn 3: "Actually, I meant cetirizine, not ibuprofen."
      Turn 4: summarize

    Expected state after Turn 3:
      - paracetamol: active
      - cetirizine: active
      - ibuprofen: retracted/superseded
    """

    def _run_four_turns(self, base_conv_id: int) -> dict:
        """Run all four turns and return final (turn 4) result."""
        t1 = pipeline.run_pipeline(
            "I want information about paracetamol.",
            conversation_id=base_conv_id,
            turn_index=0,
            prior_messages=[],
        )
        t2 = pipeline.run_pipeline(
            "I also take ibuprofen occasionally.",
            conversation_id=base_conv_id,
            turn_index=1,
            prior_messages=[
                {"role": "user", "content": "I want information about paracetamol."},
                {"role": "assistant", "content": t1["response_text"]},
            ],
        )
        t3 = pipeline.run_pipeline(
            "Actually, I meant that I take cetirizine, not ibuprofen.",
            conversation_id=base_conv_id,
            turn_index=2,
            prior_messages=[
                {"role": "user", "content": "I want information about paracetamol."},
                {"role": "assistant", "content": t1["response_text"]},
                {"role": "user", "content": "I also take ibuprofen occasionally."},
                {"role": "assistant", "content": t2["response_text"]},
            ],
        )
        t4 = pipeline.run_pipeline(
            "Can you summarize the medicines I have mentioned so far?",
            conversation_id=base_conv_id,
            turn_index=3,
            prior_messages=[
                {"role": "user", "content": "I want information about paracetamol."},
                {"role": "assistant", "content": t1["response_text"]},
                {"role": "user", "content": "I also take ibuprofen occasionally."},
                {"role": "assistant", "content": t2["response_text"]},
                {"role": "user", "content": "Actually, I meant that I take cetirizine, not ibuprofen."},
                {"role": "assistant", "content": t3["response_text"]},
            ],
        )
        return {"t1": t1, "t2": t2, "t3": t3, "t4": t4}

    def test_ibuprofen_retracted_after_correction(self):
        results = self._run_four_turns(base_conv_id=2001)
        state_after_t3 = results["t3"]["state_summary"]
        meds = state_after_t3["medications"]
        retracted_meds = [m for m in meds if "[RETRACTED]" in m]
        assert len(retracted_meds) >= 1, (
            f"Expected ibuprofen to be retracted after correction. "
            f"Medications list: {meds}"
        )
        ibu_retracted = any("ibuprofen" in m.lower() for m in retracted_meds)
        assert ibu_retracted, (
            f"Ibuprofen specifically should be retracted. Retracted meds: {retracted_meds}"
        )

    def test_cetirizine_active_after_correction(self):
        results = self._run_four_turns(base_conv_id=2002)
        state_after_t3 = results["t3"]["state_summary"]
        meds = state_after_t3["medications"]
        active_meds = [m for m in meds if not m.startswith("[RETRACTED]")]
        cetirizine_active = any("cetirizine" in m.lower() for m in active_meds)
        assert cetirizine_active, (
            f"Cetirizine should be active after correction. Active meds: {active_meds}"
        )

    def test_paracetamol_retained_after_correction(self):
        results = self._run_four_turns(base_conv_id=2003)
        state_after_t3 = results["t3"]["state_summary"]
        meds = state_after_t3["medications"]
        active_meds = [m for m in meds if not m.startswith("[RETRACTED]")]
        para_active = any("paracetamol" in m.lower() for m in active_meds)
        assert para_active, (
            f"Paracetamol should still be active (unaffected by correction). "
            f"Active meds: {active_meds}"
        )

    def test_summary_response_distinguishes_retracted(self):
        results = self._run_four_turns(base_conv_id=2004)
        summary_response = results["t4"]["response_text"].lower()
        # Summary response must mention cetirizine as active and ibuprofen as superseded/retracted
        assert "cetirizine" in summary_response, (
            f"Summary response should mention cetirizine. Response: {results['t4']['response_text']}"
        )
        retraction_indicated = (
            "retracted" in summary_response
            or "superseded" in summary_response
            or "corrected" in summary_response
        )
        assert retraction_indicated, (
            f"Summary response should indicate ibuprofen was retracted/superseded. "
            f"Response: {results['t4']['response_text']}"
        )


# ===========================================================================
# Unit tests for detect_medication_correction()
# ===========================================================================

class TestDetectMedicationCorrection:
    """Unit tests for the correction-detection helper function."""

    @pytest.fixture(scope="class")
    def norm(self):
        from dataset_loader import DatasetLoader
        from medication_normalizer import MedicationNormalizer
        return MedicationNormalizer(DatasetLoader())

    def test_detects_actually_meant_not(self, norm):
        current = ["ibuprofen"]
        retracted, added = detect_medication_correction(
            "Actually, I meant cetirizine, not ibuprofen.",
            current, norm
        )
        assert any("ibuprofen" in r.lower() for r in retracted), (
            f"Expected ibuprofen retracted, got: {retracted}"
        )

    def test_detects_i_take_x_not_y(self, norm):
        current = ["ibuprofen"]
        retracted, added = detect_medication_correction(
            "I take cetirizine, not ibuprofen.",
            current, norm
        )
        assert any("ibuprofen" in r.lower() for r in retracted), (
            f"Expected ibuprofen retracted, got: {retracted}"
        )

    def test_no_correction_without_trigger(self, norm):
        current = ["paracetamol"]
        retracted, added = detect_medication_correction(
            "I also take ibuprofen occasionally.",
            current, norm
        )
        # "also take" is not an explicit correction — should NOT retract paracetamol
        assert len(retracted) == 0, (
            f"Should not retract without correction trigger. Got: {retracted}"
        )

    def test_no_correction_on_new_medication_only(self, norm):
        current = []
        retracted, added = detect_medication_correction(
            "I take ibuprofen.",
            current, norm
        )
        assert retracted == [], (
            f"No retraction expected for new med with no prior meds. Got: {retracted}"
        )

    def test_extract_cetirizine_detected(self):
        """cetirizine must be extractable from free text."""
        mentions = extract_medication_mentions("I take cetirizine for allergies.")
        assert any("cetirizine" in m.lower() for m in mentions), (
            f"cetirizine not detected. Got: {mentions}"
        )
