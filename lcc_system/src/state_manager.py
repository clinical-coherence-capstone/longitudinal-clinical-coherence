"""
state_manager.py — Versioned, append-only patient state store.

Each update() call deep-copies the current state to history before merging new facts.
Contradictions (fact status reversals) are recorded and exposed for coherence checking.
"""
from __future__ import annotations

import copy
from datetime import datetime, timezone

from models import ClinicalFact, PatientState, StateVersion


class StateManager:
    """Maintains versioned patient state across conversation turns."""

    def __init__(self, case_id: str) -> None:
        self.case_id = case_id
        self.current_version: int = 0
        self.history: list[StateVersion] = []
        self._contradictions: list[tuple[str, str, str]] = []  # (fact_id, old_status, new_status)
        self.current_state: PatientState = PatientState(
            case_id=case_id,
            version=0,
            turn_number=0,
            timestamp=datetime.now(timezone.utc).isoformat(),
            facts={},
            revealed_evidence_ids=[],
            medications=[],
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def update(self, turn_index: int, new_facts: list[ClinicalFact]) -> PatientState:
        """Merge new_facts into current_state, detect contradictions, increment version.

        Steps:
        1. Deep-copy current_state → old_state.
        2. Snapshot old_state → StateVersion appended to history.
        3. Merge each fact (add / update / contradiction).
        4. Collect medication names from MED_* facts.
        5. Increment version.
        6. Return updated current_state.
        """
        old_state = copy.deepcopy(self.current_state)
        change_parts: list[str] = []

        # Snapshot
        snapshot = StateVersion(
            version=old_state.version,
            turn_number=old_state.turn_number,
            snapshot=old_state,
            change_summary="",  # filled below
        )

        # Merge facts
        for fact in new_facts:
            existing = self.current_state.facts.get(fact.fact_id)
            if existing is None:
                # New fact
                self.current_state.facts[fact.fact_id] = copy.deepcopy(fact)
                change_parts.append(f"Added: {fact.fact_id}={fact.status}")
            else:
                if existing.status != fact.status and existing.status != "unknown":
                    # Contradiction / correction
                    self._contradictions.append(
                        (fact.fact_id, existing.status, fact.status)
                    )
                    change_parts.append(
                        f"Contradiction: {fact.fact_id} {existing.status}→{fact.status}"
                    )
                elif existing.status != fact.status:
                    change_parts.append(
                        f"Updated: {fact.fact_id} {existing.status}→{fact.status}"
                    )
                # Update status regardless
                existing.status = fact.status
                existing.confidence = max(existing.confidence, fact.confidence)
                existing.source_turn = fact.source_turn
                existing.timestamp = fact.timestamp

            # Track revealed evidence ids
            if fact.fact_id not in self.current_state.revealed_evidence_ids:
                self.current_state.revealed_evidence_ids.append(fact.fact_id)

            # Track medications
            if fact.fact_id.startswith("MED_") or fact.fact_id.startswith("med_"):
                if fact.description not in self.current_state.medications:
                    self.current_state.medications.append(fact.description)

        # Increment version
        self.current_version += 1
        self.current_state.version = self.current_version
        self.current_state.turn_number = turn_index
        self.current_state.timestamp = datetime.now(timezone.utc).isoformat()

        # Fill snapshot change_summary
        snapshot.change_summary = "; ".join(change_parts) if change_parts else "No changes."
        self.history.append(snapshot)

        return self.current_state

    def get_version(self, n: int) -> PatientState | None:
        """Return the PatientState snapshot after the n-th update (1-indexed)."""
        if n < 1 or n > len(self.history):
            return None
        # history[n-1] is the snapshot BEFORE the n-th update, so the state AFTER
        # the n-th update is current_state if n==current_version, else history[n].
        if n == len(self.history) and n == self.current_version:
            return self.current_state
        # The snapshot at history[n-1] is the state BEFORE update n.
        # The state AFTER update n is the snapshot at history[n] if it exists.
        if n < len(self.history):
            return self.history[n].snapshot
        return self.current_state

    def get_contradictions(self) -> list[tuple[str, str, str]]:
        """Return list of (fact_id, old_status, new_status) contradiction tuples."""
        return list(self._contradictions)

    def get_fact_history(self, fact_id: str) -> list[ClinicalFact]:
        """Return all historical ClinicalFact snapshots for a given fact_id."""
        history: list[ClinicalFact] = []
        for sv in self.history:
            fact = sv.snapshot.facts.get(fact_id)
            if fact is not None:
                history.append(copy.deepcopy(fact))
        # Also include current
        current_fact = self.current_state.facts.get(fact_id)
        if current_fact is not None:
            history.append(copy.deepcopy(current_fact))
        return history

    def get_current_state(self) -> PatientState:
        """Return the current (latest) PatientState."""
        return self.current_state
