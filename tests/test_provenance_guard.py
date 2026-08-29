"""
Regression tests for provenance guard.

These tests ensure that the system CANNOT perform markdown updates
without proper provenance (verified examples from the pipeline).

This prevents the anti-pattern of "manually editing content .md files
just to pass reviews" by enforcing that all updates come from the
verify→fix→verify loop.
"""

import pytest
import tempfile
from pathlib import Path
from datetime import datetime

from src.core.models import (
    ExampleRecord,
    ExampleStatus,
    Location,
    SourceType,
)
from src.core.provenance_guard import (
    validate_provenance,
    validate_batch_provenance,
    ProvenanceViolationError,
    generate_provenance_report,
)
from src.core.database import Database
from src.services.markdown_service import MarkdownUpdateService
from tests.conftest import make_pdp
from src.utils.markdown_parser import compute_code_signature


class TestProvenanceGuard:
    """Test provenance validation logic."""

    def test_provenance_requires_verified_code(self):
        """
        REGRESSION: Provenance validation must fail if example has no verified_code.

        This prevents updating markdown with unverified code.
        """
        example = ExampleRecord(
            example_id="test123",
            file_path="test.md",
            family="test",
            language="csharp",
            status=ExampleStatus.VERIFIED,  # Status is VERIFIED...
            original_code="// code",
            verified_code=None,  # ...but no verified_code!
            location=Location(block_index=0, start_line=1, end_line=5),
            source_type=SourceType.INLINE,
        )

        with pytest.raises(ProvenanceViolationError) as exc_info:
            validate_provenance(example)

        assert "has no verified_code" in str(exc_info.value)

    def test_provenance_requires_verified_status(self):
        """
        REGRESSION: Provenance validation must fail if example is not VERIFIED or MD_UPDATED.

        This prevents updating markdown with examples that haven't passed the pipeline.
        """
        example = ExampleRecord(
            example_id="test456",
            file_path="test.md",
            family="test",
            language="csharp",
            status=ExampleStatus.DISCOVERED,  # Only DISCOVERED, not VERIFIED
            original_code="// code",
            verified_code="// fixed code",  # Has verified code
            location=Location(block_index=0, start_line=1, end_line=5),
            source_type=SourceType.INLINE,
        )

        with pytest.raises(ProvenanceViolationError) as exc_info:
            validate_provenance(example, require_verified=True)

        assert "VERIFIED or MD_UPDATED" in str(exc_info.value)
        assert "DISCOVERED" in str(exc_info.value)

    def test_provenance_succeeds_with_valid_example(self):
        """
        Provenance validation should succeed for properly verified examples.
        """
        example = ExampleRecord(
            example_id="test789",
            file_path="test.md",
            family="test",
            language="csharp",
            status=ExampleStatus.VERIFIED,
            original_code="// original",
            verified_code="// fixed and verified",
            location=Location(block_index=0, start_line=1, end_line=5),
            source_type=SourceType.INLINE,
        )

        signal = validate_provenance(example, require_verified=True)

        assert signal.example_id == "test789"
        assert signal.verification_status == ExampleStatus.VERIFIED
        assert "test789" in signal.source_description
        assert signal.verified_code_hash is not None

    def test_batch_provenance_validates_all_examples(self):
        """
        Batch provenance validation should validate all examples or fail entirely.
        """
        good_example = ExampleRecord(
            example_id="good",
            file_path="test.md",
            family="test",
            language="csharp",
            status=ExampleStatus.VERIFIED,
            original_code="// code",
            verified_code="// fixed",
            location=Location(block_index=0, start_line=1, end_line=5),
            source_type=SourceType.INLINE,
        )

        bad_example = ExampleRecord(
            example_id="bad",
            file_path="test.md",
            family="test",
            language="csharp",
            status=ExampleStatus.COMPILE_FAILED,  # Failed compilation
            original_code="// bad code",
            compilable_code=None,
            verified_code="// attempted fix",
            location=Location(block_index=1, start_line=6, end_line=10),
            source_type=SourceType.INLINE,
        )

        # Should fail because one example is not verified
        with pytest.raises(ProvenanceViolationError):
            validate_batch_provenance([good_example, bad_example])

        # Should succeed with only good examples
        signals = validate_batch_provenance([good_example, good_example])
        assert len(signals) == 2

    def test_provenance_report_generation(self):
        """
        Provenance reports should contain audit trail information.
        """
        example = ExampleRecord(
            example_id="report_test",
            file_path="test.md",
            family="test",
            language="csharp",
            status=ExampleStatus.VERIFIED,
            original_code="// code",
            verified_code="// fixed",
            location=Location(block_index=0, start_line=1, end_line=5),
            source_type=SourceType.INLINE,
        )

        signal = validate_provenance(example)
        report = generate_provenance_report([signal], "test.md")

        assert report["file"] == "test.md"
        assert report["examples_updated"] == 1
        assert len(report["provenance"]) == 1

        prov = report["provenance"][0]
        assert prov["example_id"] == "report_test"
        assert prov["status"] == "VERIFIED"
        assert prov["code_hash"] is not None


class TestMarkdownServiceProvenanceIntegration:
    """Test provenance guard integration with MarkdownUpdateService."""

    @pytest.fixture
    def temp_db(self):
        """Create temporary database for testing."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        db = Database(Path(db_path))

        # Initialize database schema
        db.initialize_schema()

        yield db

        # Cleanup
        Path(db_path).unlink(missing_ok=True)

    @pytest.fixture
    def temp_markdown_file(self):
        """Create temporary markdown file with code block."""
        content = """# Test Document

Some text here.

```csharp
// Original code
var x = 1;
```

More text.
"""
        with tempfile.NamedTemporaryFile(
            mode='w', suffix=".md", delete=False, encoding='utf-8'
        ) as f:
            f.write(content)
            f.flush()
            yield f.name

        # Cleanup
        Path(f.name).unlink(missing_ok=True)

    def test_markdown_service_blocks_unverified_examples(self, temp_db, temp_markdown_file):
        """
        CRITICAL REGRESSION TEST: MarkdownUpdateService must block updates
        when examples lack proper provenance.

        This is the PRIMARY DEFENSE against manual-edit-to-pass behavior.
        """
        # Create run in database first (FK constraint requirement)
        run_id = temp_db.create_run("test", "provenance_test_run_001")

        # Compute signature of the original code block in the temp file
        original_code_in_file = "// Original code\nvar x = 1;"
        code_sig = compute_code_signature(original_code_in_file)

        # Create an example that has VERIFIED status but NO verified_code
        # This simulates the anti-pattern: manually setting status without going through verification
        example = ExampleRecord(
            example_id="unverified_example",
            file_path=temp_markdown_file,
            family="test",
            language="csharp",
            status=ExampleStatus.VERIFIED,  # Status says VERIFIED...
            original_code=original_code_in_file,
            verified_code=None,  # ...but no verified_code! This is the provenance violation
            code_block_signature=code_sig,  # Signature for markdown service
            location=Location(
                block_index=0,
                start_line=5,
                end_line=8,
                code_signature=code_sig,
            ),
            source_type=SourceType.INLINE,
        )

        # Save example to database
        temp_db.save_example(example, run_id=run_id)

        # Create markdown service with provenance enforcement
        with tempfile.TemporaryDirectory() as artifacts_dir:
            service = MarkdownUpdateService(
                db=temp_db,
                artifacts_dir=Path(artifacts_dir),
                pdp=make_pdp(allow_writes=True),  # Enable writes
                use_workspace_copy=False,
                run_id=run_id,
            )

            # Attempt to update markdown - MUST FAIL
            with pytest.raises(ProvenanceViolationError) as exc_info:
                service.update_markdown_file(temp_markdown_file, dry_run=False)

            # Verify error message is clear
            error_msg = str(exc_info.value)
            assert "has no verified_code" in error_msg
            assert "Cannot update markdown without verified code from pipeline" in error_msg

    def test_markdown_service_allows_verified_examples(self, temp_db, temp_markdown_file):
        """
        MarkdownUpdateService should allow updates when examples are properly verified.
        """
        # Create run in database first (FK constraint requirement)
        run_id = temp_db.create_run("test", "provenance_test_run_002")

        # Compute signature of the original code block in the temp file
        original_code_in_file = "// Original code\nvar x = 1;"
        code_sig = compute_code_signature(original_code_in_file)

        # Create a VERIFIED example
        example = ExampleRecord(
            example_id="verified_example",
            file_path=temp_markdown_file,
            family="test",
            language="csharp",
            status=ExampleStatus.VERIFIED,  # VERIFIED status
            original_code=original_code_in_file,
            verified_code="// fixed code\nvar x = 2;",  # Verified code
            code_block_signature=code_sig,  # Signature for markdown service
            location=Location(
                block_index=0,
                start_line=5,
                end_line=8,
                code_signature=code_sig,  # Signature of original block
            ),
            source_type=SourceType.INLINE,
        )

        # Save example to database
        temp_db.save_example(example, run_id=run_id)

        # Create markdown service with provenance enforcement
        with tempfile.TemporaryDirectory() as artifacts_dir:
            service = MarkdownUpdateService(
                db=temp_db,
                artifacts_dir=Path(artifacts_dir),
                pdp=make_pdp(allow_writes=True),
                use_workspace_copy=False,
                run_id=run_id,
            )

            # Attempt to update markdown - SHOULD SUCCEED
            success, changes = service.update_markdown_file(temp_markdown_file, dry_run=False)

            # Verify update succeeded
            assert success is True
            assert len(changes) == 1

            # Verify provenance report was created
            provenance_dir = Path(artifacts_dir) / "provenance"
            assert provenance_dir.exists()
            report_files = list(provenance_dir.glob("*.json"))
            assert len(report_files) == 1


class TestProvenanceGuardEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_provenance_with_md_updated_status(self):
        """
        Examples with MD_UPDATED status should also be considered valid.
        """
        example = ExampleRecord(
            example_id="md_updated",
            file_path="test.md",
            family="test",
            language="csharp",
            status=ExampleStatus.MD_UPDATED,  # Already updated
            original_code="// code",
            verified_code="// fixed",
            location=Location(block_index=0, start_line=1, end_line=5),
            source_type=SourceType.INLINE,
        )

        signal = validate_provenance(example, require_verified=True)
        assert signal.verification_status == ExampleStatus.MD_UPDATED

    def test_provenance_report_includes_code_hash(self):
        """
        Provenance reports should include code hashes for verification.
        """
        example = ExampleRecord(
            example_id="hash_test",
            file_path="test.md",
            family="test",
            language="csharp",
            status=ExampleStatus.VERIFIED,
            original_code="// code",
            verified_code="console.log('test');",
            location=Location(block_index=0, start_line=1, end_line=5),
            source_type=SourceType.INLINE,
        )

        signal = validate_provenance(example)

        # Verify hash is computed and deterministic
        assert signal.verified_code_hash is not None
        assert len(signal.verified_code_hash) == 16  # First 16 chars of SHA256

        # Verify same code produces same hash
        signal2 = validate_provenance(example)
        assert signal.verified_code_hash == signal2.verified_code_hash
