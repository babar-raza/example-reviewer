"""
Integration test to verify auto_learn config loads correctly in orchestrator context.

This test simulates the orchestrator loading global config and checks that
auto_learn.enabled is True (not False).
"""

from src.core.config import ConfigurationManager
from pathlib import Path


def test_orchestrator_auto_learn_config():
    """
    Integration test verifying auto_learn loads correctly.

    This replicates what the orchestrator does when loading config.
    """
    # Simulate orchestrator loading config
    config_mgr = ConfigurationManager(
        config_dir=Path("config/families"),
        global_config_path=Path("config/global.json")
    )

    global_config = config_mgr.load_global_config()

    # This is what orchestrator checks at line 2318
    auto_learn_config = global_config.auto_learn

    print("\n" + "="*60)
    print("Auto-Learn Config Loading Integration Test")
    print("="*60)
    print(f"Config object exists: {auto_learn_config is not None}")
    print(f"Config type: {type(auto_learn_config).__name__}")
    print(f"enabled value: {auto_learn_config.enabled}")
    print(f"use_llm value: {auto_learn_config.use_llm}")
    print(f"timeout_seconds value: {auto_learn_config.timeout_seconds}")
    print("="*60)

    # These are the assertions that FAILED before the fix
    assert auto_learn_config is not None, "auto_learn_config should not be None"
    assert auto_learn_config.enabled is True, "enabled should be True (from JSON)"
    assert auto_learn_config.use_llm is False, "use_llm should be False"
    assert auto_learn_config.timeout_seconds == 300, "timeout_seconds should be 300"

    print("\n[PASS] AUTO-LEARN CONFIG LOADS CORRECTLY")
    print("[PASS] Bug SR-01-B is FIXED")
    print("\nOrchestrator log should now show:")
    print("[Auto-Learn] Config check: auto_learn_config=present, enabled=True")
    print("\nInstead of (BROKEN):")
    print("[Auto-Learn] Config check: auto_learn_config=present, enabled=False")
    print("="*60 + "\n")


if __name__ == "__main__":
    test_orchestrator_auto_learn_config()
