"""
Markdown Update Service for Example Reviewer Pipeline.
Implements Phase D: Markdown Update (Inline/Gist).
"""

import re
import uuid
import hashlib
import difflib
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple

from ..core.models import ExampleRecord, ExampleStatus, MarkdownEdit, SourceType
from ..core.database import Database
from ..core.path_guard import assert_write_allowed, READ_ONLY_PREFIXES, is_read_only_path, get_workspace_path
from ..core.provenance_guard import (
    validate_batch_provenance,
    check_provenance_enabled,
    generate_provenance_report,
    ProvenanceViolationError,
)
from ..utils.markdown_parser import parse_fenced_blocks, compute_code_signature, find_block_by_signature

# Import GistPublisher - optional dependency
try:
    from .gist_publisher import GistPublisher, GistPublishResult
    GIST_PUBLISHER_AVAILABLE = True
except ImportError:
    GIST_PUBLISHER_AVAILABLE = False

logger = logging.getLogger(__name__)


class MarkdownWriteGuardError(Exception):
    """Raised when attempting to write markdown files without proper authorization."""
    pass


class ReadOnlyPathError(Exception):
    """Raised when attempting to write to read-only test paths."""
    pass


class BlockResolutionResult:
    """Result of block location resolution with self-healing."""

    def __init__(
        self,
        block: Optional[Dict[str, Any]],
        used_fallback: bool = False,
        updated_index: Optional[int] = None,
        skip_reason: Optional[str] = None,
    ):
        """
        Args:
            block: The resolved block (or None if resolution failed)
            used_fallback: True if fallback resolution was used
            updated_index: New block_index if DB should be updated (self-healing)
            skip_reason: Reason for skipping if resolution failed
        """
        self.block = block
        self.used_fallback = used_fallback
        self.updated_index = updated_index
        self.skip_reason = skip_reason

    @property
    def success(self) -> bool:
        """True if resolution succeeded (block found)."""
        return self.block is not None

    @property
    def needs_db_update(self) -> bool:
        """True if self-healing occurred and DB should be updated."""
        return self.updated_index is not None


class MarkdownUpdateService:
    """
    Service for updating markdown files with verified code.
    Implements the D_markdown_update phase from the spec.

    SAFETY: This service enforces strict write guards:
    1. Markdown writes require explicit allow_markdown_write=True
    2. All test-* paths (test-data/, test-examples/, test-reference/, test-content/) are strictly read-only
    3. Use --use-workspace-copy to work with copies instead of originals

    Read-only enforcement is handled by src/core/path_guard.py
    """

    def __init__(
        self,
        db: Database,
        artifacts_dir: Optional[Path] = None,
        gist_publisher: Optional[Any] = None,
        gist_upload_mode: str = "inline-only",
        gist_target_account: str = "",
        allow_markdown_write: bool = False,
        use_workspace_copy: bool = False,
        workspace_root: Optional[Path] = None,
        run_id: Optional[str] = None,
        unsafe_first_block: bool = False,
    ):
        """
        Initialize markdown update service.

        Args:
            db: Database instance
            artifacts_dir: Directory for storing diff artifacts
            gist_publisher: Optional GistPublisher instance for upload modes
            gist_upload_mode: One of "inline-only", "upload-on-change", "upload-always"
            gist_target_account: GitHub account for new gist shortcodes
            allow_markdown_write: If True, allow markdown file writes (default: False for safety)
            use_workspace_copy: If True, write to workspace copies for read-only paths
            workspace_root: Root directory for workspace copies (default: artifacts/workspace)
            run_id: Run ID for workspace isolation
            unsafe_first_block: If True, allow replacement of first block when no signature exists (UNSAFE)
        """
        self.db = db
        self.artifacts_dir = artifacts_dir or Path("artifacts/diffs")
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        self.gist_publisher = gist_publisher
        self.gist_upload_mode = gist_upload_mode
        self.gist_target_account = gist_target_account
        self.allow_markdown_write = allow_markdown_write
        self.use_workspace_copy = use_workspace_copy
        self.workspace_root = workspace_root or Path("artifacts/workspace")
        self.run_id = run_id or "default"
        self.unsafe_first_block = unsafe_first_block

    def _get_write_target_path(self, file_path: str) -> str:
        """
        Get the target path for writing (original or workspace copy).

        Args:
            file_path: Original file path

        Returns:
            Target path for writing (workspace copy if enabled and path is read-only)
        """
        # If workspace copy mode is enabled and path is read-only, use workspace
        if self.use_workspace_copy and is_read_only_path(file_path):
            workspace_path = get_workspace_path(
                file_path,
                self.workspace_root,
                self.run_id
            )
            return str(workspace_path)

        return file_path

    def _validate_write_allowed(self, file_path: str) -> None:
        """
        Validate that writing to this file is allowed.

        Uses centralized path_guard module for read-only enforcement.

        Raises:
            ReadOnlyPathError: If attempting to write to test-* paths (via PermissionError)
            MarkdownWriteGuardError: If markdown writes are not authorized
        """
        # Check read-only paths first (highest priority) - uses centralized path_guard
        try:
            assert_write_allowed(file_path, reason="markdown update")
        except PermissionError as e:
            # Re-raise as ReadOnlyPathError for backward compatibility
            raise ReadOnlyPathError(str(e))

        # Check markdown write guard
        if not self.allow_markdown_write:
            raise MarkdownWriteGuardError(
                f"WRITE BLOCKED: Markdown writes are not authorized.\n"
                f"File: {file_path}\n"
                f"To allow markdown writes, set allow_markdown_write=True in global config\n"
                f"or use --allow-md-write CLI flag.\n"
                f"Default is dry-run to prevent accidental manual edits."
            )

    # REMOVED: _parse_fenced_blocks - now uses shared utils.markdown_parser.parse_fenced_blocks
    # REMOVED: _compute_code_signature - now uses shared utils.markdown_parser.compute_code_signature

    def update_markdown_file(
        self,
        file_path: str,
        dry_run: bool = False,
    ) -> Tuple[bool, List[Dict[str, Any]]]:
        """
        Update a markdown file with verified examples.

        Args:
            file_path: Path to markdown file
            dry_run: If True, don't actually write changes

        Returns:
            Tuple of (success, list of changes made)
        """
        # Get all examples for this file
        examples = self.db.get_examples_by_file(file_path, run_id=self.run_id)

        # Get examples that claim to be verified (based on status)
        # Note: We check status first, BEFORE checking verified_code, so that
        # the provenance guard can catch examples with VERIFIED status but missing code
        examples_claiming_verified = [
            e for e in examples
            if e.status in (ExampleStatus.VERIFIED, ExampleStatus.MD_UPDATED)
        ]

        if not examples_claiming_verified:
            return True, []

        # PROVENANCE GUARD: Validate that all examples have proper provenance
        # This prevents manual edits that bypass the verify→fix→verify loop
        # This runs BEFORE filtering by verified_code, so it can catch status=VERIFIED
        # but verified_code=None (anti-pattern: manually setting status without verification)
        if check_provenance_enabled(self.allow_markdown_write, self.use_workspace_copy):
            try:
                provenance_signals = validate_batch_provenance(
                    examples_claiming_verified,
                    require_verified=True
                )

                # Log provenance validation success
                logger.info(
                    f"Provenance validated for {len(provenance_signals)} examples in {file_path}"
                )

                # Generate provenance report for audit trail
                provenance_report = generate_provenance_report(provenance_signals, file_path)
                self._store_provenance_report(file_path, provenance_report)

            except ProvenanceViolationError as e:
                logger.error(f"PROVENANCE VIOLATION in {file_path}: {e}")
                raise  # Re-raise to block the update

        # After provenance validation passes, filter to only examples with verified_code
        # (This is now redundant with provenance guard but kept for safety)
        verified_examples = [
            e for e in examples_claiming_verified
            if e.verified_code
        ]

        if not verified_examples:
            # This shouldn't happen if provenance guard is working, but handle it
            logger.warning(f"No examples with verified_code found for {file_path} after provenance validation")
            return True, []
        
        # Read original file
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                original_content = f.read()
        except Exception as e:
            logger.error(f"Failed to read {file_path}: {e}")
            return False, []
        
        # Apply updates
        updated_content = original_content
        changes = []
        
        for example in verified_examples:
            if example.source_type == SourceType.INLINE:
                result = self._update_inline_example(
                    updated_content, example
                )
            else:
                result = self._update_gist_example(
                    updated_content, example
                )
            
            if result:
                updated_content, change_info = result
                changes.append(change_info)
        
        if not changes:
            return True, []
        
        # Generate and store diff
        diff = self._generate_diff(original_content, updated_content, file_path)
        diff_ref = self._store_diff(file_path, diff)

        # Write updated file if not dry run
        if not dry_run:
            # Determine target path (original or workspace copy)
            target_path = self._get_write_target_path(file_path)

            # SAFETY: Validate write is allowed before modifying file
            self._validate_write_allowed(target_path)

            try:
                # Ensure parent directory exists
                Path(target_path).parent.mkdir(parents=True, exist_ok=True)

                with open(target_path, 'w', encoding='utf-8') as f:
                    f.write(updated_content)

                # Log workspace redirect if applicable
                if target_path != file_path:
                    logger.info(f"Wrote to workspace copy: {target_path} (original: {file_path})")

                # Update example statuses
                for example in verified_examples:
                    self.db.update_example_status(example.example_id, ExampleStatus.MD_UPDATED, run_id=self.run_id)

                    # Record edit
                    edit = MarkdownEdit(
                        edit_id=str(uuid.uuid4())[:8],
                        file_path=file_path,
                        example_id=example.example_id,
                        family=example.family,
                        edit_type="inline_replace" if example.source_type == SourceType.INLINE else "gist_replace",
                        diff_ref=diff_ref,
                    )
                    self.db.save_markdown_edit(edit, run_id=self.run_id)
                    
            except Exception as e:
                logger.error(f"Failed to write {file_path}: {e}")
                return False, changes
        
        return True, changes
    
    def resolve_target_block(
        self,
        example: ExampleRecord,
        blocks: List[Dict[str, Any]],
    ) -> BlockResolutionResult:
        """
        Resolve target block with self-healing location resolution.

        Algorithm:
        1. If block_index in range:
           - Compute signature at that index
           - If matches stored signature → use it (no fallback)
        2. Else (out of range OR signature mismatch):
           - Search all blocks for signature match
           - If exactly 1 match → use fallback + mark for DB update (self-healing)
           - If 0 matches → skip (signature not found)
           - If >1 matches → skip (ambiguous/duplicate signature)

        Args:
            example: Example record with location and signature
            blocks: Parsed fenced blocks from markdown file

        Returns:
            BlockResolutionResult with block and self-healing metadata
        """
        block_index = example.location.block_index
        target_signature = example.code_block_signature

        # Step 1: Try block_index if in range
        if 0 <= block_index < len(blocks):
            block_at_index = blocks[block_index]
            # Signatures are pre-computed by parse_fenced_blocks()
            if block_at_index['signature'] == target_signature:
                # Perfect match - no fallback needed
                return BlockResolutionResult(
                    block=block_at_index,
                    used_fallback=False,
                )

        # Step 2: Signature mismatch or out of range - attempt fallback
        logger.warning(
            f"Block location mismatch for {example.example_id}: "
            f"index {block_index} not valid or signature mismatch. "
            f"Searching for signature match..."
        )

        # Find all blocks matching signature
        signature_matches = find_block_by_signature(blocks, target_signature)

        if len(signature_matches) == 0:
            # No match found - file may have changed
            return BlockResolutionResult(
                block=None,
                skip_reason=f"md_update_signature_not_found: signature {target_signature[:16]}... not found in any block",
            )

        if len(signature_matches) > 1:
            # Multiple matches - ambiguous targeting
            match_indices = [b['block_index'] for b in signature_matches]
            return BlockResolutionResult(
                block=None,
                skip_reason=f"md_update_duplicate_signature: found {len(signature_matches)} blocks with same signature at indices {match_indices}",
            )

        # Exactly 1 match - safe to use fallback with self-healing
        fallback_block = signature_matches[0]
        new_index = fallback_block['block_index']

        logger.info(
            f"SELF-HEALING: Found unique signature match for {example.example_id} "
            f"at block {new_index} (stored index was {block_index}). "
            f"Will update DB location after successful replacement."
        )

        return BlockResolutionResult(
            block=fallback_block,
            used_fallback=True,
            updated_index=new_index,
        )

    def _update_inline_example(
        self,
        content: str,
        example: ExampleRecord,
    ) -> Optional[Tuple[str, Dict[str, Any]]]:
        """
        Update an inline code block in content using block index and signature verification.

        Safe multi-block replacement logic:
        1. Parse all fenced blocks in the content
        2. If example has code_block_signature:
           - Resolve target block (with self-healing)
           - Verify signature matches before replacing
           - Update DB location if self-healing occurred
        3. If example has no code_block_signature:
           - Skip with warning unless unsafe_first_block=True

        Returns:
            Tuple of (updated_content, change_info) or None if skipped/failed
        """
        # Parse all fenced blocks
        blocks = parse_fenced_blocks(content)

        if not blocks:
            logger.warning(f"No fenced blocks found in file for {example.example_id}")
            return None

        # CASE 1: Example has code_block_signature (new migration 011 path)
        if example.code_block_signature:
            return self._update_with_signature_verification(content, example, blocks)

        # CASE 2: Example has no code_block_signature (legacy/backward compat)
        return self._update_legacy_fallback(content, example, blocks)

    def _update_with_signature_verification(
        self,
        content: str,
        example: ExampleRecord,
        blocks: List[Dict[str, Any]],
    ) -> Optional[Tuple[str, Dict[str, Any]]]:
        """
        Update using block_index + signature verification with self-healing.

        Uses resolve_target_block() to handle location mismatches intelligently:
        - If block_index points to correct signature → use it
        - If mismatch but unique signature match found → self-heal and update DB
        - If ambiguous or not found → skip with NEEDS_REVIEW
        """
        # Resolve target block with self-healing
        resolution = self.resolve_target_block(example, blocks)

        if not resolution.success:
            # Resolution failed - skip with reason
            logger.error(
                f"Failed to resolve target block for {example.example_id}: "
                f"{resolution.skip_reason}"
            )
            self.db.update_example_status(
                example.example_id,
                ExampleStatus.NEEDS_REVIEW,
                failure_reason=resolution.skip_reason,
                run_id=self.run_id,
            )
            return None

        target_block = resolution.block

        # Perform replacement
        result = self._replace_block(content, target_block, example)

        # If self-healing occurred, update DB location
        if resolution.needs_db_update:
            self._update_example_location(
                example.example_id,
                new_block_index=resolution.updated_index,
                new_start_line=target_block['start_line'],
                new_end_line=target_block['end_line'],
            )

        return result

    def _update_example_location(
        self,
        example_id: str,
        new_block_index: int,
        new_start_line: int,
        new_end_line: int,
    ) -> None:
        """
        Update example location in database after self-healing.

        This is called when resolve_target_block() finds a signature match
        at a different block_index than what was stored.
        """
        logger.info(
            f"SELF-HEALING DB UPDATE: Updating location for {example_id} "
            f"to block_index={new_block_index}, "
            f"lines {new_start_line}-{new_end_line}"
        )

        # Update example_records table with new location
        query = """
            UPDATE example_records
            SET
                location_block_index = ?,
                location_start_line = ?,
                location_end_line = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE example_id = ?
        """

        conn = self.db.conn
        cursor = conn.cursor()
        cursor.execute(query, (new_block_index, new_start_line, new_end_line, example_id))
        conn.commit()

        logger.info(f"Successfully updated location for {example_id}")

    def _update_legacy_fallback(
        self,
        content: str,
        example: ExampleRecord,
        blocks: List[Dict[str, Any]],
    ) -> Optional[Tuple[str, Dict[str, Any]]]:
        """
        Legacy fallback for examples without code_block_signature.

        Default behavior: skip with warning unless unsafe_first_block=True.
        """
        if not self.unsafe_first_block:
            logger.warning(
                f"Example {example.example_id} has no code_block_signature. "
                f"Skipping update (use --unsafe-first-block to force replacement of first block)."
            )
            return None

        # UNSAFE: Use first block
        logger.warning(
            f"UNSAFE: Replacing first block for {example.example_id} (no signature available)."
        )

        if not blocks:
            logger.error(f"No blocks found for unsafe replacement: {example.example_id}")
            return None

        target_block = blocks[0]
        return self._replace_block(content, target_block, example)

    def _find_fallback_block(
        self,
        blocks: List[Dict[str, Any]],
        target_signature: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Search for a block matching the target signature.

        Returns first block with matching signature, or None if not found.
        NOTE: Signatures are pre-computed in blocks by parse_fenced_blocks().
        """
        # Use shared utility (signatures already computed in blocks)
        matches = find_block_by_signature(blocks, target_signature)
        return matches[0] if matches else None

    def _replace_block(
        self,
        content: str,
        block: Dict[str, Any],
        example: ExampleRecord,
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Replace a specific block in the content with verified code.
        """
        lines = content.split('\n')

        fence_start_idx = block['fence_start_idx']
        fence_end_idx = block['fence_end_idx']

        # Use the language from the original fence (or default to example language)
        language = block['language'] or example.language or 'csharp'

        # Build replacement lines
        new_lines = [
            f"```{language}",
            example.verified_code,
            "```"
        ]

        # Replace the block
        result_lines = (
            lines[:fence_start_idx] +
            new_lines +
            lines[fence_end_idx + 1:]
        )

        logger.info(
            f"Replaced block {block['block_index']} in {example.file_path} "
            f"(lines {block['start_line']}-{block['end_line']}) for {example.example_id}"
        )

        return '\n'.join(result_lines), {
            'example_id': example.example_id,
            'type': 'inline_replace',
            'block_index': block['block_index'],
            'start_line': block['start_line'],
            'end_line': block['end_line'],
            'language': language,
        }
    
    def _update_gist_example(
        self,
        content: str,
        example: ExampleRecord,
    ) -> Optional[Tuple[str, Dict[str, Any]]]:
        """
        Update a gist reference in content.

        Supports three modes based on gist_upload_mode:
        - inline-only: Replace shortcode with inline code block (default)
        - upload-on-change: Upload if code changed, update shortcode with new gist ID
        - upload-always: Always upload new gist, update shortcode

        Args:
            content: Markdown content
            example: ExampleRecord with verified code

        Returns:
            Tuple of (updated_content, change_info) or None if no update needed
        """
        if not example.gist:
            return None

        # Find the gist shortcode
        pattern = re.compile(
            r'\{\{<\s*gist\s+' + re.escape(example.gist.owner) +
            r'\s+' + re.escape(example.gist.gist_id) +
            r'(?:\s+["\']?([^"\'>\s]+)["\']?)?\s*>\}\}',
            re.IGNORECASE
        )

        match = pattern.search(content)
        if not match:
            logger.warning(f"Could not find gist shortcode for {example.example_id}")
            return None

        # Extract filename from shortcode if present
        filename = match.group(1) if match.group(1) else (example.gist.filename or f"{example.example_id}.cs")

        # Determine update strategy based on mode
        if self.gist_upload_mode == "inline-only" or not self.gist_publisher:
            return self._convert_gist_to_inline(content, example, match)

        # Check if publisher is available
        if not self.gist_publisher.is_available():
            logger.warning("Gist publisher not available, falling back to inline")
            return self._convert_gist_to_inline(content, example, match)

        # For upload modes, check if code has changed
        if self.gist_upload_mode == "upload-on-change":
            # Compare code hashes
            original_hash = hashlib.sha256((example.original_code or "").encode()).hexdigest()[:16]
            verified_hash = hashlib.sha256((example.verified_code or "").encode()).hexdigest()[:16]

            if original_hash == verified_hash:
                # No code change, keep original shortcode
                return None

        # Upload to gist
        return self._upload_and_update_gist(content, example, match, filename)

    def _convert_gist_to_inline(
        self,
        content: str,
        example: ExampleRecord,
        match: re.Match,
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Convert gist shortcode to inline code block.

        Args:
            content: Original markdown content
            example: ExampleRecord with verified code
            match: Regex match for the gist shortcode

        Returns:
            Tuple of (updated_content, change_info)
        """
        replacement = f"```csharp\n{example.verified_code}\n```"
        result = content[:match.start()] + replacement + content[match.end():]

        return result, {
            'example_id': example.example_id,
            'edit_type': 'gist_to_inline',
            'original_gist': f"{example.gist.owner}/{example.gist.gist_id}",
        }

    def _upload_and_update_gist(
        self,
        content: str,
        example: ExampleRecord,
        match: re.Match,
        filename: str,
    ) -> Optional[Tuple[str, Dict[str, Any]]]:
        """
        Upload code to gist and update shortcode with new gist ID.

        Args:
            content: Original markdown content
            example: ExampleRecord with verified code
            match: Regex match for the gist shortcode
            filename: Filename for the gist

        Returns:
            Tuple of (updated_content, change_info) or falls back to inline on failure
        """
        # Build description
        description = f"Verified example from {example.family} - {example.file_path}"

        # Determine old_gist_id for update mode
        old_gist_id = None
        if self.gist_upload_mode == "upload-on-change":
            old_gist_id = example.gist.gist_id

        # Publish gist
        result = self.gist_publisher.publish_gist(
            code_content=example.verified_code,
            filename=filename,
            description=description,
            old_gist_id=old_gist_id,
        )

        if not result.success:
            logger.warning(f"Gist upload failed: {result.error}, falling back to inline")
            return self._convert_gist_to_inline(content, example, match)

        # Build new shortcode with updated gist ID
        target_account = self.gist_target_account or example.gist.owner
        new_shortcode = f'{{{{< gist {target_account} {result.gist_id} "{filename}" >}}}}'

        updated_content = content[:match.start()] + new_shortcode + content[match.end():]

        logger.info(
            f"Gist uploaded for {example.example_id}: {result.html_url}"
        )

        return updated_content, {
            'example_id': example.example_id,
            'edit_type': 'gist_replace',
            'old_gist_id': example.gist.gist_id,
            'new_gist_id': result.gist_id,
            'new_gist_url': result.html_url,
        }
    
    def _generate_diff(
        self,
        original: str,
        updated: str,
        file_path: str,
    ) -> str:
        """Generate unified diff between original and updated content."""
        original_lines = original.splitlines(keepends=True)
        updated_lines = updated.splitlines(keepends=True)
        
        diff = difflib.unified_diff(
            original_lines,
            updated_lines,
            fromfile=f"a/{file_path}",
            tofile=f"b/{file_path}",
        )
        
        return ''.join(diff)
    
    def _store_diff(self, file_path: str, diff: str) -> str:
        """Store diff as artifact and return reference."""
        # Create safe filename from path
        safe_name = Path(file_path).name.replace('.', '_')
        diff_id = str(uuid.uuid4())[:8]
        diff_filename = f"{safe_name}_{diff_id}.diff"

        diff_path = self.artifacts_dir / diff_filename
        diff_path.write_text(diff, encoding='utf-8')

        return str(diff_path)

    def _store_provenance_report(self, file_path: str, report: Dict[str, Any]) -> str:
        """
        Store provenance report as JSON artifact.

        This creates an audit trail showing that markdown updates were backed
        by verified examples from the pipeline.

        Args:
            file_path: Original markdown file path
            report: Provenance report dictionary

        Returns:
            Path to stored provenance report
        """
        import json

        # Create provenance directory if it doesn't exist
        provenance_dir = self.artifacts_dir / "provenance"
        provenance_dir.mkdir(parents=True, exist_ok=True)

        # Create safe filename from path
        safe_name = Path(file_path).name.replace('.', '_').replace('/', '_')
        report_id = str(uuid.uuid4())[:8]
        report_filename = f"{safe_name}_{report_id}_provenance.json"

        report_path = provenance_dir / report_filename
        report_path.write_text(json.dumps(report, indent=2), encoding='utf-8')

        logger.debug(f"Stored provenance report: {report_path}")

        return str(report_path)

    def update_all_files(
        self,
        family: str,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """
        Update all markdown files with verified examples for a family.
        
        Args:
            family: Family identifier
            dry_run: If True, don't actually write changes
            
        Returns:
            Statistics dictionary
        """
        stats = {
            'files_processed': 0,
            'files_updated': 0,
            'examples_updated': 0,
            'errors': 0,
        }
        
        # Get all verified examples for family
        examples = self.db.get_examples_by_family(family, ExampleStatus.VERIFIED, run_id=self.run_id)
        
        # Group by file
        files_to_update = {}
        for example in examples:
            if example.file_path not in files_to_update:
                files_to_update[example.file_path] = []
            files_to_update[example.file_path].append(example)
        
        for file_path, file_examples in files_to_update.items():
            stats['files_processed'] += 1
            
            success, changes = self.update_markdown_file(file_path, dry_run)
            
            if success and changes:
                stats['files_updated'] += 1
                stats['examples_updated'] += len(changes)
            elif not success:
                stats['errors'] += 1
        
        return stats
