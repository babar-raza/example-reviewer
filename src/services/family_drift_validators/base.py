"""Base classes for family-specific drift validation."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Any


@dataclass
class DriftIssue:
    """A single drift issue found during validation."""

    severity: str  # "critical", "high", "medium", "low"
    category: str  # e.g., "barcode_type_change", "customization_loss"
    message: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class DriftValidationResult:
    """Result of family-specific drift validation."""

    valid: bool  # True if no critical issues found
    issues: List[DriftIssue] = field(default_factory=list)
    drift_score: float = 0.0

    def to_dict(self) -> dict:
        return {
            "valid": self.valid,
            "issues": [i.to_dict() for i in self.issues],
            "drift_score": self.drift_score,
        }


class FamilyDriftValidator(ABC):
    """Base class for family-specific drift validation."""

    def __init__(self, catalog=None):
        self.catalog = catalog

    @abstractmethod
    def validate(
        self, original: str, fixed: str, context: Dict[str, Any]
    ) -> DriftValidationResult:
        """Validate code changes for family-specific semantic drift."""
        ...

    @abstractmethod
    def get_critical_patterns(self) -> List[str]:
        """Return list of critical patterns to preserve."""
        ...
