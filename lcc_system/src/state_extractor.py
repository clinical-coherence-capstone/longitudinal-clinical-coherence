"""
state_extractor.py — Extracts structured clinical facts from conversation turns.

Uses revealed_evidence_ids when available (confidence=1.0), otherwise performs
keyword-based extraction with negation window detection (confidence=0.7).
Never creates a fact for an unmentioned item.
"""
from __future__ import annotations

from datetime import datetime, timezone

from models import ClinicalFact, ConversationTurn, EvidenceVocabEntry


# ---------------------------------------------------------------------------
# Keyword → (fact_id, description) mapping
# Keys are lowercase; multi-word keys must be checked before single-word keys.
# ---------------------------------------------------------------------------
KEYWORD_MAP: dict[str, tuple[str, str]] = {
    # Symptoms — multi-word first
    "chest pain": ("SYM_CHEST_PAIN", "Chest pain"),
    "shortness of breath": ("SYM_DYSPNEA", "Dyspnea / shortness of breath"),
    "difficulty breathing": ("SYM_DYSPNEA", "Dyspnea / shortness of breath"),
    "black stool": ("SYM_MELENA", "Melena (black stools)"),
    "black stools": ("SYM_MELENA", "Melena (black stools)"),
    "blood thinner": ("MED_ANTICOAGULANT", "Medication: anticoagulant"),
    # Symptoms — single-word
    "pale": ("SYM_PALLOR", "Skin pallor"),
    "pallor": ("SYM_PALLOR", "Skin pallor"),
    "tired": ("SYM_FATIGUE", "Fatigue"),
    "exhausted": ("SYM_FATIGUE", "Fatigue"),
    "fatigue": ("SYM_FATIGUE", "Fatigue"),
    "dizzy": ("SYM_DIZZINESS", "Dizziness"),
    "dizziness": ("SYM_DIZZINESS", "Dizziness"),
    "faint": ("SYM_PRESYNCOPE", "Presyncope / near-fainting"),
    "headache": ("SYM_HEADACHE", "Headache"),
    "fever": ("SYM_FEVER", "Fever"),
    "melena": ("SYM_MELENA", "Melena (black stools)"),
    "cough": ("SYM_COUGH", "Cough"),
    "nausea": ("SYM_NAUSEA", "Nausea"),
    "vomiting": ("SYM_VOMITING", "Vomiting"),
    "palpitations": ("SYM_PALPITATIONS", "Palpitations"),
    "sweating": ("SYM_DIAPHORESIS", "Diaphoresis / sweating"),
    "edema": ("SYM_EDEMA", "Edema"),
    # Medications
    "metformin": ("MED_METFORMIN", "Medication: metformin"),
    "alogliptin": ("MED_ALOGLIPTIN", "Medication: alogliptin"),
    "metoprolol": ("MED_METOPROLOL", "Medication: metoprolol"),
    "anticoagulant": ("MED_ANTICOAGULANT", "Medication: anticoagulant"),
    "noac": ("MED_NOAC", "Medication: NOAC"),
    # Antecedents
    "kidney": ("ANT_CKD", "Antecedent: kidney disease"),
    "renal": ("ANT_CKD", "Antecedent: kidney disease"),
    "diabetes": ("ANT_DIABETES", "Antecedent: diabetes"),
    "anemia": ("ANT_ANEMIA_HX", "Antecedent: prior anemia"),
}

# Negation words that, if found within 5 tokens before a keyword, negate it.
NEGATION_WORDS: frozenset[str] = frozenset(
    {"no", "not", "without", "denies", "denied", "negative", "absent", "never"}
)


class StateExtractor:
    """Extracts ClinicalFact objects from a ConversationTurn."""

    def __init__(self, evidence_vocab: dict[str, EvidenceVocabEntry] | None = None) -> None:
        """
        Args:
            evidence_vocab: Optional mapping from evidence_id to EvidenceVocabEntry,
                used when processing revealed_evidence_ids. If None, is_antecedent
                defaults to False.
        """
        self._vocab: dict[str, EvidenceVocabEntry] = evidence_vocab or {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def extract_from_turn(
        self, turn: ConversationTurn, turn_index: int
    ) -> list[ClinicalFact]:
        """Extract ClinicalFact objects from a ConversationTurn.

        If turn.revealed_evidence_ids is non-empty, create one ClinicalFact per id
        with status='positive', confidence=1.0.
        Otherwise, scan turn.text for keyword matches with negation detection.
        """
        now = datetime.now(timezone.utc).isoformat()

        if turn.revealed_evidence_ids:
            return self._extract_from_evidence_ids(
                turn.revealed_evidence_ids, turn_index, now
            )

        return self._extract_from_text(turn.text, turn_index, now)

    @staticmethod
    def classify_fact_type(fact_id: str) -> str:
        """Returns 'symptom', 'medication', or 'antecedent' based on fact_id prefix."""
        if fact_id.startswith("MED_"):
            return "medication"
        if fact_id.startswith("ANT_"):
            return "antecedent"
        return "symptom"

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _extract_from_evidence_ids(
        self,
        evidence_ids: list[str],
        turn_index: int,
        timestamp: str,
    ) -> list[ClinicalFact]:
        facts: list[ClinicalFact] = []
        for token in evidence_ids:
            evid_id = token.split("_@_")[0] if "_@_" in token else token
            entry = self._vocab.get(evid_id)
            is_antecedent = entry.is_antecedent if entry else False
            description = entry.name if entry else evid_id

            facts.append(
                ClinicalFact(
                    fact_id=token,
                    description=description,
                    status="positive",
                    source_turn=turn_index,
                    timestamp=timestamp,
                    confidence=1.0,
                    is_antecedent=is_antecedent,
                )
            )
        return facts

    def _extract_from_text(
        self,
        text: str,
        turn_index: int,
        timestamp: str,
    ) -> list[ClinicalFact]:
        """Keyword scan with 5-token negation window."""
        if not text or not text.strip():
            return []

        lower_text = text.lower()
        found: dict[str, ClinicalFact] = {}  # fact_id → ClinicalFact (dedup)

        # Sort keywords longest-first so multi-word phrases match before sub-phrases
        sorted_keywords = sorted(KEYWORD_MAP.keys(), key=len, reverse=True)

        for keyword in sorted_keywords:
            fact_id, description = KEYWORD_MAP[keyword]
            if fact_id in found:
                continue  # already extracted by a longer keyword

            idx = lower_text.find(keyword)
            while idx != -1:
                status = self._check_negation(lower_text, idx)
                is_antecedent = fact_id.startswith("ANT_")
                found[fact_id] = ClinicalFact(
                    fact_id=fact_id,
                    description=description,
                    status=status,
                    source_turn=turn_index,
                    timestamp=timestamp,
                    confidence=0.7,
                    is_antecedent=is_antecedent,
                )
                break  # only first occurrence needed per keyword

        return list(found.values())

    @staticmethod
    def _check_negation(text: str, keyword_idx: int) -> str:
        """Return 'negative' if a negation word appears within 5 tokens before keyword."""
        # Extract the 5-word window before the keyword position
        prefix = text[:keyword_idx]
        words = prefix.split()
        window = words[-5:]  # up to 5 words before keyword
        if any(w.strip(".,;:!?") in NEGATION_WORDS for w in window):
            return "negative"
        return "positive"
