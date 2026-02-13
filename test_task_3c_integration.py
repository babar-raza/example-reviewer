#!/usr/bin/env python3
"""
Integration test for TASK-3C - API Context Integration for LLMService
Verifies that API context can be injected into LLM calls
"""

import sys
import json
from pathlib import Path
from unittest.mock import Mock, MagicMock

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.services.llm_service import LLMService, LLMServiceFactory
from src.services.api_context_service import APIContextService
from src.services.api_reference_service import APIReferenceService
from src.core.config import ApiReferenceConfig


def test_llm_service_accepts_api_context():
    """Test that LLMService accepts api_context_service parameter"""
    print("\n=== Test 1: LLMService accepts api_context_service ===")

    mock_api_context = Mock(spec=APIContextService)

    service = LLMService(
        provider="ollama",
        model="test-model",
        api_context_service=mock_api_context
    )

    assert service.api_context_service is mock_api_context
    print("✅ LLMService accepts and stores api_context_service")


def test_api_context_injection_method():
    """Test that _get_api_context_for_error method works"""
    print("\n=== Test 2: _get_api_context_for_error method ===")

    # Create mock service with return value
    mock_api_context = Mock(spec=APIContextService)
    mock_api_context.get_context_for_error = Mock(
        return_value="## API Documentation\nClass Document..."
    )

    service = LLMService(
        provider="ollama",
        model="test-model",
        api_context_service=mock_api_context
    )

    # Test the method
    context = service._get_api_context_for_error("CS0103", "The name 'Document' does not exist")

    assert context == "## API Documentation\nClass Document..."
    mock_api_context.get_context_for_error.assert_called_once_with(
        "CS0103",
        "The name 'Document' does not exist"
    )
    print("✅ _get_api_context_for_error returns context from service")


def test_api_context_injection_none_service():
    """Test graceful degradation when api_context_service is None"""
    print("\n=== Test 3: Graceful degradation when no api_context_service ===")

    service = LLMService(
        provider="ollama",
        model="test-model",
        api_context_service=None
    )

    context = service._get_api_context_for_error("CS0103", "Some error")

    assert context == ""
    print("✅ Returns empty string when api_context_service is None")


def test_factory_accepts_api_context():
    """Test that LLMServiceFactory passes api_context_service to LLMService"""
    print("\n=== Test 4: LLMServiceFactory passes api_context_service ===")

    config = {
        "llm": {
            "provider": "ollama",
            "model": "test-model",
            "temperature": 0.2,
        }
    }

    mock_api_context = Mock(spec=APIContextService)

    service = LLMServiceFactory.from_config(
        config,
        use_final_review=False,
        api_context_service=mock_api_context
    )

    assert service.api_context_service is mock_api_context
    print("✅ LLMServiceFactory passes api_context_service correctly")


def test_config_has_api_reference():
    """Test that words.json has api_reference configuration"""
    print("\n=== Test 5: words.json has api_reference config ===")

    config_path = Path(__file__).parent / "config" / "families" / "words.json"

    with open(config_path) as f:
        config = json.load(f)

    assert "api_reference" in config
    api_ref_config = config["api_reference"]

    assert api_ref_config["enabled"] is True
    assert "github.com/aspose-words" in api_ref_config["git_repo"]
    assert api_ref_config["git_ref"] == "main"
    assert api_ref_config["shallow_clone"] is True
    assert api_ref_config["auto_fetch"] is True
    assert api_ref_config["max_context_chars"] == 8000

    print(f"✅ API Reference config found:")
    print(f"   - Enabled: {api_ref_config['enabled']}")
    print(f"   - Git Repo: {api_ref_config['git_repo']}")
    print(f"   - Git Ref: {api_ref_config['git_ref']}")
    print(f"   - Shallow Clone: {api_ref_config['shallow_clone']}")
    print(f"   - Auto Fetch: {api_ref_config['auto_fetch']}")
    print(f"   - Max Context Chars: {api_ref_config['max_context_chars']}")


def test_api_reference_config_parseable():
    """Test that ApiReferenceConfig can parse words.json api_reference"""
    print("\n=== Test 6: ApiReferenceConfig parses words.json ===")

    config_path = Path(__file__).parent / "config" / "families" / "words.json"

    with open(config_path) as f:
        config = json.load(f)

    api_ref_data = config["api_reference"]

    # Create ApiReferenceConfig instance
    api_ref_config = ApiReferenceConfig(**api_ref_data)

    assert api_ref_config.git_repo == "https://github.com/aspose-words/Aspose.Words-API-References-Tutorials"
    assert api_ref_config.git_ref == "main"
    assert api_ref_config.git_subpath == "english/net"
    assert api_ref_config.shallow_clone is True
    assert api_ref_config.auto_fetch is True
    assert api_ref_config.max_context_chars == 8000

    print("✅ ApiReferenceConfig successfully parses words.json api_reference section")


def test_extract_error_code_from_logs():
    """Test that error code extraction works"""
    print("\n=== Test 7: Error code extraction from logs ===")

    service = LLMService(
        provider="ollama",
        model="test-model"
    )

    # Test various error formats
    test_cases = [
        ("error CS0103: The name 'X' does not exist", "CS0103"),
        ("Build failed: CS0246 - Type not found", "CS0246"),
        ("CS0117: 'Foo' does not contain definition", "CS0117"),
        ("No error code here", None),
    ]

    for error_logs, expected_code in test_cases:
        code = service._extract_error_code_from_logs(error_logs)
        assert code == expected_code, f"Expected {expected_code}, got {code}"

    print("✅ Error code extraction works correctly")


def main():
    """Run all integration tests"""
    print("=" * 70)
    print("TASK-3C Integration Test Suite")
    print("=" * 70)

    try:
        test_llm_service_accepts_api_context()
        test_api_context_injection_method()
        test_api_context_injection_none_service()
        test_factory_accepts_api_context()
        test_config_has_api_reference()
        test_api_reference_config_parseable()
        test_extract_error_code_from_logs()

        print("\n" + "=" * 70)
        print("ALL TESTS PASSED!")
        print("=" * 70)
        return 0

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
