"""
Risk Classifier for Error Routing (Track 2: D.4).

Implements risk-based error routing:
- LOW: auto-fix with limited retries
- MEDIUM: auto-fix with drift + validation gates
- HIGH: one attempt then NEEDS_REVIEW
- CRITICAL: immediate NEEDS_REVIEW
"""

import re
import logging
from typing import List, Optional
from ..core.models import ErrorRisk

logger = logging.getLogger(__name__)


class RiskClassifier:
    """
    Classifies compilation and runtime errors by risk level.

    Risk routing (D.4):
    - LOW: Common, safe-to-fix errors (missing usings, simple syntax)
    - MEDIUM: More complex but fixable (type mismatches, API changes)
    - HIGH: Potentially unsafe to auto-fix (security, data loss risk)
    - CRITICAL: Never auto-fix (license violations, malware patterns)
    """

    # CRITICAL: Never auto-fix these
    CRITICAL_PATTERNS = [
        r'license.*violation',
        r'copyright.*infringement',
        r'malicious.*code',
        r'security.*critical',
        r'credential.*exposed',
        r'private.*key',
    ]

    # HIGH: One attempt only, then escalate
    HIGH_RISK_PATTERNS = [
        r'file.*delete',
        r'directory.*remove',
        r'database.*drop',
        r'System\.IO\.File\.Delete',
        r'Directory\.Delete',
        r'DROP\s+TABLE',
        r'DROP\s+DATABASE',
        r'DELETE\s+FROM.*WHERE\s+1\s*=\s*1',
        r'security.*warning',
        r'certificate.*invalid',
        r'authentication.*failed',
    ]

    # LOW: Safe to auto-fix with limited retries
    LOW_RISK_PATTERNS = [
        r"using directive.*expected",
        r"namespace.*does not exist",
        r"type.*could not be found",
        r"'.*' does not contain a definition",
        r"The name '.*' does not exist",
        r"cannot convert from.*to",
        r"missing semicolon",
        r"expected '\)'",
        r"expected '\}'",
    ]

    def __init__(self):
        """Initialize risk classifier with compiled patterns."""
        self.critical_patterns = [re.compile(p, re.IGNORECASE) for p in self.CRITICAL_PATTERNS]
        self.high_risk_patterns = [re.compile(p, re.IGNORECASE) for p in self.HIGH_RISK_PATTERNS]
        self.low_risk_patterns = [re.compile(p, re.IGNORECASE) for p in self.LOW_RISK_PATTERNS]

    def classify_compilation_error(self, error_messages: List[str]) -> ErrorRisk:
        """
        Classify compilation errors by risk level.

        Args:
            error_messages: List of compiler error messages

        Returns:
            ErrorRisk level (LOW, MEDIUM, HIGH, CRITICAL)
        """
        if not error_messages:
            return ErrorRisk.MEDIUM

        # Combine all error messages for pattern matching
        combined_errors = "\n".join(error_messages)

        # Check CRITICAL first
        for pattern in self.critical_patterns:
            if pattern.search(combined_errors):
                logger.warning(f"CRITICAL error detected: {pattern.pattern}")
                return ErrorRisk.CRITICAL

        # Check HIGH
        for pattern in self.high_risk_patterns:
            if pattern.search(combined_errors):
                logger.info(f"HIGH risk error detected: {pattern.pattern}")
                return ErrorRisk.HIGH

        # Check LOW
        for pattern in self.low_risk_patterns:
            if pattern.search(combined_errors):
                return ErrorRisk.LOW

        # Default to MEDIUM for unknown patterns
        return ErrorRisk.MEDIUM

    def classify_runtime_error(
        self,
        exception_type: Optional[str],
        exception_message: Optional[str],
        stderr: Optional[str] = None,
    ) -> ErrorRisk:
        """
        Classify runtime errors by risk level.

        Args:
            exception_type: Exception type name
            exception_message: Exception message
            stderr: Standard error output

        Returns:
            ErrorRisk level (LOW, MEDIUM, HIGH, CRITICAL)
        """
        # Combine all error information
        error_text = "\n".join(filter(None, [
            exception_type or "",
            exception_message or "",
            stderr or "",
        ]))

        if not error_text:
            return ErrorRisk.MEDIUM

        # Check CRITICAL first
        for pattern in self.critical_patterns:
            if pattern.search(error_text):
                logger.warning(f"CRITICAL runtime error detected: {pattern.pattern}")
                return ErrorRisk.CRITICAL

        # Check HIGH
        for pattern in self.high_risk_patterns:
            if pattern.search(error_text):
                logger.info(f"HIGH risk runtime error detected: {pattern.pattern}")
                return ErrorRisk.HIGH

        # Low-risk runtime errors
        low_risk_runtime = [
            r'FileNotFoundException',
            r'ArgumentNullException',
            r'ArgumentException',
            r'InvalidOperationException',
            r'NullReferenceException',
        ]

        for pattern_str in low_risk_runtime:
            if re.search(pattern_str, error_text, re.IGNORECASE):
                return ErrorRisk.LOW

        # Default to MEDIUM
        return ErrorRisk.MEDIUM

    def get_max_retries_for_risk(self, risk: ErrorRisk) -> int:
        """
        Get maximum retry attempts based on risk level.

        Args:
            risk: Error risk level

        Returns:
            Maximum number of retry attempts
        """
        retry_limits = {
            ErrorRisk.CRITICAL: 0,  # No auto-fix, immediate NEEDS_REVIEW
            ErrorRisk.HIGH: 1,  # One attempt only
            ErrorRisk.MEDIUM: 3,  # Standard retry limit
            ErrorRisk.LOW: 5,  # More retries for safe errors
        }
        return retry_limits.get(risk, 3)

    def should_escalate_immediately(self, risk: ErrorRisk) -> bool:
        """
        Check if error should be escalated to NEEDS_REVIEW immediately.

        Args:
            risk: Error risk level

        Returns:
            True if should escalate without trying to auto-fix
        """
        return risk == ErrorRisk.CRITICAL
