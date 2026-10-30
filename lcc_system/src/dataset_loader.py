"""
dataset_loader.py — Single point of file I/O for all external datasets.

Loads DailyMed evidence records, RxNorm concepts/relationships/aliases, DDXPlus
condition and evidence metadata, and generates synthetic DDXPlus-format patient cases.

Error handling policy: missing/malformed files → log warning to stderr, return [] or {}.
Never raise on missing data.
"""
from __future__ import annotations

import csv
import json
import random
import sys
import copy
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from models import (
    ConditionMeta,
    EvidenceRecord,
    EvidenceVocabEntry,
    PatientCase,
    RxNormConcept,
)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
# BASE_DIR resolves to c:\Users\91895\OneDrive\Desktop\Longitudinal-Clinical-Coherence
# i.e.  lcc_system/src/dataset_loader.py → .parent = src/ → .parent = lcc_system/ → .parent = workspace root
_SRC_DIR = Path(__file__).parent          # lcc_system/src/
_LCC_DIR = _SRC_DIR.parent               # lcc_system/
BASE_DIR = _LCC_DIR.parent               # workspace root


class DatasetLoader:
    """Loads all external datasets and generates synthetic DDXPlus patient cases."""

    # -----------------------------------------------------------------------
    # File paths (class-level, resolved at import time relative to BASE_DIR)
    # -----------------------------------------------------------------------
    DAILYMED_PATH = BASE_DIR / "dailymed_corpus_final" / "medication_evidence.jsonl"
    RXNORM_CONCEPTS_PATH = BASE_DIR / "rxnorm_capstone" / "data" / "concepts.csv"
    RXNORM_RELS_PATH = BASE_DIR / "rxnorm_capstone" / "data" / "relationships.csv"
    RXNORM_ALIASES_PATH = BASE_DIR / "rxnorm_capstone" / "data" / "input_aliases.csv"
    CONDITION_MAP_PATH = (
        BASE_DIR
        / "DDXPlus_Audit_Share_Package"
        / "audit_output"
        / "condition_mapping_summary.csv"
    )
    EVIDENCE_MAP_PATH = (
        BASE_DIR
        / "DDXPlus_Audit_Share_Package"
        / "audit_output"
        / "evidence_mapping_summary.csv"
    )

    # -----------------------------------------------------------------------
    # Synthetic case templates
    # (pathology, severity, base_age, base_sex, initial_evidence,
    #  evidence_pool, differential_pool)
    # -----------------------------------------------------------------------
    CASE_TEMPLATES: list[tuple] = [
        (
            "Anemia",
            4,
            55,
            "F",
            "E_154",
            [
                "E_154", "E_76", "E_82", "E_140", "E_91",
                "E_159", "E_53", "E_56_@_2", "E_7", "E_24",
                "E_208", "E_55_@_V_123", "E_57_@_V_123",
            ],
            [("Anemia", 0.35), ("Atrial fibrillation", 0.15), ("Cluster headache", 0.10)],
        ),
        (
            "Possible NSTEMI / STEMI",
            1,
            62,
            "M",
            "E_53",
            [
                "E_53", "E_54_@_V_71", "E_55_@_V_14", "E_57_@_V_123",
                "E_56_@_7", "E_91", "E_159", "E_24",
                "E_76", "E_82", "E_7", "E_208", "E_140",
            ],
            [
                ("Possible NSTEMI / STEMI", 0.40),
                ("Unstable angina", 0.25),
                ("Pericarditis", 0.15),
            ],
        ),
        (
            "Pneumonia",
            3,
            18,
            "F",
            "E_91",
            [
                "E_91", "E_53", "E_56_@_3", "E_159", "E_82",
                "E_208", "E_7", "E_24", "E_76",
                "E_140", "E_154", "E_55_@_V_123", "E_57_@_V_123",
            ],
            [
                ("Pneumonia", 0.38),
                ("Bronchitis", 0.20),
                ("Influenza", 0.18),
            ],
        ),
        (
            "GERD",
            3,
            45,
            "M",
            "E_53",
            [
                "E_53", "E_54_@_V_112", "E_55_@_V_123", "E_56_@_2",
                "E_91", "E_140", "E_24",
                "E_7", "E_76", "E_82", "E_159", "E_208", "E_154",
            ],
            [
                ("GERD", 0.42),
                ("Boerhaave", 0.18),
                ("Unstable angina", 0.12),
            ],
        ),
        (
            "Atrial fibrillation",
            3,
            68,
            "M",
            "E_82",
            [
                "E_82", "E_76", "E_53", "E_56_@_4", "E_159",
                "E_91", "E_154", "E_24", "E_7",
                "E_208", "E_140", "E_55_@_V_14", "E_57_@_V_123",
            ],
            [
                ("Atrial fibrillation", 0.45),
                ("Possible NSTEMI / STEMI", 0.15),
                ("Anemia", 0.12),
            ],
        ),
    ]

    # -----------------------------------------------------------------------
    # Public load methods
    # -----------------------------------------------------------------------

    def load_dailymed_evidence(self) -> list[EvidenceRecord]:
        """Load medication_evidence.jsonl. Returns [] on any file error."""
        records: list[EvidenceRecord] = []
        try:
            with open(self.DAILYMED_PATH, encoding="utf-8") as fh:
                for lineno, line in enumerate(fh, start=1):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        obj: dict[str, Any] = json.loads(line)
                    except json.JSONDecodeError as exc:
                        print(
                            f"[DatasetLoader] WARNING: JSONL parse error line {lineno}: {exc}",
                            file=sys.stderr,
                        )
                        continue
                    records.append(
                        EvidenceRecord(
                            evidence_id=obj.get("evidence_id", ""),
                            active_ingredient=obj.get("active_ingredient", ""),
                            product_name=obj.get("product_name", ""),
                            all_active_ingredients=obj.get("all_active_ingredients", ""),
                            section_name=obj.get("section_name", ""),
                            evidence_text=obj.get("evidence_text", ""),
                            source_url=obj.get("source_url", ""),
                            evidence_scope=obj.get("evidence_scope", ""),
                            verification_status=obj.get("verification_status", ""),
                            notes=obj.get("notes", ""),
                        )
                    )
        except OSError as exc:
            print(
                f"[DatasetLoader] WARNING: Cannot open DailyMed JSONL: {exc}",
                file=sys.stderr,
            )
            return []
        return records

    def load_rxnorm_concepts(self) -> list[RxNormConcept]:
        """Load rxnorm concepts.csv. Returns [] on any file error."""
        concepts: list[RxNormConcept] = []
        try:
            with open(self.RXNORM_CONCEPTS_PATH, encoding="utf-8", newline="") as fh:
                reader = csv.DictReader(fh)
                for row in reader:
                    concepts.append(
                        RxNormConcept(
                            rxcui=row.get("rxcui", ""),
                            rxnorm_name=row.get("rxnorm_name", ""),
                            tty=row.get("tty", ""),
                            concept_type=row.get("concept_type", ""),
                            ingredient_names=row.get("ingredient_names", ""),
                            ingredient_rxcuis=row.get("ingredient_rxcuis", ""),
                        )
                    )
        except OSError as exc:
            print(
                f"[DatasetLoader] WARNING: Cannot open RxNorm concepts CSV: {exc}",
                file=sys.stderr,
            )
            return []
        return concepts

    def load_rxnorm_relationships(self) -> list[dict]:
        """Load rxnorm relationships.csv. Returns [] on any file error."""
        rows: list[dict] = []
        try:
            with open(self.RXNORM_RELS_PATH, encoding="utf-8", newline="") as fh:
                reader = csv.DictReader(fh)
                for row in reader:
                    rows.append(dict(row))
        except OSError as exc:
            print(
                f"[DatasetLoader] WARNING: Cannot open RxNorm relationships CSV: {exc}",
                file=sys.stderr,
            )
            return []
        return rows

    def load_rxnorm_aliases(self) -> list[dict]:
        """Load rxnorm input_aliases.csv. Returns [] on any file error."""
        rows: list[dict] = []
        try:
            with open(self.RXNORM_ALIASES_PATH, encoding="utf-8", newline="") as fh:
                reader = csv.DictReader(fh)
                for row in reader:
                    rows.append(dict(row))
        except OSError as exc:
            print(
                f"[DatasetLoader] WARNING: Cannot open RxNorm aliases CSV: {exc}",
                file=sys.stderr,
            )
            return []
        return rows

    def load_condition_metadata(self) -> dict[str, ConditionMeta]:
        """Load condition_mapping_summary.csv. Returns {} on any file error."""
        meta: dict[str, ConditionMeta] = {}
        try:
            with open(self.CONDITION_MAP_PATH, encoding="utf-8", newline="") as fh:
                reader = csv.DictReader(fh)
                for row in reader:
                    cid = row.get("condition_id", "").strip()
                    if not cid:
                        continue
                    try:
                        severity = int(row.get("severity", 3))
                        symptom_count = int(row.get("symptom_count", 0))
                        antecedent_count = int(row.get("antecedent_count", 0))
                    except (ValueError, TypeError):
                        severity, symptom_count, antecedent_count = 3, 0, 0
                    meta[cid] = ConditionMeta(
                        condition_id=cid,
                        icd10_id=row.get("icd10_id", ""),
                        severity=severity,
                        symptom_count=symptom_count,
                        antecedent_count=antecedent_count,
                    )
        except OSError as exc:
            print(
                f"[DatasetLoader] WARNING: Cannot open condition mapping CSV: {exc}",
                file=sys.stderr,
            )
            return {}
        return meta

    def load_evidence_vocab(self) -> dict[str, EvidenceVocabEntry]:
        """Load evidence_mapping_summary.csv. Returns {} on any file error.

        'is_antecedent' column is the string 'true'/'false' — converted to bool.
        'possible_values' dict is parsed from 'sample_values' column which has the
        format 'V_K: text; V_K2: text2'.
        """
        vocab: dict[str, EvidenceVocabEntry] = {}
        try:
            with open(self.EVIDENCE_MAP_PATH, encoding="utf-8", newline="") as fh:
                reader = csv.DictReader(fh)
                for row in reader:
                    eid = row.get("evidence_id", "").strip()
                    if not eid:
                        continue

                    is_antecedent = row.get("is_antecedent", "false").strip().lower() == "true"

                    # Parse 'sample_values' → {val_key: text} dict
                    possible_values: dict[str, str] = {}
                    sample_raw = row.get("sample_values", "").strip()
                    if sample_raw:
                        # Format: "V_123: nowhere; V_14: iliac wing(R); V_15: iliac wing(L)"
                        for segment in sample_raw.split(";"):
                            segment = segment.strip()
                            if ":" in segment:
                                key_part, _, val_part = segment.partition(":")
                                possible_values[key_part.strip()] = val_part.strip()

                    vocab[eid] = EvidenceVocabEntry(
                        evidence_id=eid,
                        name=row.get("name", eid),
                        data_type=row.get("data_type", "B"),
                        is_antecedent=is_antecedent,
                        question_en=row.get("question_en", ""),
                        default_value=row.get("default_value", ""),
                        possible_values=possible_values,
                    )
        except OSError as exc:
            print(
                f"[DatasetLoader] WARNING: Cannot open evidence mapping CSV: {exc}",
                file=sys.stderr,
            )
            return {}
        return vocab

    # -----------------------------------------------------------------------
    # Synthetic case generation
    # -----------------------------------------------------------------------

    def generate_synthetic_cases(self, n: int = 25) -> list[PatientCase]:
        """Generate n synthetic DDXPlus-format patient cases.

        Uses random.seed(20261027) for reproducibility. Iterates over the 5 base
        templates (by index modulo 5), varying age ±randint(0,8) and alternating sex.
        Draws a random subset of each template's evidence_pool (keeping >= 8 items).
        Populates PatientCase.severity from condition_mapping_summary.csv.
        """
        rng = random.Random(20261027)

        condition_meta = self.load_condition_metadata()

        cases: list[PatientCase] = []
        for i in range(n):
            tmpl = self.CASE_TEMPLATES[i % len(self.CASE_TEMPLATES)]
            pathology, base_severity, base_age, base_sex, initial_ev, ev_pool, diff_pool = tmpl

            # Age variation: ±randint(0,8)
            age_delta = rng.randint(0, 8)
            age_sign = 1 if rng.random() < 0.5 else -1
            age = max(1, base_age + age_sign * age_delta)

            # Sex alternation: flip for odd-indexed cases within same template tier
            template_instance = i // len(self.CASE_TEMPLATES)
            sex = base_sex if template_instance % 2 == 0 else ("M" if base_sex == "F" else "F")

            # Draw a random subset of evidence_pool; keep at least 8 items
            pool_size = len(ev_pool)
            min_keep = min(8, pool_size)
            max_keep = pool_size
            num_to_keep = rng.randint(min_keep, max_keep)
            # Always include initial_evidence first
            pool_without_initial = [e for e in ev_pool if e != initial_ev]
            chosen_extras = rng.sample(
                pool_without_initial,
                min(num_to_keep - 1, len(pool_without_initial)),
            )
            evidences = [initial_ev] + chosen_extras

            # Ensure we have at least 8 items; pad from pool if short
            while len(evidences) < 8 and len(evidences) < len(ev_pool):
                for e in ev_pool:
                    if e not in evidences:
                        evidences.append(e)
                    if len(evidences) >= 8:
                        break

            # Differential diagnosis with minor probability jitter (±0.02)
            differential: list[tuple[str, float]] = []
            for cond_name, base_prob in diff_pool:
                jitter = rng.uniform(-0.02, 0.02)
                prob = round(max(0.01, min(0.99, base_prob + jitter)), 4)
                differential.append((cond_name, prob))

            # Severity from condition metadata, fall back to template's base_severity
            cond_m = condition_meta.get(pathology)
            severity = cond_m.severity if cond_m else base_severity

            cases.append(
                PatientCase(
                    case_id=f"SYNTHETIC_{i:03d}",
                    age=age,
                    sex=sex,
                    initial_evidence=initial_ev,
                    evidences=evidences,
                    pathology=pathology,
                    differential_diagnosis=differential,
                    severity=severity,
                )
            )

        return cases

    # -----------------------------------------------------------------------
    # Convenience aggregator
    # -----------------------------------------------------------------------

    def get_all_data(self) -> dict[str, Any]:
        """Load and return all datasets as a single dict."""
        return {
            "cases": self.generate_synthetic_cases(),
            "dailymed": self.load_dailymed_evidence(),
            "concepts": self.load_rxnorm_concepts(),
            "relationships": self.load_rxnorm_relationships(),
            "aliases": self.load_rxnorm_aliases(),
            "conditions": self.load_condition_metadata(),
            "evidences": self.load_evidence_vocab(),
        }
