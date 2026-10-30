"""
models.py — All shared dataclasses for the Longitudinal Clinical Coherence system.

Python stdlib dataclasses only (no Pydantic). Python 3.11+ union syntax (str | None).
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class EvidenceVocabEntry:
    """An entry from evidence_mapping_summary.csv describing a DDXPlus evidence item."""
    evidence_id: str              # e.g. "E_91"
    name: str
    data_type: str                # "B" (binary), "C" (categorical), "M" (multi-choice)
    is_antecedent: bool
    question_en: str
    default_value: str            # e.g. "V_123" or ""
    possible_values: dict[str, str]  # val_key -> English text


@dataclass
class ConditionMeta:
    """Metadata for a DDXPlus pathology from condition_mapping_summary.csv."""
    condition_id: str             # e.g. "Anemia"
    icd10_id: str                 # e.g. "D64.9"
    severity: int                 # 1–5
    symptom_count: int
    antecedent_count: int


@dataclass
class PatientCase:
    """A DDXPlus-format patient case (real or synthetic).

    PATHOLOGY and DIFFERENTIAL_DIAGNOSIS are STRICTLY HIDDEN from the LLM
    response-generating component.
    """
    case_id: str                  # e.g. "SYNTHETIC_000"
    age: int
    sex: str                      # "M" or "F"
    initial_evidence: str         # e.g. "E_154" — chief complaint
    evidences: list[str]          # full ground-truth evidence list, HIDDEN from LLM
    pathology: str                # STRICTLY HIDDEN from LLM
    differential_diagnosis: list[tuple[str, float]]  # STRICTLY HIDDEN
    severity: int                 # from condition_mapping


@dataclass
class ClinicalFact:
    """A single extracted clinical fact from a conversation turn."""
    fact_id: str                  # e.g. "E_91" or "SYM_FATIGUE"
    description: str              # human-readable
    status: str                   # "positive", "negative", or "unknown"
    source_turn: int
    timestamp: str                # ISO 8601
    confidence: float             # 0.0–1.0
    is_antecedent: bool


@dataclass
class PatientState:
    """The structured patient state after processing some conversation turns."""
    case_id: str
    version: int
    turn_number: int
    timestamp: str                # ISO 8601
    facts: dict[str, ClinicalFact] = field(default_factory=dict)  # keyed by fact_id
    revealed_evidence_ids: list[str] = field(default_factory=list)
    medications: list[str] = field(default_factory=list)  # normalized medication names


@dataclass
class StateVersion:
    """An immutable snapshot of PatientState at a particular turn."""
    version: int
    turn_number: int
    snapshot: PatientState
    change_summary: str           # "Added: E_91. Corrected: E_53 positive→negative."


@dataclass
class ConversationTurn:
    """A single turn in a clinical conversation."""
    turn_index: int
    speaker: str                  # "patient", "doctor", or "system"
    text: str
    revealed_evidence_ids: list[str] = field(default_factory=list)
    injection: dict = field(default_factory=dict)  # {"is_injected": bool, "error_type": str, "content": str}


@dataclass
class Conversation:
    """A complete multi-turn clinical conversation."""
    case_id: str
    turns: list[ConversationTurn] = field(default_factory=list)
    current_turn: int = 0


@dataclass
class RxNormConcept:
    """A concept loaded from rxnorm_capstone/data/concepts.csv."""
    rxcui: str
    rxnorm_name: str
    tty: str                      # "IN", "PIN", "BN", "MIN", "SCD", "SBD", etc.
    concept_type: str             # "ingredient", "precise_ingredient", "brand_name", etc.
    ingredient_names: str         # comma-separated ingredient names
    ingredient_rxcuis: str        # comma-separated rxcuis


@dataclass
class MedicationNormResult:
    """Result of normalizing a free-text medication mention to RxNorm."""
    input_text: str
    rxcui: str | None             # None means unresolved
    rxnorm_name: str | None
    tty: str | None
    match_method: str             # "exact", "alias", "substring", "unresolved"
    confidence: float


@dataclass
class EvidenceRecord:
    """A single evidence record from dailymed_corpus_final/medication_evidence.jsonl."""
    evidence_id: str              # e.g. "DM-EV-ALOG-MET-001"
    active_ingredient: str
    product_name: str
    all_active_ingredients: str
    section_name: str
    evidence_text: str
    source_url: str
    evidence_scope: str           # "Single ingredient (...)" or "Combination product"
    verification_status: str
    notes: str


@dataclass
class CoherenceFlag:
    """A coherence issue detected by the CoherenceVerifier."""
    check_id: str                 # e.g. "MED_TARGET_MISMATCH", "FACT_CONTRADICTION"
    severity: str                 # "WARNING" or "ERROR"
    description: str
    turn_index: int
    evidence: str                 # supporting detail / context


@dataclass
class VerificationResult:
    """Output of the CoherenceVerifier + DecisionGate pipeline."""
    pass_through: bool
    flags: list[CoherenceFlag] = field(default_factory=list)
    gate_decision: str = "PASS"  # "PASS", "CLARIFY", "WARN", "REFUSE"
    reasoning: str = ""
