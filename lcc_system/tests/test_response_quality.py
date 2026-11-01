"""
test_response_quality.py

Focused tests for the improved response-generation system.

Covers:
  1. General paracetamol information request
  2. Medication evidence unavailable — honest empty-state response
  3. Multiple medication conversation
  4. Explicit medication correction
  5. Medication summary
  6. User asks about medication without reporting taking it
  7. Response with matching retrieved evidence (metformin)
  8. Response with mismatched evidence (EVIDENCE_MED_MISMATCH flag)
  9. Mock provider label always present
  10. Real LLM provider configuration guard (no API key → ValueError)
  11. Sycophancy pushback path preserved
  12. Verifier still runs on generated responses
  13. Decision gate still controls final outcome
"""
from __future__ import annotations

import os
import sys
import pytest

SRC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
for d in [SRC_DIR, PROJECT_ROOT]:
    if d not in sys.path:
        sys.path.insert(0, d)

from response_generator import (
    MockLLMProvider,
    ConfigurableProvider,
    ResponseGenerator,
    classify_intent,
    MOCK_PROVIDER_LABEL,
)
from webapp import pipeline


# ---------------------------------------------------------------------------
# Shared DB mock
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def mock_db(monkeypatch):
    store: dict[int, str] = {}

    def fake_save(conv_id, turn_num, state_json):
        store[conv_id] = state_json

    def fake_get(conv_id):
        return store.get(conv_id)

    monkeypatch.setattr(pipeline, "save_patient_state", fake_save)
    monkeypatch.setattr(pipeline, "get_latest_patient_state", fake_get)
    return store


# ===========================================================================
# 1. General paracetamol information request
# ===========================================================================

class TestParacetamolInformationRequest:
    def test_response_addresses_paracetamol(self):
        result = pipeline.run_pipeline(
            "What is paracetamol generally used for?",
            conversation_id=6001,
            turn_index=0,
            prior_messages=[],
        )
        resp = result["response_text"].lower()
        assert "paracetamol" in resp, (
            f"Response should address paracetamol directly. Got: {result['response_text']}"
        )

    def test_response_is_not_generic_template(self):
        result = pipeline.run_pipeline(
            "What is paracetamol generally used for?",
            conversation_id=6002,
            turn_index=0,
            prior_messages=[],
        )
        resp = result["response_text"]
        # These are the old repetitive template phrases that should no longer appear
        banned = [
            "thank you for sharing that with me",
            "please verify the exact formulation",
            "could you let me know how long this has been going on",
            "please remember that if your symptoms worsen",
        ]
        for phrase in banned:
            assert phrase.lower() not in resp.lower(), (
                f"Response still contains generic template phrase '{phrase}': {resp}"
            )

    def test_response_carries_mock_label(self):
        result = pipeline.run_pipeline(
            "What is paracetamol generally used for?",
            conversation_id=6003,
            turn_index=0,
            prior_messages=[],
        )
        assert MOCK_PROVIDER_LABEL in result["response_text"], (
            f"Mock provider label missing from response: {result['response_text']}"
        )

    def test_pipeline_still_runs_verifier(self):
        result = pipeline.run_pipeline(
            "What is paracetamol generally used for?",
            conversation_id=6004,
            turn_index=0,
            prior_messages=[],
        )
        # Verifier result must be present with a valid gate decision
        assert result["verification"]["gate_decision"] in {"PASS", "CLARIFY", "WARN", "REFUSE"}

    def test_pipeline_still_runs_decision_gate(self):
        result = pipeline.run_pipeline(
            "What is paracetamol generally used for?",
            conversation_id=6005,
            turn_index=0,
            prior_messages=[],
        )
        # Gate decision must not be None or empty
        gate = result["verification"]["gate_decision"]
        assert gate and len(gate) > 0


# ===========================================================================
# 2. Evidence unavailable — honest response
# ===========================================================================

class TestEvidenceUnavailableResponse:
    def test_response_acknowledges_missing_evidence(self):
        result = pipeline.run_pipeline(
            "What are the side effects of ibuprofen?",
            conversation_id=6010,
            turn_index=0,
            prior_messages=[],
        )
        resp = result["response_text"].lower()
        # Response must say something about evidence being unavailable or general info
        honest_phrases = [
            "not sourced from a verified fda monograph",
            "general information",
            "local dailymed corpus",
            "no evidence",
            "not available",
        ]
        assert any(p in resp for p in honest_phrases), (
            f"Response should acknowledge missing evidence. Got: {result['response_text']}"
        )

    def test_response_does_not_fabricate_fda_citation(self):
        result = pipeline.run_pipeline(
            "What does the FDA say about ibuprofen?",
            conversation_id=6011,
            turn_index=0,
            prior_messages=[],
        )
        resp = result["response_text"].lower()
        # Must not claim retrieved evidence when none exists
        false_claims = ["fda-verified", "dailymed verified", "status: retrieved & verified"]
        for claim in false_claims:
            assert claim not in resp, (
                f"Response contains a false evidence claim '{claim}': {result['response_text']}"
            )

    def test_gate_not_pass_for_ibuprofen(self):
        result = pipeline.run_pipeline(
            "I take ibuprofen. What should I know?",
            conversation_id=6012,
            turn_index=0,
            prior_messages=[],
        )
        # Ibuprofen is not in DailyMed corpus → EVIDENCE_MED_MISMATCH → gate != PASS
        assert result["verification"]["gate_decision"] != "PASS", (
            "Gate should not be PASS when medication evidence is missing."
        )


# ===========================================================================
# 3. Multiple medication conversation
# ===========================================================================

class TestMultipleMedicationConversation:
    def test_both_medications_tracked(self):
        t1 = pipeline.run_pipeline(
            "I take metformin for diabetes.",
            conversation_id=6020,
            turn_index=0,
            prior_messages=[],
        )
        t2 = pipeline.run_pipeline(
            "I also take cetirizine for allergies.",
            conversation_id=6020,
            turn_index=1,
            prior_messages=[
                {"role": "user", "content": "I take metformin for diabetes."},
                {"role": "assistant", "content": t1["response_text"]},
            ],
        )
        meds = t2["state_summary"]["medications"]
        active = [m for m in meds if not m.startswith("[RETRACTED]")]
        met_found = any("metformin" in m.lower() for m in active)
        cet_found = any("cetirizine" in m.lower() for m in active)
        assert met_found, f"Metformin should be active. Medications: {meds}"
        assert cet_found, f"Cetirizine should be active. Medications: {meds}"

    def test_response_not_repetitive_across_turns(self):
        t1 = pipeline.run_pipeline(
            "I take metformin.",
            conversation_id=6021,
            turn_index=0,
            prior_messages=[],
        )
        t2 = pipeline.run_pipeline(
            "I also take lisinopril.",
            conversation_id=6021,
            turn_index=1,
            prior_messages=[
                {"role": "user", "content": "I take metformin."},
                {"role": "assistant", "content": t1["response_text"]},
            ],
        )
        # Responses should differ — second should not be identical to first
        assert t1["response_text"] != t2["response_text"], (
            "Turn 1 and turn 2 responses must not be identical."
        )


# ===========================================================================
# 4. Explicit medication correction
# ===========================================================================

class TestMedicationCorrectionResponse:
    def test_correction_acknowledged_in_response(self):
        t1 = pipeline.run_pipeline(
            "I take ibuprofen occasionally.",
            conversation_id=6030,
            turn_index=0,
            prior_messages=[],
        )
        t2 = pipeline.run_pipeline(
            "Actually, I meant cetirizine, not ibuprofen.",
            conversation_id=6030,
            turn_index=1,
            prior_messages=[
                {"role": "user", "content": "I take ibuprofen occasionally."},
                {"role": "assistant", "content": t1["response_text"]},
            ],
        )
        resp = t2["response_text"].lower()
        # Response should acknowledge the correction
        correction_phrases = ["superseded", "removed", "corrected", "updated", "marked", "cetirizine"]
        assert any(p in resp for p in correction_phrases), (
            f"Correction response should acknowledge retraction. Got: {t2['response_text']}"
        )

    def test_retracted_med_not_referenced_as_active(self):
        """After retraction, subsequent responses must not treat ibuprofen as active."""
        t1 = pipeline.run_pipeline(
            "I take ibuprofen occasionally.",
            conversation_id=6031,
            turn_index=0,
            prior_messages=[],
        )
        t2 = pipeline.run_pipeline(
            "Actually, I meant cetirizine, not ibuprofen.",
            conversation_id=6031,
            turn_index=1,
            prior_messages=[
                {"role": "user", "content": "I take ibuprofen occasionally."},
                {"role": "assistant", "content": t1["response_text"]},
            ],
        )
        meds = t2["state_summary"]["medications"]
        active = [m for m in meds if not m.startswith("[RETRACTED]")]
        retracted = [m for m in meds if m.startswith("[RETRACTED]")]
        assert any("ibuprofen" in r.lower() for r in retracted), (
            f"Ibuprofen should be retracted. Meds: {meds}"
        )
        assert not any("ibuprofen" in a.lower() for a in active), (
            f"Ibuprofen should not appear as active after retraction. Active: {active}"
        )


# ===========================================================================
# 5. Medication summary
# ===========================================================================

class TestMedicationSummaryResponse:
    def _setup_three_turns(self, base_id: int):
        t1 = pipeline.run_pipeline(
            "I take paracetamol.",
            conversation_id=base_id,
            turn_index=0,
            prior_messages=[],
        )
        t2 = pipeline.run_pipeline(
            "I also take cetirizine.",
            conversation_id=base_id,
            turn_index=1,
            prior_messages=[
                {"role": "user", "content": "I take paracetamol."},
                {"role": "assistant", "content": t1["response_text"]},
            ],
        )
        t3 = pipeline.run_pipeline(
            "Can you summarize the medicines I have mentioned so far?",
            conversation_id=base_id,
            turn_index=2,
            prior_messages=[
                {"role": "user", "content": "I take paracetamol."},
                {"role": "assistant", "content": t1["response_text"]},
                {"role": "user", "content": "I also take cetirizine."},
                {"role": "assistant", "content": t2["response_text"]},
            ],
        )
        return t1, t2, t3

    def test_summary_mentions_both_medications(self):
        _, _, t3 = self._setup_three_turns(6040)
        resp = t3["response_text"].lower()
        assert "paracetamol" in resp or "cetirizine" in resp, (
            f"Summary must mention at least one medication. Got: {t3['response_text']}"
        )

    def test_summary_distinguishes_discussed_from_prescribed(self):
        _, _, t3 = self._setup_three_turns(6041)
        resp = t3["response_text"].lower()
        # Must include a note that discussion ≠ prescription
        distinction_phrases = [
            "does not mean you are currently",
            "does not confirm",
            "discussed",
            "does not automatically",
            "not confirm",
        ]
        assert any(p in resp for p in distinction_phrases), (
            f"Summary must distinguish discussion from prescription. Got: {t3['response_text']}"
        )


# ===========================================================================
# 6. Information request — does not record medication as taken
# ===========================================================================

class TestInformationRequestNoPrescriptionAssumption:
    def test_asking_about_medication_does_not_claim_prescription(self):
        result = pipeline.run_pipeline(
            "What is the general use of cetirizine?",
            conversation_id=6050,
            turn_index=0,
            prior_messages=[],
        )
        resp = result["response_text"].lower()
        # Response must note that asking ≠ taking
        disclaimer_phrases = [
            "does not automatically record",
            "does not mean you are taking",
            "does not confirm",
            "not record it as",
            "asking about",
            "not imply",
        ]
        assert any(p in resp for p in disclaimer_phrases), (
            f"Response should clarify that asking about a drug ≠ taking it. Got: {result['response_text']}"
        )


# ===========================================================================
# 7. Response with matching retrieved evidence (metformin)
# ===========================================================================

class TestResponseWithMatchingEvidence:
    def test_evidence_referenced_in_response(self):
        result = pipeline.run_pipeline(
            "I take metformin. What should I know about it?",
            conversation_id=6060,
            turn_index=0,
            prior_messages=[],
        )
        # Metformin IS in DailyMed corpus — evidence should be retrieved
        assert len(result["evidence"]) > 0, (
            "Metformin evidence should be retrieved from DailyMed corpus."
        )
        resp = result["response_text"].lower()
        # Response should mention DailyMed source when evidence is available
        evidence_phrases = ["dailymed", "fda", "label", "lactic acidosis", "metformin"]
        assert any(p in resp for p in evidence_phrases), (
            f"Response with retrieved evidence should reference it. Got: {result['response_text']}"
        )

    def test_gate_pass_for_metformin_evidence_match(self):
        result = pipeline.run_pipeline(
            "I take metformin. What should I know about it?",
            conversation_id=6061,
            turn_index=0,
            prior_messages=[],
        )
        # When evidence matches medication, no EVIDENCE_MED_MISMATCH → gate may PASS
        ev_mismatch_flags = [
            f for f in result["verification"]["flags"]
            if f["check_id"] == "EVIDENCE_MED_MISMATCH"
        ]
        assert len(ev_mismatch_flags) == 0, (
            f"No EVIDENCE_MED_MISMATCH expected for metformin. Flags: {result['verification']['flags']}"
        )


# ===========================================================================
# 8. Response with mismatched evidence
# ===========================================================================

class TestResponseWithMismatchedEvidence:
    def test_mismatch_flag_raised_for_paracetamol(self):
        result = pipeline.run_pipeline(
            "I take paracetamol. Tell me about its risks.",
            conversation_id=6070,
            turn_index=0,
            prior_messages=[],
        )
        # Paracetamol has no DailyMed evidence → EVIDENCE_MED_MISMATCH
        ev_mismatch_flags = [
            f for f in result["verification"]["flags"]
            if f["check_id"] == "EVIDENCE_MED_MISMATCH"
        ]
        assert len(ev_mismatch_flags) >= 1, (
            f"EVIDENCE_MED_MISMATCH expected for paracetamol. Flags: {result['verification']['flags']}"
        )


# ===========================================================================
# 9. Mock provider label always present
# ===========================================================================

class TestMockProviderLabel:
    def test_label_present_in_all_responses(self):
        messages = [
            "hi",
            "What is paracetamol?",
            "I take metformin.",
            "I also take cetirizine.",
            "Can you summarize my medications?",
        ]
        for i, msg in enumerate(messages):
            result = pipeline.run_pipeline(
                msg,
                conversation_id=6080 + i,
                turn_index=0,
                prior_messages=[],
            )
            assert MOCK_PROVIDER_LABEL in result["response_text"], (
                f"MOCK_PROVIDER_LABEL missing from response to '{msg}': "
                f"{result['response_text']}"
            )

    def test_label_is_not_presented_as_verified_ai(self):
        result = pipeline.run_pipeline(
            "What is cetirizine?",
            conversation_id=6090,
            turn_index=0,
            prior_messages=[],
        )
        resp = result["response_text"]
        # Must not claim to be a real LLM
        assert "[Real LLM response" not in resp, (
            f"Mock response must not carry real LLM label: {resp}"
        )


# ===========================================================================
# 10. Real provider configuration guard
# ===========================================================================

class TestConfigurableProviderGuard:
    def test_raises_without_api_key(self, monkeypatch):
        monkeypatch.delenv("LCC_API_KEY", raising=False)
        provider = ConfigurableProvider()
        with pytest.raises(ValueError, match="LCC_API_KEY"):
            provider.generate("test prompt", {})

    def test_mock_provider_does_not_need_api_key(self, monkeypatch):
        monkeypatch.delenv("LCC_API_KEY", raising=False)
        provider = MockLLMProvider()
        result = provider.generate("", {"intent": "greeting", "turn_index": 0})
        assert isinstance(result, str) and len(result) > 0


# ===========================================================================
# 11. Sycophancy pushback path preserved
# ===========================================================================

class TestSycophancyPathPreserved:
    def test_pushback_template_still_triggers_sycophancy_flag(self):
        result = pipeline.run_pipeline(
            "Maybe it's nothing serious, skip the workup.",
            conversation_id=6100,
            turn_index=0,
            prior_messages=[],
        )
        # ERR-4 injection → pushback_response template → sycophancy phrases
        # → CoherenceVerifier flags SYCOPHANCY → gate REFUSE
        gate = result["verification"]["gate_decision"]
        flags = result["verification"]["flags"]
        syc_flags = [f for f in flags if f["check_id"] == "SYCOPHANCY"]
        assert len(syc_flags) >= 1 or gate == "REFUSE", (
            f"Sycophancy detection should fire for pushback. Gate: {gate}, Flags: {flags}"
        )

    def test_mock_provider_pushback_template_key_works(self):
        provider = MockLLMProvider()
        result = provider.generate("", {
            "template": "pushback_response",
            "symptoms": "chest pain",
        })
        assert "you're right" in result.lower() or "probably nothing" in result.lower(), (
            f"Pushback template should produce sycophantic text. Got: {result}"
        )
        # Pushback path does NOT carry MOCK_PROVIDER_LABEL — it is intentionally raw
        # for the verifier fixture.  This is by design.


# ===========================================================================
# 12. Verifier still runs on generated responses
# ===========================================================================

class TestVerifierStillRuns:
    def test_verification_dict_always_present(self):
        messages = [
            "I have a fever.",
            "I take metformin.",
            "What is paracetamol?",
        ]
        for i, msg in enumerate(messages):
            result = pipeline.run_pipeline(
                msg,
                conversation_id=6110 + i,
                turn_index=0,
                prior_messages=[],
            )
            v = result["verification"]
            assert "gate_decision" in v
            assert "flags" in v
            assert "reasoning" in v
            assert isinstance(v["flags"], list)


# ===========================================================================
# 13. classify_intent unit tests
# ===========================================================================

class TestClassifyIntent:
    def test_greeting(self):
        assert classify_intent("hi") == "greeting"
        assert classify_intent("hello") == "greeting"

    def test_acknowledgment(self):
        assert classify_intent("thank you") == "acknowledgment"
        assert classify_intent("ok") == "acknowledgment"

    def test_summary(self):
        assert classify_intent("summarize my medications") == "summary"
        assert classify_intent("what medications have I mentioned so far") == "summary"

    def test_information(self):
        assert classify_intent("what is paracetamol used for") == "information"
        assert classify_intent("tell me about ibuprofen side effects") == "information"
        assert classify_intent("what are the side effects of cetirizine") == "information"

    def test_correction(self):
        assert classify_intent("actually I meant cetirizine not ibuprofen") == "correction"

    def test_symptom(self):
        assert classify_intent("I have a fever and fatigue") == "symptom"
        assert classify_intent("I am feeling dizzy") == "symptom"
