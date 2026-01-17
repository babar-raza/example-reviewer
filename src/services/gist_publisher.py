"""
Gist Publisher Service for Example Reviewer Pipeline.
Publishes verified code to GitHub Gists via the GitHub API.
"""

import os
import logging
from dataclasses import dataclass
from typing import Optional, Dict, Any

# requests is used for GitHub API calls
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class GistPublishResult:
    """Result of a gist publish operation."""
    success: bool
    gist_id: Optional[str] = None
    html_url: Optional[str] = None
    raw_url: Optional[str] = None
    error: Optional[str] = None
    response_code: Optional[int] = None


class GistPublisher:
    """
    Publish code to GitHub Gists via the GitHub API.

    Supports:
    - Creating new public or secret gists
    - Updating existing gists (via PATCH)
    - Graceful degradation when token not available

    All operations are non-blocking and failures don't break the pipeline.
    """

    GIST_API_URL = "https://api.github.com/gists"

    def __init__(
        self,
        target_account: str,
        token: Optional[str] = None,
        token_env_var: str = "GIST_PAT",
        is_public: bool = True,
        timeout_seconds: int = 30,
    ):
        """
        Initialize gist publisher.

        Args:
            target_account: GitHub account name for gist attribution
            token: GitHub PAT (if not provided, reads from token_env_var)
            token_env_var: Environment variable name for PAT
            is_public: Whether to create public (True) or secret (False) gists
            timeout_seconds: HTTP request timeout
        """
        self.target_account = target_account
        self.token = token or os.environ.get(token_env_var)
        self.is_public = is_public
        self.timeout_seconds = timeout_seconds

    def is_available(self) -> bool:
        """
        Check if publishing is available.

        Returns:
            True if requests library is available and token is set
        """
        if not REQUESTS_AVAILABLE:
            logger.debug("GistPublisher unavailable: requests library not installed")
            return False
        if not self.token:
            logger.debug("GistPublisher unavailable: no authentication token")
            return False
        return True

    def publish_gist(
        self,
        code_content: str,
        filename: str,
        description: str,
        old_gist_id: Optional[str] = None,
    ) -> GistPublishResult:
        """
        Create a new gist or update an existing one.

        Args:
            code_content: The code to publish
            filename: Filename for the gist (e.g., "Example.cs")
            description: Gist description
            old_gist_id: If provided, update this gist instead of creating new

        Returns:
            GistPublishResult with operation details
        """
        if not REQUESTS_AVAILABLE:
            return GistPublishResult(
                success=False,
                error="Requests library not available"
            )

        if not self.token:
            return GistPublishResult(
                success=False,
                error="No authentication token"
            )

        if not code_content or not code_content.strip():
            return GistPublishResult(
                success=False,
                error="Cannot publish empty code content"
            )

        # Ensure filename has extension
        if not filename:
            filename = "example.cs"
        elif '.' not in filename:
            filename = f"{filename}.cs"

        if old_gist_id:
            return self._update_gist(old_gist_id, filename, code_content, description)
        return self._create_gist(filename, code_content, description)

    def _create_gist(
        self,
        filename: str,
        content: str,
        description: str,
    ) -> GistPublishResult:
        """
        Create a new gist via POST /gists.

        Args:
            filename: Filename for the gist file
            content: Code content
            description: Gist description

        Returns:
            GistPublishResult with created gist details
        """
        try:
            payload = {
                "description": description,
                "public": self.is_public,
                "files": {
                    filename: {
                        "content": content
                    }
                }
            }

            response = requests.post(
                self.GIST_API_URL,
                headers=self._get_headers(),
                json=payload,
                timeout=self.timeout_seconds,
            )

            if response.status_code == 201:
                data = response.json()
                return self._parse_gist_response(data, response.status_code)

            # Handle error responses
            return GistPublishResult(
                success=False,
                error=f"GitHub API error: {response.status_code} - {response.text[:200]}",
                response_code=response.status_code,
            )

        except requests.exceptions.Timeout:
            return GistPublishResult(
                success=False,
                error=f"Request timed out after {self.timeout_seconds}s"
            )
        except requests.exceptions.RequestException as e:
            return GistPublishResult(
                success=False,
                error=f"Request failed: {str(e)}"
            )
        except Exception as e:
            logger.exception(f"Unexpected error creating gist: {e}")
            return GistPublishResult(
                success=False,
                error=f"Unexpected error: {str(e)}"
            )

    def _update_gist(
        self,
        gist_id: str,
        filename: str,
        content: str,
        description: str,
    ) -> GistPublishResult:
        """
        Update an existing gist via PATCH /gists/{id}.

        Args:
            gist_id: ID of the gist to update
            filename: Filename for the gist file
            content: New code content
            description: Updated description

        Returns:
            GistPublishResult with updated gist details
        """
        try:
            url = f"{self.GIST_API_URL}/{gist_id}"

            payload = {
                "description": description,
                "files": {
                    filename: {
                        "content": content
                    }
                }
            }

            response = requests.patch(
                url,
                headers=self._get_headers(),
                json=payload,
                timeout=self.timeout_seconds,
            )

            if response.status_code == 200:
                data = response.json()
                return self._parse_gist_response(data, response.status_code)

            # Handle error responses
            if response.status_code == 404:
                # Gist not found, fall back to creating new
                logger.warning(f"Gist {gist_id} not found, creating new gist instead")
                return self._create_gist(filename, content, description)

            return GistPublishResult(
                success=False,
                error=f"GitHub API error: {response.status_code} - {response.text[:200]}",
                response_code=response.status_code,
            )

        except requests.exceptions.Timeout:
            return GistPublishResult(
                success=False,
                error=f"Request timed out after {self.timeout_seconds}s"
            )
        except requests.exceptions.RequestException as e:
            return GistPublishResult(
                success=False,
                error=f"Request failed: {str(e)}"
            )
        except Exception as e:
            logger.exception(f"Unexpected error updating gist: {e}")
            return GistPublishResult(
                success=False,
                error=f"Unexpected error: {str(e)}"
            )

    def _get_headers(self) -> Dict[str, str]:
        """Get HTTP headers for GitHub API requests."""
        return {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "ExampleReviewerPipeline/1.0",
        }

    def _parse_gist_response(
        self,
        data: Dict[str, Any],
        status_code: int,
    ) -> GistPublishResult:
        """
        Parse GitHub API response into GistPublishResult.

        Args:
            data: JSON response from GitHub
            status_code: HTTP status code

        Returns:
            GistPublishResult with extracted details
        """
        gist_id = data.get("id")
        html_url = data.get("html_url")

        # Get raw URL for the first file
        raw_url = None
        files = data.get("files", {})
        if files:
            first_file = next(iter(files.values()), {})
            raw_url = first_file.get("raw_url")

        return GistPublishResult(
            success=True,
            gist_id=gist_id,
            html_url=html_url,
            raw_url=raw_url,
            response_code=status_code,
        )

    def get_gist(self, gist_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch a gist by ID.

        Args:
            gist_id: Gist ID to fetch

        Returns:
            Gist data dict or None on error
        """
        if not self.is_available():
            return None

        try:
            url = f"{self.GIST_API_URL}/{gist_id}"
            response = requests.get(
                url,
                headers=self._get_headers(),
                timeout=self.timeout_seconds,
            )

            if response.status_code == 200:
                return response.json()
            return None

        except Exception as e:
            logger.warning(f"Failed to fetch gist {gist_id}: {e}")
            return None

    @classmethod
    def from_config(cls, gist_config) -> 'GistPublisher':
        """
        Create publisher from GistConfig.

        Args:
            gist_config: GistConfig instance

        Returns:
            GistPublisher instance
        """
        return cls(
            target_account=gist_config.target_account,
            token_env_var=gist_config.pat_env_var,
            is_public=getattr(gist_config, 'is_public', True),
        )
