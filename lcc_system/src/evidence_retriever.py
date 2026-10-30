"""
evidence_retriever.py — Retrieves relevant DailyMed evidence records for a medication.

Filters by ingredient name overlap against active_ingredient / all_active_ingredients,
then ranks by clinical section priority (BOXED WARNING highest).
"""
from __future__ import annotations

from models import EvidenceRecord, PatientState
from dataset_loader import DatasetLoader
from medication_normalizer import MedicationNormalizer


# ---------------------------------------------------------------------------
# Section priority (lower number = higher priority = returned first)
# All 21 unique section_name values from medication_evidence.jsonl are listed.
# ---------------------------------------------------------------------------
SECTION_PRIORITY: dict[str, int] = {
    "BOXED WARNING": 1,
    "4 CONTRAINDICATIONS": 2,
    "5.1 Lactic Acidosis": 3,
    "5.3 Heart Failure": 3,
    "5.2 Pancreatitis": 3,
    "5.4 Hypersensitivity Reactions": 3,
    "5.5 Hepatic Effects": 3,
    "5.6 Vitamin B12 Deficiency": 3,
    "5.7 Hypoglycemia with Concomitant Use with Insulin or Insulin Secretagogues": 3,
    "5.8 Severe and Disabling Arthralgia": 3,
    "5.9 Bullous Pemphigoid": 3,
    "1 INDICATIONS AND USAGE": 4,
    "7 DRUG INTERACTIONS: Alcohol": 5,
    "7 DRUG INTERACTIONS: Carbonic Anhydrase Inhibitors": 5,
    "7 DRUG INTERACTIONS: Drugs that Reduce Metformin Clearance": 5,
    "7 DRUG INTERACTIONS: Cytochrome (CYP) P450": 5,
    "2.2 Recommendations for Use in Renal Impairment": 6,
    "2.3 Discontinuation for Iodinated Contrast Imaging Procedures": 6,
    "8.1 Pregnancy": 6,
    "2.1 Recommended Dosage": 7,
    "3 DOSAGE FORMS AND STRENGTHS": 8,
}


class EvidenceRetriever:
    """Retrieves DailyMed evidence records relevant to a medication."""

    def __init__(self, loader: DatasetLoader, normalizer: MedicationNormalizer) -> None:
        self.records: list[EvidenceRecord] = loader.load_dailymed_evidence()
        self.normalizer = normalizer

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def retrieve(
        self,
        medication_text: str,
        max_results: int = 5,
    ) -> list[EvidenceRecord]:
        """Retrieve evidence records relevant to the given medication text.

        Steps:
        1. Normalize medication_text via MedicationNormalizer.
        2. If unresolved → return [].
        3. Collect ingredient names to match against:
           - tty=="IN": use rxnorm_name directly.
           - tty=="MIN": call get_ingredients() for component names.
           - other: use rxnorm_name.
        4. Filter records by case-insensitive substring overlap on active_ingredient
           or all_active_ingredients.
        5. Sort by SECTION_PRIORITY ascending (lower = more important).
        6. Return top max_results.
        """
        result = self.normalizer.normalize(medication_text)
        if result.match_method == "unresolved" or result.rxnorm_name is None:
            return []

        ingredient_names = self._get_ingredient_names(result)
        if not ingredient_names:
            return []

        matched: list[EvidenceRecord] = []
        for record in self.records:
            if self._record_matches(record, ingredient_names):
                matched.append(record)

        matched.sort(key=lambda r: SECTION_PRIORITY.get(r.section_name, 9))
        return matched[:max_results]

    def retrieve_for_state(
        self,
        state: PatientState,
        max_results: int = 8,
    ) -> list[EvidenceRecord]:
        """Retrieve evidence for all medications in state.medications.

        Collects and deduplicates records across all medications, returns top
        max_results sorted by section priority.
        """
        seen_ids: set[str] = set()
        all_records: list[EvidenceRecord] = []

        for med_text in state.medications:
            for record in self.retrieve(med_text, max_results=max_results):
                if record.evidence_id not in seen_ids:
                    seen_ids.add(record.evidence_id)
                    all_records.append(record)

        # Also try normalized medication names from facts directly
        # (medications list may hold description strings like "Medication: metformin")
        for med_text in state.medications:
            # Strip "Medication: " prefix if present
            clean = med_text
            if clean.lower().startswith("medication:"):
                clean = clean.split(":", 1)[1].strip()
            if clean != med_text:
                for record in self.retrieve(clean, max_results=max_results):
                    if record.evidence_id not in seen_ids:
                        seen_ids.add(record.evidence_id)
                        all_records.append(record)

        all_records.sort(key=lambda r: SECTION_PRIORITY.get(r.section_name, 9))
        return all_records[:max_results]

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _get_ingredient_names(self, norm_result) -> list[str]:
        """Collect ingredient name strings to match against record fields."""
        if norm_result.tty == "MIN" and norm_result.rxcui:
            ingredients = self.normalizer.get_ingredients(norm_result.rxcui)
            names = [ing.rxnorm_name for ing in ingredients]
            if names:
                return names
        # Fallback: use rxnorm_name of the matched concept
        if norm_result.rxnorm_name:
            return [norm_result.rxnorm_name]
        return []

    @staticmethod
    def _record_matches(record: EvidenceRecord, ingredient_names: list[str]) -> bool:
        """Return True if any ingredient name appears in the record's ingredient fields."""
        active_lower = record.active_ingredient.lower()
        all_lower = record.all_active_ingredients.lower()
        for name in ingredient_names:
            name_lower = name.lower()
            if name_lower in active_lower or name_lower in all_lower:
                return True
        return False
