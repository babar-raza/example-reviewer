"""
Test multi-block md_update correctness (Task C).

Tests that md_update correctly targets specific code blocks in markdown files
with multiple code blocks, using block_index and signature verification.
"""

import pytest
import tempfile
import hashlib
from pathlib import Path
from datetime import datetime

from src.core.database import Database
from src.core.models import ExampleRecord, ExampleStatus, SourceType, Location
from src.services.markdown_service import MarkdownUpdateService
from tests.conftest import make_pdp


def compute_signature(code: str) -> str:
    """Compute code signature (matches service logic)."""
    normalized = code.strip().replace('\r\n', '\n')
    return hashlib.sha256(normalized.encode('utf-8')).hexdigest()


class TestMultiBlockMdUpdate:
    """Test md_update with multiple code blocks in a file."""

    @pytest.fixture
    def temp_db(self):
        """Create a temporary database."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = Path(f.name)

        db = Database(db_path)
        db.initialize_schema()

        # Create run record for test-run (required for example_run_state FK)
        with db.get_connection() as conn:
            conn.execute("""
                INSERT INTO run_records (run_id, family, started_at, status)
                VALUES (?, ?, ?, ?)
            """, ("test-run", "test-family", datetime.utcnow().isoformat(), "running"))

        yield db

        db.close()
        db_path.unlink()

    @pytest.fixture
    def markdown_service(self, temp_db):
        """Create markdown update service."""
        return MarkdownUpdateService(
            db=temp_db,
            pdp=make_pdp(allow_writes=True),
            run_id="test-run"
        )

    def test_two_examples_three_blocks_each_updates_own_block(self, temp_db, markdown_service):
        """
        Test that two examples in a file with 3 code blocks each update only their own block.

        File has 3 blocks: block 0 (example1), block 1 (example2), block 2 (unrelated).
        After update, only blocks 0 and 1 should be changed, block 2 should be unchanged.
        """
        # Create test markdown file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            file_path = f.name
            f.write("""# Test Multi-Block

## Block 0
```csharp
// Original code block 0
Console.WriteLine("Block 0");
```

## Block 1
```csharp
// Original code block 1
Console.WriteLine("Block 1");
```

## Block 2
```csharp
// Original code block 2 (unrelated)
Console.WriteLine("Block 2");
```
""")

        file_path = Path(file_path)

        try:
            # Create two examples for blocks 0 and 1
            code_block_0 = """// Original code block 0
Console.WriteLine("Block 0");"""

            code_block_1 = """// Original code block 1
Console.WriteLine("Block 1");"""

            example1 = ExampleRecord(
                family="test-family",
                file_path=str(file_path),
                source_type=SourceType.INLINE,
                language="csharp",
                location=Location(block_index=0, start_line=4, end_line=7),
                original_code=code_block_0,
                status=ExampleStatus.DISCOVERED,
                code_block_signature=compute_signature(code_block_0),
            )

            example2 = ExampleRecord(
                family="test-family",
                file_path=str(file_path),
                source_type=SourceType.INLINE,
                language="csharp",
                location=Location(block_index=1, start_line=9, end_line=12),
                original_code=code_block_1,
                status=ExampleStatus.DISCOVERED,
                code_block_signature=compute_signature(code_block_1),
            )

            # Save examples
            temp_db.save_example(example1, run_id="test-run")
            temp_db.save_example(example2, run_id="test-run")

            # Set verified code
            temp_db.update_example_code(
                example1.example_id,
                verified_code="// UPDATED Block 0\nConsole.WriteLine(\"Updated 0\");",
                run_id="test-run"
            )
            temp_db.update_example_status(
                example1.example_id,
                ExampleStatus.VERIFIED,
                run_id="test-run"
            )

            temp_db.update_example_code(
                example2.example_id,
                verified_code="// UPDATED Block 1\nConsole.WriteLine(\"Updated 1\");",
                run_id="test-run"
            )
            temp_db.update_example_status(
                example2.example_id,
                ExampleStatus.VERIFIED,
                run_id="test-run"
            )

            # Update markdown file
            success, changes = markdown_service.update_markdown_file(str(file_path), dry_run=False)

            assert success, "Markdown update should succeed"
            assert len(changes) == 2, f"Should have 2 changes, got {len(changes)}"

            # Read updated file
            updated_content = file_path.read_text()

            # Verify block 0 was updated
            assert "// UPDATED Block 0" in updated_content, "Block 0 should be updated"
            assert "Console.WriteLine(\"Updated 0\");" in updated_content, "Block 0 should have new code"
            assert "// Original code block 0" not in updated_content, "Block 0 old code should be gone"

            # Verify block 1 was updated
            assert "// UPDATED Block 1" in updated_content, "Block 1 should be updated"
            assert "Console.WriteLine(\"Updated 1\");" in updated_content, "Block 1 should have new code"
            assert "// Original code block 1" not in updated_content, "Block 1 old code should be gone"

            # Verify block 2 was NOT updated (unrelated)
            assert "// Original code block 2 (unrelated)" in updated_content, "Block 2 should be unchanged"
            assert "Console.WriteLine(\"Block 2\");" in updated_content, "Block 2 code should be unchanged"

        finally:
            file_path.unlink()

    def test_update_block_5_in_7_block_file(self, temp_db, markdown_service):
        """
        Test updating block 5 in a file with 7 code blocks.

        Only block 5 should be updated, all others should remain unchanged.
        """
        # Create test markdown file with 7 blocks
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            file_path = f.name
            blocks = []
            content = "# Test Seven Blocks\n\n"

            for i in range(7):
                code = f"// Block {i}\nConsole.WriteLine(\"Block {i}\");"
                blocks.append(code)
                content += f"## Block {i}\n```csharp\n{code}\n```\n\n"

            f.write(content)

        file_path = Path(file_path)

        try:
            # Create example for block 5
            target_block = blocks[5]

            example = ExampleRecord(
                family="test-family",
                file_path=str(file_path),
                source_type=SourceType.INLINE,
                language="csharp",
                location=Location(block_index=5, start_line=17, end_line=20),
                original_code=target_block,
                status=ExampleStatus.DISCOVERED,
                code_block_signature=compute_signature(target_block),
            )

            # Save example
            temp_db.save_example(example, run_id="test-run")

            # Set verified code
            verified = "// UPDATED Block 5\nConsole.WriteLine(\"Updated 5\");"
            temp_db.update_example_code(
                example.example_id,
                verified_code=verified,
                run_id="test-run"
            )
            temp_db.update_example_status(
                example.example_id,
                ExampleStatus.VERIFIED,
                run_id="test-run"
            )

            # Update markdown file
            success, changes = markdown_service.update_markdown_file(str(file_path), dry_run=False)

            assert success, "Markdown update should succeed"
            assert len(changes) == 1, f"Should have 1 change, got {len(changes)}"
            assert changes[0]['block_index'] == 5, "Should update block 5"

            # Read updated file
            updated_content = file_path.read_text()

            # Verify block 5 was updated
            assert "// UPDATED Block 5" in updated_content, "Block 5 should be updated"
            assert "Console.WriteLine(\"Updated 5\");" in updated_content, "Block 5 should have new code"
            assert "// Block 5\nConsole.WriteLine(\"Block 5\");" not in updated_content, "Block 5 old code should be gone"

            # Verify all other blocks are unchanged
            for i in range(7):
                if i != 5:
                    assert f"// Block {i}" in updated_content, f"Block {i} should be unchanged"
                    assert f"Console.WriteLine(\"Block {i}\");" in updated_content, f"Block {i} code should be unchanged"

        finally:
            file_path.unlink()

    def test_signature_mismatch_skips_update(self, temp_db, markdown_service):
        """
        Test that signature mismatch causes update to be skipped.

        If the code block content has changed since extraction (signature mismatch)
        and no fallback match is found, the update should be skipped and example
        marked as NEEDS_REVIEW.
        """
        # Create test markdown file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            file_path = f.name
            f.write("""# Test Signature Mismatch

```csharp
// MODIFIED code (different from extraction)
Console.WriteLine("Modified");
```
""")

        file_path = Path(file_path)

        try:
            # Create example with signature from ORIGINAL code (before modification)
            original_code = "// Original code\nConsole.WriteLine(\"Original\");"

            example = ExampleRecord(
                family="test-family",
                file_path=str(file_path),
                source_type=SourceType.INLINE,
                language="csharp",
                location=Location(block_index=0, start_line=3, end_line=6),
                original_code=original_code,
                status=ExampleStatus.DISCOVERED,
                code_block_signature=compute_signature(original_code),  # Signature won't match file
            )

            # Save example
            temp_db.save_example(example, run_id="test-run")

            # Set verified code
            temp_db.update_example_code(
                example.example_id,
                verified_code="// UPDATED code\nConsole.WriteLine(\"Updated\");",
                run_id="test-run"
            )
            temp_db.update_example_status(
                example.example_id,
                ExampleStatus.VERIFIED,
                run_id="test-run"
            )

            # Update markdown file
            success, changes = markdown_service.update_markdown_file(str(file_path), dry_run=False)

            # Should succeed but with no changes (skipped)
            assert success, "Markdown update should succeed (no fatal errors)"
            assert len(changes) == 0, f"Should have 0 changes (skipped), got {len(changes)}"

            # Read file - should be unchanged
            updated_content = file_path.read_text()
            assert "// MODIFIED code (different from extraction)" in updated_content, "File should be unchanged"
            assert "Console.WriteLine(\"Modified\");" in updated_content, "File should be unchanged"
            assert "// UPDATED code" not in updated_content, "Update should not have been applied"

            # Check example status - should be NEEDS_REVIEW
            updated_example = temp_db.get_example(example.example_id)
            examples = temp_db.get_examples_by_file(str(file_path), run_id="test-run")
            assert len(examples) == 1
            assert examples[0].status == ExampleStatus.NEEDS_REVIEW, "Example should be marked NEEDS_REVIEW"
            # Failure reason should indicate signature mismatch (old) or signature not found (new with self-healing)
            failure_reason = examples[0].failure_reason or ""
            assert ("md_update_ambiguous_block" in failure_reason or
                    "md_update_signature_not_found" in failure_reason), \
                f"Should have signature-related failure reason, got: {failure_reason}"

        finally:
            file_path.unlink()

    def test_no_signature_skips_by_default(self, temp_db):
        """
        Test that examples without code_block_signature are skipped by default.

        Legacy examples (before migration 011) don't have signatures and should
        be skipped unless unsafe_first_block=True.
        """
        # Create test markdown file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            file_path = f.name
            f.write("""# Test No Signature

```csharp
// Original code
Console.WriteLine("Original");
```
""")

        file_path = Path(file_path)

        try:
            # Create example WITHOUT code_block_signature (legacy)
            example = ExampleRecord(
                family="test-family",
                file_path=str(file_path),
                source_type=SourceType.INLINE,
                language="csharp",
                location=Location(block_index=0, start_line=3, end_line=6),
                original_code="// Original code\nConsole.WriteLine(\"Original\");",
                status=ExampleStatus.DISCOVERED,
                code_block_signature=None,  # No signature (legacy)
            )

            # Save example
            temp_db.save_example(example, run_id="test-run")

            # Set verified code
            temp_db.update_example_code(
                example.example_id,
                verified_code="// UPDATED code\nConsole.WriteLine(\"Updated\");",
                run_id="test-run"
            )
            temp_db.update_example_status(
                example.example_id,
                ExampleStatus.VERIFIED,
                run_id="test-run"
            )

            # Create service with default (unsafe_first_block=False)
            markdown_service = MarkdownUpdateService(
                db=temp_db,
                pdp=make_pdp(allow_writes=True),
                run_id="test-run",
                unsafe_first_block=False
            )

            # Update markdown file
            success, changes = markdown_service.update_markdown_file(str(file_path), dry_run=False)

            # Should succeed but with no changes (skipped due to no signature)
            assert success, "Markdown update should succeed"
            assert len(changes) == 0, f"Should have 0 changes (skipped), got {len(changes)}"

            # Read file - should be unchanged
            updated_content = file_path.read_text()
            assert "// Original code" in updated_content, "File should be unchanged"
            assert "Console.WriteLine(\"Original\");" in updated_content, "File should be unchanged"
            assert "// UPDATED code" not in updated_content, "Update should not have been applied"

        finally:
            file_path.unlink()

    def test_unsafe_first_block_updates_without_signature(self, temp_db):
        """
        Test that unsafe_first_block=True allows updates without signature (UNSAFE mode).

        When unsafe_first_block=True, examples without signatures can be updated
        (replaces first block).
        """
        # Create test markdown file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            file_path = f.name
            f.write("""# Test Unsafe Mode

```csharp
// Original code
Console.WriteLine("Original");
```
""")

        file_path = Path(file_path)

        try:
            # Create example WITHOUT code_block_signature (legacy)
            example = ExampleRecord(
                family="test-family",
                file_path=str(file_path),
                source_type=SourceType.INLINE,
                language="csharp",
                location=Location(block_index=0, start_line=3, end_line=6),
                original_code="// Original code\nConsole.WriteLine(\"Original\");",
                status=ExampleStatus.DISCOVERED,
                code_block_signature=None,  # No signature (legacy)
            )

            # Save example
            temp_db.save_example(example, run_id="test-run")

            # Set verified code
            temp_db.update_example_code(
                example.example_id,
                verified_code="// UPDATED code\nConsole.WriteLine(\"Updated\");",
                run_id="test-run"
            )
            temp_db.update_example_status(
                example.example_id,
                ExampleStatus.VERIFIED,
                run_id="test-run"
            )

            # Create service with unsafe_first_block=True
            markdown_service = MarkdownUpdateService(
                db=temp_db,
                pdp=make_pdp(allow_writes=True),
                run_id="test-run",
                unsafe_first_block=True  # UNSAFE mode
            )

            # Update markdown file
            success, changes = markdown_service.update_markdown_file(str(file_path), dry_run=False)

            # Should succeed with 1 change
            assert success, "Markdown update should succeed"
            assert len(changes) == 1, f"Should have 1 change, got {len(changes)}"

            # Read file - should be updated
            updated_content = file_path.read_text()
            assert "// UPDATED code" in updated_content, "File should be updated"
            assert "Console.WriteLine(\"Updated\");" in updated_content, "File should have new code"
            assert "// Original code" not in updated_content, "Old code should be gone"

        finally:
            file_path.unlink()
