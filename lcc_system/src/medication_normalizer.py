"""
medication_normalizer.py — Maps free-text medication mentions to RxNorm concepts.

Resolution chain: exact match → alias match → substring match → unresolved.
Ingredient-level (tty="IN") matches preferred; brand/product accepted at lower confidence.
"""
from __future__ import annotations

from models import MedicationNormResult, RxNormConcept
from dataset_loader import DatasetLoader


class MedicationNormalizer:
    """Normalizes free-text medication names to RxNorm identifiers."""

    def __init__(self, loader: DatasetLoader) -> None:
        concepts: list[RxNormConcept] = loader.load_rxnorm_concepts()
        aliases: list[dict] = loader.load_rxnorm_aliases()
        relationships: list[dict] = loader.load_rxnorm_relationships()

        # Step 1 — exact match: lower(rxnorm_name) → RxNormConcept
        self._exact: dict[str, RxNormConcept] = {
            c.rxnorm_name.lower(): c for c in concepts
        }

        # Step 2 — alias match: lower(input_name) → first candidate_rxcui string
        self._aliases: dict[str, str] = {}
        for row in aliases:
            input_name = row.get("input_name", "").lower()
            candidate_rxcuis = row.get("candidate_rxcuis", "")
            if input_name and candidate_rxcuis:
                first_rxcui = candidate_rxcuis.split(";")[0].strip()
                if first_rxcui:
                    self._aliases[input_name] = first_rxcui

        # Step 3 — substring search: list of (lower_name, concept)
        self._all_names: list[tuple[str, RxNormConcept]] = [
            (c.rxnorm_name.lower(), c) for c in concepts
        ]

        # Reverse lookup: rxcui → RxNormConcept
        self._by_rxcui: dict[str, RxNormConcept] = {c.rxcui: c for c in concepts}

        # Store relationships for get_ingredients
        self._relationships: list[dict] = relationships

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def normalize(self, text: str) -> MedicationNormResult:
        """Resolve free-text medication name to RxNorm via exact→alias→substring chain.

        Returns:
            MedicationNormResult with match_method one of:
            "exact" (confidence 1.0 for IN, 0.9 otherwise),
            "alias" (confidence 0.85),
            "substring" (confidence 0.65),
            "unresolved" (confidence 0.0).
        """
        if not text or not text.strip():
            return MedicationNormResult(
                input_text=text,
                rxcui=None,
                rxnorm_name=None,
                tty=None,
                match_method="unresolved",
                confidence=0.0,
            )

        query = text.strip().lower()

        # --- Step 1: Exact match ---
        if query in self._exact:
            c = self._exact[query]
            confidence = 1.0 if c.tty == "IN" else 0.9
            return MedicationNormResult(
                input_text=text,
                rxcui=c.rxcui,
                rxnorm_name=c.rxnorm_name,
                tty=c.tty,
                match_method="exact",
                confidence=confidence,
            )

        # --- Step 2: Alias match ---
        if query in self._aliases:
            rxcui = self._aliases[query]
            c = self._by_rxcui.get(rxcui)
            if c:
                return MedicationNormResult(
                    input_text=text,
                    rxcui=c.rxcui,
                    rxnorm_name=c.rxnorm_name,
                    tty=c.tty,
                    match_method="alias",
                    confidence=0.85,
                )

        # --- Step 3: Substring match ---
        matches: list[tuple[str, RxNormConcept]] = [
            (name, c) for name, c in self._all_names if query in name
        ]
        if matches:
            # Prefer IN tty; then take first alphabetically for determinism
            ing_matches = [m for m in matches if m[1].tty == "IN"]
            best_name, best_c = ing_matches[0] if ing_matches else matches[0]
            return MedicationNormResult(
                input_text=text,
                rxcui=best_c.rxcui,
                rxnorm_name=best_c.rxnorm_name,
                tty=best_c.tty,
                match_method="substring",
                confidence=0.65,
            )

        # --- Unresolved ---
        return MedicationNormResult(
            input_text=text,
            rxcui=None,
            rxnorm_name=None,
            tty=None,
            match_method="unresolved",
            confidence=0.0,
        )

    def get_ingredients(self, rxcui: str) -> list[RxNormConcept]:
        """For a MIN (multi-ingredient) concept, return its component IN concepts.

        Traverses relationships where rela='has_part' and subject_rxcui==rxcui.
        Returns a list of RxNormConcept objects for the object_rxcuis.
        """
        ingredients: list[RxNormConcept] = []
        for row in self._relationships:
            if row.get("rela") == "has_part" and row.get("subject_rxcui") == rxcui:
                obj_rxcui = row.get("object_rxcui", "")
                concept = self._by_rxcui.get(obj_rxcui)
                if concept:
                    ingredients.append(concept)
        return ingredients
