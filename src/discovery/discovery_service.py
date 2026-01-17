"""Compatibility wrapper for DiscoveryService."""

from typing import Any, Optional

from src.core.database import Database
from src.services.discovery_service import DiscoveryService as CoreDiscoveryService


class DiscoveryService:
    """Compatibility wrapper that accepts legacy constructor arguments."""

    def __init__(self, content_root: Any, db: Optional[Database] = None, *args, **kwargs):
        if isinstance(content_root, Database):
            self._service = CoreDiscoveryService(content_root, db, *args, **kwargs)
        else:
            content_roots = [content_root] if content_root else []
            self._service = CoreDiscoveryService(db, content_roots=content_roots, *args, **kwargs)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._service, name)


__all__ = ["DiscoveryService"]
