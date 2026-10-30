"""
demo.py - Command-line demo for the Longitudinal Clinical Coherence (LCC) system.

Runs entirely without an API key using the MockLLMProvider.

Usage:
    python demo.py [--case 0] [--form gradual_reveal] [--verbose] [--eval]
"""
import sys
import argparse
from pathlib import Path

# Add src/ to sys.path so all modules import cleanly from lcc_system/
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Now import all LCC modules
from dataset_loader import DatasetLoader
from conversation_generator import ConversationGenerator
from state_extractor import StateExtractor
from state_manager import StateManager
from medication_normalizer import MedicationNormalizer
from evidence_retriever import EvidenceRetriever
from response_generator import ResponseGenerator
from coherence_verifier import CoherenceVerifier
from decision_gate import DecisionGate
from evaluation import Evaluator, SCENARIOS


# ---------------------------------------------------------------------------
# CLI argument parsing
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Longitudinal Clinical Coherence - CLI Demo",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python demo.py                          # default case, gradual reveal\n"
            "  python demo.py --case 2 --verbose       # pneumonia case, verbose\n"
            "  python demo.py --case 2 --form pushback --verbose\n"
            "  python demo.py --eval                   # run evaluation harness\n"
        ),
    )
    parser.add_argument(
        "--case",
        type=int,
        default=0,
        help="Index of the synthetic case to use (0-24, default 0 = Anemia 55F).",
    )
    parser.add_argument(
        "--form",
        type=str,
        default="gradual_reveal",
        choices=["complete", "gradual_reveal", "pushback"],
        help="Conversation form (default: gradual_reveal).",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print fact extraction details after each patient turn.",
    )
    parser.add_argument(
        "--eval",
        action="store_true",
        help="After the demo, run the evaluation harness and print metrics.",
    )
    return parser


# ---------------------------------------------------------------------------
# Main demo flow
# ---------------------------------------------------------------------------

def run_demo(args: argparse.Namespace) -> None:
    # ------------------------------------------------------------------
    # Step 1: Banner
    # ------------------------------------------------------------------
    print("=" * 70)
    print("  Longitudinal Clinical Coherence (LCC) System - CLI Demo")
    print("  NOTE: This system is a research prototype. It is NOT clinically safe.")
    print("=" * 70)
    print()

    # ------------------------------------------------------------------
    # Step 2: Load data
    # ------------------------------------------------------------------
    print("Loading datasets...")
    loader = DatasetLoader()
    cases = loader.generate_synthetic_cases(25)

    n_evidence = len(loader.load_dailymed_evidence())
    n_concepts = len(loader.load_rxnorm_concepts())
    print(f"  Loaded {len(cases)} synthetic cases, {n_evidence} DailyMed evidence records, "
          f"{n_concepts} RxNorm concepts.")
    print()

    # ------------------------------------------------------------------
    # Step 3: Select case
    # ------------------------------------------------------------------
    if args.case < 0 or args.case >= len(cases):
        print(f"[WARNING] Case index {args.case} out of range (0-{len(cases)-1}). Using 0.")
        args.case = 0
    case = cases[args.case]

    # ------------------------------------------------------------------
    # Step 4: Case header
    # ------------------------------------------------------------------
    gen_conv = ConversationGenerator(loader)
    chief_verbalized = gen_conv.verbalize(case.initial_evidence)
    sex_str = "Female" if case.sex == "F" else "Male"

    print("-" * 70)
    print(f"  CASE: {case.case_id}")
    print(f"  Age: {case.age}   Sex: {sex_str}")
    print(f"  Chief complaint: {chief_verbalized}")
    print(f"  Pathology: [HIDDEN]   Severity: {case.severity}/5")
    print(f"  Conversation form: {args.form}")
    print("-" * 70)
    print()

    # ------------------------------------------------------------------
    # Step 5: Generate conversation
    # ------------------------------------------------------------------
    conversation = gen_conv.generate_conversation(case, form=args.form)
    total_turns = len(conversation.turns)
    patient_turns = sum(1 for t in conversation.turns if t.speaker == "patient")
    print(f"Generated conversation: {total_turns} total turns ({patient_turns} patient turns).")
    print()

    # ------------------------------------------------------------------
    # Step 6: Initialize pipeline components
    # ------------------------------------------------------------------
    state_manager = StateManager(case.case_id)
    extractor = StateExtractor(loader.load_evidence_vocab())
    normalizer = MedicationNormalizer(loader)
    retriever = EvidenceRetriever(loader, normalizer)
    response_gen = ResponseGenerator(state_manager, retriever, provider="mock")
    verifier = CoherenceVerifier(state_manager, retriever, normalizer)
    gate = DecisionGate()

    # ------------------------------------------------------------------
    # Step 7: Iterate through turns
    # ------------------------------------------------------------------
    turns_list = list(conversation.turns)

    def generate_and_print_response(turn_index: int) -> None:
        """Generate a system response for the current state and print it."""
        current_state = state_manager.get_current_state()
        if current_state.version == 0:
            return  # No patient data yet

        response_text, evidence_used = response_gen.generate_response(conversation)
        flags = verifier.verify(response_text, evidence_used, turn_index, conversation)
        decision, reasoning = gate.evaluate(flags)

        print(f"  [RESPONSE]: {response_text}")
        print()
        print(f"  [DECISION]: {decision} - {reasoning}")

        if flags:
            print("  [FLAGS]:")
            for flag in flags:
                print(f"    [{flag.severity}] {flag.check_id}: {flag.description}")

        print()

    for idx, turn in enumerate(turns_list):
        print(f"--- Turn {turn.turn_index} [{turn.speaker.upper()}] ---")

        # Show injection marker if this turn was injected
        if turn.injection.get("is_injected"):
            etype = turn.injection.get("error_type", "?")
            print(f"  [INJECTED: {etype}]")

        print(f"  {turn.text}")
        print()

        if turn.speaker == "patient":
            # Extract facts and update state
            new_facts = extractor.extract_from_turn(turn, turn.turn_index)
            state_manager.update(turn.turn_index, new_facts)

            if args.verbose and new_facts:
                print("  [FACTS EXTRACTED]")
                for fact in new_facts:
                    marker = "+" if fact.status == "positive" else ("-" if fact.status == "negative" else "?")
                    print(f"    [{marker}] {fact.fact_id}: {fact.description} "
                          f"(status={fact.status}, confidence={fact.confidence:.0%}, "
                          f"antecedent={fact.is_antecedent})")
                print()

            # If this is the last turn and it's a patient turn (e.g. pushback),
            # generate a doctor response to ensure FLAGS are shown
            is_last_turn = (idx == len(turns_list) - 1)
            if is_last_turn:
                print(f"--- [SYSTEM RESPONSE after Turn {turn.turn_index}] ---")
                generate_and_print_response(turn.turn_index)

        elif turn.speaker == "doctor":
            # Generate a system response at each doctor turn
            generate_and_print_response(turn.turn_index)

    # ------------------------------------------------------------------
    # Step 8: Final state summary
    # ------------------------------------------------------------------
    final_state = state_manager.get_current_state()
    print("=" * 70)
    print(f"=== Final Patient State (Turn {final_state.turn_number}, "
          f"State v{final_state.version}) ===")
    print("=" * 70)

    if final_state.facts:
        # Group by category
        symptoms = {k: v for k, v in final_state.facts.items()
                    if not v.is_antecedent and not k.startswith("MED_")}
        meds = {k: v for k, v in final_state.facts.items() if k.startswith("MED_")}
        antecedents = {k: v for k, v in final_state.facts.items() if v.is_antecedent}

        if symptoms:
            print("\n  Symptoms:")
            for fact_id, fact in symptoms.items():
                status_marker = "+" if fact.status == "positive" else ("-" if fact.status == "negative" else "?")
                print(f"    [{status_marker}] {fact_id}: {fact.description} "
                      f"({fact.status}, {fact.confidence:.0%})")

        if meds:
            print("\n  Medications:")
            for fact_id, fact in meds.items():
                print(f"    [M] {fact_id}: {fact.description} ({fact.status})")

        if antecedents:
            print("\n  Antecedents:")
            for fact_id, fact in antecedents.items():
                status_marker = "+" if fact.status == "positive" else ("-" if fact.status == "negative" else "?")
                print(f"    [{status_marker}] {fact_id}: {fact.description} "
                      f"({fact.status}, {fact.confidence:.0%})")
    else:
        print("  (No facts extracted)")

    contradictions = state_manager.get_contradictions()
    if contradictions:
        print(f"\n  Contradictions detected: {len(contradictions)}")
        for fact_id, old_s, new_s in contradictions:
            print(f"    {fact_id}: {old_s} -> {new_s}")

    print()

    # ------------------------------------------------------------------
    # Step 9: Optional evaluation
    # ------------------------------------------------------------------
    if args.eval:
        run_evaluation(loader)


def run_evaluation(loader: DatasetLoader) -> None:
    """Run the evaluation harness and print a metrics table."""
    print("=" * 70)
    print("=== Evaluation Harness - Comparing Baseline vs LCC ===")
    print("=" * 70)
    print(f"Running {len(SCENARIOS)} scenarios...")
    print()

    evaluator = Evaluator(loader)
    results = evaluator.evaluate_all()

    # Print summary metrics
    print(f"{'Metric':<35} {'Value':>10}")
    print("-" * 47)
    print(f"{'Total scenarios':<35} {results['total']:>10}")
    print(f"{'Correct (LCC matched expected)':<35} {results['correct']:>10}")
    print(f"{'Detection rate (ERR caught)':<35} {results['detection_rate']:>9.1%}")
    print(f"{'False positive rate (CTRL flagged)':<35} {results['false_positive_rate']:>9.1%}")
    print(f"{'False negative rate (ERR missed)':<35} {results['false_negative_rate']:>9.1%}")
    print(f"{'Mean latency (ms)':<35} {results['mean_latency_ms']:>9.1f}")
    print()

    # Print per-scenario details
    print(f"{'Scenario':<28} {'Type':<8} {'Expected':<10} {'Baseline':<10} {'LCC':<8} {'OK'}")
    print("-" * 75)
    for d in results["details"]:
        ok_marker = "PASS" if d["correct"] else "FAIL"
        print(
            f"{d['scenario_id']:<28} "
            f"{d['error_type']:<8} "
            f"{d['expected']:<10} "
            f"{d['baseline_decision']:<10} "
            f"{d['lcc_decision']:<8} "
            f"{ok_marker}"
        )

    print()
    print("Limitations:")
    print("  - The DailyMed corpus covers only the alogliptin/metformin combination product.")
    print("  - All DDXPlus patient records are synthetically generated (no real patient data).")
    print("  - Deterministic coherence checks only - no ML-based detection.")
    print("  - This is a research prototype and NOT clinically validated.")
    print()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = build_parser()
    args = parser.parse_args()
    run_demo(args)
