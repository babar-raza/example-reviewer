"""Persistent fix application and dependency resolution."""

from .persistent_fix_service import PersistentFixService, FixResult
from .dependency_resolver import DependencyResolver

__all__ = [
    'PersistentFixService',
    'FixResult',
    'DependencyResolver',
]
