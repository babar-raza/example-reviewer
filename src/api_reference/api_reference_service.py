"""
API Reference Service - Queries API index with LRU caching for performance.

This module provides fast access to API reference data with intelligent caching
and error-aware context extraction.
"""

import re
from typing import Dict, List, Optional, Set
from functools import lru_cache
from dataclasses import dataclass
from src.core.database import Database


@dataclass
class ClassContext:
    """Context for a single API class."""
    namespace: str
    constructors: List[str]
    methods: List[str]
    properties: List[str]
    notes: Optional[str]


@dataclass
class ApiContext:
    """Enriched API context for LLM prompts."""
    classes: Dict[str, ClassContext]
    missing_types: Set[str] = None
    related_suggestions: Dict[str, List[str]] = None

    def __post_init__(self):
        if self.missing_types is None:
            self.missing_types = set()
        if self.related_suggestions is None:
            self.related_suggestions = {}

    def to_prompt_text(self) -> str:
        """Format API context for inclusion in LLM prompt."""
        lines = []

        # Add negative guidance for missing types
        if self.missing_types:
            lines.append("\n**TYPES THAT DON'T EXIST:**")
            lines.append("The following types mentioned in errors DO NOT exist in this API:")
            for missing_type in sorted(self.missing_types):
                lines.append(f"  [X] {missing_type}")
                if missing_type in self.related_suggestions:
                    lines.append(f"      -> Use instead: {', '.join(self.related_suggestions[missing_type])}")
            lines.append("\n**ACTION REQUIRED**: Remove or replace these non-existent types completely!")

        # Add positive API reference
        if self.classes:
            lines.append("\n**API REFERENCE:**")
            lines.append("The following classes ARE available and their correct signatures:")

            for class_name, class_ctx in self.classes.items():
                lines.append(f"\n{class_name} class ({class_ctx.namespace}):")

                if class_ctx.constructors:
                    lines.append("  Constructors:")
                    for ctor in class_ctx.constructors[:5]:  # Limit to top 5
                        lines.append(f"    - {ctor}")

                if class_ctx.methods:
                    lines.append("  Methods:")
                    for method in class_ctx.methods[:10]:  # Limit to top 10
                        lines.append(f"    - {method}")

                if class_ctx.properties:
                    lines.append("  Properties:")
                    for prop in class_ctx.properties[:5]:  # Limit to top 5
                        lines.append(f"    - {prop}")

                if class_ctx.notes:
                    lines.append(f"  IMPORTANT: {class_ctx.notes}")

        return '\n'.join(lines) if lines else ""


class ApiReferenceService:
    """Service for querying API reference index with caching."""

    def __init__(self, db: Database, cache_size: int = 128):
        """
        Initialize API reference service.

        Args:
            db: Database instance
            cache_size: Size of LRU cache for class contexts
        """
        self.db = db
        self.cache_size = cache_size
        # Ensure database connection
        self.db.connect()

    def get_api_context_for_errors(self, family: str, compilation_errors: str,
                                   max_classes: int = 5) -> ApiContext:
        """
        Extract relevant API context based on compilation errors.

        Args:
            family: Product family (e.g., 'zip')
            compilation_errors: Compiler output text
            max_classes: Maximum number of classes to include

        Returns:
            ApiContext with relevant class information, missing types, and suggestions
        """
        # Extract class names mentioned in errors
        class_names = self._extract_class_names_from_errors(compilation_errors)

        # Limit to max_classes
        class_names = list(class_names)[:max_classes]

        # Query database for each class
        classes = {}
        missing_types = set()
        related_suggestions = {}

        for class_name in class_names:
            class_ctx = self._get_class_context_cached(family, class_name)
            if class_ctx:
                classes[class_name] = class_ctx
            else:
                # Class not found - add to missing types
                missing_types.add(class_name)
                # Try to suggest related classes
                suggestions = self._suggest_related_classes(family, class_name)
                if suggestions:
                    related_suggestions[class_name] = suggestions

        return ApiContext(
            classes=classes,
            missing_types=missing_types,
            related_suggestions=related_suggestions
        )

    @lru_cache(maxsize=128)
    def _get_class_context_cached(self, family: str, class_name: str) -> Optional[ClassContext]:
        """
        Get class context with LRU caching.

        Args:
            family: Product family
            class_name: Class name to look up

        Returns:
            ClassContext if found, None otherwise
        """
        # Query database for all members of this class
        cursor = self.db._conn.execute("""
            SELECT namespace, member_type, member_name, signature, notes, is_readonly
            FROM api_reference
            WHERE family = ? AND class_name LIKE ?
            ORDER BY
                CASE member_type
                    WHEN 'class' THEN 1
                    WHEN 'constructor' THEN 2
                    WHEN 'method' THEN 3
                    WHEN 'property' THEN 4
                    ELSE 5
                END,
                member_name
        """, (family, f'%{class_name}'))

        rows = cursor.fetchall()
        if not rows:
            return None

        namespace = rows[0][0]
        constructors = []
        methods = []
        properties = []
        notes = None

        for row in rows:
            member_type = row[1]
            signature = row[3]
            member_notes = row[4]
            is_readonly = row[5]

            if member_type == 'class':
                if member_notes:
                    notes = member_notes
            elif member_type == 'constructor':
                constructors.append(signature)
            elif member_type == 'method':
                methods.append(signature)
            elif member_type == 'property':
                prop_text = signature
                if is_readonly:
                    prop_text += " (read-only)"
                properties.append(prop_text)

        return ClassContext(
            namespace=namespace,
            constructors=constructors,
            methods=methods,
            properties=properties,
            notes=notes
        )

    def _extract_class_names_from_errors(self, errors: str) -> Set[str]:
        """
        Parse compilation errors to find mentioned class names.

        Args:
            errors: Compilation error text

        Returns:
            Set of class names found in errors
        """
        class_names = set()

        # Common C# error patterns that mention class names
        patterns = [
            r"type or namespace name '(\w+)'",
            r"'(\w+)' does not contain a (definition|constructor)",
            r"'(\w+)' does not have a constructor that takes",
            r"'(\w+)' is a (property|type|method)",
            r"'([^'\.]+)\.(\w+)' is a",  # Handles Archive.Entries
            r"No overload for method '(\w+)'",
            r"cannot convert from '\w+' to '(\w+)'",
            r"The name '(\w+)' does not exist",
        ]

        for pattern in patterns:
            matches = re.findall(pattern, errors)
            # Flatten tuple matches (from patterns with multiple groups)
            for match in matches:
                if isinstance(match, tuple):
                    # Add all non-empty groups except keywords
                    class_names.update(g for g in match if g and g not in {'definition', 'constructor', 'property', 'type', 'method', 'a'})
                else:
                    class_names.add(match)

        # Filter out common BCL types and keywords
        common_types = {
            'string', 'int', 'bool', 'object', 'var', 'void', 'byte', 'Stream',
            'List', 'Dictionary', 'Task', 'IEnumerable', 'FileStream', 'MemoryStream',
            'File', 'Directory', 'Path', 'Encoding', 'Exception', 'ArgumentException',
            'ReadOnlyCollection'
        }
        class_names = {cn for cn in class_names if cn not in common_types}

        return class_names

    def _suggest_related_classes(self, family: str, missing_type: str) -> List[str]:
        """
        Suggest related classes when a type is not found.

        Args:
            family: Product family
            missing_type: Class name that wasn't found

        Returns:
            List of suggested class names to use instead
        """
        # Hardcoded suggestions for common problematic types
        known_replacements = {
            'CompressionLevel': [
                'CompressionSettings.Deflate (static property)',
                'CompressionSettings.Bzip2 (static property)',
                'CompressionSettings.Store (static property)',
                'DeflateCompressionSettings() (no parameters)'
            ],
            'ZipArchiveMode': ['Archive class directly', 'ArchiveLoadOptions'],
            'ZipArchiveEntry': ['ArchiveEntry'],
            'ZipFile': ['Archive'],
            'FileMode': ['Use Archive constructor overloads instead'],
            'CompressionMode': ['Use compression settings classes instead']
        }

        if missing_type in known_replacements:
            return known_replacements[missing_type]

        # Try fuzzy matching with database
        suggestions = []

        # Pattern 1: Look for classes containing the missing type name
        cursor = self.db._conn.execute("""
            SELECT DISTINCT class_name
            FROM api_reference
            WHERE family = ? AND class_name LIKE ?
            ORDER BY class_name
            LIMIT 3
        """, (family, f'%{missing_type}%'))

        for row in cursor.fetchall():
            suggestions.append(row[0])

        # Pattern 2: If missing_type contains "Compression", suggest all compression classes
        if 'Compression' in missing_type or 'compress' in missing_type.lower():
            cursor = self.db._conn.execute("""
                SELECT DISTINCT class_name
                FROM api_reference
                WHERE family = ? AND (
                    class_name LIKE '%Compression%'
                    OR namespace LIKE '%.Saving%'
                )
                ORDER BY class_name
                LIMIT 5
            """, (family,))

            for row in cursor.fetchall():
                if row[0] not in suggestions:
                    suggestions.append(row[0])

        # Pattern 3: If missing_type contains "Archive", suggest archive classes
        if 'Archive' in missing_type:
            cursor = self.db._conn.execute("""
                SELECT DISTINCT class_name
                FROM api_reference
                WHERE family = ? AND class_name LIKE '%Archive%'
                ORDER BY class_name
                LIMIT 3
            """, (family,))

            for row in cursor.fetchall():
                if row[0] not in suggestions:
                    suggestions.append(row[0])

        return suggestions[:5]  # Limit to 5 suggestions

    def clear_cache(self):
        """Clear the LRU cache (useful when API index is rebuilt)."""
        self._get_class_context_cached.cache_clear()

    def get_cache_stats(self) -> Dict:
        """
        Get LRU cache statistics.

        Returns:
            Dictionary with cache hits, misses, size, and hit rate
        """
        cache_info = self._get_class_context_cached.cache_info()
        total_calls = cache_info.hits + cache_info.misses
        return {
            'hits': cache_info.hits,
            'misses': cache_info.misses,
            'maxsize': cache_info.maxsize,
            'currsize': cache_info.currsize,
            'hit_rate': cache_info.hits / total_calls if total_calls > 0 else 0.0
        }
