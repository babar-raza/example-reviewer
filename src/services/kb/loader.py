"""Shared loader for family KB files.

Replaces three independent inline loaders that each had divergent error-handling
behaviour. The key behavioural contract is:

  - File not found  → return []   (valid: families without KB files are fine)
  - JSON parse error → raise KBLoadError  (not valid: file is broken)
  - Schema violation → raise KBLoadError  (not valid: structure is wrong)
  - Invalid regex    → raise KBLoadError  (raised during schema validation)

This distinction lets call sites tell the difference between
"family has no KB" (empty list, normal) and "family KB file is broken"
(KBLoadError, requires operator attention).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import List, Union

from pydantic import ValidationError

from .models import BehavioralPattern, ReviewHint

logger = logging.getLogger(__name__)


class KBLoadError(Exception):
    """Raised when a KB file exists but cannot be loaded or validated.

    Distinct from FileNotFoundError: a missing KB file is intentional
    (the family simply has no KB yet). A KBLoadError means the file is
    present but structurally broken and requires intervention.
    """


class KnowledgeBaseLoader:
    """Static loader for family review hints and behavioral patterns."""

    @staticmethod
    def load_review_hints(
        family: str,
        config_dir: Union[str, Path] = "config/families",
    ) -> List[ReviewHint]:
        """Load and validate ``{config_dir}/{family}_review_hints.json``.

        Returns an empty list if the file does not exist (valid: the family
        has no review hints KB yet).  Raises :class:`KBLoadError` on any
        other failure (JSON parse error, schema violation, invalid regex).
        """
        path = Path(config_dir) / f"{family}_review_hints.json"
        if not path.exists():
            return []

        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise KBLoadError(f"Failed to parse {path}: {exc}") from exc

        if not isinstance(raw, list):
            raise KBLoadError(
                f"{path}: root element must be a JSON array, got {type(raw).__name__}"
            )

        try:
            return [ReviewHint.model_validate(item) for item in raw]
        except ValidationError as exc:
            raise KBLoadError(f"Schema validation failed for {path}:\n{exc}") from exc

    @staticmethod
    def load_behavioral_patterns(
        family: str,
        config_dir: Union[str, Path] = "config/families",
    ) -> List[BehavioralPattern]:
        """Load and validate ``{config_dir}/{family}_behavioral_patterns.json``.

        Returns an empty list if the file does not exist (valid: the family
        has no behavioral patterns KB yet).  Raises :class:`KBLoadError` on
        any other failure (JSON parse error, schema violation, invalid regex).

        All regex fields in every returned pattern are pre-compiled and
        guaranteed valid — invalid regex raises at load time, not at scan time.
        """
        path = Path(config_dir) / f"{family}_behavioral_patterns.json"
        if not path.exists():
            return []

        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise KBLoadError(f"Failed to parse {path}: {exc}") from exc

        if not isinstance(raw, list):
            raise KBLoadError(
                f"{path}: root element must be a JSON array, got {type(raw).__name__}"
            )

        try:
            return [BehavioralPattern.model_validate(item) for item in raw]
        except ValidationError as exc:
            raise KBLoadError(f"Schema validation failed for {path}:\n{exc}") from exc
