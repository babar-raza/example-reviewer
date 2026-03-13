"""
Deterministic behavioral-pattern scanner for semantically wrong but compilable examples.

This service is intentionally regex/config driven so it stays deterministic,
family-specific, and easy to audit. It is designed to catch silent semantic
issues before markdown write-back or finalization.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

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
        self._pattern_cache: Dict[str, List[Dict[str, Any]]] = {}

    def scan_example(
        self,
        family: str,
        code: str,
        *,
        article_intent: str = "",
        section_heading: str = "",
        markdown_content: str = "",
    ) -> List[BehavioralFinding]:
        patterns = self._load_patterns(family)
        if not patterns or not code:
            return []

        findings: List[BehavioralFinding] = []
        context_blob = "\n".join(
            part for part in (article_intent, section_heading, markdown_content[:4000]) if part
        ).lower()

        for pattern in patterns:
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

    def _evaluate_pattern(
        self,
        pattern: Dict[str, Any],
        *,
        code: str,
        context_blob: str,
    ) -> Optional[BehavioralFinding]:
        code_regex = pattern.get("code_regex", "")
        if not code_regex:
            return None

        code_match = re.search(code_regex, code, re.MULTILINE | re.DOTALL)
        if not code_match:
            return None

        missing_regex = pattern.get("missing_regex")
        if missing_regex and not re.search(missing_regex, code, re.MULTILINE | re.DOTALL):
            pass
        elif missing_regex:
            return None

        intent_keywords = [kw.lower() for kw in pattern.get("intent_keywords", [])]
        if intent_keywords and not any(keyword in context_blob for keyword in intent_keywords):
            return None

        context_keywords = [kw.lower() for kw in pattern.get("context_keywords", [])]
        if context_keywords and not any(keyword in context_blob for keyword in context_keywords):
            return None

        return BehavioralFinding(
            pattern_id=pattern["id"],
            issue_type=pattern.get("issue_type", "other"),
            severity=pattern.get("severity", "warning"),
            description=pattern.get("description", "Behavioral issue detected."),
            suggestion=pattern.get("suggestion"),
            matched_text=code_match.group(0)[:120],
        )

    def _load_patterns(self, family: str) -> List[Dict[str, Any]]:
        if family in self._pattern_cache:
            return self._pattern_cache[family]

        path = self.config_dir / f"{family}_behavioral_patterns.json"
        if not path.exists():
            self._pattern_cache[family] = []
            return []

        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(raw, list):
                raise ValueError("Behavioral pattern config must be a list")
            self._pattern_cache[family] = raw
        except Exception as exc:
            logger.warning("Failed to load behavioral patterns for %s from %s: %s", family, path, exc)
            self._pattern_cache[family] = []

        return self._pattern_cache[family]
