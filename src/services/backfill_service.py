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

            # Create destination directory
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
        Backfill API reference documentation for a family.

        Args:
            family: Family identifier
            force: Force download even if cache exists

        Returns:
            BackfillResult with operation details
        """
        start_time = datetime.now()

        try:
            # Load family config
            family_config = self.config_manager.load_family_config(family)

            # Check if cache path is configured
            if not family_config.api_reference.cache_path:
                return BackfillResult(
                    success=True,
                    target="api_reference",
                    source="config",
                    destination="",
                    skipped=True,
                    skip_reason="cache_path_not_configured",
                    duration_seconds=(datetime.now() - start_time).total_seconds()
                )

            cache_path = Path(family_config.api_reference.cache_path)

            # Check if cache already exists
            if cache_path.exists() and not force:
                return BackfillResult(
                    success=True,
                    target="api_reference",
                    source="local",
                    destination=str(cache_path),
                    skipped=True,
                    skip_reason="cache_already_exists",
                    duration_seconds=(datetime.now() - start_time).total_seconds()
                )

            # Check if sources are configured
            if not family_config.api_reference.sources:
                return BackfillResult(
                    success=True,
                    target="api_reference",
                    source="config",
                    destination=str(cache_path),
                    skipped=True,
                    skip_reason="no_sources_configured",
                    duration_seconds=(datetime.now() - start_time).total_seconds()
                )

            # Create cache directory
            cache_path.mkdir(parents=True, exist_ok=True)

            # Copy from sources (currently assumes local sources)
            files_copied = 0
            for source in family_config.api_reference.sources:
                source_path = Path(source)
                if source_path.exists():
                    if source_path.is_dir():
                        files_copied += self._copy_directory(source_path, cache_path)
                    else:
                        shutil.copy2(source_path, cache_path / source_path.name)
                        files_copied += 1
                else:
                    logger.warning(f"API reference source not found: {source}")

            logger.info(f"Backfilled {files_copied} API reference files for {family}")

            return BackfillResult(
                success=True,
                target="api_reference",
                source=",".join(family_config.api_reference.sources),
                destination=str(cache_path),
                files_copied=files_copied,
                duration_seconds=(datetime.now() - start_time).total_seconds()
            )

        except Exception as e:
            logger.exception(f"Error backfilling API reference for {family}")
            return BackfillResult(
                success=False,
                target="api_reference",
                source="",
                destination="",
                error=str(e),
                duration_seconds=(datetime.now() - start_time).total_seconds()
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

            # Find all C# example files
            cs_files = list(examples_path.rglob("*.cs"))

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
            if not getattr(family_config.gist, "enabled", True):
                return BackfillResult(
                    success=True,
                    target="gist_source_code",
                    source="config",
                    destination="database",
                    skipped=True,
                    skip_reason="gist_support_disabled",
                    duration_seconds=(datetime.now() - start_time).total_seconds()
                )

            # Get gist PAT from environment
            pat_env_var = family_config.gist.pat_env_var
            gist_pat = os.environ.get(pat_env_var)

            if not gist_pat:
                return BackfillResult(
                    success=True,
                    target="gist_source_code",
                    source="github_api",
                    destination="database",
                    skipped=True,
                    skip_reason=f"gist_pat_not_set ({pat_env_var})",
                    duration_seconds=(datetime.now() - start_time).total_seconds()
                )

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
            for item in source.rglob('*'):
                if item.is_file():
                    # Calculate relative path
                    relative_path = item.relative_to(source)
                    dest_path = destination / relative_path

                    # Create parent directory if needed
                    dest_path.parent.mkdir(parents=True, exist_ok=True)

                    # Copy file
                    shutil.copy2(item, dest_path)
                    files_copied += 1

        except Exception as e:
            logger.error(f"Error copying directory {source} to {destination}: {e}")

        return files_copied
