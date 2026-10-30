"""
decision_gate.py — Rule-based gate that maps CoherenceFlag lists to a decision string.

Decisions: PASS, CLARIFY, WARN, REFUSE.
Rule table follows plan.md §3.10 exactly.
"""
from __future__ import annotations

from models import CoherenceFlag


class DecisionGate:
    """Evaluates a list of CoherenceFlags and returns (decision, reasoning)."""

    REFUSE_CHECKS: frozenset[str] = frozenset({"SYCOPHANCY", "MED_TARGET_MISMATCH"})
    WARN_CHECKS: frozenset[str] = frozenset({"FACT_CONTRADICTION", "STALE_STATE"})

    def evaluate(
        self, flags: list[CoherenceFlag]
    ) -> tuple[str, str]:
        """Apply rule table and return (decision_str, reasoning_str).

        Rule table (checked in order):
        1. 0 flags                                     → PASS
        2. ≥1 ERROR with check_id in REFUSE_CHECKS     → REFUSE
        3. ≥1 ERROR with check_id in WARN_CHECKS       → WARN
        4. ≥1 WARNING (no ERROR)                       → CLARIFY
        5. ≥1 unclassified ERROR (not refuse/warn)     → CLARIFY
        Special: EVIDENCE_MED_MISMATCH alone           → CLARIFY
        """
        if not flags:
            return "PASS", "No coherence issues detected."

        errors = [f for f in flags if f.severity == "ERROR"]
        warnings = [f for f in flags if f.severity == "WARNING"]

        # Rule 2: REFUSE
        refuse_triggers = [f for f in errors if f.check_id in self.REFUSE_CHECKS]
        if refuse_triggers:
            flag = refuse_triggers[0]
            return (
                "REFUSE",
                f"Blocking response: {flag.description}",
            )

        # Rule 3: WARN
        warn_triggers = [f for f in errors if f.check_id in self.WARN_CHECKS]
        if warn_triggers:
            flag = warn_triggers[0]
            return (
                "WARN",
                f"Clinical incoherence detected: {flag.description}",
            )

        # Rule 4: CLARIFY (WARNING-level flags only)
        if warnings and not errors:
            flag = warnings[0]
            return (
                "CLARIFY",
                f"Clarification needed: {flag.description}",
            )

        # Rule 5: any remaining errors (unclassified) → CLARIFY
        if errors:
            flag = errors[0]
            return (
                "CLARIFY",
                f"Unclassified issue: {flag.description}",
            )

        # Fallback (only warnings were present, already handled above)
        return "CLARIFY", f"Issue detected: {flags[0].description}"
