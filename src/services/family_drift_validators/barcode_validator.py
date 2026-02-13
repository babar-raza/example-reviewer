"""BarCode family drift validator.

Detects semantic drift specific to Aspose.BarCode code examples:
- Barcode type changes (DecodeType/EncodeTypes enum values)
- Generation vs Recognition mode changes
- Customization loss (property assignments removed)
"""

import re
import logging
from typing import Dict, Set, List, Any

from src.services.family_drift_validators.base import (
    FamilyDriftValidator,
    DriftValidationResult,
    DriftIssue,
)

logger = logging.getLogger(__name__)


class BarCodeDriftValidator(FamilyDriftValidator):
    """Drift validator for Aspose.BarCode family."""

    CRITICAL_ENUMS = ["DecodeType", "EncodeTypes", "BarcodeQualityMode"]
    CRITICAL_PROPERTIES = [
        "BarcodeType", "CodeText", "Resolution",
        "BarColor", "BackColor", "ForeColor",
    ]

    def validate(
        self, original: str, fixed: str, context: Dict[str, Any]
    ) -> DriftValidationResult:
        """Validate code changes for BarCode-specific semantic drift."""
        issues: List[DriftIssue] = []

        # Check 1: Barcode type preservation
        orig_types = self._extract_barcode_types(original)
        fixed_types = self._extract_barcode_types(fixed)
        if orig_types and fixed_types and orig_types != fixed_types:
            removed = orig_types - fixed_types
            added = fixed_types - orig_types
            if removed:
                issues.append(
                    DriftIssue(
                        severity="critical",
                        category="barcode_type_change",
                        message=(
                            f"Barcode type changed: "
                            f"removed={sorted(removed)}, added={sorted(added)}"
                        ),
                    )
                )

        # Check 2: Generation vs Recognition mode
        orig_mode = self._detect_mode(original)
        fixed_mode = self._detect_mode(fixed)
        if (
            orig_mode != "unknown"
            and fixed_mode != "unknown"
            and orig_mode != fixed_mode
        ):
            issues.append(
                DriftIssue(
                    severity="critical",
                    category="api_mode_change",
                    message=f"API mode changed: {orig_mode} -> {fixed_mode}",
                )
            )

        # Check 3: Customization preservation
        orig_props = self._extract_property_assignments(original)
        fixed_props = self._extract_property_assignments(fixed)
        removed_props = set(orig_props.keys()) - set(fixed_props.keys())
        if removed_props:
            # Check if any critical properties were removed
            critical_removed = removed_props & set(self.CRITICAL_PROPERTIES)
            if critical_removed:
                issues.append(
                    DriftIssue(
                        severity="high",
                        category="critical_property_loss",
                        message=(
                            f"Critical properties removed: "
                            f"{sorted(critical_removed)}"
                        ),
                    )
                )
            elif len(removed_props) >= 2:
                issues.append(
                    DriftIssue(
                        severity="high",
                        category="customization_loss",
                        message=(
                            f"Lost {len(removed_props)} customizations: "
                            f"{sorted(list(removed_props)[:5])}"
                        ),
                    )
                )

        # Compute validity
        critical_count = sum(1 for i in issues if i.severity == "critical")
        valid = critical_count == 0

        return DriftValidationResult(
            valid=valid,
            issues=issues,
            drift_score=min(1.0, len(issues) * 0.3),
        )

    def get_critical_patterns(self) -> List[str]:
        return self.CRITICAL_ENUMS + self.CRITICAL_PROPERTIES

    # ── Extraction helpers ──────────────────────────────────────

    @staticmethod
    def _extract_barcode_types(code: str) -> Set[str]:
        """Extract all DecodeType.X and EncodeTypes.X values."""
        pattern = r"(?:DecodeType|EncodeTypes)\.(\w+)"
        return set(re.findall(pattern, code))

    @staticmethod
    def _detect_mode(code: str) -> str:
        """Detect if code is generation, recognition, or both."""
        has_generator = bool(
            re.search(r"\bBarcodeGenerator\b", code)
            or re.search(r"\.Generate\s*\(", code)
        )
        has_reader = bool(
            re.search(r"\bBarCodeReader\b", code)
            or re.search(r"\.ReadBarCodes\s*\(", code)
        )
        if has_generator and has_reader:
            return "both"
        if has_generator:
            return "generation"
        if has_reader:
            return "recognition"
        return "unknown"

    @staticmethod
    def _extract_property_assignments(code: str) -> Dict[str, str]:
        """Extract property assignments like gen.Height = 50."""
        # Strip comments first
        clean = re.sub(r"//.*$", "", code, flags=re.MULTILINE)
        clean = re.sub(r"/\*.*?\*/", "", clean, flags=re.DOTALL)

        pattern = r"\.(\w+)\s*=\s*([^;=]+?)(?:;|$)"
        matches = re.findall(pattern, clean)
        props: Dict[str, str] = {}
        for prop_name, value in matches:
            value = value.strip()
            if "(" in prop_name:
                continue
            props[prop_name] = value
        return props
