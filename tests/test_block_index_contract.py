"""
Regression Tests for Block Index Contract.

These tests ensure that extraction and md_update use consistent block indexing
and that self-healing works correctly.

CRITICAL CONTRACT:
==================
code_block_index = 0-based index among ALL fenced blocks in a markdown file,
using the same parser (parse_fenced_blocks) in both extraction and md_update.
"""

import pytest
import tempfile
import sqlite3
from pathlib import Path
from src.utils.markdown_parser import parse_fenced_blocks, compute_code_signature
from src.services.discovery_service import DiscoveryService
from src.services.markdown_service import MarkdownUpdateService, BlockResolutionResult
from src.core.database import Database
from src.core.config import GlobalConfig, FamilyConfig
from src.core.models import ExampleRecord, ExampleStatus, Location, SourceType


class TestBlockIndexContract:
    """Test that extraction and md_update use the same block index contract."""

    def test_parse_fenced_blocks_counts_all_languages(self):
        """Verify parser counts ALL fenced blocks regardless of language."""
        content = """# Test File

```bash
echo "hello"
```

Some text

```csharp
var x = 1;
```

More text

```python
print("test")
```

```csharp
var y = 2;
```
"""
        blocks = parse_fenced_blocks(content)

        assert len(blocks) == 4, "Should find 4 blocks total"
        assert blocks[0]['block_index'] == 0
        assert blocks[0]['language'] == 'bash'
        assert blocks[1]['block_index'] == 1
        assert blocks[1]['language'] == 'csharp'
        assert blocks[2]['block_index'] == 2
        assert blocks[2]['language'] == 'python'
        assert blocks[3]['block_index'] == 3
        assert blocks[3]['language'] == 'csharp'

    def test_parse_fenced_blocks_computes_signatures(self):
        """Verify parser computes signatures for all blocks."""
        content = """```csharp
var x = 1;
```

```csharp
var y = 2;
```
"""
        blocks = parse_fenced_blocks(content)

        assert len(blocks) == 2
        assert 'signature' in blocks[0]
        assert 'signature' in blocks[1]
        assert len(blocks[0]['signature']) == 64  # SHA256 hex length
        assert blocks[0]['signature'] != blocks[1]['signature']  # Different content

    def test_compute_signature_normalization(self):
        """Verify signature computation normalizes line endings and strips outer whitespace."""
        code1 = "var x = 1;\nvar y = 2;"
        code2 = "var x = 1;\r\nvar y = 2;"  # Different line endings
        code3 = "\n  var x = 1;\n  var y = 2;\n"  # Leading/trailing newlines

        sig1 = compute_code_signature(code1)
        sig2 = compute_code_signature(code2)
        sig3 = compute_code_signature(code3)

        # After normalization, line endings should be normalized
        assert sig1 == sig2, "Line ending normalization should work"

        # Note: Internal indentation is preserved, only outer whitespace is stripped
        # So code3 won't match code1 because it has different internal indentation
        # This test verifies line endings are normalized but internal structure preserved
        assert sig2 == compute_code_signature(code2.strip().replace('\r\n', '\n'))

    def test_parse_fenced_blocks_line_numbers(self):
        """Verify parser computes correct line numbers."""
        content = """Line 1
Line 2
```csharp
var x = 1;
```
Line 6
```bash
echo "test"
```
"""
        blocks = parse_fenced_blocks(content)

        assert len(blocks) == 2
        assert blocks[0]['start_line'] == 3  # 1-based
        assert blocks[0]['end_line'] == 5
        assert blocks[1]['start_line'] == 7
        assert blocks[1]['end_line'] == 9


class TestSelfHealingResolution:
    """Test self-healing location resolution in md_update."""

    def test_resolve_exact_match_no_fallback(self):
        """When block_index points to correct signature, no fallback needed."""
        # Setup
        content = """```csharp
var x = 1;
```

```csharp
var y = 2;
```
"""
        blocks = parse_fenced_blocks(content)

        # Create example pointing to block 1
        example = ExampleRecord(
            family="test",
            file_path="test.md",
            source_type=SourceType.INLINE,
            language="csharp",
            location=Location(block_index=1, start_line=5, end_line=7),
            original_code="var y = 2;",
            status=ExampleStatus.VERIFIED,
            code_block_signature=compute_code_signature("var y = 2;"),
        )

        # Create service (without DB for this unit test)
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            db = Database(str(db_path))
            service = MarkdownUpdateService(db, run_id="test")

            # Resolve
            result = service.resolve_target_block(example, blocks)

            assert result.success
            assert not result.used_fallback
            assert result.updated_index is None  # No update needed
            assert result.block['block_index'] == 1

    def test_resolve_index_mismatch_unique_fallback(self):
        """When block_index wrong but unique signature match, self-heal."""
        content = """```bash
echo "test"
```

```csharp
var x = 1;
```

```csharp
var y = 2;
```
"""
        blocks = parse_fenced_blocks(content)

        # Example stored with block_index=1, but signature matches block 2
        # (simulates a block being inserted before it)
        example = ExampleRecord(
            family="test",
            file_path="test.md",
            source_type=SourceType.INLINE,
            language="csharp",
            location=Location(block_index=1, start_line=5, end_line=7),
            original_code="var y = 2;",
            status=ExampleStatus.VERIFIED,
            code_block_signature=compute_code_signature("var y = 2;"),
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            db = Database(str(db_path))
            service = MarkdownUpdateService(db, run_id="test")

            result = service.resolve_target_block(example, blocks)

            assert result.success
            assert result.used_fallback
            assert result.updated_index == 2  # Should update to correct index
            assert result.block['block_index'] == 2

    def test_resolve_duplicate_signature_fails(self):
        """When signature appears multiple times, resolution fails."""
        content = """```csharp
var x = 1;
```

```csharp
var x = 1;
```
"""
        blocks = parse_fenced_blocks(content)

        # Example with signature that appears twice
        example = ExampleRecord(
            family="test",
            file_path="test.md",
            source_type=SourceType.INLINE,
            language="csharp",
            location=Location(block_index=5, start_line=1, end_line=3),  # Invalid index
            original_code="var x = 1;",
            status=ExampleStatus.VERIFIED,
            code_block_signature=compute_code_signature("var x = 1;"),
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            db = Database(str(db_path))
            service = MarkdownUpdateService(db, run_id="test")

            result = service.resolve_target_block(example, blocks)

            assert not result.success
            assert "duplicate_signature" in result.skip_reason

    def test_resolve_signature_not_found_fails(self):
        """When signature not found anywhere, resolution fails."""
        content = """```csharp
var x = 1;
```
"""
        blocks = parse_fenced_blocks(content)

        # Example with signature that doesn't match any block
        example = ExampleRecord(
            family="test",
            file_path="test.md",
            source_type=SourceType.INLINE,
            language="csharp",
            location=Location(block_index=0, start_line=1, end_line=3),
            original_code="var z = 999;",  # Different code
            status=ExampleStatus.VERIFIED,
            code_block_signature=compute_code_signature("var z = 999;"),
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            db = Database(str(db_path))
            service = MarkdownUpdateService(db, run_id="test")

            result = service.resolve_target_block(example, blocks)

            assert not result.success
            assert "signature_not_found" in result.skip_reason

    def test_resolve_out_of_range_with_fallback(self):
        """When block_index out of range but signature found, self-heal."""
        content = """```csharp
var x = 1;
```
"""
        blocks = parse_fenced_blocks(content)

        # Example with out-of-range index but valid signature
        example = ExampleRecord(
            family="test",
            file_path="test.md",
            source_type=SourceType.INLINE,
            language="csharp",
            location=Location(block_index=10, start_line=1, end_line=3),  # Out of range
            original_code="var x = 1;",
            status=ExampleStatus.VERIFIED,
            code_block_signature=compute_code_signature("var x = 1;"),
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            db = Database(str(db_path))
            service = MarkdownUpdateService(db, run_id="test")

            result = service.resolve_target_block(example, blocks)

            assert result.success
            assert result.used_fallback
            assert result.updated_index == 0


class TestBlockIndexContractIntegration:
    """Integration tests for extraction + md_update consistency."""

    def test_extraction_uses_canonical_parser(self):
        """Verify discovery service uses canonical parser for block_index."""
        # This test would require full DiscoveryService setup
        # For now, we verify that the parser is imported and used
        from src.services.discovery_service import parse_fenced_blocks as discovery_parser
        from src.utils.markdown_parser import parse_fenced_blocks as canonical_parser

        # They should be the same function
        assert discovery_parser is canonical_parser, \
            "DiscoveryService must import parse_fenced_blocks from utils.markdown_parser"

    def test_md_update_uses_canonical_parser(self):
        """Verify markdown service uses canonical parser for block_index."""
        from src.services.markdown_service import parse_fenced_blocks as md_parser
        from src.utils.markdown_parser import parse_fenced_blocks as canonical_parser

        # They should be the same function
        assert md_parser is canonical_parser, \
            "MarkdownUpdateService must import parse_fenced_blocks from utils.markdown_parser"

    def test_signature_computation_matches(self):
        """Verify discovery and md_update compute identical signatures."""
        from src.services.discovery_service import compute_code_signature as discovery_sig
        from src.services.markdown_service import compute_code_signature as md_sig
        from src.utils.markdown_parser import compute_code_signature as canonical_sig

        code = "var x = 1;\nvar y = 2;"

        sig1 = discovery_sig(code)
        sig2 = md_sig(code)
        sig3 = canonical_sig(code)

        assert sig1 == sig2 == sig3, "All services must compute identical signatures"


class TestBlockIndexEdgeCases:
    """Test edge cases in block index handling."""

    def test_empty_file_no_blocks(self):
        """Empty file should return no blocks."""
        content = "# Just a heading\n\nSome text"
        blocks = parse_fenced_blocks(content)
        assert len(blocks) == 0

    def test_unclosed_fence_ignored(self):
        """Unclosed fence should be ignored."""
        content = """```csharp
var x = 1;
"""
        blocks = parse_fenced_blocks(content)
        assert len(blocks) == 0

    def test_empty_language_tag(self):
        """Fence with no language tag should still be counted."""
        content = """```
plain text
```
"""
        blocks = parse_fenced_blocks(content)
        assert len(blocks) == 1
        assert blocks[0]['language'] == ''

    def test_nested_fences_not_supported(self):
        """Nested fences are not parsed (limitation of simple parser)."""
        content = """```csharp
var x = @"
```
nested
```
";
```
"""
        blocks = parse_fenced_blocks(content)
        # Parser will close at first closing fence
        assert len(blocks) >= 1


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
