"""
Context drift validator for LLM-generated code fixes.

Phase-2 Gate B: Prevents LLM from changing the application context type
(e.g., console → ASP.NET, ASP.NET → console) during fix attempts.
"""

import logging
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass

try:
    from src.core.app_context import AppContext
    from src.pipeline.app_context_classifier import classify_app_context
except ImportError:
    AppContext = None
    classify_app_context = None

logger = logging.getLogger(__name__)


@dataclass
class ContextDriftResult:
    """Result of context drift validation."""

    drift_detected: bool
    original_context: str
    fixed_context: str
    drift_allowed: bool
    rejection_reason: Optional[str] = None

    @property
    def should_reject(self) -> bool:
        """Whether the fix should be rejected due to drift."""
        return self.drift_detected and not self.drift_allowed


class ContextDriftValidator:
    """
    Validates that LLM fixes don't change application context type.

    Phase-2 Gate B: When enabled, rejects fixes that drift from
    console → ASP.NET or ASP.NET → console.
    """

    def __init__(self, enabled: bool = False):
        """
        Initialize context drift validator.

        Args:
            enabled: Whether to enforce context validation (default: False)
        """
        self.enabled = enabled

        if not classify_app_context:
            logger.warning(
                "Context drift validator initialized but classifier unavailable. "
                "Drift validation will be skipped."
            )

    def validate(
        self,
        original_code: str,
        fixed_code: str,
        original_context: Optional[str] = None
    ) -> ContextDriftResult:
        """
        Validate that fixed code maintains the same app_context as original.

        Args:
            original_code: Original code before LLM fix
            fixed_code: Code after LLM fix
            original_context: Known app_context of original (optional, will classify if missing)

        Returns:
            ContextDriftResult with validation details
        """
        # Skip validation if disabled or classifier unavailable
        if not self.enabled or not classify_app_context:
            # Return permissive result (no drift detected or allowed)
            return ContextDriftResult(
                drift_detected=False,
                original_context=original_context or "unknown",
                fixed_context="unknown",
                drift_allowed=True
            )

        # Classify original context if not provided
        if not original_context:
            original_context_enum = classify_app_context(original_code)
            original_context = original_context_enum.value if hasattr(original_context_enum, 'value') else str(original_context_enum)

        # Classify fixed code context
        fixed_context_enum = classify_app_context(fixed_code)
        fixed_context = fixed_context_enum.value if hasattr(fixed_context_enum, 'value') else str(fixed_context_enum)

        # Check for drift
        drift_detected = original_context != fixed_context

        if drift_detected:
            logger.warning(
                f"Context drift detected: {original_context} → {fixed_context}"
            )

            rejection_reason = (
                f"LLM fix changed app_context from '{original_context}' to '{fixed_context}'. "
                f"This is not allowed when context enforcement is enabled."
            )

            return ContextDriftResult(
                drift_detected=True,
                original_context=original_context,
                fixed_context=fixed_context,
                drift_allowed=False,
                rejection_reason=rejection_reason
            )
        else:
            logger.debug(
                f"No context drift: {original_context} → {fixed_context}"
            )

            return ContextDriftResult(
                drift_detected=False,
                original_context=original_context,
                fixed_context=fixed_context,
                drift_allowed=True
            )

    def get_drift_metadata(self, result: ContextDriftResult) -> Dict[str, Any]:
        """
        Extract metadata from drift validation result for persistence.

        Args:
            result: ContextDriftResult from validate()

        Returns:
            Dictionary with drift metadata
        """
        return {
            "drift_detected": result.drift_detected,
            "original_context": result.original_context,
            "fixed_context": result.fixed_context,
            "drift_allowed": result.drift_allowed,
            "rejection_reason": result.rejection_reason
        }


def validate_context_drift(
    original_code: str,
    fixed_code: str,
    original_context: Optional[str] = None,
    enabled: bool = False
) -> ContextDriftResult:
    """
    Convenience function for one-off context drift validation.

    Args:
        original_code: Original code before LLM fix
        fixed_code: Code after LLM fix
        original_context: Known app_context of original (optional)
        enabled: Whether to enforce validation

    Returns:
        ContextDriftResult with validation details
    """
    validator = ContextDriftValidator(enabled=enabled)
    return validator.validate(original_code, fixed_code, original_context)
