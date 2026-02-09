"""
API Reference Service - Fetches and caches API documentation from Git repositories.

This service provides:
- Shallow cloning of API reference repositories
- File indexing for fast lookups
- Context extraction based on error signatures
- Graceful degradation when documentation unavailable

TASK-3A: Implementation for enhanced LLM context with official API documentation.
"""

import re
import logging
import subprocess
from pathlib import Path
from typing import Optional, Dict, List, Set, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FileIndexEntry:
    """Represents a file in the API reference index."""
    file_path: Path
    relative_path: str
    entity_names: frozenset  # Must be immutable for hashing
    content_preview: str
    file_size: int


class APIReferenceService:
    """Fetches and caches API documentation from Git repositories."""

    def __init__(self, family: str, config: 'ApiReferenceConfig', cache_dir: Path):
        """
        Initialize API reference service.

        Args:
            family: Family identifier (e.g., 'words', 'zip')
            config: API reference configuration
            cache_dir: Base cache directory (e.g., artifacts/cache)
        """
        self.family = family
        self.config = config
        self.cache_dir = cache_dir / family / "api-reference"
        self._index: Optional[Dict[str, List[FileIndexEntry]]] = None
        self._indexed = False

    def ensure_cached(self) -> bool:
        """
        Ensure API reference is cloned and available.

        Returns:
            True if API reference is available (already cached or successfully cloned),
            False if unavailable (git clone failed or not configured)
        """
        if not self.config.git_repo:
            logger.debug(f"[{self.family}] API reference not configured (no git_repo)")
            return False

        if self.cache_dir.exists():
            logger.debug(f"[{self.family}] API reference already cached at {self.cache_dir}")
            return True

        if self.config.auto_fetch:
            logger.info(f"[{self.family}] Fetching API reference from {self.config.git_repo}")
            return self._fetch_from_git()
        else:
            logger.warning(f"[{self.family}] API reference not cached and auto_fetch disabled")
            return False

    def _fetch_from_git(self) -> bool:
        """
        Shallow clone API reference repository.

        Returns:
            True if clone successful, False otherwise
        """
        # Ensure parent directory exists
        self.cache_dir.parent.mkdir(parents=True, exist_ok=True)

        # Build git clone command
        cmd = ["git", "clone"]

        if self.config.shallow_clone:
            cmd.extend(["--depth", "1"])

        cmd.extend([
            "--branch", self.config.git_ref,
            "--single-branch",
            self.config.git_repo,
            str(self.cache_dir)
        ])

        try:
            timeout = self.config.clone_timeout_seconds
            logger.debug(f"[{self.family}] Running: {' '.join(cmd)} (timeout={timeout}s)")
            result = subprocess.run(
                cmd,
                check=True,
                timeout=timeout,
                capture_output=True,
                text=True
            )
            logger.info(f"[{self.family}] API reference cloned successfully")
            logger.debug(f"[{self.family}] Git output: {result.stdout}")
            return True

        except subprocess.TimeoutExpired:
            logger.warning(f"[{self.family}] Git clone timed out after {self.config.clone_timeout_seconds} seconds")
            return False

        except subprocess.CalledProcessError as e:
            logger.warning(f"[{self.family}] Git clone failed: {e.stderr}")
            return False

        except FileNotFoundError:
            logger.warning(f"[{self.family}] Git executable not found - cannot clone API reference")
            return False

        except Exception as e:
            logger.warning(f"[{self.family}] Unexpected error cloning API reference: {e}")
            return False

    def _build_file_index(self) -> Dict[str, List[FileIndexEntry]]:
        """
        Scan cached repository and build searchable index.

        Returns:
            Dictionary mapping entity names to file index entries
        """
        if self._indexed and self._index is not None:
            return self._index

        logger.info(f"[{self.family}] Building file index for API reference")

        # Determine scan directory
        scan_dir = self.cache_dir
        if self.config.git_subpath:
            scan_dir = self.cache_dir / self.config.git_subpath
            if not scan_dir.exists():
                logger.warning(f"[{self.family}] Subpath {self.config.git_subpath} not found, scanning entire cache")
                scan_dir = self.cache_dir

        # Index structure: entity_name -> [FileIndexEntry, ...]
        index: Dict[str, List[FileIndexEntry]] = {}

        # Scan for markdown and C# files
        file_patterns = ["**/*.md", "**/*.cs", "**/*.html"]
        scanned_files = 0

        for pattern in file_patterns:
            for file_path in scan_dir.glob(pattern):
                if not file_path.is_file():
                    continue

                scanned_files += 1

                # Extract entity names from file path and content
                entity_names = self._extract_entity_names(file_path, scan_dir)

                if not entity_names:
                    continue

                # Read content preview (first 500 chars)
                try:
                    content = file_path.read_text(encoding='utf-8', errors='ignore')
                    preview = content[:500]
                except Exception as e:
                    logger.debug(f"[{self.family}] Failed to read {file_path}: {e}")
                    preview = ""

                # Create index entry
                relative_path = str(file_path.relative_to(scan_dir))
                entry = FileIndexEntry(
                    file_path=file_path,
                    relative_path=relative_path,
                    entity_names=frozenset(entity_names),
                    content_preview=preview,
                    file_size=file_path.stat().st_size
                )

                # Add to index for each entity name
                for entity_name in entity_names:
                    if entity_name not in index:
                        index[entity_name] = []
                    index[entity_name].append(entry)

        logger.info(f"[{self.family}] Indexed {len(index)} entities from {scanned_files} files")

        self._index = index
        self._indexed = True
        return index

    def _extract_entity_names(self, file_path: Path, base_dir: Path) -> Set[str]:
        """
        Extract entity names from file path and content.

        Args:
            file_path: Path to file
            base_dir: Base directory for relative paths

        Returns:
            Set of entity names found in file
        """
        entity_names: Set[str] = set()

        # Extract from file path (e.g., "charttype.md" -> "ChartType")
        stem = file_path.stem
        if stem:
            # Normalize to PascalCase approximation
            entity_names.add(stem)
            entity_names.add(stem.lower())
            if '_' in stem or '-' in stem:
                parts = re.split(r'[_-]', stem)
                entity_names.add(''.join(word.capitalize() for word in parts))

        # Extract from content (class names, namespace declarations)
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')

            # C# patterns
            if file_path.suffix == '.cs':
                # class/interface/enum/struct declarations
                for match in re.finditer(r'\b(?:class|interface|enum|struct)\s+(\w+)', content):
                    entity_names.add(match.group(1))

                # namespace declarations
                for match in re.finditer(r'\bnamespace\s+([\w.]+)', content):
                    entity_names.add(match.group(1))

            # Markdown patterns
            elif file_path.suffix in ['.md', '.html']:
                # Headers with entity names (e.g., "# ChartType Enum")
                for match in re.finditer(r'^#+\s*(\w+)(?:\s+(?:Class|Interface|Enum|Struct|Namespace|Property|Method))?', content, re.MULTILINE):
                    entity_names.add(match.group(1))

                # Code fence class references
                for match in re.finditer(r'`(\w+)`', content):
                    entity_names.add(match.group(1))

        except Exception as e:
            logger.debug(f"[{self.family}] Failed to extract entities from {file_path}: {e}")

        return entity_names

    def get_context_for_error(
        self,
        error_signature: str,
        error_msg: str,
        max_chars: Optional[int] = None
    ) -> str:
        """
        Extract relevant API documentation based on error signature.

        Args:
            error_signature: Error code (e.g., 'CS0103', 'CS0117')
            error_msg: Full error message
            max_chars: Maximum characters to return (defaults to config.max_context_chars)

        Returns:
            Formatted context string with API documentation, or empty string if unavailable
        """
        # Ensure cache is available
        if not self.ensure_cached():
            logger.debug(f"[{self.family}] API reference not available for context extraction")
            return ""

        # Build index if needed
        index = self._build_file_index()
        if not index:
            logger.debug(f"[{self.family}] API reference index is empty")
            return ""

        # Extract entity names from error message
        entity_names = self._extract_entities_from_error(error_signature, error_msg)
        if not entity_names:
            logger.debug(f"[{self.family}] No entities extracted from error: {error_msg}")
            return ""

        # Search index for matching files
        matching_entries = self._search_index(index, entity_names)
        if not matching_entries:
            logger.debug(f"[{self.family}] No matching API documentation found for: {entity_names}")
            return ""

        # Rank by relevance and assemble context
        max_chars = max_chars or self.config.max_context_chars
        context = self._assemble_context(matching_entries, entity_names, max_chars)

        if context:
            logger.info(f"[{self.family}] Extracted {len(context)} chars of API context for {entity_names}")

        return context

    def _extract_entities_from_error(self, error_signature: str, error_msg: str) -> Set[str]:
        """
        Extract entity names from error message.

        Args:
            error_signature: Error code (e.g., 'CS0103')
            error_msg: Full error message

        Returns:
            Set of entity names mentioned in error
        """
        entity_names: Set[str] = set()

        # Common patterns for entity extraction
        patterns = [
            r"'([\w.]+)' does not exist",
            r"'([\w.]+)' could not be found",
            r"'([\w.]+)' does not contain a definition for '([\w.]+)'",
            r"type or namespace name '([\w.]+)'",
            r"`([\w.]+)`",
            r"'([\w.]+)'",
        ]

        for pattern in patterns:
            for match in re.finditer(pattern, error_msg):
                for group in match.groups():
                    if group and len(group) > 1:  # Skip single chars
                        # Add full dotted name
                        entity_names.add(group)
                        # Also split on dots for namespace.Type patterns
                        if '.' in group:
                            parts = group.split('.')
                            entity_names.update(p for p in parts if len(p) > 1)

        return entity_names

    def _search_index(
        self,
        index: Dict[str, List[FileIndexEntry]],
        entity_names: Set[str]
    ) -> List[Tuple[FileIndexEntry, int]]:
        """
        Search index for files matching entity names.

        Args:
            index: File index
            entity_names: Entity names to search for

        Returns:
            List of (entry, relevance_score) tuples, sorted by relevance
        """
        matches: Dict[FileIndexEntry, int] = {}

        for entity_name in entity_names:
            # Exact match
            if entity_name in index:
                for entry in index[entity_name]:
                    matches[entry] = matches.get(entry, 0) + 10

            # Case-insensitive match
            entity_lower = entity_name.lower()
            for key, entries in index.items():
                if key.lower() == entity_lower:
                    for entry in entries:
                        matches[entry] = matches.get(entry, 0) + 8

            # Partial match (substring)
            for key, entries in index.items():
                if entity_lower in key.lower() or key.lower() in entity_lower:
                    for entry in entries:
                        matches[entry] = matches.get(entry, 0) + 3

        # Sort by relevance score (descending)
        sorted_matches = sorted(matches.items(), key=lambda x: x[1], reverse=True)

        return sorted_matches

    def _assemble_context(
        self,
        matching_entries: List[Tuple[FileIndexEntry, int]],
        entity_names: Set[str],
        max_chars: int
    ) -> str:
        """
        Assemble context from matching files within character budget.

        Args:
            matching_entries: List of (entry, score) tuples
            entity_names: Original entity names from error
            max_chars: Maximum characters to include

        Returns:
            Formatted context string
        """
        context_parts = []
        total_chars = 0

        # Header
        header = f"# API Reference Context\n\nRelevant documentation for: {', '.join(sorted(entity_names))}\n\n"
        context_parts.append(header)
        total_chars += len(header)

        # Add files in order of relevance
        for entry, score in matching_entries:
            if total_chars >= max_chars:
                break

            # Read file content
            try:
                content = entry.file_path.read_text(encoding='utf-8', errors='ignore')
            except Exception as e:
                logger.debug(f"[{self.family}] Failed to read {entry.file_path}: {e}")
                continue

            # Format file section
            file_header = f"## {entry.relative_path} (relevance: {score})\n\n"
            file_section = file_header + content + "\n\n---\n\n"

            # Check if we have budget
            if total_chars + len(file_section) > max_chars:
                # Try to include partial content
                remaining = max_chars - total_chars - len(file_header) - 50
                if remaining > 100:
                    truncated_content = content[:remaining] + "\n\n[...truncated...]"
                    file_section = file_header + truncated_content + "\n\n---\n\n"
                else:
                    break

            context_parts.append(file_section)
            total_chars += len(file_section)

        return ''.join(context_parts)

    def get_stats(self) -> Dict[str, any]:
        """
        Get statistics about the cached API reference.

        Returns:
            Dictionary with cache statistics
        """
        stats = {
            'cached': self.cache_dir.exists(),
            'cache_path': str(self.cache_dir),
            'indexed': self._indexed,
            'config': {
                'git_repo': self.config.git_repo,
                'git_ref': self.config.git_ref,
                'git_subpath': self.config.git_subpath,
                'auto_fetch': self.config.auto_fetch,
            }
        }

        if self._indexed and self._index:
            stats['entity_count'] = len(self._index)
            stats['total_files'] = sum(len(entries) for entries in self._index.values())

        return stats
