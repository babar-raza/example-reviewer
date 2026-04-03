"""
SR-03 — Unit tests for the Phase E structurally_flagged logic in
Orchestrator._run_final_review_phase().

We test the grouping logic in isolation: given a set of examples in auto_pass_files
(no LLM-fixed examples) and a _article_validation_results dict that contains a
filename_mismatch finding for one file, that file must be moved into the review set
(files dict) rather than being auto-passed.
"""

import pytest
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Helper — build minimal Orchestrator-like object without real services
# ---------------------------------------------------------------------------

def _build_grouping_state(
    file_path: str,
    validation_findings: list,
    llm_fixed_ids: set,
):
    """
    Build the minimal state dicts that the structurally_flagged block operates on.
    Returns (files, auto_pass_files) after applying the same grouping + promotion
    logic as _run_final_review_phase().
    """
    from src.core.models import ExampleRecord, ExampleStatus

    # Create a single example record for the given file path (no LLM fix)
    example = MagicMock(spec=ExampleRecord)
    example.example_id = "ex-001"
    example.file_path = file_path

    files = {}
    auto_pass_files = {}
    only_review_llm_fixed = True

    # ---- Grouping loop (mirrors orchestrator logic) ----
    has_llm_fixed = any(
        e.example_id in llm_fixed_ids for e in [example]
    )
    if only_review_llm_fixed and not has_llm_fixed:
        auto_pass_files.setdefault(file_path, []).append(example)
    else:
        files.setdefault(file_path, []).append(example)

    # ---- Merge: any file with an LLM-fixed example pulls rest in ----
    for fk, fexs in list(auto_pass_files.items()):
        if fk in files:
            files[fk].extend(fexs)
            del auto_pass_files[fk]

    # ---- structurally_flagged promotion (the code under test) ----
    article_validation_results = {file_path: validation_findings}
    structurally_flagged = {
        fp
        for fp, findings in article_validation_results.items()
        if any(f.get("type") == "filename_mismatch" for f in findings)
        and fp in auto_pass_files
    }
    for fp in structurally_flagged:
        files[fp] = auto_pass_files.pop(fp)

    return files, auto_pass_files


# ---------------------------------------------------------------------------
# SR-03 tests
# ---------------------------------------------------------------------------

class TestStructurallyFlagged:
    def test_filename_mismatch_moves_file_to_review_set(self):
        """A file with filename_mismatch finding must move from auto_pass to review set."""
        fp = "/content/kb/how-to-forms.md"
        findings = [{"type": "filename_mismatch", "severity": "warning",
                     "message": "Prose references X but code uses Y"}]

        files, auto_pass = _build_grouping_state(
            file_path=fp,
            validation_findings=findings,
            llm_fixed_ids=set(),  # no LLM-fixed examples in this file
        )

        assert fp in files, "filename_mismatch file should be in review set"
        assert fp not in auto_pass, "filename_mismatch file should NOT be auto-passed"

    def test_no_filename_mismatch_stays_in_auto_pass(self):
        """A file with only unrelated findings must NOT be promoted."""
        fp = "/content/kb/normal-article.md"
        findings = [{"type": "duplicate_prose", "severity": "warning",
                     "message": "Some overlap"}]

        files, auto_pass = _build_grouping_state(
            file_path=fp,
            validation_findings=findings,
            llm_fixed_ids=set(),
        )

        assert fp not in files, "File with no filename_mismatch should not be in review set"
        assert fp in auto_pass, "File with no filename_mismatch should stay in auto_pass"

    def test_no_findings_stays_in_auto_pass(self):
        """A file with zero findings must stay auto-passed."""
        fp = "/content/kb/clean-article.md"

        files, auto_pass = _build_grouping_state(
            file_path=fp,
            validation_findings=[],
            llm_fixed_ids=set(),
        )

        assert fp not in files
        assert fp in auto_pass

    def test_llm_fixed_file_already_in_review_unaffected(self):
        """A file that already has LLM-fixed examples is in files regardless."""
        fp = "/content/kb/llm-fixed.md"
        findings = [{"type": "filename_mismatch", "severity": "warning",
                     "message": "mismatch"}]

        files, auto_pass = _build_grouping_state(
            file_path=fp,
            validation_findings=findings,
            llm_fixed_ids={"ex-001"},  # this example is LLM-fixed
        )

        # File enters files dict via the normal LLM-fixed path, not auto_pass
        assert fp in files
        assert fp not in auto_pass
