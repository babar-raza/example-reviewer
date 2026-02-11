"""
Backfill Service for Example Reviewer Pipeline.
Handles automatic downloading of test data, API references, and examples.
"""

import os
import shutil
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime, timedelta

from .discovery_service import GistResolver
from ..core.path_guard import assert_write_allowed, is_read_only_path

logger = logging.getLogger(__name__)

# Try to import GitPython - graceful degradation if not available
try:
    from git import Repo, GitCommandError
    GIT_AVAILABLE = True
except ImportError:
    GIT_AVAILABLE = False
    logger.warning("GitPython not available - backfill from Git repos disabled")


@dataclass
class BackfillResult:
    """Result of a backfill operation."""
    success: bool
    target: str
    source: str
    destination: str
    files_copied: int = 0
    error: Optional[str] = None
    skipped: bool = False
    skip_reason: Optional[str] = None
    duration_seconds: float = 0.0
    items_processed: int = 0
    items_downloaded: int = 0
    items_failed: int = 0


class BackfillService:
    """
    Service for backfilling missing data from external sources.

    Supports:
    - Test data from example_repo
    - API references from configured sources
    - Example code for vector DB population
    """

    # Cache directory for cloned repos
    CACHE_DIR = Path(".cache/backfill")

    # Minimum time between repo refreshes (24 hours)
    REPO_REFRESH_INTERVAL = timedelta(hours=24)

    def __init__(
        self,
        config_manager=None,
        cache_dir: Optional[Path] = None,
        timeout_seconds: int = 120,
        db=None,
        config=None,
    ):
        """
        Initialize backfill service.

        Args:
            config_manager: Configuration manager instance
            cache_dir: Directory for caching cloned repos
            timeout_seconds: Timeout for Git operations
        """
        self.config_manager = config_manager
        self.cache_dir = cache_dir or self.CACHE_DIR
        self.timeout_seconds = timeout_seconds
        self.db = db
        self.config = config

        # Create cache directory
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def backfill_test_data(
        self,
        family: str,
        force: bool = False,
    ) -> BackfillResult:
        """
        Backfill test data for a family from example_repo.

        Args:
            family: Family identifier
            force: Force download even if data exists locally

        Returns:
            BackfillResult with operation details
        """
        start_time = datetime.now()

        try:
            # Load family config
            family_config = self.config_manager.load_family_config(family)

            # Check if test data already exists
            local_path = Path(family_config.test_data.local_path)

            # CRITICAL: If local_path is in a read-only directory, redirect to artifacts/backfill
            original_path = local_path
            if is_read_only_path(local_path):
                # Redirect to artifacts/backfill/<family>/test-data/...
                local_path = Path("artifacts/backfill") / family / "test-data"
                logger.info(
                    f"Redirecting backfill from read-only path {original_path} "
                    f"to artifacts: {local_path}"
                )

            if local_path.exists() and not force:
                return BackfillResult(
                    success=True,
                    target="test_data",
                    source="local",
                    destination=str(local_path),
                    skipped=True,
                    skip_reason="test_data_already_exists",
                    duration_seconds=(datetime.now() - start_time).total_seconds()
                )

            # Check if auto-download is enabled
            if not family_config.test_data.download_if_missing and not force:
                return BackfillResult(
                    success=True,
                    target="test_data",
                    source="config",
                    destination=str(local_path),
                    skipped=True,
                    skip_reason="download_if_missing_disabled",
                    duration_seconds=(datetime.now() - start_time).total_seconds()
                )

            # Check if example_repo is configured
            if not family_config.example_repo.url:
                return BackfillResult(
                    success=False,
                    target="test_data",
                    source="example_repo",
                    destination=str(local_path),
                    error="example_repo.url not configured",
                    duration_seconds=(datetime.now() - start_time).total_seconds()
                )

            # Check if test_data_path is configured
            if not family_config.example_repo.test_data_path:
                return BackfillResult(
                    success=False,
                    target="test_data",
                    source=family_config.example_repo.url,
                    destination=str(local_path),
                    error="example_repo.test_data_path not configured",
                    duration_seconds=(datetime.now() - start_time).total_seconds()
                )

            # Clone/fetch repo if GitPython available
            if not GIT_AVAILABLE:
                return BackfillResult(
                    success=False,
                    target="test_data",
                    source=family_config.example_repo.url,
                    destination=str(local_path),
                    error="GitPython not installed - pip install gitpython",
                    duration_seconds=(datetime.now() - start_time).total_seconds()
                )

            # Get or clone repo
            repo_path = self._get_or_clone_repo(
                url=family_config.example_repo.url,
                ref=family_config.example_repo.ref,
                family=family,
            )

            if not repo_path:
                return BackfillResult(
                    success=False,
                    target="test_data",
                    source=family_config.example_repo.url,
                    destination=str(local_path),
                    error="Failed to clone repository",
                    duration_seconds=(datetime.now() - start_time).total_seconds()
                )

            # Copy test data from repo to local path
            source_path = repo_path / family_config.example_repo.test_data_path
            if not source_path.exists():
                return BackfillResult(
                    success=False,
                    target="test_data",
                    source=str(source_path),
                    destination=str(local_path),
                    error=f"test_data_path not found in repo: {family_config.example_repo.test_data_path}",
                    duration_seconds=(datetime.now() - start_time).total_seconds()
                )

            # Create destination directory (with path guard)
            assert_write_allowed(local_path, reason=f"backfill test data for {family}")
            local_path.mkdir(parents=True, exist_ok=True)

            # Copy files
            files_copied = self._copy_directory(source_path, local_path)

            logger.info(f"Backfilled {files_copied} test data files for {family} from {family_config.example_repo.url}")

            return BackfillResult(
                success=True,
                target="test_data",
                source=family_config.example_repo.url,
                destination=str(local_path),
                files_copied=files_copied,
                duration_seconds=(datetime.now() - start_time).total_seconds()
            )

        except Exception as e:
            logger.exception(f"Error backfilling test data for {family}")
            return BackfillResult(
                success=False,
                target="test_data",
                source="",
                destination="",
                error=str(e),
                duration_seconds=(datetime.now() - start_time).total_seconds()
            )

    def backfill_api_reference(
        self,
        family: str,
        force: bool = False,
    ) -> BackfillResult:
        """
        Deprecated: API reference backfill removed (TASK-DLL-04).
        API catalogs are now generated directly from assembly reflection.
        """
        return BackfillResult(
            success=True,
            target="api_reference",
            source="deprecated",
            destination="",
            skipped=True,
            skip_reason="api_reference_backfill_removed_use_assembly_reflection",
            duration_seconds=0.0
        )

    def backfill_examples_to_vector_db(
        self,
        family: str,
        vector_service,
        force: bool = False,
    ) -> BackfillResult:
        """
        Backfill verified examples from example_repo to vector DB.

        Args:
            family: Family identifier
            vector_service: VectorDBService instance
            force: Force re-indexing even if examples exist

        Returns:
            BackfillResult with operation details
        """
        start_time = datetime.now()

        try:
            # Check if vector service is available
            if not vector_service or not vector_service.is_available():
                return BackfillResult(
                    success=True,
                    target="examples",
                    source="vector_db",
                    destination="",
                    skipped=True,
                    skip_reason="vector_db_not_available",
                    duration_seconds=(datetime.now() - start_time).total_seconds()
                )

            # Load family config
            family_config = self.config_manager.load_family_config(family)

            # Check if example_repo is configured
            if not family_config.example_repo.url:
                return BackfillResult(
                    success=False,
                    target="examples",
                    source="example_repo",
                    destination="vector_db",
                    error="example_repo.url not configured",
                    duration_seconds=(datetime.now() - start_time).total_seconds()
                )

            # Check if examples_path is configured
            if not family_config.example_repo.examples_path:
                return BackfillResult(
                    success=False,
                    target="examples",
                    source=family_config.example_repo.url,
                    destination="vector_db",
                    error="example_repo.examples_path not configured",
                    duration_seconds=(datetime.now() - start_time).total_seconds()
                )

            # Check GitPython availability
            if not GIT_AVAILABLE:
                return BackfillResult(
                    success=False,
                    target="examples",
                    source=family_config.example_repo.url,
                    destination="vector_db",
                    error="GitPython not installed - pip install gitpython",
                    duration_seconds=(datetime.now() - start_time).total_seconds()
                )

            # Get or clone repo
            repo_path = self._get_or_clone_repo(
                url=family_config.example_repo.url,
                ref=family_config.example_repo.ref,
                family=family,
            )

            if not repo_path:
                return BackfillResult(
                    success=False,
                    target="examples",
                    source=family_config.example_repo.url,
                    destination="vector_db",
                    error="Failed to clone repository",
                    duration_seconds=(datetime.now() - start_time).total_seconds()
                )

            # Extract examples from repo
            examples_path = repo_path / family_config.example_repo.examples_path
            if not examples_path.exists():
                return BackfillResult(
                    success=False,
                    target="examples",
                    source=str(examples_path),
                    destination="vector_db",
                    error=f"examples_path not found in repo: {family_config.example_repo.examples_path}",
                    duration_seconds=(datetime.now() - start_time).total_seconds()
                )

            # Find all C# example files (sorted deterministically for stable ordering)
            cs_files = sorted(examples_path.rglob("*.cs"), key=lambda p: str(p).lower())

            # Add to vector DB
            files_indexed = 0
            for cs_file in cs_files:
                try:
                    code = cs_file.read_text(encoding='utf-8')

                    # Add to vector DB with metadata
                    vector_service.add_example(
                        example_id=f"repo_{family}_{cs_file.stem}",
                        code=code,
                        metadata={
                            'family': family,
                            'source': 'example_repo',
                            'file_path': str(cs_file.relative_to(repo_path)),
                            'verified': True,
                        }
                    )
                    files_indexed += 1

                except Exception as e:
                    logger.warning(f"Failed to index {cs_file}: {e}")

            logger.info(f"Backfilled {files_indexed} examples for {family} to vector DB")

            return BackfillResult(
                success=True,
                target="examples",
                source=family_config.example_repo.url,
                destination="vector_db",
                files_copied=files_indexed,
                duration_seconds=(datetime.now() - start_time).total_seconds()
            )

        except Exception as e:
            logger.exception(f"Error backfilling examples for {family}")
            return BackfillResult(
                success=False,
                target="examples",
                source="",
                destination="vector_db",
                error=str(e),
                duration_seconds=(datetime.now() - start_time).total_seconds()
            )

    def _get_or_clone_repo(
        self,
        url: str,
        ref: str,
        family: str,
    ) -> Optional[Path]:
        """
        Get cached repo or clone from URL.

        Args:
            url: Git repository URL
            ref: Branch/tag/commit to checkout
            family: Family identifier (for cache naming)

        Returns:
            Path to cloned repo or None on failure
        """
        if not GIT_AVAILABLE:
            logger.error("GitPython not available")
            return None

        # Create repo cache directory
        repo_name = url.split('/')[-1].replace('.git', '')
        repo_cache_path = self.cache_dir / family / repo_name

        try:
            # Check if repo already cached
            if repo_cache_path.exists() and (repo_cache_path / '.git').exists():
                logger.info(f"Using cached repo at {repo_cache_path}")

                # Check if we should refresh (>24 hours old)
                timestamp_file = repo_cache_path / '.backfill_timestamp'
                should_refresh = True

                if timestamp_file.exists():
                    try:
                        last_fetch = datetime.fromisoformat(timestamp_file.read_text())
                        if datetime.now() - last_fetch < self.REPO_REFRESH_INTERVAL:
                            should_refresh = False
                    except Exception:
                        pass

                if should_refresh:
                    logger.info(f"Refreshing cached repo...")
                    try:
                        repo = Repo(repo_cache_path)
                        repo.remotes.origin.fetch()
                        repo.git.checkout(ref)
                        repo.git.pull()

                        # Update timestamp
                        timestamp_file.write_text(datetime.now().isoformat())
                    except Exception as e:
                        logger.warning(f"Failed to refresh repo, using cached version: {e}")

                return repo_cache_path

            # Clone repo
            logger.info(f"Cloning {url} to {repo_cache_path}")
            repo_cache_path.parent.mkdir(parents=True, exist_ok=True)

            # Shallow clone for efficiency
            repo = Repo.clone_from(
                url,
                repo_cache_path,
                branch=ref,
                depth=1,
            )

            # Create timestamp file
            repo_cache_path.mkdir(parents=True, exist_ok=True)
            timestamp_file = repo_cache_path / '.backfill_timestamp'
            timestamp_file.write_text(datetime.now().isoformat())

            logger.info(f"Successfully cloned {url}")
            return repo_cache_path

        except GitCommandError as e:
            logger.error(f"Git command failed: {e}")
            return None
        except Exception as e:
            logger.exception(f"Failed to clone repo: {e}")
            return None

    def backfill_gist_source_code(
        self,
        family: str,
        force: bool = False,
        dry_run: bool = False,
    ) -> BackfillResult:
        """
        Backfill gist source code for examples with empty original_code.

        Fetches gist content from GitHub API using the configured PAT.
        Only processes examples with source_type=GIST that have empty original_code.

        Args:
            family: Family identifier
            force: Force re-fetch even if original_code exists

        Returns:
            BackfillResult with operation details
        """
        start_time = datetime.now()

        try:
            # Load family config
            if self.config is not None:
                family_config = self.config
            elif self.config_manager is not None:
                family_config = self.config_manager.load_family_config(family)
            else:
                return BackfillResult(
                    success=False,
                    target="gist_source_code",
                    source="config",
                    destination="database",
                    error="config_manager or config is required",
                    duration_seconds=(datetime.now() - start_time).total_seconds()
                )

            # Check if gist support is enabled
            if not family_config.gist or not getattr(family_config.gist, "enabled", True):
                return BackfillResult(
                    success=True,
                    target="gist_source_code",
                    source="config",
                    destination="database",
                    skipped=True,
                    skip_reason="gist_support_disabled_or_not_configured",
                    duration_seconds=(datetime.now() - start_time).total_seconds()
                )

            # Get gist PAT from environment (optional — public gists work without auth)
            pat_env_var = family_config.gist.pat_env_var
            gist_pat = os.environ.get(pat_env_var)

            if not gist_pat:
                logger.info(f"No {pat_env_var} set, fetching public gists without authentication (rate-limited)")


            from ..core.database import Database
            from ..core.models import SourceType

            db = self.db or Database(Path("data/example_reviewer.db"))

            # Get gist examples with empty original_code
            examples = db.get_examples_by_family(family)
            gist_examples = []
            for example in examples:
                if example.source_type != SourceType.GIST:
                    continue
                if example.gist is None:
                    continue
                if example.original_code and not force:
                    continue
                gist_examples.append(example)

            if not gist_examples:
                return BackfillResult(
                    success=True,
                    target="gist_source_code",
                    source="github_api",
                    destination="database",
                    skipped=True,
                    skip_reason="no_gist_examples_need_backfill",
                    duration_seconds=(datetime.now() - start_time).total_seconds(),
                    items_processed=0,
                    items_downloaded=0,
                    items_failed=0,
                )

            # Create resolver with PAT
            resolver = GistResolver(token=gist_pat)

            # Fetch content for each gist example
            files_backfilled = 0
            errors = []
            items_processed = 0

            for example in gist_examples:
                items_processed += 1
                try:
                    gist_info = example.gist

                    # Use GistResolver to fetch content
                    content = resolver.resolve_gist(
                        owner=gist_info.owner,
                        gist_id=gist_info.gist_id,
                        filename=gist_info.filename,
                    )

                    if content:
                        if not dry_run:
                            db.update_example_original_code(example.example_id, content)
                        files_backfilled += 1
                        logger.debug(f"Backfilled gist content for {example.example_id}")
                    else:
                        errors.append(f"{example.example_id}: Empty response from gist")

                except Exception as e:
                    errors.append(f"{example.example_id}: {str(e)}")
                    logger.warning(f"Failed to backfill gist for {example.example_id}: {e}")

            logger.info(
                f"Backfilled {files_backfilled} gist examples for {family} "
                f"({len(errors)} errors)"
            )

            return BackfillResult(
                success=True,
                target="gist_source_code",
                source="github_api",
                destination="database",
                files_copied=files_backfilled,
                error="; ".join(errors[:5]) if errors else None,
                duration_seconds=(datetime.now() - start_time).total_seconds(),
                items_processed=items_processed,
                items_downloaded=files_backfilled,
                items_failed=len(errors),
            )

        except Exception as e:
            logger.exception(f"Error backfilling gist source code for {family}")
            return BackfillResult(
                success=False,
                target="gist_source_code",
                source="github_api",
                destination="database",
                error=str(e),
                duration_seconds=(datetime.now() - start_time).total_seconds()
            )

    def backfill_examples_files(
        self,
        family: str,
        force: bool = False,
    ) -> BackfillResult:
        """
        Backfill example files from example_repo to disk (artifacts/backfill/<family>/examples/).

        Handles both examples_path and samples_path if configured, storing them in
        separate subdirectories (examples/ and samples/).

        Also creates an index JSON file with metadata for each example.

        Args:
            family: Family identifier
            force: Force download even if examples exist locally

        Returns:
            BackfillResult with operation details
        """
        start_time = datetime.now()
        import json
        import hashlib

        try:
            # Load family config
            family_config = self.config_manager.load_family_config(family)

            # Base destination path
            base_dest = Path("artifacts/backfill") / family
            index_path = base_dest / "examples-index.json"

            # Check if examples already exist
            examples_dest = base_dest / "examples"
            samples_dest = base_dest / "samples"
            if examples_dest.exists() and not force:
                return BackfillResult(
                    success=True,
                    target="examples_files",
                    source="local",
                    destination=str(base_dest),
                    skipped=True,
                    skip_reason="examples_files_already_exist",
                    duration_seconds=(datetime.now() - start_time).total_seconds()
                )

            # Check if example_repo is configured
            if not family_config.example_repo.url:
                return BackfillResult(
                    success=False,
                    target="examples_files",
                    source="example_repo",
                    destination=str(base_dest),
                    error="example_repo.url not configured",
                    duration_seconds=(datetime.now() - start_time).total_seconds()
                )

            # Check if at least one path is configured
            has_examples = bool(family_config.example_repo.examples_path)
            has_samples = bool(getattr(family_config.example_repo, 'samples_path', ''))
            if not has_examples and not has_samples:
                return BackfillResult(
                    success=False,
                    target="examples_files",
                    source=family_config.example_repo.url,
                    destination=str(base_dest),
                    error="neither examples_path nor samples_path configured",
                    duration_seconds=(datetime.now() - start_time).total_seconds()
                )

            # Check GitPython availability
            if not GIT_AVAILABLE:
                return BackfillResult(
                    success=False,
                    target="examples_files",
                    source=family_config.example_repo.url,
                    destination=str(base_dest),
                    error="GitPython not installed - pip install gitpython",
                    duration_seconds=(datetime.now() - start_time).total_seconds()
                )

            # Get or clone repo
            repo_path = self._get_or_clone_repo(
                url=family_config.example_repo.url,
                ref=family_config.example_repo.ref,
                family=family,
            )

            if not repo_path:
                return BackfillResult(
                    success=False,
                    target="examples_files",
                    source=family_config.example_repo.url,
                    destination=str(base_dest),
                    error="Failed to clone repository",
                    duration_seconds=(datetime.now() - start_time).total_seconds()
                )

            # Collect source paths to process
            source_paths = []
            if has_examples:
                examples_src = repo_path / family_config.example_repo.examples_path
                if examples_src.exists():
                    source_paths.append(("examples", examples_src, examples_dest))
                else:
                    logger.warning(f"examples_path not found: {family_config.example_repo.examples_path}")

            if has_samples:
                samples_src = repo_path / family_config.example_repo.samples_path
                if samples_src.exists():
                    source_paths.append(("samples", samples_src, samples_dest))
                else:
                    logger.warning(f"samples_path not found: {family_config.example_repo.samples_path}")

            if not source_paths:
                return BackfillResult(
                    success=False,
                    target="examples_files",
                    source=family_config.example_repo.url,
                    destination=str(base_dest),
                    error="no valid source paths found in repo",
                    duration_seconds=(datetime.now() - start_time).total_seconds()
                )

            # Copy .cs files and build index
            index_entries = []
            files_copied = 0

            for source_type, source_path, dest_path in source_paths:
                # Create destination directory (with path guard)
                assert_write_allowed(dest_path, reason=f"backfill {source_type} files for {family}")
                dest_path.mkdir(parents=True, exist_ok=True)

                # Find all C# example files (sorted deterministically)
                cs_files = sorted(source_path.rglob("*.cs"), key=lambda p: str(p).lower())

                for cs_file in cs_files:
                    try:
                        # Calculate relative path
                        relative_path = cs_file.relative_to(source_path)
                        dest_file = dest_path / relative_path

                        # Create parent directory if needed
                        assert_write_allowed(dest_file, reason=f"backfill {source_type} file {cs_file.name}")
                        dest_file.parent.mkdir(parents=True, exist_ok=True)

                        # Copy file
                        shutil.copy2(cs_file, dest_file)
                        files_copied += 1

                        # Read file for index metadata
                        code = cs_file.read_text(encoding='utf-8')

                        # Generate stable ID from file path (include source_type for uniqueness)
                        full_path = f"{source_type}/{relative_path}"
                        file_id = hashlib.sha256(full_path.encode()).hexdigest()[:16]

                        # Basic tag inference (can be enhanced later)
                        tags = [source_type]  # Tag with source type
                        if "compression" in code.lower():
                            tags.append("compression")
                        if "extract" in code.lower():
                            tags.append("extraction")
                        if "encrypt" in code.lower():
                            tags.append("encryption")
                        if "password" in code.lower():
                            tags.append("password")

                        # Add to index
                        index_entries.append({
                            "id": file_id,
                            "path": full_path.replace("\\", "/"),
                            "class_name": cs_file.stem,
                            "source_type": source_type,
                            "tags": tags,
                            "size_bytes": cs_file.stat().st_size,
                        })

                    except Exception as e:
                        logger.warning(f"Failed to copy {source_type} file {cs_file}: {e}")

            # Write index JSON
            assert_write_allowed(index_path, reason=f"write examples index for {family}")
            index_path.parent.mkdir(parents=True, exist_ok=True)
            with open(index_path, 'w', encoding='utf-8') as f:
                json.dump({
                    "family": family,
                    "source": family_config.example_repo.url,
                    "generated_at": datetime.now().isoformat(),
                    "total_examples": len(index_entries),
                    "examples_count": len([e for e in index_entries if e.get("source_type") == "examples"]),
                    "samples_count": len([e for e in index_entries if e.get("source_type") == "samples"]),
                    "examples": index_entries
                }, f, indent=2)

            logger.info(f"Backfilled {files_copied} example/sample files for {family} to {base_dest}")

            return BackfillResult(
                success=True,
                target="examples_files",
                source=family_config.example_repo.url,
                destination=str(base_dest),
                files_copied=files_copied,
                duration_seconds=(datetime.now() - start_time).total_seconds()
            )

        except Exception as e:
            logger.exception(f"Error backfilling example files for {family}")
            return BackfillResult(
                success=False,
                target="examples_files",
                source="",
                destination="",
                error=str(e),
                duration_seconds=(datetime.now() - start_time).total_seconds()
            )

    def _copy_directory(self, source: Path, destination: Path) -> int:
        """
        Copy all files from source to destination recursively.

        Args:
            source: Source directory
            destination: Destination directory

        Returns:
            Number of files copied
        """
        files_copied = 0

        try:
            # Sort rglob results deterministically (case-normalized for Windows compatibility)
            for item in sorted(source.rglob('*'), key=lambda p: str(p).lower()):
                if item.is_file():
                    # Calculate relative path
                    relative_path = item.relative_to(source)
                    dest_path = destination / relative_path

                    # Create parent directory if needed (with path guard)
                    assert_write_allowed(dest_path, reason="backfill directory copy")
                    dest_path.parent.mkdir(parents=True, exist_ok=True)

                    # Copy file
                    shutil.copy2(item, dest_path)
                    files_copied += 1

        except Exception as e:
            logger.error(f"Error copying directory {source} to {destination}: {e}")

        return files_copied

    def backfill_rar_fixtures(
        self,
        family: str,
        force: bool = False,
    ) -> BackfillResult:
        """
        Task 3: Backfill RAR fixtures from example_repo.

        Attempts to fetch RAR files from the example repo's test data path:
        - plrabn12.rar
        - encrypted.rar

        If unavailable, marks them as requiring substitution.

        Args:
            family: Family identifier
            force: Force download even if files exist

        Returns:
            BackfillResult with operation details
        """
        start_time = datetime.now()
        import requests

        try:
            # Load family config
            family_config = self.config_manager.load_family_config(family)

            # Destination path
            rar_dest = Path("artifacts/backfill") / family / "test-data"
            rar_dest.mkdir(parents=True, exist_ok=True)

            # RAR fixtures to fetch
            rar_fixtures = ["plrabn12.rar", "encrypted.rar"]
            files_fetched = 0
            errors = []

            # Check if example_repo is configured
            if not family_config.example_repo.url:
                return BackfillResult(
                    success=False,
                    target="rar_fixtures",
                    source="example_repo",
                    destination=str(rar_dest),
                    error="example_repo.url not configured",
                    duration_seconds=(datetime.now() - start_time).total_seconds()
                )

            # Construct raw URL for GitHub
            # Example: https://raw.githubusercontent.com/aspose-zip/Aspose.ZIP-for-.NET/master/Examples/Data/
            repo_url = family_config.example_repo.url
            ref = family_config.example_repo.ref
            test_data_path = family_config.example_repo.test_data_path

            # Parse GitHub URL to raw URL
            if "github.com" in repo_url:
                # https://github.com/owner/repo -> https://raw.githubusercontent.com/owner/repo
                raw_base = repo_url.replace("github.com", "raw.githubusercontent.com")
                raw_base = raw_base.rstrip(".git")
            else:
                logger.warning(f"Non-GitHub repo URL, cannot construct raw URL: {repo_url}")
                return BackfillResult(
                    success=False,
                    target="rar_fixtures",
                    source=repo_url,
                    destination=str(rar_dest),
                    error="Only GitHub repos supported for raw file fetching",
                    duration_seconds=(datetime.now() - start_time).total_seconds()
                )

            for rar_file in rar_fixtures:
                dest_file = rar_dest / rar_file

                if dest_file.exists() and not force:
                    logger.debug(f"RAR fixture already exists: {rar_file}")
                    files_fetched += 1
                    continue

                # Construct raw URL for this file
                raw_url = f"{raw_base}/{ref}/{test_data_path}/{rar_file}"
                logger.info(f"Attempting to fetch RAR fixture: {raw_url}")

                try:
                    response = requests.get(raw_url, timeout=30)
                    if response.status_code == 200 and len(response.content) > 0:
                        # Verify it's not an error page
                        if response.content[:4] == b'Rar!' or response.content[:7] == b'Rar!\x1a\x07\x00':
                            # Valid RAR file
                            assert_write_allowed(dest_file, reason=f"backfill RAR fixture {rar_file}")
                            dest_file.write_bytes(response.content)
                            files_fetched += 1
                            logger.info(f"Successfully fetched RAR fixture: {rar_file}")
                        else:
                            # Not a valid RAR file
                            errors.append(f"{rar_file}: Not a valid RAR file (invalid header)")
                    else:
                        errors.append(f"{rar_file}: HTTP {response.status_code}")
                except requests.RequestException as e:
                    errors.append(f"{rar_file}: {str(e)}")

            return BackfillResult(
                success=files_fetched > 0 or len(errors) == 0,
                target="rar_fixtures",
                source=repo_url,
                destination=str(rar_dest),
                files_copied=files_fetched,
                error="; ".join(errors) if errors else None,
                duration_seconds=(datetime.now() - start_time).total_seconds(),
                items_processed=len(rar_fixtures),
                items_downloaded=files_fetched,
                items_failed=len(errors),
            )

        except Exception as e:
            logger.exception(f"Error backfilling RAR fixtures for {family}")
            return BackfillResult(
                success=False,
                target="rar_fixtures",
                source="",
                destination="",
                error=str(e),
                duration_seconds=(datetime.now() - start_time).total_seconds()
            )
