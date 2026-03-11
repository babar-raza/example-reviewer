"""
Tests for frontmatter intent extraction and allow_cross_block_variable_context gate.
"""
import pytest
from unittest.mock import MagicMock
from src.services.discovery_service import DiscoveryService
from src.core.config import DiscoveryPatternsConfig


def make_ds(allow_cross_block=False):
    """Create a DiscoveryService with minimal setup for unit tests."""
    ds = DiscoveryService.__new__(DiscoveryService)
    ds.db = None
    ds.content_roots = []
    ds.global_config = None
    ds.family_config = None
    ds.filter_stats = {'total_checked': 0, 'filtered_out': 0, 'reasons': {}, 'filtered_gists': 0}
    ds.skipped_candidates = []
    dp = DiscoveryPatternsConfig(
        allow_cross_block_variable_context=allow_cross_block,
        require_code_indicators=[],
    )
    ds.discovery_patterns = dp
    ds.filtering_config = dp
    return ds


# ── _extract_frontmatter_intent tests ─────────────────────────────────────────

def test_extract_frontmatter_full():
    """Happy path: title + description + steps all present."""
    ds = make_ds()
    content = (
        "---\n"
        "title: \"How to Remove Blank Pages\"\n"
        "description: \"Remove blank pages from Word docs using C#\"\n"
        "step1: \"Load document\"\n"
        "step2: \"Detect blank pages\"\n"
        "step3: \"Save cleaned doc\"\n"
        "---\n"
        "\nSome article content.\n"
    )
    intent = ds._extract_frontmatter_intent(content)
    assert intent is not None
    assert "How to Remove Blank Pages" in intent
    assert "Remove blank pages" in intent
    assert "Load document" in intent
    assert "Detect blank pages" in intent
    assert "Save cleaned doc" in intent


def test_extract_frontmatter_title_only():
    """Only title present — still returns intent."""
    ds = make_ds()
    content = "---\ntitle: \"My Article\"\n---\nContent.\n"
    intent = ds._extract_frontmatter_intent(content)
    assert intent is not None
    assert "My Article" in intent


def test_extract_frontmatter_no_frontmatter():
    """No YAML frontmatter — returns None."""
    ds = make_ds()
    content = "# Just a heading\n\nSome content.\n"
    intent = ds._extract_frontmatter_intent(content)
    assert intent is None


def test_extract_frontmatter_empty_keys():
    """Frontmatter present but none of title/description/steps — returns None."""
    ds = make_ds()
    content = "---\ndraft: false\nweight: 8\n---\nContent.\n"
    intent = ds._extract_frontmatter_intent(content)
    assert intent is None


def test_extract_frontmatter_malformed_yaml():
    """Malformed YAML — returns None gracefully."""
    ds = make_ds()
    content = "---\ntitle: [unclosed\n---\nContent.\n"
    intent = ds._extract_frontmatter_intent(content)
    assert intent is None


def test_extract_frontmatter_step_truncation():
    """Steps stop at first missing step (gap in numbering)."""
    ds = make_ds()
    content = (
        "---\n"
        "title: \"Test\"\n"
        "step1: \"Step one\"\n"
        "step2: \"Step two\"\n"
        "step4: \"Step four (gap — should NOT appear)\"\n"
        "---\n"
    )
    intent = ds._extract_frontmatter_intent(content)
    assert "Step one" in intent
    assert "Step two" in intent
    assert "Step four" not in intent  # Gap at step3 stops extraction


def test_extract_frontmatter_cap_at_800_chars():
    """Intent string is capped at 800 characters."""
    ds = make_ds()
    long_desc = "X" * 1000
    content = f"---\ntitle: \"T\"\ndescription: \"{long_desc}\"\n---\n"
    intent = ds._extract_frontmatter_intent(content)
    assert intent is not None
    assert len(intent) <= 800


def test_extract_frontmatter_description_truncated_at_300():
    """Description is truncated at 300 chars within the intent."""
    ds = make_ds()
    long_desc = "D" * 500
    content = f"---\ntitle: \"T\"\ndescription: \"{long_desc}\"\n---\n"
    intent = ds._extract_frontmatter_intent(content)
    assert intent is not None
    # The description in the intent should be ≤ 300 chars (before overall cap)
    lines = intent.split('\n')
    summary_line = next((l for l in lines if l.startswith('Summary:')), None)
    assert summary_line is not None
    assert len(summary_line) <= len("Summary: ") + 300


# ── allow_cross_block_variable_context tests ──────────────────────────────────

FRAGMENT_WITH_UNDECLARED = """\
Document finalDoc = (Document)originalDoc.Clone(false);
finalDoc.RemoveAllChildren();

blankPages.Add(totalPages);

for (int i = 1; i < blankPages.Count; i++)
{
    int index = (int)blankPages[i - 1] + 1;
    int count = (int)blankPages[i] - index;

    if (count > 0)
        finalDoc.AppendDocument(originalDoc.ExtractPages(index, count), ImportFormatMode.KeepSourceFormatting);
}
"""


def test_cross_block_false_blocks_fragment():
    """Without the flag, a short fragment using variables declared in a prior block is filtered.

    blankPages and originalDoc are declared in a different code block (multi-block tutorial).
    With allow_cross_block_variable_context=False, this should be rejected.
    """
    ds = make_ds(allow_cross_block=False)
    ok, reason = ds.filter_snippet(FRAGMENT_WITH_UNDECLARED)
    assert not ok, f"Expected filtered but got ok=True, reason={reason!r}"
    assert reason == "fragment_undeclared_context_variable"


def test_cross_block_true_allows_fragment():
    """With allow_cross_block_variable_context=True, same fragment passes variable check."""
    ds = make_ds(allow_cross_block=True)
    ok, reason = ds.filter_snippet(FRAGMENT_WITH_UNDECLARED)
    # Should NOT be filtered for undeclared variable reason
    if not ok:
        assert "undeclared" not in reason and "outer_context" not in reason, (
            f"Expected cross-block flag to suppress undeclared check, but got: {reason!r}"
        )
