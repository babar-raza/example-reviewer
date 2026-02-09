#!/usr/bin/env python
"""
Standalone test script for LLMService routing logic (TASK-4C).
Tests smart model routing without pytest dependency.
"""

import sys
import os
import json
from io import StringIO

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.services.llm_service import LLMService
from src.pipeline.error_complexity_classifier import ErrorComplexityClassifier


class TestRunner:
    """Simple test runner without pytest dependency."""

    def __init__(self):
        self.tests_passed = 0
        self.tests_failed = 0
        self.test_results = []

    def test(self, name, condition, message=""):
        """Run a test assertion."""
        if condition:
            self.tests_passed += 1
            status = "PASS"
            print(f"  [PASS] {name}")
        else:
            self.tests_failed += 1
            status = "FAIL"
            print(f"  [FAIL] {name}")
            if message:
                print(f"         {message}")
        self.test_results.append((name, status, message))

    def summary(self):
        """Print test summary."""
        print("\n" + "=" * 70)
        print("TEST SUMMARY")
        print("=" * 70)
        print(f"Passed: {self.tests_passed}")
        print(f"Failed: {self.tests_failed}")
        print(f"Total:  {self.tests_passed + self.tests_failed}")
        success_rate = (
            100 * self.tests_passed / (self.tests_passed + self.tests_failed)
            if (self.tests_passed + self.tests_failed) > 0
            else 0
        )
        print(f"Success Rate: {success_rate:.1f}%")
        print("=" * 70)


def test_extract_error_code():
    """Test extracting error codes from logs."""
    print("\n[TEST] Extract Error Code from Logs")
    runner = TestRunner()

    service = LLMService(provider="ollama", model="test-model")

    # Test CS0246 extraction
    logs = "error CS0246: The type or namespace name 'Archive' could not be found"
    code = service._extract_error_code_from_logs(logs)
    runner.test("Extract CS0246", code == "CS0246", f"Got: {code}")

    # Test CS0103 extraction
    logs = "error CS0103: The name 'x' does not exist"
    code = service._extract_error_code_from_logs(logs)
    runner.test("Extract CS0103", code == "CS0103", f"Got: {code}")

    # Test no error code
    logs = "Some generic error message"
    code = service._extract_error_code_from_logs(logs)
    runner.test("No error code returns None", code is None, f"Got: {code}")

    runner.summary()
    return runner.tests_failed == 0


def test_model_selection():
    """Test model selection based on complexity."""
    print("\n[TEST] Model Selection by Complexity")
    runner = TestRunner()

    routing_config = {
        "enabled": True,
        "model_tiers": {
            "small": "test-small",
            "medium": "test-medium",
            "large": "test-large"
        }
    }

    service = LLMService(provider="ollama", model="default-model")
    service.set_routing_config(routing_config)

    # Test simple error -> small model
    model = service._select_model_for_error(
        "CS0246",
        "The type or namespace name 'Archive' could not be found"
    )
    runner.test(
        "Simple error (CS0246) -> small model",
        model == "test-small",
        f"Got: {model}"
    )

    # Test medium error -> medium model
    model = service._select_model_for_error(
        "CS7036",
        "No overload for method 'Extract' takes 1 arguments"
    )
    runner.test(
        "Medium error (CS7036) -> medium model",
        model == "test-medium",
        f"Got: {model}"
    )

    # Test complex error -> large model
    model = service._select_model_for_error(
        "CS1061",
        "Archive does not contain a definition for 'SaveAsync'"
    )
    runner.test(
        "Complex error (CS1061) -> large model",
        model == "test-large",
        f"Got: {model}"
    )

    runner.summary()
    return runner.tests_failed == 0


def test_tier_distribution():
    """Test tier distribution tracking."""
    print("\n[TEST] Tier Distribution Tracking")
    runner = TestRunner()

    routing_config = {
        "enabled": True,
        "model_tiers": {
            "small": "small-model",
            "medium": "medium-model",
            "large": "large-model"
        }
    }

    service = LLMService(provider="ollama", model="test-model")
    service.set_routing_config(routing_config)

    # Simulate routing decisions
    service._select_model_for_error("CS0246", "Missing type 1")
    service._select_model_for_error("CS0246", "Missing type 2")
    service._select_model_for_error("CS7036", "Missing argument")
    service._select_model_for_error("CS1061", "Member not found 1")
    service._select_model_for_error("CS1061", "Member not found 2")
    service._select_model_for_error("CS1061", "Member not found 3")

    dist = service.get_tier_distribution()
    runner.test("Small tier count", dist["small"] == 2, f"Got: {dist['small']}")
    runner.test("Medium tier count", dist["medium"] == 1, f"Got: {dist['medium']}")
    runner.test("Large tier count", dist["large"] == 3, f"Got: {dist['large']}")

    runner.summary()
    return runner.tests_failed == 0


def test_routing_disabled():
    """Test that disabled routing uses default model."""
    print("\n[TEST] Routing Disabled")
    runner = TestRunner()

    service = LLMService(provider="ollama", model="my-default-model")
    # Routing not enabled

    model = service._select_model_for_error("CS0246", "Missing type")
    runner.test(
        "Disabled routing uses default model",
        model == "my-default-model",
        f"Got: {model}"
    )

    runner.summary()
    return runner.tests_failed == 0


def test_routing_metadata():
    """Test routing metadata collection."""
    print("\n[TEST] Routing Metadata")
    runner = TestRunner()

    routing_config = {
        "enabled": True,
        "model_tiers": {
            "small": "gpt-3.5-turbo",
            "medium": "gpt-4",
            "large": "gpt-4-turbo"
        }
    }

    service = LLMService(provider="ollama", model="test-model")
    service.set_routing_config(routing_config)

    service._select_model_for_error("CS0246", "Missing type")
    service._select_model_for_error("CS1061", "Member not found")

    metadata = service.get_routing_metadata()

    runner.test(
        "Metadata has routing_enabled",
        metadata.get("routing_enabled") is True,
        f"Got: {metadata.get('routing_enabled')}"
    )
    runner.test(
        "Metadata has tier_distribution",
        "tier_distribution" in metadata,
        f"Keys: {list(metadata.keys())}"
    )
    runner.test(
        "Metadata has routed_models",
        "routed_models" in metadata,
        f"Keys: {list(metadata.keys())}"
    )

    routed = metadata.get("routed_models", {})
    runner.test(
        "Small tier routed to gpt-3.5-turbo",
        routed.get("small") == "gpt-3.5-turbo",
        f"Got: {routed.get('small')}"
    )
    runner.test(
        "Large tier routed to gpt-4-turbo",
        routed.get("large") == "gpt-4-turbo",
        f"Got: {routed.get('large')}"
    )

    runner.summary()
    return runner.tests_failed == 0


def test_complexity_classifier_integration():
    """Test integration with ErrorComplexityClassifier."""
    print("\n[TEST] ErrorComplexityClassifier Integration")
    runner = TestRunner()

    classifier = ErrorComplexityClassifier()

    # Test simple error
    score = classifier.score_error("CS0246", "Missing type 'Archive'")
    tier = classifier.route_to_tier(score)
    runner.test(
        "Simple error scores < 0.4",
        score < 0.4,
        f"Score: {score}"
    )
    runner.test(
        "Simple error routes to small tier",
        tier == "small",
        f"Tier: {tier}"
    )

    # Test complex error
    score = classifier.score_error("CS1061", "Member 'SaveAsync' not found in Archive")
    tier = classifier.route_to_tier(score)
    runner.test(
        "Complex error scores >= 0.7",
        score >= 0.7,
        f"Score: {score}"
    )
    runner.test(
        "Complex error routes to large tier",
        tier == "large",
        f"Tier: {tier}"
    )

    runner.summary()
    return runner.tests_failed == 0


def main():
    """Run all tests."""
    print("=" * 70)
    print("LLMService Routing Tests (TASK-4C)")
    print("=" * 70)

    results = []

    results.append(("Extract Error Code", test_extract_error_code()))
    results.append(("Model Selection", test_model_selection()))
    results.append(("Tier Distribution", test_tier_distribution()))
    results.append(("Routing Disabled", test_routing_disabled()))
    results.append(("Routing Metadata", test_routing_metadata()))
    results.append(("Classifier Integration", test_complexity_classifier_integration()))

    print("\n" + "=" * 70)
    print("OVERALL TEST RESULTS")
    print("=" * 70)

    total_passed = sum(1 for _, result in results if result)
    total_tests = len(results)

    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"  {test_name}: {status}")

    print("\n" + f"Total: {total_passed}/{total_tests} test groups passed")

    if total_passed == total_tests:
        print("\nAll tests PASSED!")
        return 0
    else:
        print(f"\n{total_tests - total_passed} test group(s) FAILED!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
