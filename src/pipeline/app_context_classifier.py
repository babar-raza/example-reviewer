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

        # Check ASP.NET Core MVC
        if cls._matches_any(normalized_code, cls.MVC_PATTERNS):
            logger.debug("Classified as aspnet_core_mvc (MVC patterns detected)")
            return AppContext.ASPNET_CORE_MVC

        # Check ASP.NET Core Web API
        if cls._matches_any(normalized_code, cls.WEBAPI_PATTERNS):
            logger.debug("Classified as aspnet_core_webapi (Web API patterns detected)")
            return AppContext.ASPNET_CORE_WEBAPI

        # Check if it's a library (no entrypoint)
        has_entrypoint = cls._matches_any(normalized_code, cls.ENTRYPOINT_PATTERNS)
        has_class_only = cls._matches_any(normalized_code, cls.LIBRARY_INDICATORS)

        if has_class_only and not has_entrypoint:
            # Check if there's any standalone logic (not just class definitions)
            lines = [line.strip() for line in normalized_code.split('\n') if line.strip()]

            # Filter out using statements, namespace declarations, class/interface declarations
            non_structural_lines = [
                line for line in lines
                if not line.startswith('using ')
                and not line.startswith('namespace ')
                and not re.match(r'^\s*(public|private|protected|internal|static)?\s*(class|interface|enum|struct)\s+\w+', line)
                and not line in ['{', '}']
            ]

            # If mostly structural, it's a library
            if len(non_structural_lines) < len(lines) * 0.3:
                logger.debug("Classified as library (class-only, no entrypoint)")
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


def classify_app_context(code: str) -> AppContext:
    """
    Convenience function to classify application context.

    Args:
        code: C# code to classify

    Returns:
        AppContext enum value
    """
    return AppContextClassifier.classify(code)
