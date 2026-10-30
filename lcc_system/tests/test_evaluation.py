"""
test_evaluation.py — Unit tests for evaluation.py.

Tests that evaluate_all() returns a dict with all required metric keys,
that rates are floats in [0.0, 1.0], that len(details) == len(SCENARIOS),
and that iterating details raises no KeyError.
"""
import pytest
from dataset_loader import DatasetLoader
from evaluation import Evaluator, SCENARIOS, ERROR_TYPES, TestScenario


@pytest.fixture(scope="module")
def loader():
    return DatasetLoader()


@pytest.fixture(scope="module")
def evaluator(loader):
    return Evaluator(loader)


@pytest.fixture(scope="module")
def results(evaluator):
    """Run evaluate_all() once for the whole module to save time."""
    return evaluator.evaluate_all()


# ---------------------------------------------------------------------------
# evaluate_all() return structure
# ---------------------------------------------------------------------------

class TestEvaluateAllKeys:
    def test_returns_dict(self, results):
        assert isinstance(results, dict)

    def test_has_total(self, results):
        assert "total" in results

    def test_has_correct(self, results):
        assert "correct" in results

    def test_has_detection_rate(self, results):
        assert "detection_rate" in results

    def test_has_false_positive_rate(self, results):
        assert "false_positive_rate" in results

    def test_has_false_negative_rate(self, results):
        assert "false_negative_rate" in results

    def test_has_mean_latency_ms(self, results):
        assert "mean_latency_ms" in results

    def test_has_details(self, results):
        assert "details" in results


# ---------------------------------------------------------------------------
# Rates are floats in [0.0, 1.0]
# ---------------------------------------------------------------------------

class TestRateValues:
    def test_detection_rate_is_float(self, results):
        assert isinstance(results["detection_rate"], float)

    def test_detection_rate_in_range(self, results):
        assert 0.0 <= results["detection_rate"] <= 1.0

    def test_false_positive_rate_is_float(self, results):
        assert isinstance(results["false_positive_rate"], float)

    def test_false_positive_rate_in_range(self, results):
        assert 0.0 <= results["false_positive_rate"] <= 1.0

    def test_false_negative_rate_is_float(self, results):
        assert isinstance(results["false_negative_rate"], float)

    def test_false_negative_rate_in_range(self, results):
        assert 0.0 <= results["false_negative_rate"] <= 1.0

    def test_mean_latency_ms_is_non_negative(self, results):
        assert results["mean_latency_ms"] >= 0.0


# ---------------------------------------------------------------------------
# Details list
# ---------------------------------------------------------------------------

class TestDetailsStructure:
    def test_details_is_list(self, results):
        assert isinstance(results["details"], list)

    def test_details_length_equals_scenarios(self, results):
        assert len(results["details"]) == len(SCENARIOS)

    def test_no_key_error_iterating_details(self, results):
        required_keys = {
            "scenario_id", "error_type", "expected",
            "baseline_decision", "lcc_decision", "correct", "latency_ms",
        }
        for detail in results["details"]:
            for key in required_keys:
                assert key in detail, f"Missing key '{key}' in detail: {detail}"

    def test_correct_is_bool(self, results):
        for detail in results["details"]:
            assert isinstance(detail["correct"], bool)

    def test_latency_ms_is_non_negative(self, results):
        for detail in results["details"]:
            assert detail["latency_ms"] >= 0.0

    def test_lcc_decision_valid_values(self, results):
        valid = {"PASS", "CLARIFY", "WARN", "REFUSE"}
        for detail in results["details"]:
            assert detail["lcc_decision"] in valid

    def test_baseline_decision_always_pass(self, results):
        """Baseline never calls verifier, so always PASS."""
        for detail in results["details"]:
            assert detail["baseline_decision"] == "PASS"


# ---------------------------------------------------------------------------
# Counts are internally consistent
# ---------------------------------------------------------------------------

class TestMetricConsistency:
    def test_total_equals_len_scenarios(self, results):
        assert results["total"] == len(SCENARIOS)

    def test_correct_lte_total(self, results):
        assert results["correct"] <= results["total"]

    def test_correct_gte_zero(self, results):
        assert results["correct"] >= 0


# ---------------------------------------------------------------------------
# SCENARIOS list sanity
# ---------------------------------------------------------------------------

class TestScenariosDefinition:
    def test_at_least_10_scenarios(self):
        assert len(SCENARIOS) >= 10

    def test_all_are_test_scenario_instances(self):
        for s in SCENARIOS:
            assert isinstance(s, TestScenario)

    def test_expected_decisions_valid(self):
        valid = {"PASS", "CLARIFY", "WARN", "REFUSE"}
        for s in SCENARIOS:
            assert s.expected_decision in valid, (
                f"Scenario {s.scenario_id} has invalid expected_decision '{s.expected_decision}'"
            )

    def test_error_types_defined(self):
        for s in SCENARIOS:
            assert s.error_type in ERROR_TYPES, (
                f"Scenario {s.scenario_id} has unknown error_type '{s.error_type}'"
            )

    def test_scenario_ids_unique(self):
        ids = [s.scenario_id for s in SCENARIOS]
        assert len(ids) == len(set(ids)), "Duplicate scenario_ids found"

    def test_err_scenarios_expect_non_pass(self):
        """ERR scenarios should NOT expect PASS (they should detect errors)."""
        for s in SCENARIOS:
            if s.error_type.startswith("ERR"):
                assert s.expected_decision != "PASS", (
                    f"ERR scenario {s.scenario_id} expects PASS — this is suspicious"
                )

    def test_ctrl_scenarios_expect_pass(self):
        """CTRL scenarios (legitimate updates) should expect PASS."""
        for s in SCENARIOS:
            if s.error_type.startswith("CTRL"):
                assert s.expected_decision == "PASS", (
                    f"CTRL scenario {s.scenario_id} expects {s.expected_decision} instead of PASS"
                )


# ---------------------------------------------------------------------------
# ERROR_TYPES dict
# ---------------------------------------------------------------------------

class TestErrorTypesDict:
    def test_has_err1_through_err4(self):
        for k in ("ERR-1", "ERR-2", "ERR-3", "ERR-4"):
            assert k in ERROR_TYPES

    def test_has_ctrl5_and_ctrl6(self):
        assert "CTRL-5" in ERROR_TYPES
        assert "CTRL-6" in ERROR_TYPES

    def test_values_are_strings(self):
        for k, v in ERROR_TYPES.items():
            assert isinstance(v, str) and len(v) > 0
