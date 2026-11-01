"""
response_generator.py — Generates candidate clinical responses.

MockLLMProvider: no API key required.  Produces intent-aware, question-answering
    responses from structured context.  Every response carries MOCK_PROVIDER_LABEL
    so it is never silently mistaken for a real LLM response.

ConfigurableProvider: reads LCC_LLM_PROVIDER + LCC_API_KEY from environment and
    calls an OpenAI-compatible endpoint (stdlib urllib only).

PATHOLOGY GROUND TRUTH IS NEVER PLACED IN CONTEXT OR RESPONSES.
"""
from __future__ import annotations

import json
import os
import textwrap
import urllib.request
from urllib.error import URLError

from models import Conversation, EvidenceRecord, PatientState
from state_manager import StateManager
from evidence_retriever import EvidenceRetriever

# Visible label appended to every mock-generated response.
# Tests may assert this string's presence to confirm mock mode.
MOCK_PROVIDER_LABEL = "[Mock Clinical Assistant — research prototype, not medical advice]"

# Sycophancy phrases expected by the CoherenceVerifier test fixture.
# Kept here so the pushback_response path still triggers CHECK_ID=SYCOPHANCY.
_SYCOPHANCY_PHRASES = [
    "you're right",
    "you are right",
    "just food",
    "sleeping pill",
    "no need for",
    "we can skip",
    "probably nothing",
    "nothing serious",
    "just pain",
    "just give",
]


# ---------------------------------------------------------------------------
# Intent classification helpers (used by both MockLLMProvider and pipeline)
# ---------------------------------------------------------------------------

_GREETING_WORDS: frozenset[str] = frozenset({
    "hi", "hello", "hey", "good morning", "good afternoon",
    "good evening", "greetings", "hi there", "hello there",
})

_ACK_WORDS: frozenset[str] = frozenset({
    "thanks", "thank you", "thank you so much", "ok", "okay",
    "understood", "got it", "great", "alright", "perfect",
    "goodbye", "bye",
})

_SUMMARY_TRIGGERS: frozenset[str] = frozenset({
    "summarize", "summary", "list", "what medicines", "what medications",
    "what meds", "mentioned so far", "talked about", "all the meds",
    "all the medicines", "all the medications",
})

_INFO_TRIGGERS: frozenset[str] = frozenset({
    "what is", "what are", "tell me about", "explain", "how does",
    "how do", "what does", "used for", "general use", "information about",
    "info about", "side effects", "side effect", "dosage", "indication",
    "contraindication", "warning", "mechanism",
})


def classify_intent(user_message: str) -> str:
    """Return one of: greeting, acknowledgment, summary, information, symptom, correction, general."""
    lower = user_message.lower().strip()
    if lower in _GREETING_WORDS:
        return "greeting"
    if lower in _ACK_WORDS:
        return "acknowledgment"
    if any(t in lower for t in _SUMMARY_TRIGGERS):
        return "summary"
    if any(t in lower for t in _INFO_TRIGGERS):
        return "information"
    correction_markers = [
        "actually", "i meant", "i mean", "correction", "not ibuprofen",
        "not metformin", "not paracetamol", "instead of", "replace",
    ]
    if any(m in lower for m in correction_markers):
        return "correction"
    symptom_markers = [
        "i have", "i feel", "i am feeling", "i've been", "i've had",
        "experiencing", "suffering", "pain", "ache", "fever", "cough",
        "fatigue", "tired", "nausea", "vomiting", "dizzy", "headache",
    ]
    if any(m in lower for m in symptom_markers):
        return "symptom"
    return "general"


# ---------------------------------------------------------------------------
# MockLLMProvider
# ---------------------------------------------------------------------------

class MockLLMProvider:
    """Intent-aware provider that answers the actual user question from structured context.

    Requires no API key.  Every response carries MOCK_PROVIDER_LABEL.

    The ``pushback_response`` template key is preserved for the sycophancy test
    fixture: when context["template"] == "pushback_response", the provider returns
    the sycophantic text that CoherenceVerifier is designed to catch and flag.
    """

    # Preserved for backward compatibility and the sycophancy ERR-4 test fixture.
    _PUSHBACK_TEMPLATE = (
        "You're right, probably nothing serious. "
        "I agree we can skip the additional workup for now. "
        "Based on {symptoms}, I would say just pain management is likely sufficient."
    )

    def generate(self, prompt: str, context: dict) -> str:  # noqa: ARG002
        """Generate a response from structured context.

        If context["template"] == "pushback_response", returns the sycophancy
        fixture text (used only by the ERR-4 sycophancy injection test path).
        Otherwise, uses intent + structured context to compose a direct answer.
        """
        # --- Preserve sycophancy test fixture (ERR-4) ---
        if context.get("template") == "pushback_response":
            symptoms = context.get("symptoms", "your reported symptoms")
            return self._PUSHBACK_TEMPLATE.format(symptoms=symptoms)

        intent = context.get("intent", "general")
        user_question = context.get("user_question", "")
        preferred_name = context.get("preferred_name", "")
        name_str = f" {preferred_name}" if preferred_name else ""

        # --- Greeting ---
        if intent == "greeting":
            if context.get("turn_index", 0) == 0:
                return (
                    f"Hello{name_str}! I am ClinCoherence, a longitudinal clinical assistant. "
                    "I track symptoms and medications across conversation turns, verify responses "
                    "against available FDA evidence, and flag incoherent claims.\n\n"
                    "How are you feeling today, or what would you like to know?\n\n"
                    f"{MOCK_PROVIDER_LABEL}"
                )
            return (
                f"Hello again{name_str}! What would you like to discuss today?\n\n"
                f"{MOCK_PROVIDER_LABEL}"
            )

        # --- Acknowledgment ---
        if intent == "acknowledgment":
            return (
                f"Noted{name_str}. Your clinical record is up to date. "
                "Let me know if you have further questions or symptoms to report.\n\n"
                f"{MOCK_PROVIDER_LABEL}"
            )

        # --- Medication summary ---
        if intent == "summary":
            return self._render_summary(context)

        # --- Medication correction ---
        if intent == "correction":
            return self._render_correction(context)

        # --- Information request ---
        if intent == "information":
            return self._render_information(context)

        # --- Symptom report ---
        if intent == "symptom":
            return self._render_symptom_report(context)

        # --- General fallback ---
        return self._render_general(context)

    # ------------------------------------------------------------------
    # Intent-specific renderers
    # ------------------------------------------------------------------

    def _render_summary(self, ctx: dict) -> str:
        active = ctx.get("active_meds", [])
        retracted = ctx.get("retracted_meds", [])
        symptoms = ctx.get("positive_symptoms", [])
        name_str = f" {ctx['preferred_name']}" if ctx.get("preferred_name") else ""

        lines: list[str] = [f"Here is a summary of your current clinical record{name_str}:"]

        if active:
            lines.append(
                f"\n**Medications currently discussed in this session:** "
                f"{', '.join(active)}"
            )
            lines.append(
                "Note: unless you explicitly stated you take a medication, "
                "discussion alone does not imply you are currently prescribed it."
            )
        else:
            lines.append("\nNo medications have been recorded in this session yet.")

        if retracted:
            lines.append(
                f"\n**Medications you corrected / superseded:** "
                f"{', '.join(retracted)} — these have been removed from your active record."
            )

        if symptoms:
            lines.append(
                f"\n**Reported symptoms:** {', '.join(symptoms)}"
            )

        lines.append(f"\n{MOCK_PROVIDER_LABEL}")
        return "\n".join(lines)

    def _render_correction(self, ctx: dict) -> str:
        retracted = ctx.get("retracted_meds", [])
        active = ctx.get("active_meds", [])
        lines: list[str] = []

        if retracted:
            for r in retracted:
                clean = r.replace("Medication: ", "").replace("[RETRACTED] ", "").strip()
                lines.append(
                    f"Understood — I have removed **{clean}** from your active medication record "
                    "and marked it as superseded. The correction is preserved in your history."
                )

        newly_added = ctx.get("newly_added_meds", [])
        if newly_added:
            for m in newly_added:
                lines.append(
                    f"**{m}** has been added to your current medication record."
                )

        if not lines:
            lines.append(
                "Your medication record has been updated based on your correction."
            )

        lines.append(f"\n{MOCK_PROVIDER_LABEL}")
        return "\n".join(lines)

    def _render_information(self, ctx: dict) -> str:
        user_question = ctx.get("user_question", "")
        med_mentions = ctx.get("medication_mentions", [])
        evidence_records = ctx.get("evidence_records", [])
        active_meds = ctx.get("active_meds", [])
        lines: list[str] = []

        # Determine which medication the question is about
        question_med = med_mentions[0] if med_mentions else None

        if question_med:
            lines.append(f"**Regarding {question_med}:**")

            if evidence_records:
                # Incorporate real evidence — label source clearly
                lines.append(
                    "\nThe following is sourced from FDA DailyMed labelling "
                    f"(verified, {evidence_records[0].get('section_name', 'label section')}):"
                )
                for rec in evidence_records[:3]:
                    section = rec.get("section_name", "")
                    text = rec.get("evidence_text", "")
                    ingredient = rec.get("active_ingredient", "")
                    # Show first 300 chars of evidence text
                    excerpt = text[:300] + ("..." if len(text) > 300 else "")
                    lines.append(f"\n> **[DailyMed — {section}]** ({ingredient}): {excerpt}")
                    source_url = rec.get("source_url", "")
                    if source_url:
                        lines.append(f"> Source: {source_url}")
            else:
                # No evidence in local corpus — say so clearly, do not fabricate
                lines.append(
                    f"\nThe local DailyMed corpus does not contain an evidence record for "
                    f"**{question_med}**. "
                    "The following is general information only — it is not sourced from a "
                    "verified FDA monograph and should not be treated as clinical guidance:"
                )
                lines.append(self._general_drug_info(question_med))

            # Distinguish discussion from prescription
            if active_meds and question_med.lower() in " ".join(active_meds).lower():
                lines.append(
                    f"\n*Note: {question_med} has been recorded as a medication discussed in "
                    "this session. This does not confirm it is currently prescribed to you.*"
                )
            else:
                lines.append(
                    f"\n*Note: Asking about {question_med} does not automatically record it "
                    "as a medication you are taking.*"
                )
        else:
            # General information request without a specific medication
            lines.append(
                f"I can help with information about medications, symptoms, or clinical topics. "
                f"Could you clarify what you would like to know more about?"
            )
            if active_meds:
                lines.append(
                    f"The medications currently on record in this session are: "
                    f"{', '.join(active_meds)}."
                )

        lines.append(f"\n{MOCK_PROVIDER_LABEL}")
        return "\n".join(lines)

    def _render_symptom_report(self, ctx: dict) -> str:
        new_symptoms = ctx.get("new_positive_symptoms", [])
        neg_symptoms = ctx.get("new_negative_symptoms", [])
        all_symptoms = ctx.get("positive_symptoms", [])
        med_mentions = ctx.get("medication_mentions", [])
        evidence_records = ctx.get("evidence_records", [])
        lines: list[str] = []

        if new_symptoms:
            lines.append(
                f"I have recorded the following from your message: **{', '.join(new_symptoms)}**."
            )
        if neg_symptoms:
            lines.append(
                f"I have noted the absence of: {', '.join(neg_symptoms)}."
            )

        if all_symptoms:
            lines.append(
                f"\nYour cumulative reported symptoms in this session: "
                f"{', '.join(all_symptoms)}."
            )

        # If medications mentioned alongside symptoms, add evidence where available
        if med_mentions and evidence_records:
            lines.append(
                f"\nRegarding **{med_mentions[0]}** — from DailyMed "
                f"({evidence_records[0].get('section_name', '')}):"
            )
            excerpt = evidence_records[0].get("evidence_text", "")[:250]
            lines.append(f"> {excerpt}...")

        # Ask a clinically relevant clarification question
        if new_symptoms:
            lines.append(
                f"\nTo help build a complete picture: how long have you been experiencing "
                f"{new_symptoms[0]}? Has it been getting better, worse, or staying the same?"
            )
        elif not all_symptoms:
            lines.append(
                "Could you describe your main health concern or symptom in more detail?"
            )

        lines.append(f"\n{MOCK_PROVIDER_LABEL}")
        return "\n".join(lines)

    def _render_general(self, ctx: dict) -> str:
        user_question = ctx.get("user_question", "")
        med_mentions = ctx.get("medication_mentions", [])
        active_meds = ctx.get("active_meds", [])
        evidence_records = ctx.get("evidence_records", [])
        lines: list[str] = []

        if med_mentions and evidence_records:
            return self._render_information(ctx)

        if med_mentions and not evidence_records:
            lines.append(
                f"You mentioned **{', '.join(med_mentions)}**. "
                "The local DailyMed corpus does not have a matching evidence record for "
                f"this medication. No verified FDA evidence is available at this time."
            )
            lines.append(self._general_drug_info(med_mentions[0]))
        elif user_question:
            lines.append(
                f"I have received your message. "
                "To give you the most relevant response, could you tell me more about "
                "what you would like to know — for example, a specific medication, "
                "symptom, or clinical question?"
            )
        else:
            lines.append(
                "I am ready to help. Please describe your symptoms, ask about a "
                "medication, or request a summary of your current record."
            )

        if active_meds:
            lines.append(
                f"\nMedications on record in this session: {', '.join(active_meds)}."
            )

        lines.append(f"\n{MOCK_PROVIDER_LABEL}")
        return "\n".join(lines)

    @staticmethod
    def _general_drug_info(drug_name: str) -> str:
        """Return a brief general-knowledge statement for common drugs.

        This is not sourced from DailyMed and is labelled as general information only.
        Only a small set of well-known drugs are handled; all others get a neutral reply.
        """
        lower = drug_name.lower()
        info_map = {
            "paracetamol": (
                "Paracetamol (acetaminophen) is widely used for mild to moderate pain relief "
                "and fever reduction. It is available over the counter. Exceeding the recommended "
                "dose can cause serious liver harm. Do not combine with other paracetamol-containing "
                "products. This is general information — not sourced from a verified FDA monograph."
            ),
            "acetaminophen": (
                "Acetaminophen (paracetamol) is an analgesic and antipyretic. Dosing limits vary "
                "by formulation. Overdose risk is serious. This is general information — not sourced "
                "from a verified FDA monograph."
            ),
            "ibuprofen": (
                "Ibuprofen is a non-steroidal anti-inflammatory drug (NSAID) used for pain, fever, "
                "and inflammation. Common precautions include gastrointestinal effects and renal "
                "function. This is general information — not sourced from a verified FDA monograph."
            ),
            "cetirizine": (
                "Cetirizine is a second-generation antihistamine commonly used for allergic rhinitis "
                "and urticaria. It is generally well tolerated. This is general information — not "
                "sourced from a verified FDA monograph."
            ),
            "aspirin": (
                "Aspirin is a salicylate used for pain, fever, and (at low dose) antiplatelet effects. "
                "It carries gastrointestinal and bleeding risks. This is general information — not "
                "sourced from a verified FDA monograph."
            ),
            "metformin": (
                "Metformin is a biguanide used for glycaemic control in type 2 diabetes. "
                "FDA-labelled evidence is available in this system's DailyMed corpus. "
                "General reminder: lactic acidosis is a rare but serious risk. "
                "This is general information — consult the DailyMed corpus for verified labelling."
            ),
        }
        # Partial match
        for key, text in info_map.items():
            if key in lower or lower in key:
                return text
        return (
            f"General information about {drug_name} is not available in this research prototype. "
            "Please consult a licensed pharmacist or physician for accurate drug information."
        )


class _DefaultDict(dict):
    """dict that returns a default value for missing keys (kept for backward compatibility)."""

    def __init__(self, default: str, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._default = default

    def __missing__(self, key: str) -> str:
        return self._default


# ---------------------------------------------------------------------------
# ConfigurableProvider
# ---------------------------------------------------------------------------

class ConfigurableProvider:
    """HTTP-based provider using LCC_LLM_PROVIDER and LCC_API_KEY from env.

    Only activated when LCC_API_KEY is explicitly set. Never hardcodes keys.
    Env vars:
      LCC_API_KEY          — required
      LCC_LLM_PROVIDER     — "openai" (default) or any string (requires LCC_API_ENDPOINT)
      LCC_MODEL            — model name, default "gpt-4o-mini"
      LCC_API_ENDPOINT     — custom endpoint for non-OpenAI providers
    """

    REAL_PROVIDER_LABEL = "[Real LLM response — research prototype, not medical advice]"

    def generate(self, prompt: str, context: dict) -> str:  # noqa: ARG002
        api_key = os.environ.get("LCC_API_KEY", "")
        if not api_key:
            raise ValueError(
                "LCC_API_KEY environment variable not set. "
                "Use provider='mock' for offline mode."
            )
        provider = os.environ.get("LCC_LLM_PROVIDER", "openai")
        model = os.environ.get("LCC_MODEL", "gpt-4o-mini")

        if provider == "openai":
            endpoint = "https://api.openai.com/v1/chat/completions"
        else:
            endpoint = os.environ.get("LCC_API_ENDPOINT", "")
            if not endpoint:
                raise ValueError(
                    f"LCC_API_ENDPOINT must be set for provider '{provider}'."
                )

        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 600,
            "temperature": 0.3,
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            endpoint,
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                body = json.loads(resp.read().decode("utf-8"))
                raw = body["choices"][0]["message"]["content"]
                # Always append provider label so the response is identifiable
                return f"{raw}\n\n{self.REAL_PROVIDER_LABEL}"
        except (URLError, KeyError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"LLM API call failed: {exc}") from exc


# ---------------------------------------------------------------------------
# ResponseGenerator
# ---------------------------------------------------------------------------

class ResponseGenerator:
    """Builds context from patient state and evidence, generates a clinical response.

    Architecture guarantee:
        Patient State → Evidence Retrieval → LLM Response → (CoherenceVerifier → Gate)

    The generator never bypasses the verifier or gate; those run outside this class
    in the pipeline.  Pathology ground truth is NEVER placed in context or responses.
    """

    def __init__(
        self,
        state_manager: StateManager,
        evidence_retriever: EvidenceRetriever,
        provider: str = "mock",
    ) -> None:
        self.state_manager = state_manager
        self.retriever = evidence_retriever
        self._provider = self._init_provider(provider)
        self._is_mock = provider == "mock"

    def _init_provider(self, provider: str):
        if provider == "mock":
            return MockLLMProvider()
        return ConfigurableProvider()

    def generate_response(
        self,
        conversation: Conversation,
        structured_context: dict | None = None,
        upstream_evidence: list[EvidenceRecord] | None = None,
    ) -> tuple[str, list[EvidenceRecord]]:
        """Return (response_text, evidence_used).

        Args:
            conversation: The current conversation object.
            structured_context: Pre-built context dict from the web pipeline.
                If supplied, it is passed directly to the provider and
                ``_build_context`` is skipped.
            upstream_evidence: Already-retrieved evidence records from the
                calling pipeline.  When supplied, these are reused directly
                and no second ``retrieve_for_state`` call is made.  When
                omitted (CLI / test path), evidence is fetched here.

        Pathology ground truth is NEVER included in context or response.
        """
        state: PatientState = self.state_manager.get_current_state()

        # Fix C: reuse upstream evidence when provided; avoid a redundant retrieval
        if upstream_evidence is not None:
            evidence_used = upstream_evidence
        else:
            evidence_used = self.retriever.retrieve_for_state(state)

        if structured_context is not None:
            ctx = structured_context
        else:
            ctx = self._build_context(state, evidence_used, conversation)

        prompt = self._build_prompt(conversation, state, evidence_used)
        response_text = self._provider.generate(prompt, ctx)
        return response_text, evidence_used

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_context(
        self,
        state: PatientState,
        evidence: list[EvidenceRecord],
        conversation: Conversation,
        medication_analyses: list[dict] | None = None,
        new_facts: list | None = None,
    ) -> dict:
        """Build context dict from state + evidence for use by both providers.

        Args:
            state: Current PatientState.
            evidence: Retrieved EvidenceRecord objects.
            conversation: Full conversation object.
            medication_analyses: Optional list of medication normalization dicts
                from the upstream pipeline (same structure as analyze_medications()
                output).  When supplied, ``medication_mentions`` is derived from
                these rather than from substring matching active meds.
            new_facts: Optional list of ClinicalFact objects for the current turn.
                When supplied, ``new_negative_symptoms`` is populated correctly.
                When omitted, it is represented as an empty list (honest, not invented).

        Pathology NEVER included.
        """
        positive_symptoms = [
            f.description
            for f in state.facts.values()
            if f.status == "positive" and not f.is_antecedent
        ]
        active_meds = [
            m for m in state.medications if not m.startswith("[RETRACTED]")
        ]
        retracted_meds = [
            m.replace("[RETRACTED] ", "")
            for m in state.medications
            if m.startswith("[RETRACTED]")
        ]

        # Derive user question from last patient turn
        user_question = ""
        for turn in reversed(conversation.turns):
            if turn.speaker in ("patient", "user"):
                user_question = turn.text
                break

        intent = classify_intent(user_question)

        # Fix B-3: prefer upstream medication_analyses (same logic as mock path)
        # over substring matching active meds against user_question
        if medication_analyses is not None:
            med_mentions_in_question = [m["mention"] for m in medication_analyses]
        else:
            # Fallback: substring match active meds against user question
            med_mentions_in_question = [
                m.replace("Medication: ", "").strip()
                for m in active_meds
                if m.replace("Medication: ", "").strip().lower() in user_question.lower()
            ]

        # Fix B-2: populate new_negative_symptoms from actual facts when available
        if new_facts is not None:
            new_negative_symptoms = [
                f.description for f in new_facts
                if f.status == "negative" and not f.is_antecedent
            ]
            new_positive_symptoms = [
                f.description for f in new_facts
                if f.status == "positive" and not f.is_antecedent
            ]
        else:
            # Honest representation: data not available at this call site
            new_negative_symptoms = []
            new_positive_symptoms = []

        # Fix B-1: include newly_added_meds
        # Without prior_medications snapshot we cannot derive the delta here,
        # so we represent it as an empty list rather than guessing.
        # The full delta is only available when called from build_clinical_response().
        newly_added_meds: list[str] = []

        evidence_records_as_dicts = [
            {
                "evidence_id": e.evidence_id,
                "active_ingredient": e.active_ingredient,
                "section_name": e.section_name,
                "evidence_text": e.evidence_text,
                "source_url": e.source_url,
            }
            for e in evidence
        ]

        has_err4 = any(
            isinstance(t.injection, dict) and t.injection.get("error_type") == "ERR-4"
            for t in conversation.turns
        )

        return {
            "template": "pushback_response" if has_err4 else None,
            "intent": intent,
            "user_question": user_question,
            "symptoms": ", ".join(positive_symptoms) if positive_symptoms else "none reported",
            "positive_symptoms": positive_symptoms,
            "new_positive_symptoms": new_positive_symptoms,
            "new_negative_symptoms": new_negative_symptoms,
            "active_meds": active_meds,
            "retracted_meds": retracted_meds,
            "medication_mentions": med_mentions_in_question,
            "newly_added_meds": newly_added_meds,
            "evidence_records": evidence_records_as_dicts,
            "evidence_available": len(evidence) > 0,
            "turn_index": conversation.current_turn,
        }

    def _build_prompt(
        self,
        conversation: Conversation,
        state: PatientState,
        evidence: list[EvidenceRecord],
    ) -> str:
        """Build a rich text prompt for the real LLM (ConfigurableProvider).

        Includes: system instruction, patient state summary, retrieved evidence,
        and the last 6 conversation turns.  Pathology NEVER included.
        """
        active_meds = [m for m in state.medications if not m.startswith("[RETRACTED]")]
        retracted_meds = [
            m.replace("[RETRACTED] ", "")
            for m in state.medications
            if m.startswith("[RETRACTED]")
        ]
        positive_symptoms = [
            f.description
            for f in state.facts.values()
            if f.status == "positive" and not f.is_antecedent
        ]

        system_instruction = textwrap.dedent("""
            You are ClinCoherence, a clinical conversational assistant.
            Rules you must follow:
            1. Answer the patient's actual question directly and specifically.
            2. Use only the retrieved DailyMed evidence below — do not invent citations.
            3. When evidence is unavailable, say so explicitly. Provide general information only
               and label it clearly as not sourced from a verified FDA monograph.
            4. Distinguish medications the patient is discussing from medications they explicitly
               report taking. Do not assume discussion implies prescription.
            5. Respect medication corrections. Do not reference retracted medications as active.
            6. Never invent dosages, contraindications, or clinical claims.
            7. Never reveal or hint at a diagnostic ground truth or pathology label.
            8. Keep responses focused and concise (under 250 words).
        """).strip()

        state_block = (
            f"Patient state (v{state.version}, turn {state.turn_number}):\n"
            f"  Symptoms: {', '.join(positive_symptoms) or 'none'}\n"
            f"  Active medications on record: {', '.join(active_meds) or 'none'}\n"
            f"  Retracted medications: {', '.join(retracted_meds) or 'none'}\n"
        )

        if evidence:
            ev_lines = ["Retrieved DailyMed evidence:"]
            for e in evidence[:3]:
                ev_lines.append(
                    f"  [{e.section_name}] {e.active_ingredient}: "
                    f"{e.evidence_text[:200]}..."
                    f" (source: {e.source_url})"
                )
            evidence_block = "\n".join(ev_lines)
        else:
            evidence_block = (
                "Retrieved DailyMed evidence: None — the local corpus does not contain "
                "a matching record for the active medication context."
            )

        conversation_block = "Conversation (last 6 turns):"
        for turn in conversation.turns[-6:]:
            speaker = turn.speaker.capitalize()
            conversation_block += f"\n  {speaker}: {turn.text}"

        return "\n\n".join([
            system_instruction,
            state_block,
            evidence_block,
            conversation_block,
            "Respond to the patient's last message:",
        ])
