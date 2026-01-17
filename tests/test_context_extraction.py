"""
Test suite for CD-04: Make Context Extraction Configurable
Tests the configurable context extraction feature in discovery_service.py
"""

import pytest
import time
from pathlib import Path
from unittest.mock import Mock

from src.core.config import ContextExtractionConfig, DiscoveryPatternsConfig
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


@pytest.fixture
def temp_db(tmp_path):
    """Create a temporary database for testing."""
    db_path = tmp_path / "test.db"
    db = Database(str(db_path))
    yield db
    # Cleanup is automatic with tmp_path


def _build_default_service(temp_db):
    """Create discovery service with default configuration."""
    patterns_config = DiscoveryPatternsConfig()
    service = DiscoveryService(
        db=temp_db,
        filtering_config=patterns_config
    )
    service.discovery_patterns = patterns_config
    return service


@pytest.fixture
def default_service(temp_db):
    """Create discovery service with default configuration."""
    return _build_default_service(temp_db)


def test_default_context_extraction(default_service):
    """Test that default context extraction works as before."""
    lines = SAMPLE_MARKDOWN.split('\n')

    # Find the first code block (starts at line with "```csharp")
    code_start_idx = next(i for i, line in enumerate(lines) if line.strip() == '```csharp')

    heading, description = default_service._extract_context(lines, code_start_idx)

    # Should extract "Section One" heading
    assert heading == "Section One"

    # Should extract 2 paragraphs (default max_paragraphs=2)
    assert "first paragraph" in description
    assert "Another paragraph" in description
    assert len(description) > 10  # Should pass min_context_length


def test_max_paragraphs_limit(temp_db):
    """Test that max_paragraphs limit is enforced."""
    # Configure with max_paragraphs=1
    context_config = ContextExtractionConfig(max_paragraphs=1)
    patterns_config = DiscoveryPatternsConfig(context_extraction=context_config)

    service = DiscoveryService(db=temp_db, filtering_config=patterns_config)
    service.discovery_patterns = patterns_config

    lines = SAMPLE_MARKDOWN.split('\n')
    code_start_idx = next(i for i, line in enumerate(lines) if line.strip() == '```csharp')

    heading, description = service._extract_context(lines, code_start_idx)

    # Should only capture 1 paragraph
    assert "Another paragraph" in description
    # Should not have both paragraphs separated by double newline
    assert description.count('\n\n') == 0


def test_max_heading_distance(temp_db):
    """Test max_heading_distance limits how far back we look for headings."""
    # Create markdown with heading far from code
    markdown = "# Title\n" + "\n" * 60 + "```csharp\nclass Test {}\n```"

    # With default max_heading_distance=50, should find heading
    context_config = ContextExtractionConfig(max_heading_distance=50)
    patterns_config = DiscoveryPatternsConfig(context_extraction=context_config)
    service = DiscoveryService(db=temp_db, filtering_config=patterns_config)
    service.discovery_patterns = patterns_config

    lines = markdown.split('\n')
    code_start_idx = next(i for i, line in enumerate(lines) if line.strip().startswith('```csharp'))

    heading, description = service._extract_context(lines, code_start_idx)

    # Heading is within 50 lines, but outside the context_window_lines (default 20)
    # So we should NOT find it with default context_window_lines=20
    assert heading == ""

    # Now test with larger context_window_lines
    context_config = ContextExtractionConfig(
        max_heading_distance=65,
        context_window_lines=65
    )
    patterns_config = DiscoveryPatternsConfig(context_extraction=context_config)
    service = DiscoveryService(db=temp_db, filtering_config=patterns_config)
    service.discovery_patterns = patterns_config

    heading, description = service._extract_context(lines, code_start_idx)

    # Now should find the heading
    assert heading == "Title"


def test_include_file_header(temp_db):
    """Test that file header is included when configured."""
    # Without file header
    context_config = ContextExtractionConfig(include_file_header=False)
    patterns_config = DiscoveryPatternsConfig(context_extraction=context_config)
    service = DiscoveryService(db=temp_db, filtering_config=patterns_config)
    service.discovery_patterns = patterns_config

    lines = SAMPLE_MARKDOWN.split('\n')
    code_start_idx = next(i for i, line in enumerate(lines) if line.strip() == '```csharp')

    heading, description = service._extract_context(lines, code_start_idx)

    assert "File: Main Title" not in description

    # With file header
    context_config = ContextExtractionConfig(include_file_header=True)
    patterns_config = DiscoveryPatternsConfig(context_extraction=context_config)
    service = DiscoveryService(db=temp_db, filtering_config=patterns_config)
    service.discovery_patterns = patterns_config

    heading, description = service._extract_context(lines, code_start_idx)

    # Should include file header
    assert "File: Main Title" in description


def test_context_window_lines(temp_db):
    """Test that context_window_lines controls the search window."""
    # Create markdown with content beyond default window
    markdown = "# Title\n" + "Content line\n" * 30 + "Near code\n```csharp\nclass Test {}\n```"

    # With small window, should not capture distant content
    context_config = ContextExtractionConfig(context_window_lines=5)
    patterns_config = DiscoveryPatternsConfig(context_extraction=context_config)
    service = DiscoveryService(db=temp_db, filtering_config=patterns_config)
    service.discovery_patterns = patterns_config

    lines = markdown.split('\n')
    code_start_idx = next(i for i, line in enumerate(lines) if line.strip().startswith('```csharp'))

    heading, description = service._extract_context(lines, code_start_idx)

    # Should only capture recent content
    assert "Near code" in description

    # With larger window
    context_config = ContextExtractionConfig(context_window_lines=35)
    patterns_config = DiscoveryPatternsConfig(context_extraction=context_config)
    service = DiscoveryService(db=temp_db, filtering_config=patterns_config)
    service.discovery_patterns = patterns_config

    heading, description = service._extract_context(lines, code_start_idx)

    # Should find the title heading now
    assert heading == "Title"


def test_min_context_length_filter(temp_db):
    """Test that min_context_length filters out too-short context."""
    markdown = "# Title\n\nShort\n\n```csharp\nclass Test {}\n```"

    # With high min_context_length, should filter out
    context_config = ContextExtractionConfig(min_context_length=50)
    patterns_config = DiscoveryPatternsConfig(context_extraction=context_config)
    service = DiscoveryService(db=temp_db, filtering_config=patterns_config)
    service.discovery_patterns = patterns_config

    lines = markdown.split('\n')
    code_start_idx = next(i for i, line in enumerate(lines) if line.strip().startswith('```csharp'))

    heading, description = service._extract_context(lines, code_start_idx)

    # Description should be filtered out (too short)
    assert description == ""
    assert heading == "Title"  # Heading is separate, not filtered

    # With low min_context_length, should keep
    context_config = ContextExtractionConfig(min_context_length=3)
    patterns_config = DiscoveryPatternsConfig(context_extraction=context_config)
    service = DiscoveryService(db=temp_db, filtering_config=patterns_config)
    service.discovery_patterns = patterns_config

    heading, description = service._extract_context(lines, code_start_idx)

    assert description == "Short"


def test_context_extraction_disabled(temp_db):
    """Test that context extraction can be completely disabled."""
    # Disable context extraction
    context_config = ContextExtractionConfig(enabled=False)
    patterns_config = DiscoveryPatternsConfig(context_extraction=context_config)
    service = DiscoveryService(db=temp_db, filtering_config=patterns_config)
    service.discovery_patterns = patterns_config

    lines = SAMPLE_MARKDOWN.split('\n')
    code_start_idx = next(i for i, line in enumerate(lines) if line.strip() == '```csharp')

    heading, description = service._extract_context(lines, code_start_idx)

    # Both should be empty when disabled
    assert heading == ""
    assert description == ""


def test_context_extraction_performance(temp_db):
    """Test that context extraction completes within 5ms per snippet."""
    # Create a larger markdown document
    large_markdown = "# Main Title\n\n"
    for i in range(10):
        large_markdown += f"## Section {i}\n\n"
        large_markdown += "This is a paragraph with some context. " * 10
        large_markdown += "\n\n```csharp\nclass Test{i} {{ }}\n```\n\n"

    context_config = ContextExtractionConfig()
    patterns_config = DiscoveryPatternsConfig(context_extraction=context_config)
    service = DiscoveryService(db=temp_db, filtering_config=patterns_config)
    service.discovery_patterns = patterns_config

    lines = large_markdown.split('\n')
    code_blocks = [i for i, line in enumerate(lines) if line.strip().startswith('```csharp')]

    # Measure time for multiple extractions
    start_time = time.perf_counter()
    for code_idx in code_blocks:
        service._extract_context(lines, code_idx)
    end_time = time.perf_counter()

    avg_time_ms = ((end_time - start_time) / len(code_blocks)) * 1000

    # Should complete in less than 5ms per snippet
    assert avg_time_ms < 5.0, f"Context extraction took {avg_time_ms:.2f}ms (threshold: 5ms)"


def test_context_extraction_with_zero_max_paragraphs(temp_db):
    """Test edge case: max_paragraphs=0 should not extract paragraphs."""
    context_config = ContextExtractionConfig(max_paragraphs=0)
    patterns_config = DiscoveryPatternsConfig(context_extraction=context_config)
    service = DiscoveryService(db=temp_db, filtering_config=patterns_config)
    service.discovery_patterns = patterns_config

    lines = SAMPLE_MARKDOWN.split('\n')
    code_start_idx = next(i for i, line in enumerate(lines) if line.strip() == '```csharp')

    heading, description = service._extract_context(lines, code_start_idx)

    # Should still get heading
    assert heading == "Section One"

    # But no description (0 paragraphs)
    # However, if there's a file header, it might still be there
    # Let's test without file header
    if not service.discovery_patterns.context_extraction.include_file_header:
        # Description should be empty or filtered by min_context_length
        assert len(description) < 10 or description == ""


def test_backward_compatibility(temp_db):
    """Test that default config matches original hardcoded behavior."""
    # Original behavior: max_paragraphs=2, enabled, no file header
    service = _build_default_service(temp_db)

    lines = SAMPLE_MARKDOWN.split('\n')
    code_start_idx = next(i for i, line in enumerate(lines) if line.strip() == '```csharp')

    heading, description = service._extract_context(lines, code_start_idx)

    # Should match original behavior
    assert heading == "Section One"
    assert "first paragraph" in description
    assert "Another paragraph" in description
    assert "File:" not in description  # No file header by default


def test_family_config_override(temp_db):
    """Test that family config can override global context settings."""
    from src.core.config import ConfigurationManager

    # Load actual configs
    config_mgr = ConfigurationManager(
        config_dir=Path("c:/Users/prora/OneDrive/Documents/GitHub/example-reviewer/config/families"),
        global_config_path=Path("c:/Users/prora/OneDrive/Documents/GitHub/example-reviewer/config/global.json")
    )

    global_config = config_mgr.load_global_config()

    # Check global defaults
    assert global_config.discovery_patterns.context_extraction.max_paragraphs == 2
    assert global_config.discovery_patterns.context_extraction.include_file_header == False

    # Check zip family overrides
    zip_config = config_mgr.load_family_config("zip")
    if zip_config.discovery_patterns:
        assert zip_config.discovery_patterns.context_extraction.max_paragraphs == 3
        assert zip_config.discovery_patterns.context_extraction.include_file_header == True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
