"""
Unit tests for find_block_by_signature_fuzzy in src/utils/markdown_parser.py

Covers:
- Happy path: finds block matching first 5 normalized lines
- No match: returns []
- Ambiguous: returns multiple matches
- Empty original_code: returns []
- Normalization: whitespace and semicolon differences ignored
"""
import pytest
from src.utils.markdown_parser import (
    parse_fenced_blocks,
    find_block_by_signature_fuzzy,
)

SAMPLE_MD = """\
Some text before.

```csharp
var doc = new Document();
doc.Save("output.docx");
var para = doc.FirstSection.Body.FirstParagraph;
para.AppendChild(new Run(doc, "Hello"));
doc.Save("final.docx");
```

More text.

```csharp
var archive = new Archive();
archive.CreateEntry("test.txt", stream);
archive.Save("output.zip");
```
"""


def _get_blocks():
    return parse_fenced_blocks(SAMPLE_MD)


class TestFindBlockBySignatureFuzzy:
    def test_happy_path_finds_matching_block(self):
        blocks = _get_blocks()
        # Use the first block's content as original_code (exact match on first 5 lines)
        original = blocks[0]['content']
        matches = find_block_by_signature_fuzzy(blocks, original)
        assert len(matches) == 1
        assert matches[0]['block_index'] == 0

    def test_matches_with_trailing_whitespace_difference(self):
        blocks = _get_blocks()
        # Add trailing whitespace to first few lines — should still match
        original_lines = blocks[0]['content'].splitlines()
        modified_original = '\n'.join(
            line + '  ' for line in original_lines[:5]
        ) + '\n' + '\n'.join(original_lines[5:])
        matches = find_block_by_signature_fuzzy(blocks, modified_original)
        assert len(matches) == 1

    def test_no_match_returns_empty(self):
        blocks = _get_blocks()
        original = "completely different code that does not appear in any block"
        matches = find_block_by_signature_fuzzy(blocks, original)
        assert matches == []

    def test_empty_original_code_returns_empty(self):
        blocks = _get_blocks()
        matches = find_block_by_signature_fuzzy(blocks, "")
        assert matches == []

    def test_whitespace_only_original_returns_empty(self):
        blocks = _get_blocks()
        matches = find_block_by_signature_fuzzy(blocks, "   \n   \n   ")
        assert matches == []

    def test_ambiguous_match_returns_multiple(self):
        # Create markdown where two blocks share the same first 5 lines
        md = """\
```csharp
var x = 1;
var y = 2;
var z = 3;
var w = 4;
var v = 5;
// different suffix A
```

```csharp
var x = 1;
var y = 2;
var z = 3;
var w = 4;
var v = 5;
// different suffix B
```
"""
        blocks = parse_fenced_blocks(md)
        original = "var x = 1;\nvar y = 2;\nvar z = 3;\nvar w = 4;\nvar v = 5;\n// different suffix A"
        matches = find_block_by_signature_fuzzy(blocks, original)
        assert len(matches) == 2, f"Expected 2 ambiguous matches, got {len(matches)}"

    def test_second_block_matched_when_first_differs(self):
        blocks = _get_blocks()
        # Use second block's content
        original = blocks[1]['content']
        matches = find_block_by_signature_fuzzy(blocks, original)
        assert len(matches) == 1
        assert matches[0]['block_index'] == 1

    def test_head_lines_parameter_respected(self):
        blocks = _get_blocks()
        # Use only 1 line for comparison — should still find match
        original = blocks[0]['content']
        matches = find_block_by_signature_fuzzy(blocks, original, head_lines=1)
        # With head_lines=1, the first line "var doc = new Document();" should match block 0
        assert any(m['block_index'] == 0 for m in matches)
