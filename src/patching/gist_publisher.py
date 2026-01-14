"""
GitHub Gist Publisher for Example Review System.
Publishes code snippets as new GitHub gists when code changes.
"""

import hashlib
import logging
import requests
from typing import Optional, Dict
from datetime import datetime

from src.core.database import Database

logger = logging.getLogger(__name__)


class GistPublisher:
    """
    Service for publishing code as GitHub gists.

    Features:
    - Publishes code as new gists via GitHub API
    - Requires GitHub PAT with gist permission
    - Records publications in database
    - Never logs full token (only last 4 chars for security)
    - Handles rate limits and errors
    """

    GITHUB_API_BASE = "https://api.github.com/gists"

    def __init__(self, owner: str, token: str, db: Database, is_public: bool = True):
        """
        Initialize gist publisher.

        Args:
            owner: GitHub username for new gists
            token: GitHub PAT with gist permission (NEVER LOG THIS)
            db: Database instance
            is_public: Whether gists should be public (default True)
        """
        self.owner = owner
        self.token = token
        self.db = db
        self.is_public = is_public

        # Validate token format (basic check)
        if not token or len(token) < 10:
            raise ValueError("Invalid GitHub token: token must be at least 10 characters")

    def publish_gist(self, snippet_id: int, code_content: str, filename: str,
                     description: str, old_gist_id: str = None, old_owner: str = None) -> dict:
        """
        Publish code as new GitHub gist.

        Makes POST request to GitHub API to create a new gist with the provided code.

        Args:
            snippet_id: Snippet ID being published
            code_content: Code to publish
            filename: Filename for the gist file
            description: Gist description
            old_gist_id: Original gist ID (if replacing an existing gist)
            old_owner: Original gist owner (if replacing an existing gist)

        Returns:
            Dictionary with:
                - success: bool (True if published successfully)
                - gist_id: str (new gist ID)
                - html_url: str (public gist URL)
                - raw_url: str (raw content URL)
                - error: str (error message if failed)
        """
        # Compute code hash for tracking
        code_hash = hashlib.sha256(code_content.encode('utf-8')).hexdigest()

        # Prepare API request
        url = self.GITHUB_API_BASE
        headers = {
            'Authorization': f'Bearer {self.token}',
            'Accept': 'application/vnd.github.v3+json',
            'Content-Type': 'application/json'
        }

        payload = {
            'description': description,
            'public': self.is_public,
            'files': {
                filename: {
                    'content': code_content
                }
            }
        }

        # Log request (with redacted token)
        token_redacted = "..." + self.token[-4:] if len(self.token) >= 4 else "***"
        logger.info(
            f"Publishing gist for snippet {snippet_id}: "
            f"filename={filename}, owner={self.owner}, token=...{token_redacted}"
        )

        try:
            # Make API request
            response = requests.post(url, json=payload, headers=headers, timeout=30)

            # Handle 401 Unauthorized
            if response.status_code == 401:
                error_msg = "GitHub API returned 401 Unauthorized: invalid token or insufficient permissions"
                logger.error(f"Gist publication failed for snippet {snippet_id}: {error_msg}")

                # Store failure in database
                self.db.create_gist_publication(
                    snippet_id=snippet_id,
                    old_gist_id=old_gist_id or '',
                    old_owner=old_owner or '',
                    old_filename=filename,
                    new_gist_id='',
                    new_owner=self.owner,
                    new_filename=filename,
                    new_url='',
                    new_raw_url='',
                    code_hash=code_hash,
                    status='failed',
                    error_message=error_msg
                )

                return {
                    'success': False,
                    'gist_id': None,
                    'html_url': None,
                    'raw_url': None,
                    'error': error_msg
                }

            # Handle 403 Forbidden (rate limit or permissions)
            if response.status_code == 403:
                rate_limit_remaining = response.headers.get('X-RateLimit-Remaining', '?')

                if rate_limit_remaining == '0':
                    error_msg = "GitHub API rate limit exceeded"
                else:
                    error_msg = "GitHub API returned 403 Forbidden: insufficient permissions or rate limited"

                logger.error(f"Gist publication failed for snippet {snippet_id}: {error_msg}")

                # Store failure in database
                self.db.create_gist_publication(
                    snippet_id=snippet_id,
                    old_gist_id=old_gist_id or '',
                    old_owner=old_owner or '',
                    old_filename=filename,
                    new_gist_id='',
                    new_owner=self.owner,
                    new_filename=filename,
                    new_url='',
                    new_raw_url='',
                    code_hash=code_hash,
                    status='failed',
                    error_message=error_msg
                )

                return {
                    'success': False,
                    'gist_id': None,
                    'html_url': None,
                    'raw_url': None,
                    'error': error_msg
                }

            # Handle 404 Not Found
            if response.status_code == 404:
                error_msg = "GitHub API returned 404 Not Found: endpoint not available"
                logger.error(f"Gist publication failed for snippet {snippet_id}: {error_msg}")

                # Store failure in database
                self.db.create_gist_publication(
                    snippet_id=snippet_id,
                    old_gist_id=old_gist_id or '',
                    old_owner=old_owner or '',
                    old_filename=filename,
                    new_gist_id='',
                    new_owner=self.owner,
                    new_filename=filename,
                    new_url='',
                    new_raw_url='',
                    code_hash=code_hash,
                    status='failed',
                    error_message=error_msg
                )

                return {
                    'success': False,
                    'gist_id': None,
                    'html_url': None,
                    'raw_url': None,
                    'error': error_msg
                }

            # Handle 500 Internal Server Error
            if response.status_code >= 500:
                error_msg = f"GitHub API returned {response.status_code}: server error"
                logger.error(f"Gist publication failed for snippet {snippet_id}: {error_msg}")

                # Store failure in database
                self.db.create_gist_publication(
                    snippet_id=snippet_id,
                    old_gist_id=old_gist_id or '',
                    old_owner=old_owner or '',
                    old_filename=filename,
                    new_gist_id='',
                    new_owner=self.owner,
                    new_filename=filename,
                    new_url='',
                    new_raw_url='',
                    code_hash=code_hash,
                    status='failed',
                    error_message=error_msg
                )

                return {
                    'success': False,
                    'gist_id': None,
                    'html_url': None,
                    'raw_url': None,
                    'error': error_msg
                }

            # Handle other non-201 responses
            if response.status_code != 201:
                error_msg = f"GitHub API returned unexpected status {response.status_code}"
                logger.error(f"Gist publication failed for snippet {snippet_id}: {error_msg}")

                # Store failure in database
                self.db.create_gist_publication(
                    snippet_id=snippet_id,
                    old_gist_id=old_gist_id or '',
                    old_owner=old_owner or '',
                    old_filename=filename,
                    new_gist_id='',
                    new_owner=self.owner,
                    new_filename=filename,
                    new_url='',
                    new_raw_url='',
                    code_hash=code_hash,
                    status='failed',
                    error_message=error_msg
                )

                return {
                    'success': False,
                    'gist_id': None,
                    'html_url': None,
                    'raw_url': None,
                    'error': error_msg
                }

            # Parse successful response
            gist_data = response.json()
            new_gist_id = gist_data['id']
            html_url = gist_data['html_url']

            # Extract raw URL from files
            files = gist_data.get('files', {})
            raw_url = ''
            if filename in files:
                raw_url = files[filename].get('raw_url', '')

            logger.info(
                f"Successfully published gist for snippet {snippet_id}: "
                f"gist_id={new_gist_id}, url={html_url}"
            )

            # Store success in database
            self.db.create_gist_publication(
                snippet_id=snippet_id,
                old_gist_id=old_gist_id or '',
                old_owner=old_owner or '',
                old_filename=filename,
                new_gist_id=new_gist_id,
                new_owner=self.owner,
                new_filename=filename,
                new_url=html_url,
                new_raw_url=raw_url,
                code_hash=code_hash,
                status='success',
                error_message=None
            )

            return {
                'success': True,
                'gist_id': new_gist_id,
                'html_url': html_url,
                'raw_url': raw_url,
                'error': None
            }

        except requests.exceptions.Timeout:
            error_msg = "GitHub API request timed out"
            logger.error(f"Gist publication failed for snippet {snippet_id}: {error_msg}")

            # Store failure in database
            self.db.create_gist_publication(
                snippet_id=snippet_id,
                old_gist_id=old_gist_id or '',
                old_owner=old_owner or '',
                old_filename=filename,
                new_gist_id='',
                new_owner=self.owner,
                new_filename=filename,
                new_url='',
                new_raw_url='',
                code_hash=code_hash,
                status='failed',
                error_message=error_msg
            )

            return {
                'success': False,
                'gist_id': None,
                'html_url': None,
                'raw_url': None,
                'error': error_msg
            }

        except requests.exceptions.RequestException as e:
            error_msg = f"GitHub API request failed: {str(e)}"
            logger.error(f"Gist publication failed for snippet {snippet_id}: {error_msg}")

            # Store failure in database
            self.db.create_gist_publication(
                snippet_id=snippet_id,
                old_gist_id=old_gist_id or '',
                old_owner=old_owner or '',
                old_filename=filename,
                new_gist_id='',
                new_owner=self.owner,
                new_filename=filename,
                new_url='',
                new_raw_url='',
                code_hash=code_hash,
                status='failed',
                error_message=error_msg
            )

            return {
                'success': False,
                'gist_id': None,
                'html_url': None,
                'raw_url': None,
                'error': error_msg
            }

        except Exception as e:
            error_msg = f"Unexpected error during gist publication: {str(e)}"
            logger.error(f"Gist publication failed for snippet {snippet_id}: {error_msg}")

            # Store failure in database
            self.db.create_gist_publication(
                snippet_id=snippet_id,
                old_gist_id=old_gist_id or '',
                old_owner=old_owner or '',
                old_filename=filename,
                new_gist_id='',
                new_owner=self.owner,
                new_filename=filename,
                new_url='',
                new_raw_url='',
                code_hash=code_hash,
                status='failed',
                error_message=error_msg
            )

            return {
                'success': False,
                'gist_id': None,
                'html_url': None,
                'raw_url': None,
                'error': error_msg
            }
