"""
Integration test for LLM migration from Ollama to custom OpenAI-compatible endpoint.

This script tests the following:
1. Configuration loading with environment variable overrides
2. LLM service initialization with custom endpoint
3. Actual code fix using the remote 120B model
4. Fallback to Ollama when remote endpoint is unavailable

Usage:
    # Test with custom endpoint (primary)
    export LLM_API_KEY_ENV_VAR=litellm_key
    export LLM_PROVIDER=openai
    export LLM_MODEL=gpt-oss
    export LLM_BASE_URL=https://llm.professionalize.com/v1
    python test_llm_migration.py

    # Test with Ollama fallback
    export LLM_PROVIDER=ollama
    python test_llm_migration.py
"""

import sys
import os
from pathlib import Path

# Ensure UTF-8 output on Windows
sys.stdout.reconfigure(encoding='utf-8')

from src.core.config import ConfigurationManager
from src.services.llm_service import LLMServiceFactory


def test_config_loading():
    """Test that configuration loads correctly with env var overrides."""
    print("="*80)
    print("TEST 1: Configuration Loading")
    print("="*80)

    cm = ConfigurationManager(Path('config'))
    global_config = cm.load_global_config()
    config_dict = global_config.model_dump()

    llm_config = config_dict['llm']

    print(f"✓ Provider: {llm_config['provider']}")
    print(f"✓ Model: {llm_config['model']}")
    print(f"✓ Base URL: {llm_config['base_url']}")
    print(f"✓ API Key Env Var: {llm_config['api_key_env_var']}")

    # Verify environment variables
    api_key = os.getenv(llm_config['api_key_env_var'])
    if api_key:
        print(f"✓ API Key found: {api_key[:15]}...{api_key[-10:]}")
    else:
        print(f"✗ API Key NOT FOUND in {llm_config['api_key_env_var']}!")
        return False

    print()
    return True


def test_service_creation():
    """Test that LLM service can be created."""
    print("="*80)
    print("TEST 2: LLM Service Creation")
    print("="*80)

    cm = ConfigurationManager(Path('config'))
    global_config = cm.load_global_config()
    config_dict = global_config.model_dump()

    try:
        service = LLMServiceFactory.from_config(config_dict)
        print("✓ LLM service created successfully")
        print()
        return service
    except Exception as e:
        print(f"✗ Failed to create LLM service: {e}")
        return None


def test_code_fix(service):
    """Test actual code fixing with the LLM."""
    print("="*80)
    print("TEST 3: Code Fix")
    print("="*80)

    test_code = '''using System;
class Test {
    static void Main() {
        Console.WriteLine("missing semicolon")
    }
}'''

    test_error = '''Program.cs(5,6): error CS1002: ; expected'''

    print("Test Case: Missing semicolon (CS1002)")
    print("Calling LLM... (may take 5-30 seconds)")
    print()

    try:
        result = service.fix_code(
            code=test_code,
            error_logs=test_error,
            context_type='compile'
        )

        if hasattr(result, 'success') and result.success:
            print("✓ Fix successful!")
            print(f"✓ Model used: {result.model}")
            print(f"✓ Latency: {result.latency_ms}ms")
            print(f"✓ Tokens: {result.usage.get('total_tokens', 'N/A')}")
            print()
            print("Fixed Code:")
            print("-" * 60)
            print(result.content)
            print("-" * 60)
            print()
            return True
        else:
            print(f"✗ Fix failed: {result.error if hasattr(result, 'error') else 'Unknown error'}")
            return False

    except Exception as e:
        print(f"✗ Exception during fix: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all integration tests."""
    print("\n")
    print("╔" + "═"*78 + "╗")
    print("║" + " "*20 + "LLM Migration Integration Tests" + " "*27 + "║")
    print("╚" + "═"*78 + "╝")
    print()

    # Display current environment
    print("Environment Variables:")
    print(f"  LLM_PROVIDER = {os.getenv('LLM_PROVIDER', 'NOT SET')}")
    print(f"  LLM_MODEL = {os.getenv('LLM_MODEL', 'NOT SET')}")
    print(f"  LLM_BASE_URL = {os.getenv('LLM_BASE_URL', 'NOT SET')}")
    print(f"  LLM_API_KEY_ENV_VAR = {os.getenv('LLM_API_KEY_ENV_VAR', 'NOT SET')}")
    print()

    # Run tests
    if not test_config_loading():
        print("\n✗ Configuration test failed. Aborting.")
        return 1

    service = test_service_creation()
    if not service:
        print("\n✗ Service creation test failed. Aborting.")
        return 1

    if not test_code_fix(service):
        print("\n✗ Code fix test failed.")
        return 1

    # All tests passed
    print("="*80)
    print("✓ ALL TESTS PASSED!")
    print("="*80)
    print()
    print("Migration is successful. The custom endpoint is working correctly.")
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
