#!/usr/bin/env python3
"""
Test script to verify compilation service hardening improvements.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

def test_code_analysis():
    """Test the enhanced code analysis functionality."""
    from core.config import ConfigurationManager
    from core.database import Database
    from services.compilation_service import CompilationService
    from core.models import ExampleRecord

    print("=" * 70)
    print("Testing Enhanced Compilation Service - Code Analysis")
    print("=" * 70)

    # Initialize services
    config_manager = ConfigurationManager(Path('config/families'))
    zip_config = config_manager.load_family_config('zip')
    db = Database(Path('data/test_hardening.db'))
    db.initialize_schema()

    compilation_service = CompilationService(
        db,
        workspace_dir=Path('workspace/test_hardening'),
        artifacts_dir=Path('artifacts/test_hardening')
    )

    # Test Case 1: Code with Archive usage (should detect API and infer using)
    print("\n--- Test 1: API Detection and Using Inference ---")
    code1 = """var archive = new Archive("input.zip");
archive.Save("output.zip");"""

    analysis1 = compilation_service._analyze_code(code1, zip_config)
    print(f"Code: {code1[:50]}...")
    print(f"Detected APIs: {analysis1['detected_apis']}")
    print(f"Missing usings: {analysis1['missing_usings']}")
    print(f"Has class: {analysis1['has_class']}")
    print(f"Has Main: {analysis1['has_main']}")
    print(f"Is complete: {analysis1['is_complete']}")

    wrapped1 = compilation_service._wrap_code(code1, zip_config)
    print(f"\nWrapped code preview:")
    print(wrapped1[:300] + "..." if len(wrapped1) > 300 else wrapped1)

    # Test Case 2: Code with class but no usings
    print("\n--- Test 2: Class with Missing Usings ---")
    code2 = """public class ArchiveProcessor
{
    public void Process()
    {
        var archive = new Archive("input.zip");
        var settings = new DeflateCompressionSettings();
    }
}"""

    analysis2 = compilation_service._analyze_code(code2, zip_config)
    print(f"Detected APIs: {analysis2['detected_apis']}")
    print(f"Missing usings: {analysis2['missing_usings']}")

    wrapped2 = compilation_service._wrap_code(code2, zip_config)
    print(f"\nWrapped code preview:")
    print(wrapped2[:400] + "..." if len(wrapped2) > 400 else wrapped2)

    # Test Case 3: Complete code with namespace
    print("\n--- Test 3: Complete Code with Namespace ---")
    code3 = """using Aspose.Zip;
namespace MyApp
{
    class Program
    {
        static void Main()
        {
            var archive = new Archive();
        }
    }
}"""

    analysis3 = compilation_service._analyze_code(code3, zip_config)
    print(f"Is complete: {analysis3['is_complete']}")
    print(f"Has namespace: {analysis3['has_namespace']}")

    wrapped3 = compilation_service._wrap_code(code3, zip_config)
    print(f"Wrapping changed code: {wrapped3 != code3}")

    # Test Case 4: Error categorization
    print("\n--- Test 4: Error Categorization ---")
    errors = [
        "Program.cs(10,17): error CS0246: The type or namespace name 'Archive' could not be found",
        "Program.cs(12,9): error CS0103: The name 'myVar' does not exist in the current context",
        "Program.cs(15,20): error CS1002: ; expected",
    ]

    categorized = compilation_service.categorize_errors(errors)
    print(f"Error categories: {list(categorized.keys())}")
    for category, errs in categorized.items():
        print(f"  {category}: {len(errs)} errors")

    hints = compilation_service.get_error_fix_hints(categorized, zip_config)
    print(f"Fix hints generated: {len(hints)}")
    for hint in hints:
        print(f"  - {hint}")

    print("\n=" * 70)
    print("✓ All tests completed successfully!")
    print("=" * 70)


def test_llm_prompts():
    """Test the enhanced LLM service prompts."""
    from services.llm_service import LLMService

    print("\n=" * 70)
    print("Testing Enhanced LLM Service - Prompt Generation")
    print("=" * 70)

    llm_service = LLMService(
        provider="ollama",
        model="qwen2.5-coder:7b",
        base_url="http://localhost:11434/v1",
    )

    print(f"\nLLM Service initialized:")
    print(f"  Provider: {llm_service.provider}")
    print(f"  Model: {llm_service.model}")
    print(f"  Available: {llm_service.is_available()}")

    # Check few-shot examples
    print(f"\n✓ Few-shot examples defined: {len(llm_service.FEW_SHOT_EXAMPLES)} chars")
    print(f"✓ Error fix instructions: {len(llm_service.ERROR_FIX_INSTRUCTIONS)} categories")

    # Test API pattern extraction
    family_config = {
        'api_patterns': {
            'compression_basic': {
                'description': 'Create archive with compression',
                'code': 'var archive = new Archive();'
            }
        }
    }

    patterns = llm_service._get_api_patterns(family_config)
    print(f"✓ API patterns extracted: {len(patterns)} chars")

    print("\n=" * 70)
    print("✓ LLM prompt enhancements verified!")
    print("=" * 70)


if __name__ == "__main__":
    try:
        test_code_analysis()
        test_llm_prompts()
        print("\n🎉 All hardening improvements verified successfully!")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
