"""Code analysis and pattern detection."""

from .code_pattern_detector import CodePatternDetector, CodePattern
from .pattern_registry import PatternRegistry
from .namespace_validator import NamespaceValidator

__all__ = [
    'CodePatternDetector',
    'CodePattern',
    'PatternRegistry',
    'NamespaceValidator',
]
