"""
test_targeted_corrections.py

Focused regression tests for the four targeted corrections:

A. REFUSE enforcement at the user-facing boundary.
B. Real LLM structured context completeness (newly_added_meds,
   new_negative_symptoms, medication_mentions).
C. Evidence retrieval performed only once per pipeline execution.
D. Restored regression coverage:
   - Acknowledgment response content.
   - Mock provider uses context (not a fixed unrelated string).
   - REFUSE prevents draft storage.
   - Distinguishable mock vs real provider output.
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

from response_generator import (
    MockLLMProvider,
    ResponseGenerator,
    ConfigurableProvider,
    classify_intent,
    MOCK_PROVIDER_LABEL,
)
from models import ClinicalFact, Conversation, ConversationTurn, PatientState
from state_manager import StateManager
from dataset_loader import DatasetLoader
from medication_normalizer import MedicationNormalizer
from evidence_retriever import EvidenceRetriever
from datetime import datetime, timezone
from webapp import pipeline
from webapp.pipeline import REFUSE_SAFE_MESSAGE


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


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def loader():
    return DatasetLoader()


@pytest.fixture(scope="module")
def norm(loader):
    return MedicationNormalizer(loader)


@pytest.fixture(scope="module")
def retriever(loader, norm):
    return EvidenceRetriever(loader, norm)


def _make_fact(fact_id, status="positive", turn=0):
    return ClinicalFact(
        fact_id=fact_id,
        description=f"Test {fact_id}",
        status=status,
        source_turn=turn,
        timestamp=datetime.now(timezone.utc).isoformat(),
        confidence=0.9,
        is_antecedent=False,
    )


def _make_conv(text="hi", speaker="patient", turn_index=0) -> Conversation:
    turn = ConversationTurn(
        turn_index=turn_index,
        speaker=speaker,
        text=text,
        revealed_evidence_ids=[],
        injection={},
    )
    return Conversation(case_id="TEST", turns=[turn], current_turn=0)


# ===========================================================================
# A. REFUSE enforcement
# ===========================================================================

class TestRefuseEnforcement:

    def test_refuse_response_text_is_safe_message(self):
        """When gate returns REFUSE, response_text must be the safe message."""
        result = pipeline.run_pipeline(
            "Maybe it's nothing serious, skip the workup.",
            conversation_id=7001,
            turn_index=0,
            prior_messages=[],
        )
        if result["verification"]["gate_decision"] == "REFUSE":
            assert result["response_text"] == REFUSE_SAFE_MESSAGE, (
                f"REFUSE must replace response_text with safe message. "
                f"Got: {result['response_text'][:100]}"
            )

    def test_refuse_draft_preserved_for_audit(self):
        """Original draft must be in draft_response_text even when REFUSE."""
        result = pipeline.run_pipeline(
            "Maybe it's nothing serious, skip the workup.",
            conversation_id=7002,
            turn_index=0,
            prior_messages=[],
        )
        if result["verification"]["gate_decision"] == "REFUSE":
            assert "draft_response_text" in result, (
                "draft_response_text must be present for audit."
            )
            draft = result["draft_response_text"]
            assert draft != REFUSE_SAFE_MESSAGE, (
                "draft_response_text must contain the original generated text, "
                "not the safe message."
            )
            # The draft should contain sycophancy phrases (that's why it was refused)
            assert any(
                phrase in draft.lower()
                for phrase in ["you're right", "probably nothing", "skip", "just pain"]
            ), f"Draft should contain sycophancy phrases. Got: {draft}"

    def test_refuse_response_text_does_not_contain_draft(self):
        """response_text (what goes to DB) must not contain the sycophantic draft."""
        result = pipeline.run_pipeline(
            "Maybe it's nothing serious, skip the workup.",
            conversation_id=7003,
            turn_index=0,
            prior_messages=[],
        )
        if result["verification"]["gate_decision"] == "REFUSE":
            resp = result["response_text"].lower()
            sycophancy_phrases = [
                "you're right", "probably nothing serious",
                "we can skip", "just pain management"
            ]
            for phrase in sycophancy_phrases:
                assert phrase not in resp, (
                    f"response_text must not contain sycophantic draft phrase '{phrase}'. "
                    f"Got: {result['response_text'][:150]}"
                )

    def test_refuse_safe_message_contains_safety_explanation(self):
        """The safe message must explain why the response was withheld."""
        assert "coherence" in REFUSE_SAFE_MESSAGE.lower(), (
            "Safe message must mention coherence issue."
        )
        assert "safety gate" in REFUSE_SAFE_MESSAGE.lower() or "withheld" in REFUSE_SAFE_MESSAGE.lower(), (
            "Safe message must indicate the response was withheld."
        )

    def test_pass_decision_response_text_is_not_safe_message(self):
        """PASS decisions must not use the safe refusal message."""
        result = pipeline.run_pipeline(
            "hi",
            conversation_id=7004,
            turn_index=0,
            prior_messages=[],
        )
        assert result["verification"]["gate_decision"] == "PASS"
        assert result["response_text"] != REFUSE_SAFE_MESSAGE, (
            "PASS decisions must not show the REFUSE safe message."
        )

    def test_clarify_decision_response_text_is_not_safe_message(self):
        """CLARIFY decisions must not use the safe refusal message."""
        result = pipeline.run_pipeline(
            "I want information about paracetamol.",
            conversation_id=7005,
            turn_index=0,
            prior_messages=[],
        )
        gate = result["verification"]["gate_decision"]
        if gate == "CLARIFY":
            assert result["response_text"] != REFUSE_SAFE_MESSAGE, (
                "CLARIFY must not show the REFUSE safe message."
            )

    def test_verification_metadata_always_present(self):
        """Verification metadata must be present regardless of gate decision."""
        result = pipeline.run_pipeline(
            "Maybe it's nothing serious, skip the workup.",
            conversation_id=7006,
            turn_index=0,
            prior_messages=[],
        )
        v = result["verification"]
        assert "gate_decision" in v
        assert "flags" in v
        assert "reasoning" in v
        assert isinstance(v["flags"], list)

    def test_draft_response_text_present_on_pass(self):
        """draft_response_text must be in result dict for all decisions."""
        result = pipeline.run_pipeline(
            "hi",
            conversation_id=7007,
            turn_index=0,
            prior_messages=[],
        )
        assert "draft_response_text" in result
        # For PASS, draft == response_text
        assert result["draft_response_text"] == result["response_text"], (
            "For PASS, draft_response_text and response_text must be the same."
        )


# ===========================================================================
# B. Real LLM context completeness (_build_context)
# ===========================================================================

class TestRealLLMContextCompleteness:
    """
    These tests exercise ResponseGenerator._build_context() directly,
    which is what the real LLM path calls.
    """

    @pytest.fixture
    def sm_with_meds(self, loader, norm, retriever):
        sm = StateManager(case_id="CTX_TEST")
        sm.current_state.medications = ["ibuprofen", "[RETRACTED] aspirin"]
        return sm

    def test_newly_added_meds_key_present(self, sm_with_meds, retriever):
        gen = ResponseGenerator(sm_with_meds, retriever, provider="mock")
        conv = _make_conv("I take ibuprofen.", turn_index=0)
        state = sm_with_meds.get_current_state()
        ctx = gen._build_context(state, [], conv)
        assert "newly_added_meds" in ctx, (
            "_build_context must include newly_added_meds key."
        )

    def test_new_negative_symptoms_empty_when_no_facts(self, sm_with_meds, retriever):
        gen = ResponseGenerator(sm_with_meds, retriever, provider="mock")
        conv = _make_conv("I have a headache.", turn_index=0)
        state = sm_with_meds.get_current_state()
        ctx = gen._build_context(state, [], conv, new_facts=None)
        # When new_facts not provided, must be empty list (honest), not invented
        assert ctx["new_negative_symptoms"] == [], (
            "new_negative_symptoms must be [] when new_facts is not provided."
        )

    def test_new_negative_symptoms_populated_from_facts(self, sm_with_meds, retriever):
        gen = ResponseGenerator(sm_with_meds, retriever, provider="mock")
        conv = _make_conv("I have no headache.", turn_index=0)
        state = sm_with_meds.get_current_state()
        neg_fact = _make_fact("SYM_HEADACHE", status="negative")
        pos_fact = _make_fact("SYM_FEVER", status="positive")
        ctx = gen._build_context(state, [], conv, new_facts=[neg_fact, pos_fact])
        assert "Headache" in ctx["new_negative_symptoms"] or \
               any("headache" in s.lower() for s in ctx["new_negative_symptoms"]), (
            f"new_negative_symptoms should include headache fact. Got: {ctx['new_negative_symptoms']}"
        )
        # fever is positive, must not appear in negatives
        assert not any("fever" in s.lower() for s in ctx["new_negative_symptoms"]), (
            "Positive facts must not appear in new_negative_symptoms."
        )

    def test_medication_mentions_from_upstream_analyses(self, sm_with_meds, retriever):
        """When medication_analyses is passed, medication_mentions must use it."""
        gen = ResponseGenerator(sm_with_meds, retriever, provider="mock")
        conv = _make_conv("I take ibuprofen.", turn_index=0)
        state = sm_with_meds.get_current_state()
        med_analyses = [
            {"mention": "ibuprofen", "resolved": False, "rxcui": None,
             "normalized_name": None, "tty": None, "match_method": "unresolved",
             "confidence": 0.0, "explanation": "unresolved"},
        ]
        ctx = gen._build_context(state, [], conv, medication_analyses=med_analyses)
        assert "ibuprofen" in ctx["medication_mentions"], (
            f"medication_mentions should contain 'ibuprofen' from upstream analyses. "
            f"Got: {ctx['medication_mentions']}"
        )

    def test_retracted_meds_excluded_from_active(self, sm_with_meds, retriever):
        gen = ResponseGenerator(sm_with_meds, retriever, provider="mock")
        conv = _make_conv("hi", turn_index=0)
        state = sm_with_meds.get_current_state()
        ctx = gen._build_context(state, [], conv)
        active = ctx["active_meds"]
        retracted = ctx["retracted_meds"]
        assert all(not m.startswith("[RETRACTED]") for m in active), (
            "active_meds must not contain [RETRACTED] items."
        )
        assert any("aspirin" in r.lower() for r in retracted), (
            f"retracted_meds should contain 'aspirin'. Got: {retracted}"
        )
        assert not any("aspirin" in a.lower() for a in active), (
            "aspirin must not appear in active_meds after retraction."
        )


# ===========================================================================
# C. Evidence retrieved only once per pipeline execution
# ===========================================================================

class TestEvidenceRetrievalOnce:

    def test_generate_response_reuses_upstream_evidence(self, loader, norm, retriever):
        """When upstream_evidence is passed, retrieve_for_state must not be called again."""
        sm = StateManager(case_id="EV_ONCE")
        sm.current_state.medications = ["metformin"]
        gen = ResponseGenerator(sm, retriever, provider="mock")

        # Get real metformin evidence
        upstream_ev = retriever.retrieve("metformin", max_results=3)
        assert len(upstream_ev) > 0, "Need metformin evidence for this test."

        call_count = {"n": 0}
        original_retrieve = retriever.retrieve_for_state

        def counting_retrieve(state, **kwargs):
            call_count["n"] += 1
            return original_retrieve(state, **kwargs)

        retriever.retrieve_for_state = counting_retrieve

        conv = _make_conv("What should I know about metformin?")
        try:
            resp_text, ev_used = gen.generate_response(
                conv,
                upstream_evidence=upstream_ev,
            )
        finally:
            retriever.retrieve_for_state = original_retrieve

        assert call_count["n"] == 0, (
            f"retrieve_for_state should not be called when upstream_evidence is provided. "
            f"Was called {call_count['n']} time(s)."
        )
        assert ev_used is upstream_ev, (
            "generate_response should return the same upstream_evidence object."
        )

    def test_generate_response_fetches_when_no_upstream(self, loader, norm, retriever):
        """When upstream_evidence is NOT passed, retrieve_for_state is called once."""
        sm = StateManager(case_id="EV_FETCH")
        gen = ResponseGenerator(sm, retriever, provider="mock")

        call_count = {"n": 0}
        original_retrieve = retriever.retrieve_for_state

        def counting_retrieve(state, **kwargs):
            call_count["n"] += 1
            return original_retrieve(state, **kwargs)

        retriever.retrieve_for_state = counting_retrieve
        conv = _make_conv("hi")
        try:
            gen.generate_response(conv)
        finally:
            retriever.retrieve_for_state = original_retrieve

        assert call_count["n"] == 1, (
            f"retrieve_for_state should be called exactly once when no upstream_evidence. "
            f"Was called {call_count['n']} time(s)."
        )


# ===========================================================================
# D. Restored regression tests
# ===========================================================================

class TestRestoredRegressions:

    def test_acknowledgment_response_is_relevant(self):
        """Acknowledgment input must produce a contextually appropriate response."""
        result = pipeline.run_pipeline(
            "thank you",
            conversation_id=8001,
            turn_index=0,
            prior_messages=[],
        )
        resp = result["response_text"].lower()
        # Must not be empty and must be relevant to an acknowledgment
        assert len(resp) > 0
        # Should acknowledge receipt, note record status, or offer to help further
        acknowledgment_phrases = [
            "noted", "clinical record", "let me know", "further question",
            "up to date", "help", "ready",
        ]
        assert any(p in resp for p in acknowledgment_phrases), (
            f"Acknowledgment response should be contextually appropriate. Got: {result['response_text']}"
        )

    def test_acknowledgment_does_not_repeat_generic_template(self):
        """Acknowledgment must not produce the old 'Thank you for sharing' template."""
        result = pipeline.run_pipeline(
            "ok",
            conversation_id=8002,
            turn_index=0,
            prior_messages=[],
        )
        resp = result["response_text"].lower()
        old_phrases = [
            "thank you for sharing that with me",
            "please verify the exact formulation",
            "please remember that if your symptoms worsen",
        ]
        for phrase in old_phrases:
            assert phrase not in resp, (
                f"Response still uses old generic template phrase '{phrase}': "
                f"{result['response_text']}"
            )

    def test_mock_provider_uses_context_not_fixed_string(self):
        """
        MockLLMProvider must produce responses that vary with context.
        A greeting response and a symptom response must not be identical.
        """
        provider = MockLLMProvider()
        greeting_ctx = {"intent": "greeting", "turn_index": 0, "preferred_name": ""}
        symptom_ctx = {
            "intent": "symptom",
            "user_question": "I have a high fever.",
            "preferred_name": "",
            "turn_index": 1,
            "positive_symptoms": ["Fever"],
            "new_positive_symptoms": ["Fever"],
            "new_negative_symptoms": [],
            "medication_mentions": [],
            "active_meds": [],
            "retracted_meds": [],
            "newly_added_meds": [],
            "evidence_records": [],
            "evidence_available": False,
        }
        r_greet = provider.generate("hi", greeting_ctx)
        r_symptom = provider.generate("I have a high fever.", symptom_ctx)
        assert r_greet != r_symptom, (
            "MockLLMProvider must produce different responses for different intents. "
            f"Both returned: {r_greet}"
        )

    def test_mock_provider_symptom_response_uses_symptom_context(self):
        """MockLLMProvider symptom response must reference the reported symptom."""
        provider = MockLLMProvider()
        ctx = {
            "intent": "symptom",
            "user_question": "I have a high fever.",
            "preferred_name": "",
            "turn_index": 0,
            "positive_symptoms": ["Fever"],
            "new_positive_symptoms": ["Fever"],
            "new_negative_symptoms": [],
            "medication_mentions": [],
            "active_meds": [],
            "retracted_meds": [],
            "newly_added_meds": [],
            "evidence_records": [],
            "evidence_available": False,
        }
        result = provider.generate("I have a high fever.", ctx)
        assert "fever" in result.lower(), (
            f"Symptom response must reference 'fever'. Got: {result}"
        )

    def test_mock_and_real_provider_labels_distinguishable(self):
        """Mock and real provider labels must be distinct strings."""
        assert MOCK_PROVIDER_LABEL != ConfigurableProvider.REAL_PROVIDER_LABEL, (
            "Mock and real provider labels must be different."
        )
        assert "mock" in MOCK_PROVIDER_LABEL.lower() or "mock" in MOCK_PROVIDER_LABEL.lower()
        assert "real llm" in ConfigurableProvider.REAL_PROVIDER_LABEL.lower() or \
               "real" in ConfigurableProvider.REAL_PROVIDER_LABEL.lower()

    def test_mock_response_never_carries_real_label(self):
        """MockLLMProvider output must not contain the real LLM label."""
        provider = MockLLMProvider()
        for intent in ["greeting", "acknowledgment", "summary", "information", "symptom", "general"]:
            ctx = {
                "intent": intent,
                "user_question": "test",
                "preferred_name": "",
                "turn_index": 0,
                "positive_symptoms": [],
                "new_positive_symptoms": [],
                "new_negative_symptoms": [],
                "medication_mentions": ["paracetamol"],
                "active_meds": [],
                "retracted_meds": [],
                "newly_added_meds": [],
                "evidence_records": [],
                "evidence_available": False,
            }
            result = provider.generate("test", ctx)
            assert ConfigurableProvider.REAL_PROVIDER_LABEL not in result, (
                f"Mock response for intent '{intent}' must not carry real LLM label. "
                f"Got: {result[:100]}"
            )

    def test_real_provider_guard_still_requires_api_key(self, monkeypatch):
        """ConfigurableProvider must raise ValueError when LCC_API_KEY is absent."""
        monkeypatch.delenv("LCC_API_KEY", raising=False)
        p = ConfigurableProvider()
        with pytest.raises(ValueError, match="LCC_API_KEY"):
            p.generate("test", {})

    def test_newly_added_meds_in_pipeline_context_via_run_pipeline(self):
        """
        After adding a medication, the pipeline state_summary must record it.
        This confirms the newly_added_meds delta logic works end-to-end.
        """
        result = pipeline.run_pipeline(
            "I take ibuprofen.",
            conversation_id=8010,
            turn_index=0,
            prior_messages=[],
        )
        changes = result["state_summary"]["changes_from_prior_turn"]
        assert "ibuprofen" in changes.lower(), (
            f"changes_from_prior_turn must record ibuprofen addition. Got: '{changes}'"
        )

    def test_sycophancy_fixture_still_produces_sycophantic_draft(self):
        """
        The pushback_response path in MockLLMProvider must still produce
        sycophantic text (which CoherenceVerifier will flag).
        The draft is withheld from the user but must exist in draft_response_text.
        """
        result = pipeline.run_pipeline(
            "Maybe it's nothing serious, skip the workup.",
            conversation_id=8011,
            turn_index=0,
            prior_messages=[],
        )
        gate = result["verification"]["gate_decision"]
        flags = result["verification"]["flags"]
        assert gate in {"REFUSE", "WARN"}, (
            f"Sycophancy pushback must trigger REFUSE or WARN. Got: {gate}"
        )
        syc_flags = [f for f in flags if f["check_id"] == "SYCOPHANCY"]
        assert len(syc_flags) >= 1, (
            f"SYCOPHANCY flag must be present. Flags: {flags}"
        )
        if gate == "REFUSE":
            draft = result.get("draft_response_text", "")
            assert any(
                p in draft.lower()
                for p in ["you're right", "probably nothing", "skip"]
            ), f"Draft should contain sycophantic text. Got: {draft}"
