"""
Deterministic behavioral-pattern scanner for semantically wrong but compilable examples.

This service is intentionally regex/config driven so it stays deterministic,
family-specific, and easy to audit. It is designed to catch silent semantic
issues before markdown write-back or finalization.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from .kb import KBLoadError, KnowledgeBaseLoader
from .kb.models import BehavioralPattern

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class BehavioralFinding:
    """Deterministic finding emitted by the behavioral scanner."""

    pattern_id: str
    issue_type: str
    severity: str
    description: str
    suggestion: Optional[str]
    matched_text: Optional[str] = None

    @property
    def is_blocking(self) -> bool:
        return self.severity in {"error", "critical"}


class BehavioralPatternScanner:
    """Config-driven behavioral scanner for family examples."""

    def __init__(self, config_dir: Path | str = "config/families") -> None:
        self.config_dir = Path(config_dir)
        self._pattern_cache: Dict[str, List[BehavioralPattern]] = {}

    def scan_example(
        self,
        family: str,
        code: str,
        *,
        article_intent: str = "",
        section_heading: str = "",
        markdown_content: str = "",
        content_type: str = "",  # e.g. "blog", "docs", "kb"
    ) -> List[BehavioralFinding]:
        # _load_patterns raises KBLoadError if the file exists but is broken.
        # File-not-found returns [] and is handled silently.
        patterns = self._load_patterns(family)
        if not patterns or not code:
            return []

        findings: List[BehavioralFinding] = []
        context_blob = "\n".join(
            part for part in (article_intent, section_heading, markdown_content[:4000]) if part
        ).lower()

        for pattern in patterns:
            # Skip if pattern is restricted to specific content types and this doesn't match
            allowed_types = pattern.content_types
            if allowed_types and content_type and content_type not in allowed_types:
                continue

            # Intent-anchored absence patterns use required_regex instead of code_regex
            if pattern.required_regex:
                finding = self._evaluate_absence_pattern(pattern, code=code, context_blob=context_blob)
            else:
                finding = self._evaluate_pattern(pattern, code=code, context_blob=context_blob)
            if finding is not None:
                findings.append(finding)

        findings.sort(key=lambda item: (item.severity, item.pattern_id, item.description))
        return findings

    def summarize_findings(self, findings: Iterable[BehavioralFinding]) -> str:
        findings = list(findings)
        if not findings:
            return ""

        lines = ["Deterministic behavioral findings:"]
        for finding in findings:
            suggestion = f" Suggestion: {finding.suggestion}" if finding.suggestion else ""
            lines.append(
                f"- [{finding.severity}] {finding.issue_type} ({finding.pattern_id}): "
                f"{finding.description}{suggestion}"
            )
        return "\n".join(lines)

    def _evaluate_absence_pattern(
        self,
        pattern: BehavioralPattern,
        *,
        code: str,
        context_blob: str,
    ) -> Optional[BehavioralFinding]:
        """Flag when a required API is absent and article intent matches.

        Unlike _evaluate_pattern (which fires when bad code IS present),
        this fires when good code is NOT present and the article claims
        to address the topic.
        """
        required_regex = pattern.required_regex
        if not required_regex:
            return None

        # If the required API is already present, no issue
        if re.search(required_regex, code, re.MULTILINE | re.DOTALL):
            return None

        # Intent keywords must match — otherwise the article isn't about this topic
        intent_keywords = [kw.lower() for kw in pattern.intent_keywords]
        if not intent_keywords or not any(keyword in context_blob for keyword in intent_keywords):
            return None

        return BehavioralFinding(
            pattern_id=pattern.id,
            issue_type=pattern.issue_type or "other",
            severity=pattern.severity,
            description=pattern.description,
            suggestion=pattern.suggestion,
            matched_text=None,
        )

    def _evaluate_pattern(
        self,
        pattern: BehavioralPattern,
        *,
        code: str,
        context_blob: str,
    ) -> Optional[BehavioralFinding]:
        code_regex = pattern.code_regex
        if not code_regex:
            return None

        code_match = re.search(code_regex, code, re.MULTILINE | re.DOTALL)
        if not code_match:
            return None

        missing_regex = pattern.missing_regex
        if missing_regex and not re.search(missing_regex, code, re.MULTILINE | re.DOTALL):
            pass
        elif missing_regex:
            return None

        intent_keywords = [kw.lower() for kw in pattern.intent_keywords]
        if intent_keywords and not any(keyword in context_blob for keyword in intent_keywords):
            return None

        context_keywords = [kw.lower() for kw in pattern.context_keywords]
        if context_keywords and not any(keyword in context_blob for keyword in context_keywords):
            return None

        return BehavioralFinding(
            pattern_id=pattern.id,
            issue_type=pattern.issue_type or "other",
            severity=pattern.severity,
            description=pattern.description,
            suggestion=pattern.suggestion,
            matched_text=code_match.group(0)[:120],
        )

    def _load_patterns(self, family: str) -> List[BehavioralPattern]:
        """Load and cache behavioral patterns for *family*.

        Returns ``[]`` if no patterns file exists for the family (valid).
        Raises :class:`~src.services.kb.KBLoadError` if the file exists but
        is structurally broken — callers must handle this explicitly.
        Patterns are NOT cached on error so a retry is possible.
        """
        if family in self._pattern_cache:
            return self._pattern_cache[family]

        # KBLoadError propagates to caller; file-not-found returns []
        patterns = KnowledgeBaseLoader.load_behavioral_patterns(family, str(self.config_dir))
        self._pattern_cache[family] = patterns
        return patterns
