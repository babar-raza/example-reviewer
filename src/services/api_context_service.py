"""
API Context Service - Smart chunking to extract relevant API documentation.

This service intelligently extracts and assembles relevant API documentation
based on error messages, respecting character budgets and relevance rankings.

TASK-3B: Implementation for smart API documentation chunking.
"""

import re
import logging
from typing import List, Dict, Optional, Set, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)


class APIContextService:
    """Smart chunking to extract relevant API documentation."""

    def __init__(self, api_reference_service=None):
        """
        Initialize API context service.

        Args:
            api_reference_service: Optional APIReferenceService instance for docs access.
                                  If provided, enables documentation-based context extraction.
        """
        self.api_reference = api_reference_service

    def extract_entities_from_error(
        self,
        error_signature: str,
        error_message: str
    ) -> Set[str]:
        """
        Extract entity names from error message.

        Handles various error patterns including:
        - 'TypeName' does not exist
        - type or namespace name 'TypeName'
        - 'Namespace.Type' could not be found
        - Reference to `TypeName` in backticks

        Args:
            error_signature: Error code (e.g., 'CS0103', 'CS0117')
            error_message: Full error message

        Returns:
            Set of entity names mentioned in error
        """
        entity_names: Set[str] = set()

        # Common patterns for entity extraction from error messages
        patterns = [
            r"'([\w.]+)' does not exist",                                    # CS0103 style
            r"'([\w.]+)' could not be found",                                # General
            r"'([\w.]+)' does not contain a definition for '([\w.]+)'",     # CS0117 style
            r"type or namespace name '([\w.]+)'",                            # CS0246 style
            r"`([\w.]+)`",                                                   # Backtick style
            r"'([\w.]+)' is inaccessible",                                   # Accessibility error
            r"The name '([\w.]+)' does not exist",                           # Alternative phrasing
            r"Cannot find type '([\w.]+)'",                                  # Type resolution
            r"([\w.]+) could not be resolved",                               # Resolution error
        ]

        for pattern in patterns:
            for match in re.finditer(pattern, error_message):
                for group in match.groups():
                    if group and len(group) > 1:  # Skip single chars
                        # Add full dotted name
                        entity_names.add(group)

                        # Split dotted names into components for broader matching
                        if '.' in group:
                            parts = group.split('.')
                            # Add all parts except common namespace prefixes
                            entity_names.update(
                                p for p in parts
                                if len(p) > 1 and p != 'System' and p != 'Aspose'
                            )

        # Extract entity names from stacktraces if present
        stacktrace_entities = self._extract_entities_from_stacktrace(error_message)
        entity_names.update(stacktrace_entities)

        logger.debug(f"Extracted {len(entity_names)} entities from error: {entity_names}")
        return entity_names

    def _extract_entities_from_stacktrace(self, error_message: str) -> Set[str]:
        """
        Extract entity names from stack traces in error message.

        Args:
            error_message: Full error message potentially containing stack trace

        Returns:
            Set of entity names from stack traces
        """
        entities: Set[str] = set()

        # Look for method/class references in stack traces
        # Pattern: at Namespace.ClassName.MethodName(...)
        pattern = r"at\s+([\w.]+)\.(\w+)\s*\("
        for match in re.finditer(pattern, error_message):
            full_name = match.group(1)
            method_name = match.group(2)

            # Extract class name (last component before method)
            parts = full_name.split('.')
            if parts:
                class_name = parts[-1]
                if len(class_name) > 1:
                    entities.add(class_name)

            if len(method_name) > 1:
                entities.add(method_name)

        return entities

    def assemble_context(
        self,
        error_entities: Set[str],
        docs_index: Dict[str, List],
        max_chars: int = 8000
    ) -> str:
        """
        Assemble relevant API documentation context.

        Algorithm:
        1. Search docs index for exact entity matches
        2. Rank matches by relevance (exact > case-insensitive > partial)
        3. Assemble context most-relevant-first until budget exhausted
        4. Respect character budget throughout

        Args:
            error_entities: Set of entity names from error (e.g., ['ChartType', 'Document'])
            docs_index: Index mapping entity names to documentation files
                       Structure: {'TypeName': [FileIndexEntry, ...], ...}
            max_chars: Maximum characters in assembled context (default 8000)

        Returns:
            Formatted markdown context string, or empty string if no matches
        """
        if not error_entities or not docs_index:
            logger.debug("No entities or empty index, returning empty context")
            return ""

        # Search for matches with relevance scoring
        ranked_matches = self._rank_matches(error_entities, docs_index)
        if not ranked_matches:
            logger.debug(f"No matches found for entities: {error_entities}")
            return ""

        # Assemble context within budget
        context = self._build_context_chunks(ranked_matches, max_chars, error_entities)
        return context

    def _rank_matches(
        self,
        error_entities: Set[str],
        docs_index: Dict[str, List]
    ) -> List[Tuple[str, int]]:
        """
        Rank documentation matches by relevance.

        Scoring:
        - Exact match: 100 points
        - Case-insensitive match: 80 points
        - Partial match (substring): 30 points

        Args:
            error_entities: Set of entity names to search for
            docs_index: Documentation index

        Returns:
            List of (entity_name, relevance_score) tuples sorted by score (descending)
        """
        scores: Dict[str, int] = {}

        for entity in error_entities:
            entity_lower = entity.lower()

            # Exact match
            if entity in docs_index:
                scores[entity] = scores.get(entity, 0) + 100

            # Case-insensitive match
            for key in docs_index.keys():
                if key.lower() == entity_lower and key != entity:
                    scores[entity] = scores.get(entity, 0) + 80

            # Partial match (substring) - both directions
            for key in docs_index.keys():
                key_lower = key.lower()
                if entity_lower in key_lower or key_lower in entity_lower:
                    if key.lower() != entity_lower:  # Not already counted
                        scores[entity] = scores.get(entity, 0) + 30

        # Sort by score descending, then by entity name for determinism
        ranked = sorted(scores.items(), key=lambda x: (-x[1], x[0]))
        logger.debug(f"Ranked {len(ranked)} matches: {ranked[:5]}")  # Log top 5
        return ranked

    def _build_context_chunks(
        self,
        ranked_matches: List[Tuple[str, int]],
        max_chars: int,
        error_entities: Set[str]
    ) -> str:
        """
        Build context chunks from ranked matches.

        Assembles documentation in relevance order, stopping at character budget.
        Includes header identifying which entities are being documented.

        Args:
            ranked_matches: List of (entity_name, score) tuples from _rank_matches
            max_chars: Maximum characters to include
            error_entities: Original error entities (for header)

        Returns:
            Formatted context string
        """
        chunks: List[str] = []
        total_chars = 0

        # Header with entity list
        header = f"## Relevant API Documentation\n"
        header += f"Entities from error: {', '.join(sorted(error_entities))}\n\n"
        chunks.append(header)
        total_chars += len(header)

        # Add entity documentation sections in relevance order
        for entity_name, score in ranked_matches:
            if total_chars >= max_chars:
                logger.debug(f"Character budget exhausted at {total_chars}/{max_chars}")
                break

            # Create section for this entity
            section = f"### {entity_name} (relevance score: {score})\n"
            section += f"_This entity was mentioned in the error message._\n\n"

            # Check budget for section header
            if total_chars + len(section) > max_chars:
                # Not enough space for even a header, stop
                break

            chunks.append(section)
            total_chars += len(section)

        # Footer with note about truncation
        if len(ranked_matches) > len(chunks) - 1:  # Subtract 1 for header
            footer = "\n---\n\n*Note: Additional matches not shown due to character limit.*\n"
            chunks.append(footer)
            total_chars += len(footer)

        context = ''.join(chunks)
        logger.info(f"Assembled context: {total_chars} chars from {len(chunks)-1} entities")
        return context

    def get_context_for_error(
        self,
        error_signature: str,
        error_message: str,
        docs_index: Optional[Dict[str, List]] = None,
        max_chars: int = 8000
    ) -> str:
        """
        Get complete context for an error.

        This is the main entry point. It:
        1. Extracts entities from error message
        2. Searches documentation index for matches
        3. Ranks by relevance
        4. Assembles context within budget
        5. Returns formatted markdown

        Args:
            error_signature: Error code (e.g., 'CS0103')
            error_message: Full error message
            docs_index: Optional documentation index
                       If None and api_reference available, uses it to build index
            max_chars: Maximum context characters (default 8000)

        Returns:
            Formatted context string, or empty string if unavailable
        """
        # Extract entities from error
        entities = self.extract_entities_from_error(error_signature, error_message)
        if not entities:
            logger.debug("No entities extracted from error")
            return ""

        # Get documentation index
        if docs_index is None:
            if not self.api_reference:
                logger.debug("No API reference service available")
                return ""

            # Try to get context from API reference service
            try:
                api_context = self.api_reference.get_context_for_error(
                    error_signature,
                    error_message,
                    max_chars
                )
                return api_context
            except Exception as e:
                logger.warning(f"Failed to get context from API reference: {e}")
                return ""
        else:
            # Assemble context from provided index
            return self.assemble_context(entities, docs_index, max_chars)

    def truncate_context(self, context: str, max_chars: int) -> str:
        """
        Truncate context to maximum character limit.

        Tries to truncate at sentence boundaries to preserve readability.

        Args:
            context: Context string to truncate
            max_chars: Maximum characters

        Returns:
            Truncated context string
        """
        if len(context) <= max_chars:
            return context

        # Try to truncate at last sentence boundary
        truncated = context[:max_chars]
        last_period = truncated.rfind('.')
        last_newline = truncated.rfind('\n')

        if last_period > max_chars * 0.8:  # If period is in last 20%
            truncated = truncated[:last_period+1]
        elif last_newline > max_chars * 0.8:  # If newline is in last 20%
            truncated = truncated[:last_newline]

        truncated += "\n\n[...truncated due to character limit...]"
        return truncated

    def merge_contexts(self, contexts: List[str], max_chars: int) -> str:
        """
        Merge multiple context strings into single output.

        Respects character budget and maintains separation between sources.

        Args:
            contexts: List of context strings to merge
            max_chars: Maximum total characters

        Returns:
            Merged context string
        """
        if not contexts:
            return ""

        parts: List[str] = []
        total = 0

        for context in contexts:
            if not context.strip():
                continue

            if total + len(context) <= max_chars:
                parts.append(context)
                total += len(context)
            else:
                # Add truncated version
                remaining = max_chars - total
                if remaining > 100:
                    truncated = self.truncate_context(context, remaining)
                    parts.append(truncated)
                break

        return "\n\n---\n\n".join(parts)
