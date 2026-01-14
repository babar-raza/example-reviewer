"""
GitHub Gist Service for Example Review System.
Fetches gist content from GitHub API with caching and rate limit handling.
"""

import re
import os
import json
import hashlib
import logging
import requests
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta

from src.core.database import Database

logger = logging.getLogger(__name__)


@dataclass
class GistFetchResult:
    """Result of fetching a gist file."""
    success: bool
    gist_id: str
    owner: str
    filename: Optional[str] = None
    content: Optional[str] = None
    content_hash: Optional[str] = None
    raw_url: Optional[str] = None
    language: Optional[str] = None
    updated_at: Optional[str] = None
    error: Optional[str] = None
    skip_reason: Optional[str] = None


class GistService:
    """
    Service for fetching and caching GitHub Gists.

    Features:
    - Parses Hugo gist shortcode variants
    - Fetches from GitHub Gist API (public, no auth required)
    - Optional GITHUB_TOKEN for higher rate limits
    - Disk caching with ETag support
    - Smart C# file selection
    - Rate limit detection and handling
    """

    GITHUB_API_BASE = "https://api.github.com/gists"
    CSHARP_EXTENSIONS = {'.cs', '.csx'}

    def __init__(self, cache_dir: Path, db: Database):
        """
        Initialize gist service.

        Args:
            cache_dir: Directory for caching gist responses
            db: Database instance for persistence
        """
        self.cache_dir = cache_dir
        self.db = db
        self.github_token = os.environ.get('GITHUB_TOKEN')

        # Create cache directories
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def parse_gist_shortcode(self, shortcode: str) -> Optional[Tuple[str, str, Optional[str]]]:
        """
        Parse Hugo gist shortcode.

        Supported formats:
        - {{< gist "username" "gistid" >}}
        - {{< gist "username" "gistid" "filename.cs" >}}
        - {{<gist "username" "gistid">}} (no space after {{<)
        - {{< gist username gistid >}} (unquoted, if present in repo)
        - {{< gist username gistid filename.cs >}} (unquoted)

        Args:
            shortcode: Gist shortcode string

        Returns:
            Tuple of (username, gist_id, filename) or None if parse fails
        """
        # Try quoted form first (fully quoted)
        quoted_pattern = r'{{<\s*gist\s+"([^"]+)"\s+"([^"]+)"(?:\s+"([^"]+)")?\s*>}}'
        match = re.search(quoted_pattern, shortcode)

        if match:
            username = match.group(1)
            gist_id = match.group(2)
            filename = match.group(3) if match.group(3) else None
            return (username, gist_id, filename)

        # Try mixed form (unquoted owner/ID, quoted filename) - ACTUAL Aspose format
        mixed_pattern = r'{{<\s*gist\s+(\S+)\s+(\S+)(?:\s+"([^"]+)")?\s*>}}'
        match = re.search(mixed_pattern, shortcode)

        if match:
            username = match.group(1)
            gist_id = match.group(2)
            filename = match.group(3) if match.group(3) else None
            return (username, gist_id, filename)

        # Try fully unquoted form (fallback)
        unquoted_pattern = r'{{<\s*gist\s+(\S+)\s+(\S+)(?:\s+(\S+))?\s*>}}'
        match = re.search(unquoted_pattern, shortcode)

        if match:
            username = match.group(1)
            gist_id = match.group(2)
            filename = match.group(3) if match.group(3) else None
            return (username, gist_id, filename)

        return None

    def fetch_gist(self, gist_id: str, owner: str, filename: Optional[str] = None) -> GistFetchResult:
        """
        Fetch a gist from GitHub API or cache.

        Strategy:
        1. Check cache for existing gist data
        2. Use ETag for conditional request (If-None-Match)
        3. Fetch from GitHub API if needed
        4. Select appropriate C# file if filename not specified
        5. Cache response and persist to database

        Args:
            gist_id: GitHub gist ID
            owner: Gist owner username
            filename: Optional specific file to fetch

        Returns:
            GistFetchResult with content or error information
        """
        # Check cache first
        cache_file = self.cache_dir / f"{gist_id}.json"
        etag = None

        if cache_file.exists():
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cached_data = json.load(f)
                    etag = cached_data.get('etag')

                    # If we have the specific file cached, try to use it
                    gist_data = cached_data.get('data', {})
                    if filename and filename in gist_data.get('files', {}):
                        file_data = gist_data['files'][filename]
                        # Verify cache is still valid (less than 1 hour old)
                        cached_time = cached_data.get('cached_at')
                        if cached_time:
                            cached_dt = datetime.fromisoformat(cached_time)
                            if datetime.utcnow() - cached_dt < timedelta(hours=1):
                                # Use cached version
                                return self._build_result_from_cache(
                                    gist_id, owner, filename, file_data, cached_data
                                )
            except Exception:
                # Cache read failed, proceed with fresh fetch
                pass

        # Fetch from GitHub API
        url = f"{self.GITHUB_API_BASE}/{gist_id}"
        headers = {'Accept': 'application/vnd.github.v3+json'}

        if self.github_token:
            headers['Authorization'] = f'token {self.github_token}'

        if etag:
            headers['If-None-Match'] = etag

        try:
            response = requests.get(url, headers=headers, timeout=10)

            # Handle 304 Not Modified (cache is still valid)
            if response.status_code == 304 and cache_file.exists():
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cached_data = json.load(f)
                    cached_etag = cached_data.get('etag')
                    return self._process_gist_data(
                        cached_data['data'], gist_id, owner, filename,
                        from_cache=True, etag=cached_etag
                    )

            # Handle rate limiting
            if response.status_code == 403:
                rate_limit_remaining = response.headers.get('X-RateLimit-Remaining', '?')
                if rate_limit_remaining == '0':
                    self.db.upsert_gist(
                        gist_id, owner, None, None, 'rate_limited',
                        'GitHub API rate limit exceeded'
                    )
                    return GistFetchResult(
                        success=False,
                        gist_id=gist_id,
                        owner=owner,
                        error='GitHub API rate limit exceeded. Set GITHUB_TOKEN env var for higher limits.'
                    )

            # Handle not found
            if response.status_code == 404:
                self.db.upsert_gist(
                    gist_id, owner, None, None, 'not_found',
                    'Gist not found'
                )
                return GistFetchResult(
                    success=False,
                    gist_id=gist_id,
                    owner=owner,
                    error=f'Gist {gist_id} not found'
                )

            # Handle other errors
            if response.status_code != 200:
                error_msg = f'GitHub API returned status {response.status_code}'
                self.db.upsert_gist(
                    gist_id, owner, None, None, 'error', error_msg
                )
                return GistFetchResult(
                    success=False,
                    gist_id=gist_id,
                    owner=owner,
                    error=error_msg
                )

            # Parse response
            gist_data = response.json()
            response_etag = response.headers.get('ETag')

            # Cache response
            cache_data = {
                'gist_id': gist_id,
                'etag': response_etag,
                'cached_at': datetime.utcnow().isoformat(),
                'data': gist_data
            }

            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2)

            # Process gist data
            return self._process_gist_data(gist_data, gist_id, owner, filename,
                                          from_cache=False, etag=response_etag)

        except requests.exceptions.Timeout:
            error_msg = 'GitHub API request timed out'
            self.db.upsert_gist(gist_id, owner, None, None, 'error', error_msg)
            return GistFetchResult(
                success=False,
                gist_id=gist_id,
                owner=owner,
                error=error_msg
            )
        except requests.exceptions.RequestException as e:
            error_msg = f'GitHub API request failed: {str(e)}'
            self.db.upsert_gist(gist_id, owner, None, None, 'error', error_msg)
            return GistFetchResult(
                success=False,
                gist_id=gist_id,
                owner=owner,
                error=error_msg
            )

    def _process_gist_data(self, gist_data: Dict, gist_id: str, owner: str,
                          requested_filename: Optional[str] = None,
                          from_cache: bool = False,
                          etag: Optional[str] = None) -> GistFetchResult:
        """
        Process gist data and select appropriate file.

        Args:
            gist_data: GitHub API response data
            gist_id: Gist ID
            owner: Gist owner
            requested_filename: Specific file requested (optional)
            from_cache: Whether data is from cache
            etag: ETag from HTTP response or cache

        Returns:
            GistFetchResult with selected file content
        """
        description = gist_data.get('description', '')
        updated_at = gist_data.get('updated_at')
        files = gist_data.get('files', {})

        # Persist gist metadata
        self.db.upsert_gist(gist_id, owner, description, updated_at, 'success', None, etag)

        # If specific filename requested, use it
        if requested_filename:
            if requested_filename in files:
                file_data = files[requested_filename]
                return self._extract_file_content(
                    gist_id, owner, requested_filename, file_data, updated_at
                )
            else:
                return GistFetchResult(
                    success=False,
                    gist_id=gist_id,
                    owner=owner,
                    error=f'Requested file "{requested_filename}" not found in gist'
                )

        # No specific file requested - smart selection for C# files
        csharp_files = []
        for filename, file_data in files.items():
            ext = Path(filename).suffix.lower()
            if ext in self.CSHARP_EXTENSIONS:
                csharp_files.append((filename, file_data))

        # No C# files found
        if not csharp_files:
            return GistFetchResult(
                success=False,
                gist_id=gist_id,
                owner=owner,
                skip_reason='No C# files (.cs/.csx) found in gist'
            )

        # Exactly one C# file - use it
        if len(csharp_files) == 1:
            filename, file_data = csharp_files[0]
            return self._extract_file_content(
                gist_id, owner, filename, file_data, updated_at
            )

        # Multiple C# files - ambiguous
        filenames = ', '.join([f[0] for f in csharp_files])
        return GistFetchResult(
            success=False,
            gist_id=gist_id,
            owner=owner,
            skip_reason=f'Ambiguous gist: multiple C# files found ({filenames}). '
                       f'Specify filename in shortcode.'
        )

    def _extract_file_content(self, gist_id: str, owner: str, filename: str,
                             file_data: Dict, updated_at: Optional[str]) -> GistFetchResult:
        """
        Extract content from a gist file.

        Args:
            gist_id: Gist ID
            owner: Gist owner
            filename: Filename
            file_data: GitHub API file data
            updated_at: Gist updated_at timestamp

        Returns:
            GistFetchResult with file content
        """
        content = file_data.get('content', '')
        raw_url = file_data.get('raw_url', '')
        language = file_data.get('language', '')
        file_size = file_data.get('size', 0)

        # Compute content hash
        content_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()

        # Persist file to database
        self.db.upsert_gist_file(
            gist_id, filename, raw_url, language, content, content_hash, file_size
        )

        # Also cache file separately for quick access
        file_cache_dir = self.cache_dir / gist_id
        file_cache_dir.mkdir(exist_ok=True)

        file_cache_path = file_cache_dir / f"{filename}.raw"
        with open(file_cache_path, 'w', encoding='utf-8') as f:
            f.write(content)

        return GistFetchResult(
            success=True,
            gist_id=gist_id,
            owner=owner,
            filename=filename,
            content=content,
            content_hash=content_hash,
            raw_url=raw_url,
            language=language,
            updated_at=updated_at
        )

    def _build_result_from_cache(self, gist_id: str, owner: str, filename: str,
                                 file_data: Dict, cached_data: Dict) -> GistFetchResult:
        """
        Build GistFetchResult from cached data.

        Args:
            gist_id: Gist ID
            owner: Owner username
            filename: Filename
            file_data: Cached file data
            cached_data: Full cached gist data

        Returns:
            GistFetchResult from cache
        """
        content = file_data.get('content', '')
        content_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()

        return GistFetchResult(
            success=True,
            gist_id=gist_id,
            owner=owner,
            filename=filename,
            content=content,
            content_hash=content_hash,
            raw_url=file_data.get('raw_url'),
            language=file_data.get('language'),
            updated_at=cached_data.get('data', {}).get('updated_at')
        )

    def verify_cache(self) -> Dict[str, any]:
        """
        Verify cache integrity and remove corrupted files.

        Scans all .json cache files and validates:
        - Valid JSON structure
        - Required fields: gist_id, etag, cached_at, data
        - Valid cached_at timestamp format (ISO8601)
        - data is dict and contains files key

        Corrupted files are automatically removed and logged at WARNING level.

        Returns:
            Dict with keys:
            - total_files: int (total cache files scanned)
            - valid_files: int (valid cache files)
            - corrupted_files: int (corrupted files removed)
            - removed_files: List[str] (paths of removed files)
            - errors: List[Dict] (file paths and error messages)
        """
        total_files = 0
        valid_files = 0
        corrupted_files = 0
        removed_files = []
        errors = []

        # Ensure cache directory exists
        if not self.cache_dir.exists():
            return {
                'total_files': 0,
                'valid_files': 0,
                'corrupted_files': 0,
                'removed_files': [],
                'errors': []
            }

        # Scan all .json files in cache directory
        try:
            cache_files = list(self.cache_dir.glob('*.json'))
            total_files = len(cache_files)

            for cache_file in cache_files:
                file_path = str(cache_file)
                is_valid = True
                error_msg = None

                try:
                    # Attempt to read and parse JSON
                    with open(cache_file, 'r', encoding='utf-8') as f:
                        cache_data = json.load(f)

                    # Validate required fields
                    required_fields = ['gist_id', 'etag', 'cached_at', 'data']
                    missing_fields = [field for field in required_fields if field not in cache_data]

                    if missing_fields:
                        is_valid = False
                        error_msg = f"Missing required fields: {', '.join(missing_fields)}"
                    else:
                        # Validate cached_at is valid ISO timestamp
                        try:
                            datetime.fromisoformat(cache_data['cached_at'])
                        except (ValueError, TypeError):
                            is_valid = False
                            error_msg = "Invalid cached_at timestamp format"

                        # Validate data is dict and has files
                        if is_valid:
                            if not isinstance(cache_data['data'], dict):
                                is_valid = False
                                error_msg = "data field is not a dict"
                            elif 'files' not in cache_data['data']:
                                is_valid = False
                                error_msg = "data.files field missing"

                except json.JSONDecodeError as e:
                    is_valid = False
                    error_msg = f"Invalid JSON: {str(e)}"
                except Exception as e:
                    is_valid = False
                    error_msg = f"Read error: {str(e)}"

                # Handle corrupted files
                if not is_valid:
                    logger.warning(
                        f"Corrupted cache file detected: {file_path} - {error_msg}, removing"
                    )

                    # Attempt to remove corrupted file
                    try:
                        cache_file.unlink()
                        corrupted_files += 1
                        removed_files.append(file_path)
                    except Exception as remove_error:
                        error_detail = {
                            'file': file_path,
                            'validation_error': error_msg,
                            'removal_error': str(remove_error)
                        }
                        errors.append(error_detail)
                        logger.error(
                            f"Failed to remove corrupted cache file {file_path}: {remove_error}"
                        )
                else:
                    valid_files += 1

        except Exception as scan_error:
            logger.error(f"Error scanning cache directory {self.cache_dir}: {scan_error}")
            errors.append({
                'file': str(self.cache_dir),
                'error': f"Directory scan error: {str(scan_error)}"
            })

        # Log summary
        if corrupted_files > 0:
            logger.warning(
                f"Cache validation complete: {total_files} files scanned, "
                f"{valid_files} valid, {corrupted_files} corrupted (removed)"
            )
        else:
            logger.info(
                f"Cache validation complete: {total_files} files scanned, all valid"
            )

        return {
            'total_files': total_files,
            'valid_files': valid_files,
            'corrupted_files': corrupted_files,
            'removed_files': removed_files,
            'errors': errors
        }
