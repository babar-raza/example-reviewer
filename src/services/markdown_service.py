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
        # Get all verified examples for this file
        examples = self.db.get_examples_by_file(file_path, run_id=self.run_id)
        verified_examples = [
            e for e in examples
            if e.status in (ExampleStatus.VERIFIED, ExampleStatus.MD_UPDATED)
            and e.verified_code
        ]
        
        if not verified_examples:
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
    
    def _update_inline_example(
        self,
        content: str,
        example: ExampleRecord,
    ) -> Optional[Tuple[str, Dict[str, Any]]]:
        """
        Update an inline code block in content.
        
        Uses location metadata to ensure safe replacement.
        """
        lines = content.split('\n')
        
        start_line = example.location.start_line - 1  # 0-indexed
        end_line = example.location.end_line - 1
        
        # Validate we're replacing the right block
        if start_line >= len(lines) or end_line >= len(lines):
            logger.warning(f"Location out of bounds for {example.example_id}")
            return None
        
        # Find the actual fence boundaries
        fence_start = None
        fence_end = None
        
        # Look backwards from start_line for opening fence
        for i in range(start_line, max(0, start_line - 5), -1):
            if lines[i].startswith('```'):
                fence_start = i
                break
        
        # Look forwards from end_line for closing fence
        for i in range(end_line, min(len(lines), end_line + 5)):
            if lines[i].startswith('```') and fence_start is not None and i > fence_start:
                fence_end = i
                break
        
        if fence_start is None or fence_end is None:
            logger.warning(f"Could not find fence boundaries for {example.example_id}")
            return None
        
        # Extract language from opening fence
        opening_fence = lines[fence_start]
        lang_match = re.match(r'^```(\w*).*$', opening_fence)
        language = lang_match.group(1) if lang_match else 'cs'
        
        # Build replacement
        new_lines = [
            f"```{language}",
            example.verified_code,
            "```"
        ]
        
        # Replace the block
        result_lines = (
            lines[:fence_start] +
            new_lines +
            lines[fence_end + 1:]
        )
        
        return '\n'.join(result_lines), {
            'example_id': example.example_id,
            'type': 'inline_replace',
            'start_line': fence_start + 1,
            'end_line': fence_end + 1,
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
