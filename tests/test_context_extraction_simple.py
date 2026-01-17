"""
Simplified test suite for CD-04: Make Context Extraction Configurable
Tests without pytest dependency
"""

import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.config import ContextExtractionConfig, DiscoveryPatternsConfig, ConfigurationManager
from src.services.discovery_service import DiscoveryService
from src.core.database import Database


# Sample markdown content for testing
SAMPLE_MARKDOWN = """# Main Title

This is the introduction paragraph.

## Section One

This is the first paragraph before the code.
It describes what the code does.

Another paragraph with more context.
This should also be captured.

```csharp
using System;

public class Example {
    public void Test() {
        Console.WriteLine("Hello");
    }
}
```

## Section Two

Brief description.

```csharp
using System;
namespace Test {
    public class Another {
        public void Method() { }
    }
}
```
"""


def run_test(test_name, test_func):
    """Run a single test and report results."""
    try:
        test_func()
        print(f"PASS {test_name}")
        return True
    except AssertionError as e:
        print(f"FAIL {test_name}: {e}")
        return False
    except Exception as e:
        print(f"ERROR {test_name}: Unexpected error: {e}")
        return False


def test_default_context_extraction():
    """Test that default context extraction works as before."""
    db = Database(":memory:")
    patterns_config = DiscoveryPatternsConfig()
    service = DiscoveryService(db=db, filtering_config=patterns_config)
    service.discovery_patterns = patterns_config

    lines = SAMPLE_MARKDOWN.split('\n')
    code_start_idx = next(i for i, line in enumerate(lines) if line.strip() == '```csharp')

    heading, description = service._extract_context(lines, code_start_idx)

    assert heading == "Section One", f"Expected 'Section One', got '{heading}'"
    assert "first paragraph" in description, f"Expected 'first paragraph' in description"
    assert "Another paragraph" in description, f"Expected 'Another paragraph' in description"
    assert len(description) > 10, f"Description too short: {len(description)}"


def test_max_paragraphs_limit():
    """Test that max_paragraphs limit is enforced."""
    db = Database(":memory:")
    context_config = ContextExtractionConfig(max_paragraphs=1)
    patterns_config = DiscoveryPatternsConfig(context_extraction=context_config)
    service = DiscoveryService(db=db, filtering_config=patterns_config)
    service.discovery_patterns = patterns_config

    lines = SAMPLE_MARKDOWN.split('\n')
    code_start_idx = next(i for i, line in enumerate(lines) if line.strip() == '```csharp')

    heading, description = service._extract_context(lines, code_start_idx)

    assert "Another paragraph" in description, f"Expected 'Another paragraph' in single paragraph"
    assert description.count('\n\n') == 0, f"Should not have paragraph separators with max_paragraphs=1"


def test_max_heading_distance():
    """Test max_heading_distance limits how far back we look for headings."""
    db = Database(":memory:")
    markdown = "# Title\n" + "\n" * 60 + "```csharp\nclass Test {}\n```"

    # With larger context_window_lines
    context_config = ContextExtractionConfig(
        max_heading_distance=65,
        context_window_lines=65
    )
    patterns_config = DiscoveryPatternsConfig(context_extraction=context_config)
    service = DiscoveryService(db=db, filtering_config=patterns_config)
    service.discovery_patterns = patterns_config

    lines = markdown.split('\n')
    code_start_idx = next(i for i, line in enumerate(lines) if line.strip().startswith('```csharp'))

    heading, description = service._extract_context(lines, code_start_idx)

    assert heading == "Title", f"Expected 'Title', got '{heading}'"


def test_include_file_header():
    """Test that file header is included when configured."""
    db = Database(":memory:")

    # Without file header
    context_config = ContextExtractionConfig(include_file_header=False)
    patterns_config = DiscoveryPatternsConfig(context_extraction=context_config)
    service = DiscoveryService(db=db, filtering_config=patterns_config)
    service.discovery_patterns = patterns_config

    lines = SAMPLE_MARKDOWN.split('\n')
    code_start_idx = next(i for i, line in enumerate(lines) if line.strip() == '```csharp')

    heading, description = service._extract_context(lines, code_start_idx)

    assert "File: Main Title" not in description, f"File header should not be included"

    # With file header
    context_config = ContextExtractionConfig(include_file_header=True)
    patterns_config = DiscoveryPatternsConfig(context_extraction=context_config)
    service = DiscoveryService(db=db, filtering_config=patterns_config)
    service.discovery_patterns = patterns_config

    heading, description = service._extract_context(lines, code_start_idx)

    assert "File: Main Title" in description, f"File header should be included"


def test_context_window_lines():
    """Test that context_window_lines controls the search window."""
    db = Database(":memory:")
    markdown = "# Title\n" + "Content line\n" * 30 + "Near code\n```csharp\nclass Test {}\n```"

    # With small window
    context_config = ContextExtractionConfig(context_window_lines=5)
    patterns_config = DiscoveryPatternsConfig(context_extraction=context_config)
    service = DiscoveryService(db=db, filtering_config=patterns_config)
    service.discovery_patterns = patterns_config

    lines = markdown.split('\n')
    code_start_idx = next(i for i, line in enumerate(lines) if line.strip().startswith('```csharp'))

    heading, description = service._extract_context(lines, code_start_idx)

    assert "Near code" in description, f"Should capture nearby content"


def test_min_context_length_filter():
    """Test that min_context_length filters out too-short context."""
    db = Database(":memory:")
    markdown = "# Title\n\nShort\n\n```csharp\nclass Test {}\n```"

    # With high min_context_length
    context_config = ContextExtractionConfig(min_context_length=50)
    patterns_config = DiscoveryPatternsConfig(context_extraction=context_config)
    service = DiscoveryService(db=db, filtering_config=patterns_config)
    service.discovery_patterns = patterns_config

    lines = markdown.split('\n')
    code_start_idx = next(i for i, line in enumerate(lines) if line.strip().startswith('```csharp'))

    heading, description = service._extract_context(lines, code_start_idx)

    assert description == "", f"Description should be filtered out (too short)"
    assert heading == "Title", f"Heading should not be filtered"


def test_context_extraction_disabled():
    """Test that context extraction can be completely disabled."""
    db = Database(":memory:")
    context_config = ContextExtractionConfig(enabled=False)
    patterns_config = DiscoveryPatternsConfig(context_extraction=context_config)
    service = DiscoveryService(db=db, filtering_config=patterns_config)
    service.discovery_patterns = patterns_config

    lines = SAMPLE_MARKDOWN.split('\n')
    code_start_idx = next(i for i, line in enumerate(lines) if line.strip() == '```csharp')

    heading, description = service._extract_context(lines, code_start_idx)

    assert heading == "", f"Heading should be empty when disabled"
    assert description == "", f"Description should be empty when disabled"


def test_context_extraction_performance():
    """Test that context extraction completes within 5ms per snippet."""
    db = Database(":memory:")
    large_markdown = "# Main Title\n\n"
    for i in range(10):
        large_markdown += f"## Section {i}\n\n"
        large_markdown += "This is a paragraph with some context. " * 10
        large_markdown += f"\n\n```csharp\nclass Test{i} {{ }}\n```\n\n"

    context_config = ContextExtractionConfig()
    patterns_config = DiscoveryPatternsConfig(context_extraction=context_config)
    service = DiscoveryService(db=db, filtering_config=patterns_config)
    service.discovery_patterns = patterns_config

    lines = large_markdown.split('\n')
    code_blocks = [i for i, line in enumerate(lines) if line.strip().startswith('```csharp')]

    start_time = time.perf_counter()
    for code_idx in code_blocks:
        service._extract_context(lines, code_idx)
    end_time = time.perf_counter()

    avg_time_ms = ((end_time - start_time) / len(code_blocks)) * 1000

    assert avg_time_ms < 5.0, f"Context extraction took {avg_time_ms:.2f}ms (threshold: 5ms)"
    print(f"  Performance: {avg_time_ms:.3f}ms per snippet")


def test_config_loading():
    """Test that configurations load correctly from JSON files."""
    try:
        config_mgr = ConfigurationManager(
            config_dir=Path("config/families"),
            global_config_path=Path("config/global.json")
        )

        global_config = config_mgr.load_global_config()

        assert global_config.discovery_patterns.context_extraction.max_paragraphs == 2
        assert global_config.discovery_patterns.context_extraction.include_file_header == False
        assert global_config.discovery_patterns.context_extraction.enabled == True

        print("  Global config loaded successfully")

        # Check zip family overrides
        zip_config = config_mgr.load_family_config("zip")
        if zip_config.discovery_patterns:
            assert zip_config.discovery_patterns.context_extraction.max_paragraphs == 3
            assert zip_config.discovery_patterns.context_extraction.include_file_header == True
            print("  Zip family overrides verified")

    except FileNotFoundError:
        print("  Warning: Config files not found, skipping config loading test")
        raise


def main():
    """Run all tests."""
    print("\n" + "="*70)
    print("CD-04: Context Extraction Configuration Tests")
    print("="*70 + "\n")

    tests = [
        ("Default context extraction", test_default_context_extraction),
        ("Max paragraphs limit", test_max_paragraphs_limit),
        ("Max heading distance", test_max_heading_distance),
        ("Include file header", test_include_file_header),
        ("Context window lines", test_context_window_lines),
        ("Min context length filter", test_min_context_length_filter),
        ("Context extraction disabled", test_context_extraction_disabled),
        ("Context extraction performance", test_context_extraction_performance),
        ("Configuration loading", test_config_loading),
    ]

    passed = 0
    failed = 0

    for test_name, test_func in tests:
        if run_test(test_name, test_func):
            passed += 1
        else:
            failed += 1

    print("\n" + "="*70)
    print(f"Results: {passed} passed, {failed} failed")
    print("="*70 + "\n")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
