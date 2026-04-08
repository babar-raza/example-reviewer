"""Typed Pydantic models for family KB files.

Two distinct model types — one per file type — are intentionally kept separate
because they serve different subsystems with different semantics:

  ReviewHint         — human-readable guidance injected into LLM prompts
  BehavioralPattern  — deterministic regex rules for enforcement scanning
"""

from __future__ import annotations

import re
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ReviewHint(BaseModel):
    """A single entry from ``{family}_review_hints.json``.

    Required fields: ``id``, ``hint``.
    All other fields are optional filters or metadata.
    """

    model_config = ConfigDict(extra="forbid")

    id: str
    hint: str
    pattern: Optional[str] = None
    context: Optional[str] = None
    issue_type: Optional[str] = None
    detection_keywords: List[str] = Field(default_factory=list)
    correction: Optional[str] = None
    content_types: Optional[List[str]] = None


class BehavioralPattern(BaseModel):
    """A single entry from ``{family}_behavioral_patterns.json``.

    Required fields: ``id``, ``severity``, ``description``, and at least one of
    ``code_regex`` or ``required_regex``.

    All regex fields are validated with ``re.compile()`` at load time so invalid
    patterns raise immediately rather than silently disabling enforcement.
    """

    model_config = ConfigDict(extra="forbid")

    id: str
    severity: Literal["error", "warning", "critical"]
    description: str
    issue_type: Optional[str] = None
    code_regex: Optional[str] = None
    required_regex: Optional[str] = None
    missing_regex: Optional[str] = None
    intent_keywords: List[str] = Field(default_factory=list)
    context_keywords: List[str] = Field(default_factory=list)
    content_types: Optional[List[str]] = None
    suggestion: Optional[str] = None

    @model_validator(mode="after")
    def _validate_regexes_and_presence(self) -> "BehavioralPattern":
        # Validate all regex fields compile before accepting the pattern.
        for field_name, value in (
            ("code_regex", self.code_regex),
            ("required_regex", self.required_regex),
            ("missing_regex", self.missing_regex),
        ):
            if value is not None:
                try:
                    re.compile(value, re.MULTILINE | re.DOTALL)
                except re.error as exc:
                    raise ValueError(
                        f"Pattern '{self.id}': field '{field_name}' contains invalid regex: {exc}"
                    ) from exc

        # At least one of code_regex or required_regex must be present so the
        # scanner has something to match against.
        if not self.code_regex and not self.required_regex:
            raise ValueError(
                f"Pattern '{self.id}' must define at least one of: code_regex, required_regex"
            )

        return self
