"""
Deterministic application context classifier for C# code examples.

Classifies code snippets by application architecture type using pattern matching.
Does NOT use LLM - purely deterministic for reproducibility.
"""

import re
import logging
from typing import Optional
from ..core.app_context import AppContext

logger = logging.getLogger(__name__)


class AppContextClassifier:
    """
    Deterministic classifier for C# application context.

    Uses pattern matching to detect application architecture type.
    Priority order (checked top to bottom):
    1. ASP.NET Core patterns (minimal, MVC, WebAPI)
    2. Library (no entrypoint, class-only)
    3. Console (default for code with Main or standalone logic)
    """

    # ASP.NET Core Minimal Hosting API patterns
    MINIMAL_HOSTING_PATTERNS = [
        r'\bWebApplication\s*\.',
        r'\bWebApplicationBuilder\b',
        r'\.CreateBuilder\s*\(',
        r'\bapp\.Map(Get|Post|Put|Delete|Patch)\s*\(',
        r'\bbuilder\.Services\s*\.',
        r'\bapp\.Run\s*\(',
        r'\bapp\.UseRouting\s*\(',
    ]

    # ASP.NET Core MVC patterns
    MVC_PATTERNS = [
        r'\bController\b',
        r'\bIActionResult\b',
        r'\bViewResult\b',
        r'\bView\s*\(',
        r'\bMicrosoft\.AspNetCore\.Mvc\b',
        r'\bHttpContext\b',
        r'\bRedirectToAction\s*\(',
        r'\[HttpGet\]',
        r'\[HttpPost\]',
        r'\bActionResult<',
    ]

    # ASP.NET Core Web API patterns
    WEBAPI_PATTERNS = [
        r'\[ApiController\]',
        r'\bControllerBase\b',
        r'\bFromBody\]',
        r'\bFromQuery\]',
        r'\bFromRoute\]',
        r'\bMapControllers\s*\(',
        r'\bOk\s*\(',
        r'\bBadRequest\s*\(',
        r'\bNotFound\s*\(',
    ]

    # Library patterns (no entrypoint)
    LIBRARY_INDICATORS = [
        r'^\s*public\s+class\s+\w+',
        r'^\s*public\s+interface\s+\w+',
        r'^\s*public\s+static\s+class\s+\w+',
        r'^\s*static\s+class\s+\w+',
        r'^\s*internal\s+(?:static\s+)?class\s+\w+',
    ]

    # Entrypoint patterns (has Main method)
    ENTRYPOINT_PATTERNS = [
        r'\bstatic\s+(?:async\s+)?(?:void|Task|Task<int>|int)\s+Main\s*\(',
        r'\bpublic\s+static\s+(?:async\s+)?(?:void|Task|Task<int>|int)\s+Main\s*\(',
    ]

    @classmethod
    def classify(cls, code: str) -> AppContext:
        """
        Classify code by application context using deterministic pattern matching.

        Args:
            code: C# code to classify

        Returns:
            AppContext enum value
        """
        if not code or not code.strip():
            return AppContext.UNKNOWN

        # Normalize whitespace for matching
        normalized_code = code.strip()

        # Check ASP.NET Core Minimal Hosting (highest priority for web contexts)
        if cls._matches_any(normalized_code, cls.MINIMAL_HOSTING_PATTERNS):
            logger.debug("Classified as aspnet_core_minimal (minimal hosting API detected)")
            return AppContext.ASPNET_CORE_MINIMAL

        # Check ASP.NET Core Web API vs MVC (order matters)
        # WebAPI uses ControllerBase and [ApiController]
        # MVC uses Controller (inherits from ControllerBase) and View()
        # If code has specific WebAPI markers, it's WebAPI
        has_webapi_markers = (
            re.search(r'\[ApiController\]', normalized_code) or
            re.search(r':\s*ControllerBase\b', normalized_code)
        )

        # If code has MVC-specific markers, it's MVC
        has_mvc_markers = (
            re.search(r':\s*Controller\b', normalized_code) or
            re.search(r'\bView\s*\(', normalized_code)
        )

        # MVC takes priority if it has MVC-specific markers (Controller base or View())
        if has_mvc_markers and cls._matches_any(normalized_code, cls.MVC_PATTERNS):
            logger.debug("Classified as aspnet_core_mvc (MVC-specific patterns detected)")
            return AppContext.ASPNET_CORE_MVC

        # WebAPI if it has WebAPI-specific markers (ControllerBase or [ApiController])
        if has_webapi_markers and cls._matches_any(normalized_code, cls.WEBAPI_PATTERNS):
            logger.debug("Classified as aspnet_core_webapi (WebAPI-specific patterns detected)")
            return AppContext.ASPNET_CORE_WEBAPI

        # Fallback: check for general MVC or WebAPI patterns
        if cls._matches_any(normalized_code, cls.MVC_PATTERNS):
            logger.debug("Classified as aspnet_core_mvc (MVC patterns detected)")
            return AppContext.ASPNET_CORE_MVC

        if cls._matches_any(normalized_code, cls.WEBAPI_PATTERNS):
            logger.debug("Classified as aspnet_core_webapi (Web API patterns detected)")
            return AppContext.ASPNET_CORE_WEBAPI

        # Check if it's a library (no entrypoint, only type definitions)
        has_entrypoint = cls._matches_any(normalized_code, cls.ENTRYPOINT_PATTERNS)
        has_class_only = cls._matches_any(normalized_code, cls.LIBRARY_INDICATORS)

        # Check for top-level statements (entrypoint without Main)
        has_top_level_statements = cls._has_top_level_statements(normalized_code)

        if has_class_only and not has_entrypoint and not has_top_level_statements:
            logger.debug("Classified as library (type definitions only, no entrypoint)")
            return AppContext.LIBRARY

        # Default: console application
        logger.debug("Classified as console (default)")
        return AppContext.CONSOLE

    @classmethod
    def _matches_any(cls, code: str, patterns: list) -> bool:
        """
        Check if code matches any of the given regex patterns.

        Args:
            code: Code to check
            patterns: List of regex patterns

        Returns:
            True if any pattern matches
        """
        for pattern in patterns:
            try:
                if re.search(pattern, code, re.MULTILINE | re.IGNORECASE):
                    return True
            except re.error as e:
                logger.warning(f"Invalid regex pattern '{pattern}': {e}")
        return False

    @classmethod
    def _has_top_level_statements(cls, code: str) -> bool:
        """
        Check if code has top-level statements (executable code outside of type definitions).

        This helps distinguish libraries (only type definitions) from console apps.
        Top-level statements are statements outside of class/interface/struct/enum/namespace.

        Args:
            code: Code to check

        Returns:
            True if code has top-level statements
        """
        lines = code.split('\n')
        depth = 0  # Track nesting depth
        in_namespace = False
        in_type = False

        for line in lines:
            stripped = line.strip()

            # Skip empty lines, comments, attributes
            if not stripped or stripped.startswith('//') or stripped.startswith('['):
                continue

            # Skip using statements
            if stripped.startswith('using '):
                continue

            # Track namespace
            if stripped.startswith('namespace '):
                in_namespace = True
                depth = 0
                continue

            # Track type definitions (class, interface, struct, enum, record)
            if re.match(r'^(public|private|protected|internal|static|sealed|abstract|\s)+(class|interface|struct|enum|record)\s+\w+', stripped):
                in_type = True
                depth = 0
                continue

            # Count braces
            open_braces = stripped.count('{')
            close_braces = stripped.count('}')

            # Before counting braces, check if we have a statement at depth 0
            # (outside namespace and type definitions)
            if depth == 0 and not in_namespace and not in_type:
                # This line is at top level
                # Check if it's a statement (not just braces)
                non_brace_content = stripped.replace('{', '').replace('}', '').strip()
                if non_brace_content and not non_brace_content.startswith('//'):
                    return True

            # Update depth
            depth += open_braces
            depth -= close_braces

            # When we close back to depth 0, we're exiting the current block
            if depth == 0:
                in_type = False
                # Note: we keep in_namespace True even at depth 0 within the namespace
                # because there might be multiple types in the same namespace

        return False


def classify_app_context(code: str) -> AppContext:
    """
    Convenience function to classify application context.

    Args:
        code: C# code to classify

    Returns:
        AppContext enum value
    """
    return AppContextClassifier.classify(code)
