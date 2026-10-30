"""
response_generator.py — Generates candidate clinical responses.

MockLLMProvider: no API key required; fills templated responses from patient state.
ConfigurableProvider: reads LCC_LLM_PROVIDER + LCC_API_KEY from environment and
    calls an OpenAI-compatible endpoint (stdlib urllib only).

PATHOLOGY GROUND TRUTH IS NEVER PLACED IN CONTEXT OR RESPONSES.
"""
from __future__ import annotations

import json
import os
import urllib.request
from urllib.error import URLError

from models import Conversation, EvidenceRecord, PatientState
from state_manager import StateManager
from evidence_retriever import EvidenceRetriever


# ---------------------------------------------------------------------------
# MockLLMProvider
# ---------------------------------------------------------------------------

class MockLLMProvider:
    """Template-based provider requiring no API key."""

    RESPONSE_TEMPLATES: dict[str, str] = {
        "initial_assessment": (
            "Based on the information provided, the patient presents with {symptoms}. "
            "Given the demographics (age {age}, {sex}), the differential includes "
            "{differentials}. I recommend {recommendation}."
        ),
        "clarification_needed": (
            "I note {symptoms} but need clarification about {unclear_points} "
            "before proceeding."
        ),
        "medication_counseling": (
            "Regarding {medication}: {evidence_summary}. "
            "This is particularly relevant given the patient's {relevant_condition}."
        ),
    }

    _TEMPLATE_KEYS = [
        "symptoms", "age", "sex", "differentials", "recommendation",
        "medication", "evidence_summary", "relevant_condition", "unclear_points",
    ]

    def generate(self, prompt: str, context: dict) -> str:  # noqa: ARG002
        """Fill the appropriate response template from context dict.

        Missing keys silently become '[unknown]'.
        """
        template_key = context.get("template", "initial_assessment")
        template = self.RESPONSE_TEMPLATES.get(
            template_key, self.RESPONSE_TEMPLATES["initial_assessment"]
        )
        safe_ctx = {k: context.get(k, "[unknown]") for k in self._TEMPLATE_KEYS}
        try:
            return template.format(**safe_ctx)
        except KeyError:
            return template.format_map(_DefaultDict("[unknown]", safe_ctx))


class _DefaultDict(dict):
    """dict that returns a default value for missing keys."""

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
    """

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
            "max_tokens": 512,
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
                return body["choices"][0]["message"]["content"]
        except (URLError, KeyError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"LLM API call failed: {exc}") from exc


# ---------------------------------------------------------------------------
# ResponseGenerator
# ---------------------------------------------------------------------------

class ResponseGenerator:
    """Builds context from patient state and evidence, generates a clinical response."""

    def __init__(
        self,
        state_manager: StateManager,
        evidence_retriever: EvidenceRetriever,
        provider: str = "mock",
    ) -> None:
        self.state_manager = state_manager
        self.retriever = evidence_retriever
        self._provider = self._init_provider(provider)

    def _init_provider(self, provider: str):
        if provider == "mock":
            return MockLLMProvider()
        return ConfigurableProvider()

    def generate_response(
        self, conversation: Conversation
    ) -> tuple[str, list[EvidenceRecord]]:
        """Return (response_text, evidence_used).

        Pathology ground truth is NEVER included in context or response.
        """
        state: PatientState = self.state_manager.get_current_state()
        evidence_used = self.retriever.retrieve_for_state(state)
        context = self._build_context(state, evidence_used, conversation)
        prompt = self._build_prompt(conversation)
        response_text = self._provider.generate(prompt, context)
        return response_text, evidence_used

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_context(
        self,
        state: PatientState,
        evidence: list[EvidenceRecord],
        conversation: Conversation,
    ) -> dict:
        """Build context dict from state + evidence. Pathology NEVER included."""
        positive_symptoms = [
            f.description
            for f in state.facts.values()
            if f.status == "positive" and not f.is_antecedent
        ]
        symptoms_str = ", ".join(positive_symptoms) if positive_symptoms else "no reported symptoms"

        meds = [
            m.replace("Medication: ", "") for m in state.medications
        ]
        meds_str = ", ".join(meds) if meds else "none"

        # Extract age/sex from first patient turn text (best-effort)
        age_str = "unknown"
        sex_str = "unknown"
        for turn in conversation.turns:
            if turn.speaker == "patient" and turn.turn_index == 0:
                text = turn.text
                if "-year-old" in text:
                    parts = text.split("-year-old")
                    age_candidate = parts[0].split()[-1]
                    if age_candidate.isdigit():
                        age_str = age_candidate
                if "female" in text.lower():
                    sex_str = "female"
                elif "male" in text.lower():
                    sex_str = "male"
                break

        evidence_summary = (
            "; ".join(e.evidence_text[:80] for e in evidence[:2])
            if evidence
            else "no specific evidence available"
        )

        return {
            "symptoms": symptoms_str,
            "age": age_str,
            "sex": sex_str,
            "differentials": "to be determined",
            "recommendation": "further workup",
            "medication": meds_str,
            "evidence_summary": evidence_summary,
            "relevant_condition": symptoms_str,
            "unclear_points": "further history required",
            # Note: pathology NEVER set here
        }

    @staticmethod
    def _build_prompt(conversation: Conversation) -> str:
        """Build a text prompt from the conversation history."""
        lines = [f"Clinical conversation for case {conversation.case_id}:"]
        for turn in conversation.turns[-6:]:  # last 6 turns for context
            speaker = turn.speaker.capitalize()
            lines.append(f"{speaker}: {turn.text}")
        lines.append("\nProvide a clinical assessment based on the above information.")
        return "\n".join(lines)
