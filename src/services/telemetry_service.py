"""
TelemetryService for Example Reviewer Pipeline.
Handles HTTP API posting and SQLite storage for run telemetry.
"""

import logging
import subprocess
from datetime import datetime, timezone
from typing import Optional, Dict, Any

import httpx

from ..core.config import TelemetryConfig, FamilyConfig
from ..core.database import Database
from ..core.models import TelemetryRun

logger = logging.getLogger(__name__)


class TelemetryService:
    """
    Service for telemetry recording with dual-write to HTTP API and SQLite.

    Features:
    - Creates TelemetryRun events with full ~40 field schema
    - Posts to HTTP API (non-blocking, with retry)
    - Saves to local SQLite for persistence
    - Associates git commits with runs
    - Graceful degradation (telemetry failures don't crash pipeline)
    """

    def __init__(self, config: TelemetryConfig, db: Database):
        """
        Initialize TelemetryService.

        Args:
            config: TelemetryConfig with HTTP API settings
            db: Database instance for local storage
        """
        self.config = config
        self.db = db
        self._http_client: Optional[httpx.Client] = None

    @property
    def http_client(self) -> httpx.Client:
        """Lazy-initialize HTTP client."""
        if self._http_client is None:
            self._http_client = httpx.Client(
                timeout=self.config.http_api_timeout_seconds,
                follow_redirects=True,
            )
        return self._http_client

    def close(self) -> None:
        """Close HTTP client."""
        if self._http_client:
            self._http_client.close()
            self._http_client = None

    def create_run_event(
        self,
        run_id: str,
        job_type: str,
        family_config: FamilyConfig,
        status: str = "running",
    ) -> TelemetryRun:
        """
        Create a new TelemetryRun event populated from config and context.

        Args:
            run_id: Pipeline run ID
            job_type: Type of job (e.g., 'validation', 'discovery')
            family_config: FamilyConfig for product context
            status: Initial status (default: 'running')

        Returns:
            TelemetryRun with all fields populated
        """
        # Get git info from pipeline repository (example-reviewer repo)
        pipeline_git = self._get_pipeline_repo_git_metadata()

        # Get content root for subdomain field
        content_root = None
        if family_config.content_roots:
            content_root = family_config.content_roots[0]

        # Extract subdomain from content roots
        subdomain = content_root or ""

        # Use family example repo URL for website field (backward compatibility)
        website_url = family_config.example_repo.url if family_config.example_repo else ""

        # Create event with all fields populated
        event = TelemetryRun(
            run_id=run_id,
            job_type=job_type,
            status=status,
            product=family_config.display_name or f"Aspose.{family_config.family.title()}",
            product_family=family_config.family,
            platform="dotnet",
            subdomain=subdomain,
            website=website_url,
            git_repo=pipeline_git["repo_url"],  # Pipeline repo URL
            git_branch=pipeline_git["branch"],  # Pipeline repo branch
            git_commit_hash=pipeline_git["commit_sha"],  # Pipeline repo commit
            git_run_tag=f"{family_config.family}-{run_id[:8]}",
        )

        return event

    def start_run(self, event: TelemetryRun) -> bool:
        """
        Start tracking a run - POST to API and save locally.

        Args:
            event: TelemetryRun event to record

        Returns:
            True if at least local save succeeded
        """
        saved_locally = False
        posted_to_api = False

        # Save to local SQLite (always try this first)
        try:
            self.db.save_telemetry_run(event)
            saved_locally = True
            logger.debug(f"Saved telemetry run locally: {event.event_id}")
        except Exception as e:
            logger.warning(f"Failed to save telemetry run locally: {e}")

        # POST to HTTP API if enabled
        if self.config.http_api_enabled:
            posted_to_api = self._post_to_api(event)
            if posted_to_api:
                # Update local record to reflect API posting
                self.db.update_telemetry_run(event.event_id, {
                    'api_posted': True,
                    'api_posted_at': datetime.now(timezone.utc),
                })

        return saved_locally

    def update_run(self, event_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update a run - PATCH API and update locally.

        Args:
            event_id: Event ID to update
            updates: Fields to update

        Returns:
            True if at least local update succeeded
        """
        updated_locally = False

        # Update local SQLite
        try:
            updated_locally = self.db.update_telemetry_run(event_id, updates)
            if updated_locally:
                logger.debug(f"Updated telemetry run locally: {event_id}")
        except Exception as e:
            logger.warning(f"Failed to update telemetry run locally: {e}")

        # PATCH HTTP API if enabled
        if self.config.http_api_enabled:
            self._patch_api(event_id, updates)

        return updated_locally

    def complete_run(
        self,
        event_id: str,
        status: str,
        items_discovered: int = 0,
        items_succeeded: int = 0,
        items_failed: int = 0,
        items_skipped: int = 0,
        error_summary: Optional[str] = None,
        error_details: Optional[str] = None,
        output_summary: str = "",
    ) -> bool:
        """
        Complete a run with final statistics.

        Args:
            event_id: Event ID to complete
            status: Final status ('success', 'failure', 'partial')
            items_discovered: Total items discovered
            items_succeeded: Items that succeeded
            items_failed: Items that failed
            items_skipped: Items skipped
            error_summary: Error summary if failed
            error_details: Detailed error info
            output_summary: Summary of outputs

        Returns:
            True if at least local update succeeded
        """
        end_time = datetime.now(timezone.utc)

        # Get existing record to calculate duration
        existing = self.db.get_telemetry_run(event_id)
        duration_ms = 0
        if existing:
            delta = end_time - existing.start_time
            duration_ms = int(delta.total_seconds() * 1000)

        updates = {
            'status': status,
            'end_time': end_time,
            'duration_ms': duration_ms,
            'items_discovered': items_discovered,
            'items_succeeded': items_succeeded,
            'items_failed': items_failed,
            'items_skipped': items_skipped,
            'output_summary': output_summary,
        }

        if error_summary:
            updates['error_summary'] = error_summary
        if error_details:
            updates['error_details'] = error_details

        return self.update_run(event_id, updates)

    def emit_event(
        self,
        run_id: str,
        event_type: str,
        family: str,
        phase: Optional[str] = None,
        example_id: Optional[str] = None,
        duration_ms: Optional[int] = None,
        success: bool = True,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Emit a telemetry event to the database.

        Args:
            run_id: Run identifier
            event_type: Type of event (e.g., 'timeout_exceeded', 'compilation_success')
            family: Product family
            phase: Pipeline phase
            example_id: Example identifier
            duration_ms: Duration in milliseconds
            success: Whether operation succeeded
            metadata: Additional metadata

        Returns:
            event_id
        """
        from ..core.models import TelemetryEvent
        import uuid

        event = TelemetryEvent(
            event_id=str(uuid.uuid4()),
            run_id=run_id,
            family=family,
            event_type=event_type,
            phase=phase,
            example_id=example_id,
            duration_ms=duration_ms,
            success=success,
            metadata=metadata or {},
            timestamp=datetime.now(timezone.utc),
        )

        try:
            self.db.save_telemetry_event(event)
            logger.debug(f"Emitted telemetry event: {event_type} for example {example_id}")
            return event.event_id
        except Exception as e:
            logger.warning(f"Failed to emit telemetry event: {e}")
            return ""

    def associate_commit(
        self,
        event_id: str,
        commit_hash: str,
        commit_timestamp: Optional[datetime] = None,
    ) -> bool:
        """
        Associate a git commit with a telemetry run.

        Args:
            event_id: Event ID to update
            commit_hash: Git commit SHA
            commit_timestamp: Timestamp of the commit

        Returns:
            True if at least local update succeeded
        """
        updates = {
            'git_commit_hash': commit_hash,
            'git_commit_timestamp': commit_timestamp or datetime.now(timezone.utc),
        }

        updated_locally = self.update_run(event_id, updates)

        # POST to /associate-commit endpoint if API enabled
        if self.config.http_api_enabled:
            self._post_associate_commit(event_id, commit_hash, commit_timestamp)

        return updated_locally

    def _post_to_api(self, event: TelemetryRun) -> bool:
        """
        POST telemetry event to HTTP API with retry logic.

        Args:
            event: TelemetryRun to post

        Returns:
            True if posted successfully
        """
        if not self.config.http_api_enabled:
            return False

        url = f"{self.config.http_api_url}/api/v1/runs"
        data = event.to_api_dict()
        retry_count = 0

        while retry_count <= self.config.http_api_retry_count:
            try:
                response = self.http_client.post(url, json=data)
                if response.status_code in (200, 201):
                    logger.info(f"Posted telemetry run to API: {event.event_id}")
                    return True
                else:
                    logger.warning(
                        f"API POST failed with status {response.status_code}: {response.text[:200]}"
                    )
            except httpx.TimeoutException:
                logger.warning(f"API POST timeout (attempt {retry_count + 1})")
            except httpx.RequestError as e:
                logger.warning(f"API POST request error: {e}")
            except Exception as e:
                logger.warning(f"API POST unexpected error: {e}")

            retry_count += 1

        # Update retry count in local record
        try:
            self.db.update_telemetry_run(event.event_id, {'api_retry_count': retry_count})
        except Exception:
            pass

        logger.warning(f"Failed to POST telemetry run after {retry_count} attempts")
        return False

    def _patch_api(self, event_id: str, updates: Dict[str, Any]) -> bool:
        """
        PATCH telemetry event to HTTP API with retry logic.

        Args:
            event_id: Event ID to patch
            updates: Fields to update

        Returns:
            True if patched successfully
        """
        if not self.config.http_api_enabled:
            return False

        url = f"{self.config.http_api_url}/api/v1/runs/{event_id}"

        # Convert datetime objects to ISO strings for JSON
        data = {}
        for key, value in updates.items():
            if isinstance(value, datetime):
                data[key] = value.isoformat()
            else:
                data[key] = value

        retry_count = 0
        while retry_count <= self.config.http_api_retry_count:
            try:
                response = self.http_client.patch(url, json=data)
                if response.status_code in (200, 204):
                    logger.debug(f"Patched telemetry run via API: {event_id}")
                    return True
                else:
                    logger.warning(
                        f"API PATCH failed with status {response.status_code}: {response.text[:200]}"
                    )
            except httpx.TimeoutException:
                logger.warning(f"API PATCH timeout (attempt {retry_count + 1})")
            except httpx.RequestError as e:
                logger.warning(f"API PATCH request error: {e}")
            except Exception as e:
                logger.warning(f"API PATCH unexpected error: {e}")

            retry_count += 1

        logger.warning(f"Failed to PATCH telemetry run after {retry_count} attempts")
        return False

    def _post_associate_commit(
        self,
        event_id: str,
        commit_hash: str,
        commit_timestamp: Optional[datetime] = None,
    ) -> bool:
        """
        POST to /associate-commit endpoint.

        Args:
            event_id: Event ID
            commit_hash: Git commit SHA
            commit_timestamp: Commit timestamp

        Returns:
            True if posted successfully
        """
        if not self.config.http_api_enabled:
            return False

        url = f"{self.config.http_api_url}/api/v1/runs/{event_id}/associate-commit"
        data = {
            'commit_hash': commit_hash,
            'commit_timestamp': commit_timestamp.isoformat() if commit_timestamp else None,
        }

        try:
            response = self.http_client.post(url, json=data)
            if response.status_code in (200, 201, 204):
                logger.info(f"Associated commit {commit_hash[:8]} with run {event_id}")
                return True
            else:
                logger.warning(
                    f"associate-commit failed with status {response.status_code}"
                )
        except Exception as e:
            logger.warning(f"associate-commit error: {e}")

        return False

    def _get_git_branch(self, content_path: Optional[str] = None) -> str:
        """
        Get current git branch name.

        Args:
            content_path: Optional path to content directory (to get branch from content repo)

        Returns:
            Branch name or empty string if not in a git repo
        """
        try:
            # Determine working directory for git command
            cwd = None
            if content_path:
                from pathlib import Path
                content_dir = Path(content_path)
                if content_dir.exists():
                    cwd = content_dir if content_dir.is_dir() else content_dir.parent

            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=cwd,
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass
        return ""

    def _get_pipeline_repo_git_metadata(self) -> Dict[str, str]:
        """
        Get git metadata for the pipeline repository (example-reviewer repo).

        Returns:
            Dict with keys: repo_url, branch, commit_sha
        """
        metadata = {
            "repo_url": "",
            "branch": "",
            "commit_sha": ""
        }

        try:
            # Get remote URL
            result = subprocess.run(
                ["git", "config", "--get", "remote.origin.url"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                repo_url = result.stdout.strip()
                # Clean up URL (remove .git, convert ssh to https)
                if repo_url.endswith('.git'):
                    repo_url = repo_url[:-4]
                if repo_url.startswith('git@github.com:'):
                    repo_url = repo_url.replace('git@github.com:', 'https://github.com/')
                metadata["repo_url"] = repo_url

            # Get branch
            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                metadata["branch"] = result.stdout.strip()

            # Get commit SHA
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                metadata["commit_sha"] = result.stdout.strip()

        except Exception as e:
            logger.debug(f"Failed to get pipeline repo git metadata: {e}")

        return metadata
