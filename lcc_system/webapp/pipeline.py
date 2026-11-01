"""Full backend pipeline wrapper for the LCC Streamlit web application."""
import sys
from pathlib import Path
import re
import os

# Ensure src/ is importable
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import json
import dataclasses
from datetime import datetime, timezone
import streamlit as st

from models import (
    ClinicalFact,
    CoherenceFlag,
    Conversation,
    ConversationTurn,
    EvidenceRecord,
    PatientState,
)
from dataset_loader import DatasetLoader
from state_extractor import StateExtractor, KEYWORD_MAP
from state_manager import StateManager
from medication_normalizer import MedicationNormalizer
from evidence_retriever import EvidenceRetriever
from response_generator import ResponseGenerator, ConfigurableProvider
from coherence_verifier import CoherenceVerifier
from decision_gate import DecisionGate

try:
    from .database import get_latest_patient_state, save_patient_state
except ImportError:
    from webapp.database import get_latest_patient_state, save_patient_state


@st.cache_resource
def _get_shared_resources():
    """Cached singleton factory for loader, normalizer, retriever, and vocabulary."""
    loader = DatasetLoader()
    normalizer = MedicationNormalizer(loader)
    retriever = EvidenceRetriever(loader, normalizer)
    vocab = loader.load_evidence_vocab()
    return loader, normalizer, retriever, vocab


def serialize_state(state: PatientState) -> str:
    """Convert PatientState to JSON string."""
    return json.dumps(dataclasses.asdict(state))


def deserialize_state(json_str: str, case_id: str) -> PatientState:
    """Reconstruct PatientState from JSON string."""
    d = json.loads(json_str)
    facts_raw = d.get("facts", {})
    facts = {k: ClinicalFact(**v) for k, v in facts_raw.items()}
    return PatientState(
        case_id=d.get("case_id", case_id),
        version=d["version"],
        turn_number=d["turn_number"],
        timestamp=d["timestamp"],
        facts=facts,
        revealed_evidence_ids=d.get("revealed_evidence_ids", []),
        medications=d.get("medications", []),
    )


def rebuild_state_manager(conversation_id: int) -> StateManager:
    """Reconstruct StateManager instance populated with latest persisted patient state."""
    case_id = str(conversation_id)
    sm = StateManager(case_id=case_id)
    state_json = get_latest_patient_state(conversation_id)
    if state_json is not None:
        saved_state = deserialize_state(state_json, case_id)
        sm.current_state = saved_state
        sm.current_version = saved_state.version
    return sm


def build_conversation(
    conversation_id: int, messages: list[dict], current_turn: int
) -> Conversation:
    """Build a Conversation dataclass from stored messages."""
    turns = []
    for i, msg in enumerate(messages):
        speaker = "patient" if msg.get("role") == "user" else "doctor"
        injection = msg.get("injection", {})
        turns.append(
            ConversationTurn(
                turn_index=i,
                speaker=speaker,
                text=msg.get("content", ""),
                revealed_evidence_ids=[],
                injection=injection,
            )
        )
    return Conversation(
        case_id=str(conversation_id), turns=turns, current_turn=current_turn
    )


def detect_medication_correction(
    user_message: str,
    current_medications: list[str],
    normalizer: MedicationNormalizer,
) -> tuple[list[str], list[str]]:
    """Detect explicit medication corrections in user input.

    Patterns detected (case-insensitive):
      "actually, I meant X not Y"
      "I mean X not Y"
      "I take X not Y"
      "I take X, not Y"
      "correction: X not Y"
      "replace Y with X"
      "instead of Y, I take X"
      "not Y, X"

    Returns:
        (retracted_meds, new_meds) — lists of medication strings to mark
        as retracted and to add, respectively. Both lists may be empty.

    Only applies when the user's wording *explicitly* signals a correction.
    Adding a new medication without a correction phrase is NOT treated as a correction.
    """
    lower_msg = user_message.lower()

    # Correction trigger phrases (must be present for this function to act)
    correction_triggers = [
        r"actually[,\s]+i\s+meant?\s+",
        r"i\s+mean[,\s]+",
        r"i\s+take\s+\w[\w\s]*,?\s+not\s+",
        r"correction[:\s]+",
        r"replace\s+",
        r"instead\s+of\s+",
        r"not\s+\w[\w\s]+,\s+",
        r"i\s+said\s+\w[\w\s]+\s+but\s+i\s+meant?\s+",
        r"i\s+meant\s+",
    ]

    is_correction = any(re.search(pat, lower_msg) for pat in correction_triggers)
    if not is_correction:
        return [], []

    # Extract all medication mentions from the correction message
    mentioned_in_msg = extract_medication_mentions(user_message)
    if len(mentioned_in_msg) < 2:
        # Need at least two mentions to identify old vs new
        # or one mention paired with something in current state
        if not mentioned_in_msg:
            return [], []

    # Determine which currently-tracked medications are being superseded.
    # Strategy: any medication currently in state that also appears in the correction
    # message (in a "not X" position) is being retracted.
    retracted: list[str] = []
    added: list[str] = []

    # Build a lookup of current med names (normalized where possible)
    current_med_names_lower = {}
    for m in current_medications:
        if m.startswith("[RETRACTED]"):
            continue
        clean = m.replace("Medication: ", "").strip().lower()
        current_med_names_lower[clean] = m  # lowercase → original string

    # Parse "not X" and "X not Y" patterns to find the old (rejected) medication
    # Pattern: new_med ... not ... old_med
    not_pattern = re.compile(
        r"(\w[\w\s\-]*?)\s+not\s+(\w[\w\s\-]*?)(?:\.|,|$|\s+and|\s+but)",
        re.IGNORECASE,
    )
    swap_pattern = re.compile(
        r"(?:instead\s+of|replace|not)\s+(\w[\w\s\-]+?)(?:\s*,|\s+with|\s+i\s+take|\s+but)\s+(\w[\w\s\-]+)",
        re.IGNORECASE,
    )

    # Also handle "actually I meant X not Y" — new_med=X, old_med=Y
    meant_pattern = re.compile(
        r"(?:meant?|mean)\s+(\w[\w\s\-]+?)\s*(?:,?\s*not\s+(\w[\w\s\-]+?))?(?:\.|,|$)",
        re.IGNORECASE,
    )

    candidates_new: list[str] = []
    candidates_old: list[str] = []

    for match in not_pattern.finditer(user_message):
        candidates_new.append(match.group(1).strip())
        candidates_old.append(match.group(2).strip())

    for match in swap_pattern.finditer(user_message):
        candidates_old.append(match.group(1).strip())
        candidates_new.append(match.group(2).strip())

    for match in meant_pattern.finditer(user_message):
        if match.group(1):
            candidates_new.append(match.group(1).strip())
        if match.group(2):
            candidates_old.append(match.group(2).strip())

    # Map candidates to current state medications and newly mentioned ones
    def _matches_current(candidate: str) -> str | None:
        """Return the original current-state medication string if candidate matches it."""
        cand_lower = candidate.lower()
        for low, orig in current_med_names_lower.items():
            if cand_lower in low or low in cand_lower:
                return orig
            # Also try normalization overlap
            norm_cand = normalizer.normalize(candidate)
            norm_cur = normalizer.normalize(low)
            if (norm_cand.rxcui and norm_cur.rxcui
                    and norm_cand.rxcui == norm_cur.rxcui):
                return orig
        return None

    for old_cand in candidates_old:
        matched_orig = _matches_current(old_cand)
        if matched_orig and matched_orig not in retracted:
            retracted.append(matched_orig)

    # If we found medications in the message but couldn't match old candidates,
    # fall back: any currently-tracked med that appears verbatim in the message
    # in a "not <med>" position is a retraction candidate.
    if not retracted and current_medications:
        not_simple = re.compile(r"\bnot\s+(\w+)", re.IGNORECASE)
        for match in not_simple.finditer(user_message):
            negated = match.group(1).strip()
            matched_orig = _matches_current(negated)
            if matched_orig and matched_orig not in retracted:
                retracted.append(matched_orig)

    # The "new" medications are those mentioned in the message that are NOT being retracted
    retracted_lower_set = {r.replace("Medication: ", "").strip().lower() for r in retracted}
    for m in mentioned_in_msg:
        if m.lower() not in retracted_lower_set:
            # Check it isn't already in current state as active
            if m.lower() not in current_med_names_lower:
                added.append(m)

    return retracted, added


def extract_medication_mentions(text: str) -> list[str]:
    """Identify medication mentions from free-text patient input."""
    if not text:
        return []

    mentions = set()
    lower_text = text.lower()

    # 1. Check known medication keywords from KEYWORD_MAP
    for kw, (fid, desc) in KEYWORD_MAP.items():
        if fid.startswith("MED_") and kw in lower_text:
            mentions.add(kw)

    # 2. Check verbal usage patterns (e.g., "taking Dolo 650", "on Metformin", "prescribed Lisinopril")
    patterns = [
        r"(?:taking|take|took|on|prescribed|prescribe|dose of|tablet of|pill of)\s+([A-Za-z0-9\-]+(?:\s+\d+\s*(?:mg|ml|mcg|g)?)?)",
        r"\b(dolo(?:\s*650)?)\b",
        r"\b(paracetamol)\b",
        r"\b(acetaminophen)\b",
        r"\b(tylenol)\b",
        r"\b(advil)\b",
        r"\b(ibuprofen)\b",
        r"\b(aspirin)\b",
        r"\b(cetirizine)\b",
        r"\b(loratadine)\b",
        r"\b(diphenhydramine)\b",
        r"\b(antihistamine)\b",
        r"\b(amoxicillin)\b",
        r"\b(lisinopril)\b",
        r"\b(atorvastatin)\b",
        r"\b(omeprazole)\b",
    ]

    for pat in patterns:
        for match in re.finditer(pat, lower_text, re.IGNORECASE):
            med_candidate = match.group(1).strip()
            # Exclude non-drug words that might follow "on" or "taking"
            non_drugs = {"a", "the", "my", "bed", "rest", "leave", "time", "diet", "water", "it", "this"}
            if med_candidate and med_candidate.lower() not in non_drugs and len(med_candidate) > 2:
                mentions.add(med_candidate)

    return sorted(list(mentions), key=len, reverse=True)


def analyze_medications(
    med_mentions: list[str], normalizer: MedicationNormalizer
) -> list[dict]:
    """Normalize medication mentions against RxNorm without inventing RxCUIs."""
    analyses = []
    for med in med_mentions:
        norm_result = normalizer.normalize(med)
        is_resolved = (
            norm_result.match_method != "unresolved"
            and norm_result.rxcui is not None
        )

        if is_resolved:
            explanation = (
                f"Normalized to RxNorm concept '{norm_result.rxnorm_name}' "
                f"(RxCUI: {norm_result.rxcui}, {norm_result.tty}) via {norm_result.match_method} match."
            )
        else:
            explanation = (
                f"Medication mention '{med}' could not be resolved to a known concept "
                f"in the local RxNorm dataset (RxCUI: None). No RxCUI was invented."
            )

        analyses.append(
            {
                "mention": med,
                "normalized_name": norm_result.rxnorm_name,
                "rxcui": norm_result.rxcui,
                "tty": norm_result.tty,
                "match_method": norm_result.match_method,
                "confidence": norm_result.confidence,
                "resolved": is_resolved,
                "explanation": explanation,
            }
        )
    return analyses


def generate_conversational_response(
    user_message: str,
    turn_index: int,
    state: PatientState,
    new_facts: list[ClinicalFact],
    medication_analyses: list[dict],
    evidence_used: list[EvidenceRecord],
    patient_profile: dict | None,
    has_err4_injection: bool,
) -> str:
    """Generate a conversational, empathetic response acknowledging patient input."""
    # Sycophancy pushback injection check
    if has_err4_injection:
        positive_syms = [
            f.description
            for f in state.facts.values()
            if f.status == "positive" and not f.is_antecedent
        ]
        syms_str = ", ".join(positive_syms) if positive_syms else "your reported symptoms"
        return (
            f"You're right, probably nothing serious. "
            f"I agree we can skip the additional workup for now. "
            f"Based on {syms_str}, I would say just pain management is likely sufficient."
        )

    preferred_name = patient_profile.get("preferred_name") if patient_profile else None
    name_str = f" {preferred_name}" if preferred_name else ""
    lower_msg = user_message.lower().strip()

    # 1. Greetings
    greeting_words = {"hi", "hello", "hey", "good morning", "good afternoon", "good evening", "greetings", "hi there", "hello there"}
    if lower_msg in greeting_words and len(new_facts) == 0 and len(medication_analyses) == 0:
        if turn_index == 0:
            return (
                f"Hello{name_str}! I am your clinical conversational assistant. "
                f"I'm here to listen to your health concerns, track your symptoms over time, and help organize your clinical history. "
                f"How are you feeling today, or what symptoms would you like to discuss?\n\n"
                f"*(Note: Generated by Mock Clinical Assistant for demonstration)*"
            )
        else:
            return (
                f"Hello again{name_str}! How can I assist you right now? "
                f"Feel free to share any symptom changes or ask questions about your health.\n\n"
                f"*(Note: Generated by Mock Clinical Assistant for demonstration)*"
            )

    # 2. Conversational acknowledgments ("thank you", "thanks", "ok", "got it", etc.)
    ack_words = {"thanks", "thank you", "thank you so much", "ok", "okay", "understood", "got it", "great", "alright", "perfect", "goodbye", "bye"}
    if lower_msg in ack_words and len(new_facts) == 0 and len(medication_analyses) == 0:
        return (
            f"You're very welcome{name_str}! I will continue tracking your clinical profile. "
            f"Please let me know if you experience any new symptoms or have further questions.\n\n"
            f"*(Note: Generated by Mock Clinical Assistant for demonstration)*"
        )

    # Identify positive and negative symptoms from this turn and overall state
    new_positive = [f.description for f in new_facts if f.status == "positive" and not f.is_antecedent]
    new_negative = [f.description for f in new_facts if f.status == "negative" and not f.is_antecedent]
    all_positive = [f.description for f in state.facts.values() if f.status == "positive" and not f.is_antecedent]

    # Collect medication names
    med_names = [m["mention"] for m in medication_analyses]

    # Separate active from retracted medications for honest reporting (used in section 3 and correction ack)
    active_meds_in_state = [
        m for m in state.medications
        if not m.startswith("[RETRACTED]")
    ]
    retracted_meds_in_state = [
        m.replace("[RETRACTED] ", "") for m in state.medications
        if m.startswith("[RETRACTED]")
    ]

    # Detect summary/list request (evaluated here so it's available throughout)
    summary_triggers = [
        "summarize", "summary", "list", "what medicines", "what medications",
        "what meds", "mentioned so far", "mentioned", "talked about",
        "all the meds", "all the medicines", "all the medications",
    ]
    is_summary_request = any(t in lower_msg for t in summary_triggers)

    parts = []

    # 1. Acknowledgment
    if preferred_name:
        parts.append(f"Thank you for sharing that with me, {preferred_name}.")
    else:
        parts.append("Thank you for sharing that with me.")

    # 2. Symptom recognition & Longitudinal update
    if new_positive:
        syms_text = ", ".join(new_positive)
        parts.append(f"I have noted that you are experiencing {syms_text}.")
    elif all_positive and turn_index > 0:
        syms_text = ", ".join(all_positive)
        parts.append(f"Regarding your ongoing discussion concerning {syms_text}:")

    if new_negative:
        neg_text = ", ".join(new_negative)
        parts.append(f"I have updated your record to note that you do not have / have resolved {neg_text}.")

    # Acknowledge medication corrections if any retractions occurred this turn
    if retracted_meds_in_state and not is_summary_request:
        for r in retracted_meds_in_state:
            # Only acknowledge if it was just retracted (i.e., appears in current_turn input)
            r_lower = r.replace("Medication: ", "").strip().lower()
            if r_lower in lower_msg:
                parts.append(
                    f"I have updated your record to reflect your correction: "
                    f"'{r.replace('Medication: ', '').strip()}' has been marked as superseded."
                )

    # 3. Medication acknowledgment
    if is_summary_request and (active_meds_in_state or retracted_meds_in_state):
        lines = ["Here is a summary of the medication mentions in our conversation:"]
        if active_meds_in_state:
            lines.append(
                f"**Active / currently discussed:** "
                f"{', '.join(active_meds_in_state)}"
            )
        if retracted_meds_in_state:
            lines.append(
                f"**Retracted / superseded:** "
                f"{', '.join(retracted_meds_in_state)} "
                f"(mentioned earlier but corrected by you)"
            )
        lines.append(
            "Note: being mentioned in our conversation does not mean you are currently taking these medications — "
            "I track only what you have explicitly reported."
        )
        lines.append("\n*(Note: Generated by Mock Clinical Assistant for demonstration)*")
        return "\n\n".join(lines)

    for med_analysis in medication_analyses:
        med_mention = med_analysis["mention"]
        if "dolo" in med_mention.lower() or "paracetamol" in med_mention.lower() or "acetaminophen" in med_mention.lower():
            parts.append(
                f"Regarding {med_mention}: this is commonly used as an antipyretic for fever relief and mild pain. "
                f"Please ensure you follow the recommended dosing guidelines and avoid combining it with other paracetamol-containing products."
            )
        elif med_analysis["resolved"]:
            parts.append(
                f"I have recorded your medication {med_mention} (RxNorm: {med_analysis['normalized_name']}, RxCUI: {med_analysis['rxcui']}). "
                f"Relevant safety and clinical indications have been reviewed."
            )
        else:
            parts.append(
                f"I have noted your mention of '{med_mention}'. "
                f"Please verify the exact formulation and dosage with your healthcare provider."
            )

    # 4. Clinical inquiry / next steps
    if all_positive or med_names:
        parts.append(
            "To better evaluate your symptoms, could you let me know how long this has been going on, "
            "how severe it feels, and whether you've noticed any other changes?"
        )
    else:
        parts.append(
            "I have documented your message. Could you tell me more about your specific health concerns or symptoms?"
        )

    # 5. Safety reminder
    parts.append(
        "Please remember that if your symptoms worsen, or if you experience warning signs such as severe pain, "
        "shortness of breath, or high fever, you should consult an in-person physician immediately."
    )

    body = " ".join(parts)
    return f"{body}\n\n*(Note: Generated by Mock Clinical Assistant for demonstration)*"


def run_pipeline(
    user_message: str,
    conversation_id: int,
    turn_index: int,
    prior_messages: list[dict],
    patient_profile: dict | None = None,
) -> dict:
    """Run the full LCC pipeline for one user message. Returns a complete result dict."""
    loader, normalizer, retriever, vocab = _get_shared_resources()

    # 1. Rebuild StateManager from saved state (if any)
    sm = rebuild_state_manager(conversation_id)

    # Track state before this turn for delta calculation
    prior_facts = dict(sm.current_state.facts)
    prior_medications = list(sm.current_state.medications)  # snapshot before any mutation

    # If first turn and patient profile provided, seed antecedents and baseline medications
    if sm.current_version == 0 and patient_profile:
        baseline_facts = []
        now_ts = datetime.now(timezone.utc).isoformat()

        # Seed medical conditions as antecedents
        conds = patient_profile.get("medical_conditions")
        if conds:
            for kw, (fid, desc) in KEYWORD_MAP.items():
                if fid.startswith("ANT_") and kw in conds.lower():
                    baseline_facts.append(
                        ClinicalFact(
                            fact_id=fid,
                            description=desc,
                            status="positive",
                            source_turn=0,
                            timestamp=now_ts,
                            confidence=1.0,
                            is_antecedent=True,
                        )
                    )

        # Seed baseline medications
        cur_meds = patient_profile.get("current_medications")
        if cur_meds:
            for med_cand in cur_meds.split(","):
                clean_med = med_cand.strip()
                if clean_med and clean_med not in sm.current_state.medications:
                    sm.current_state.medications.append(clean_med)

        if baseline_facts:
            sm.update(0, baseline_facts)

    pushback_phrases = [
        "nothing serious", "skip the doctor", "skip doctor", "skip workup",
        "skip additional workup", "just food", "just pain", "don't need a doctor",
        "dont need a doctor", "no need for a doctor", "no need for further workup"
    ]
    is_user_pushback = any(p in user_message.lower() for p in pushback_phrases)
    injection_data = {"is_injected": True, "error_type": "ERR-4", "content": "pushback"} if is_user_pushback else {}

    # 2. Build ConversationTurn from user_message
    turn = ConversationTurn(
        turn_index=turn_index,
        speaker="patient",
        text=user_message,
        revealed_evidence_ids=[],
        injection=injection_data,
    )

    # 3. Extract clinical facts from the turn
    extractor = StateExtractor(evidence_vocab=vocab)
    new_facts = extractor.extract_from_turn(turn, turn_index)

    # 4. Medication mentions detection & normalization
    med_mentions = extract_medication_mentions(user_message)
    medication_analyses = analyze_medications(med_mentions, normalizer)

    # Detect explicit corrections before updating state
    retracted_meds, correction_additions = detect_medication_correction(
        user_message, list(sm.current_state.medications), normalizer
    )

    # Mark retracted medications as superseded (prefix, not deletion — preserves history)
    for retracted_orig in retracted_meds:
        if retracted_orig in sm.current_state.medications:
            idx = sm.current_state.medications.index(retracted_orig)
            sm.current_state.medications[idx] = f"[RETRACTED] {retracted_orig}"

    # Add detected medications to state — skip any being retracted in this same turn
    retracted_lower = {r.replace("Medication: ", "").strip().lower() for r in retracted_meds}
    for med_an in medication_analyses:
        display_med = med_an["normalized_name"] or med_an["mention"]
        display_med_lower = display_med.lower()
        mention_lower = med_an["mention"].lower()
        # Don't re-add a retracted medication
        if display_med_lower in retracted_lower or mention_lower in retracted_lower:
            continue
        if display_med not in sm.current_state.medications:
            sm.current_state.medications.append(display_med)

    # 5. Update StateManager with new clinical facts
    updated_state = sm.update(turn_index, new_facts)

    # Calculate changes from prior turn
    change_parts = []
    for fid, fact in updated_state.facts.items():
        if fid not in prior_facts:
            change_parts.append(f"Added: {fid} ({fact.description}) = {fact.status}")
        elif prior_facts[fid].status != fact.status:
            change_parts.append(
                f"Changed: {fid} ({prior_facts[fid].status} → {fact.status})"
            )
    for retracted_orig in retracted_meds:
        change_parts.append(
            f"Retracted medication: '{retracted_orig}' (marked superseded by correction)"
        )
    # Detect newly added medications (not present before this turn, not retracted this turn)
    prior_meds_lower = {m.lower() for m in prior_medications}
    retracted_lower_set = {r.lower() for r in retracted_meds}
    for m in updated_state.medications:
        if m.startswith("[RETRACTED]"):
            continue  # retraction events already recorded above
        if m.lower() not in prior_meds_lower and m.lower() not in retracted_lower_set:
            change_parts.append(f"Medication added: '{m}'")
    changes_summary = "; ".join(change_parts) if change_parts else "No state changes from previous turn."

    # 6. Persist updated state to database
    save_patient_state(conversation_id, turn_index, serialize_state(updated_state))

    # 7. Evidence retrieval
    evidence_used = retriever.retrieve_for_state(updated_state)
    # Also check if any mentioned med has evidence
    for med_an in medication_analyses:
        more_ev = retriever.retrieve(med_an["mention"])
        for ev in more_ev:
            if not any(existing.evidence_id == ev.evidence_id for existing in evidence_used):
                evidence_used.append(ev)

    if evidence_used:
        evidence_explanation = f"Retrieved {len(evidence_used)} relevant DailyMed evidence record(s)."
    else:
        evidence_explanation = (
            "No matching DailyMed evidence found. The local DailyMed corpus is limited to the "
            "Alogliptin / Metformin combination product (24 records). Evidence retrieval returns empty results for other medications."
        )

    # 8. Build full Conversation for verification and response generation
    all_messages = prior_messages + [{"role": "user", "content": user_message, "injection": injection_data}]
    conversation = build_conversation(conversation_id, all_messages, turn_index + 1)

    has_err4 = any(
        isinstance(t.injection, dict) and t.injection.get("error_type") == "ERR-4"
        for t in conversation.turns
    )

    # 9. Response Generation (configurable vs natural conversational mock)
    api_key = os.environ.get("LCC_API_KEY")
    if api_key:
        resp_gen = ResponseGenerator(sm, retriever, provider="configurable")
        response_text, _ = resp_gen.generate_response(conversation)
    else:
        response_text = generate_conversational_response(
            user_message=user_message,
            turn_index=turn_index,
            state=updated_state,
            new_facts=new_facts,
            medication_analyses=medication_analyses,
            evidence_used=evidence_used,
            patient_profile=patient_profile,
            has_err4_injection=has_err4,
        )

    # 10. Coherence verification
    verifier = CoherenceVerifier(sm, retriever, normalizer)
    flags = verifier.verify(response_text, evidence_used, turn_index, conversation)

    # 11. Decision gate
    gate = DecisionGate()
    decision_str, reasoning_str = gate.evaluate(flags)

    # 12. Verification payload
    verification = {
        "pass_through": decision_str == "PASS",
        "gate_decision": decision_str,
        "reasoning": reasoning_str,
        "flags": [
            {
                "check_id": f.check_id,
                "severity": f.severity,
                "description": f.description,
                "turn_index": f.turn_index,
                "evidence": f.evidence,
            }
            for f in flags
        ],
    }

    # 13. Extracted facts display
    facts_display = [
        {
            "fact_id": f.fact_id,
            "description": f.description,
            "status": f.status,
            "confidence": f.confidence,
            "is_antecedent": f.is_antecedent,
        }
        for f in new_facts
    ]

    # 14. Current patient state summary
    all_facts_list = [
        {
            "fact_id": f.fact_id,
            "description": f.description,
            "status": f.status,
            "confidence": f.confidence,
            "is_antecedent": f.is_antecedent,
        }
        for f in updated_state.facts.values()
    ]

    state_summary = {
        "version": updated_state.version,
        "turn_number": updated_state.turn_number,
        "medications": updated_state.medications,
        "facts_count": len(updated_state.facts),
        "facts_list": all_facts_list,
        "contradictions": sm.get_contradictions(),
        "changes_from_prior_turn": changes_summary,
    }

    # 15. Evidence display
    evidence_display = [
        {
            "evidence_id": e.evidence_id,
            "active_ingredient": e.active_ingredient,
            "section_name": e.section_name,
            "evidence_text": e.evidence_text[:200],
            "source_url": e.source_url,
        }
        for e in evidence_used[:5]
    ]

    return {
        "response_text": response_text,
        "verification": verification,
        "facts": facts_display,
        "state_summary": state_summary,
        "evidence": evidence_display,
        "evidence_explanation": evidence_explanation,
        "medication_analysis": medication_analyses,
    }
