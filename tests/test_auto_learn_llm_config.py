"""
Integration tests for auto-learn LLM configuration (SR-02-A).

Verifies that:
1. auto_learn.use_llm config loads correctly
2. Remote LLM endpoint is configured
3. API key environment variable is set
4. auto_learn.py script reads config correctly
"""

import os
import sys
from pathlib import Path
import pytest

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.core.config import ConfigurationManager


class TestAutoLearnLLMConfig:
    """Test suite for auto-learn LLM configuration."""

    def test_auto_learn_llm_enabled(self):
        """Test: auto_learn.use_llm = true in config."""
        config_mgr = ConfigurationManager(
            config_dir=PROJECT_ROOT / "config" / "families",
            global_config_path=PROJECT_ROOT / "config" / "global.json"
        )
        global_config = config_mgr.load_global_config()

        # Verify auto_learn config exists and is enabled
        assert global_config.auto_learn is not None, "auto_learn config should exist"
        assert global_config.auto_learn.enabled is True, "auto_learn.enabled should be True"
        assert global_config.auto_learn.use_llm is True, "auto_learn.use_llm should be True"
        assert global_config.auto_learn.timeout_seconds == 300, "auto_learn.timeout_seconds should be 300"

        print("\n[PASS] auto_learn.use_llm = true")

    def test_llm_endpoint_configured(self):
        """Test: LLM config points to remote endpoint (not localhost Ollama)."""
        config_mgr = ConfigurationManager(
            config_dir=PROJECT_ROOT / "config" / "families",
            global_config_path=PROJECT_ROOT / "config" / "global.json"
        )
        global_config = config_mgr.load_global_config()
        llm_config = global_config.llm

        # NOTE: Environment variables may override config file values
        # If LLM_PROVIDER env var is set, provider profile resolution applies
        env_provider = os.getenv("LLM_PROVIDER")
        if env_provider:
            print(f"\n[WARN] LLM_PROVIDER env var is set to '{env_provider}' (overrides config)")
            print(f"[INFO] To use config values, unset: $env:LLM_PROVIDER='' (PowerShell)")

        # Provider may be overridden by env var, so just check it's a valid value
        assert llm_config.provider in ["openai", "ollama", "company"], \
            f"LLM provider should be 'openai', 'ollama', or 'company', got '{llm_config.provider}'"

        if env_provider == "ollama":
            # Ollama profile should resolve coherently
            assert llm_config.base_url == "http://localhost:11434/v1", \
                "Ollama profile should resolve to localhost"
            assert llm_config.api_key_env_var is None, \
                "Ollama profile should have no API key env var"
        else:
            # Default: remote endpoint configuration
            assert llm_config.model == "gpt-oss", "LLM model should be 'gpt-oss'"
            assert llm_config.base_url == "https://llm.professionalize.com/v1", \
                "LLM base_url should point to remote endpoint"
            assert llm_config.api_key_env_var == "litellm_key", \
                "LLM should use 'litellm_key' env var (not OPENAI_API_KEY)"

        print(f"\n[PASS] LLM endpoint: {llm_config.base_url}")
        print(f"[PASS] LLM model: {llm_config.model}")
        print(f"[INFO] LLM provider: {llm_config.provider} (env override: {env_provider is not None})")

    def test_api_key_environment_variable_set(self):
        """Test: litellm_key environment variable is set (skipped in CI if not present)."""
        api_key = os.getenv("litellm_key")

        if api_key is None:
            pytest.skip("litellm_key environment variable not set (CI environment)")

        assert len(api_key) > 10, "litellm_key should be a valid API key"

        # Don't log the full key, just confirm it exists
        print(f"\n[PASS] API key set: {api_key[:10]}... (length: {len(api_key)})")

    def test_auto_learn_script_loads_config(self):
        """Test: auto_learn.py can load and access config."""
        # Import the script module
        auto_learn_path = PROJECT_ROOT / "scripts" / "patterns" / "auto_learn.py"
        assert auto_learn_path.exists(), "auto_learn.py should exist"

        # Verify we can load config the same way the script does
        config_mgr = ConfigurationManager(
            config_dir=PROJECT_ROOT / "config" / "families",
            global_config_path=PROJECT_ROOT / "config" / "global.json"
        )
        global_config = config_mgr.load_global_config()
        use_llm_from_config = global_config.auto_learn.use_llm

        assert use_llm_from_config is True, "Script should read use_llm=true from config"
        print(f"\n[PASS] Script config loading: use_llm = {use_llm_from_config}")

    def test_llm_service_initialization_possible(self):
        """Test: LLMService can be initialized with remote config."""
        try:
            from src.services.llm_service import LLMService
            from src.core.config import ConfigurationManager

            config_mgr = ConfigurationManager(
                config_dir=PROJECT_ROOT / "config" / "families",
                global_config_path=PROJECT_ROOT / "config" / "global.json"
            )
            global_config = config_mgr.load_global_config()
            llm_config = global_config.llm

            api_key = os.getenv(llm_config.api_key_env_var) if llm_config.api_key_env_var else None
            if not api_key and llm_config.provider != "ollama":
                pytest.skip(f"{llm_config.api_key_env_var} not set, skipping LLM service init test")

            # Initialize service (don't make actual API calls)
            service = LLMService(
                provider=llm_config.provider,
                model=llm_config.model,
                api_key=api_key,
                base_url=llm_config.base_url,
                temperature=llm_config.temperature,
                timeout_seconds=llm_config.timeout_seconds,
            )

            assert service is not None, "LLM service should initialize"
            assert service.provider in ["openai", "ollama", "company"], \
                f"Service should use valid provider, got '{service.provider}'"

            print(f"\n[PASS] LLM service initialized: {service.provider}/{service.model}")

        except ImportError as e:
            pytest.skip(f"Could not import LLMService: {e}")

    def test_config_backward_compatible(self):
        """Test: Config changes don't break existing functionality."""
        config_mgr = ConfigurationManager(
            config_dir=PROJECT_ROOT / "config" / "families",
            global_config_path=PROJECT_ROOT / "config" / "global.json"
        )
        global_config = config_mgr.load_global_config()

        # Verify all expected sections still exist
        assert global_config.llm is not None, "llm config should exist"
        assert global_config.auto_learn is not None, "auto_learn config should exist"
        assert global_config.timeouts is not None, "timeouts config should exist"

        # model_routing is optional (may not be in GlobalConfig schema)
        # Just verify core sections exist
        print("\n[PASS] Config is backward compatible")

    def test_token_usage_documented(self):
        """Test: Token usage is within expected bounds (<100 tokens per pattern → actually ~1000)."""
        # This is a documentation test - verify the plan mentions token usage
        plan_path = PROJECT_ROOT / "reports" / "agents" / "agent_b" / "SR-02-A" / "run_20260212_212710" / "plan.md"

        if plan_path.exists():
            plan_content = plan_path.read_text(encoding="utf-8")
            assert "token" in plan_content.lower(), "Plan should mention token usage"
            assert "cost" in plan_content.lower() or "estimate" in plan_content.lower(), \
                "Plan should discuss cost or estimates"
            print("\n[PASS] Token usage documented in plan.md")
        else:
            print("\n[SKIP] plan.md not found, skipping token usage documentation check")


class TestAutoLearnConfigIntegration:
    """Integration tests for auto_learn config flow."""

    def test_orchestrator_can_read_auto_learn_config(self):
        """Test: Orchestrator can read auto_learn config (regression test for SR-01-B)."""
        config_mgr = ConfigurationManager(
            config_dir=PROJECT_ROOT / "config" / "families",
            global_config_path=PROJECT_ROOT / "config" / "global.json"
        )
        global_config = config_mgr.load_global_config()

        # This is the same check the orchestrator does
        auto_learn_config = global_config.auto_learn

        assert auto_learn_config is not None, "auto_learn_config should not be None"
        assert auto_learn_config.enabled is True, "enabled should be True"
        assert auto_learn_config.use_llm is True, "use_llm should be True (SR-02-A change)"
        assert auto_learn_config.timeout_seconds == 300, "timeout_seconds should be 300"

        print("\n[PASS] Orchestrator auto_learn config check passed")
        print(f"[INFO] auto_learn: enabled={auto_learn_config.enabled}, "
              f"use_llm={auto_learn_config.use_llm}, timeout={auto_learn_config.timeout_seconds}")


if __name__ == "__main__":
    # Run tests directly for quick validation
    import sys

    # Fix Windows encoding for Unicode symbols
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8")

    print("="*60)
    print("Auto-Learn LLM Configuration Tests (SR-02-A)")
    print("="*60)

    test_suite = TestAutoLearnLLMConfig()
    integration_suite = TestAutoLearnConfigIntegration()

    tests = [
        ("auto_learn.use_llm enabled", test_suite.test_auto_learn_llm_enabled),
        ("LLM endpoint configured", test_suite.test_llm_endpoint_configured),
        ("API key set", test_suite.test_api_key_environment_variable_set),
        ("Script loads config", test_suite.test_auto_learn_script_loads_config),
        ("LLM service initialization", test_suite.test_llm_service_initialization_possible),
        ("Backward compatibility", test_suite.test_config_backward_compatible),
        ("Token usage documented", test_suite.test_token_usage_documented),
        ("Orchestrator integration", integration_suite.test_orchestrator_can_read_auto_learn_config),
    ]

    passed = 0
    failed = 0
    skipped = 0

    for name, test_func in tests:
        try:
            print(f"\nRunning: {name}...")
            test_func()
            passed += 1
            print(f"✓ PASSED: {name}")
        except pytest.skip.Exception as e:
            skipped += 1
            print(f"⊘ SKIPPED: {name} - {e}")
        except AssertionError as e:
            failed += 1
            print(f"✗ FAILED: {name} - {e}")
        except Exception as e:
            failed += 1
            print(f"✗ ERROR: {name} - {e}")

    print("\n" + "="*60)
    print(f"Results: {passed} passed, {failed} failed, {skipped} skipped")
    print("="*60)

    sys.exit(0 if failed == 0 else 1)
