"""Semantic Signature Service for API-level drift detection.

Extracts and compares semantic fingerprints of C# code examples to detect
intent-changing modifications that embedding-based drift detection misses.
"""

import json
import re
import logging
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Set, Optional, Any, Tuple

logger = logging.getLogger(__name__)


# Critical enums by family - changes to these are always flagged
CRITICAL_ENUM_FAMILIES: Dict[str, List[str]] = {
    "barcode": ["DecodeType", "EncodeTypes", "BarcodeQualityMode"],
    "zip": ["CompressionLevel", "CompressionMethod", "EncryptionMethod"],
    "words": ["SaveFormat", "LoadFormat"],
}


@dataclass
class SemanticSignature:
    """Captures semantic intent of C# code."""

    enum_values: Dict[str, List[str]] = field(default_factory=dict)
    method_calls: List[str] = field(default_factory=list)
    constructor_types: List[str] = field(default_factory=list)
    property_assignments: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), default=str)

    @classmethod
    def from_dict(cls, data: dict) -> "SemanticSignature":
        return cls(**data)


@dataclass
class SignatureDrift:
    """Results of signature comparison."""

    drift_score: float = 0.0
    critical: bool = False
    critical_reason: Optional[str] = None
    enum_changes: Dict[str, Tuple] = field(default_factory=dict)
    method_changes: Dict[str, List[str]] = field(default_factory=dict)
    type_changes: List[Tuple] = field(default_factory=list)
    property_changes: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "drift_score": self.drift_score,
            "critical": self.critical,
            "critical_reason": self.critical_reason,
            "enum_changes": {
                k: (list(v[0]), list(v[1])) for k, v in self.enum_changes.items()
            },
            "method_changes": self.method_changes,
            "type_changes": [
                (list(t[0]), list(t[1])) for t in self.type_changes
            ],
            "property_changes": self.property_changes,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), default=str)


class SemanticSignatureService:
    """Extracts and compares semantic signatures of C# code."""

    def __init__(self, family: str, api_catalog=None):
        """
        Args:
            family: Product family identifier (e.g., "barcode", "zip")
            api_catalog: APICatalogService instance for enum/type validation
        """
        self.family = family
        self.catalog = api_catalog
        self._known_enums: Dict[str, List[str]] = {}
        self._known_types: Set[str] = set()

        if self.catalog and self.catalog.is_loaded:
            try:
                self._known_enums = self.catalog.get_all_enums() or {}
            except Exception as e:
                logger.warning(f"Failed to load enums from catalog for '{family}': {e}")
                self._known_enums = {}
            try:
                self._known_types = set(self.catalog.get_all_types() or [])
            except Exception as e:
                logger.warning(f"Failed to load types from catalog for '{family}': {e}")
                self._known_types = set()
        elif self.catalog and not self.catalog.is_loaded:
            logger.warning(f"API catalog for '{family}' not loaded - signature validation will use critical enums only")

        # Always include critical enum-like patterns for this family.
        # Some critical types (e.g., EncodeTypes, DecodeType) are classes
        # with static fields, not true enums, but must still be tracked.
        for crit_name in CRITICAL_ENUM_FAMILIES.get(family, []):
            if crit_name not in self._known_enums:
                self._known_enums[crit_name] = []

    def extract_signature(self, code: str) -> SemanticSignature:
        """Parse C# code and extract semantic signature."""
        if not code or not code.strip():
            return SemanticSignature()

        # Strip comments to avoid false matches
        clean_code = self._strip_comments(code)

        return SemanticSignature(
            enum_values=self._extract_enum_values(clean_code),
            method_calls=self._extract_method_calls(clean_code),
            constructor_types=self._extract_constructor_types(clean_code),
            property_assignments=self._extract_property_assignments(clean_code),
        )

    def compare_signatures(
        self,
        original: SemanticSignature,
        fixed: SemanticSignature,
        critical_enums: Optional[List[str]] = None,
    ) -> SignatureDrift:
        """Compare two signatures and compute drift."""
        if critical_enums is None:
            critical_enums = CRITICAL_ENUM_FAMILIES.get(self.family, [])

        enum_changes = self._compute_enum_changes(original, fixed)
        method_changes = self._compute_method_changes(original, fixed)
        type_changes = self._compute_type_changes(original, fixed)
        property_changes = self._compute_property_changes(original, fixed)

        # Check if critical enum changed
        critical = False
        critical_reason = None
        if critical_enums and enum_changes:
            critical_changed = set(enum_changes.keys()) & set(critical_enums)
            if critical_changed:
                critical = True
                details = []
                for e in critical_changed:
                    orig_vals, fixed_vals = enum_changes[e]
                    details.append(f"{e}: {orig_vals} -> {fixed_vals}")
                critical_reason = (
                    f"Critical enum changed: {'; '.join(details)}"
                )

        drift_score = self._calculate_drift_score(
            enum_changes, method_changes, type_changes, property_changes
        )

        return SignatureDrift(
            drift_score=drift_score,
            critical=critical,
            critical_reason=critical_reason,
            enum_changes=enum_changes,
            method_changes=method_changes,
            type_changes=type_changes,
            property_changes=property_changes,
        )

    # ── Extraction helpers ──────────────────────────────────────────

    def _extract_enum_values(self, code: str) -> Dict[str, List[str]]:
        """Extract Type.Member patterns, validate against catalog enums."""
        pattern = r"\b(\w+)\.(\w+)\b"
        matches = re.findall(pattern, code)

        enum_values: Dict[str, List[str]] = {}
        for type_name, member_name in matches:
            # Only include if it's a known enum from the catalog
            if type_name in self._known_enums:
                if type_name not in enum_values:
                    enum_values[type_name] = []
                if member_name not in enum_values[type_name]:
                    enum_values[type_name].append(member_name)

        return enum_values

    def _extract_method_calls(self, code: str) -> List[str]:
        """Extract method invocations (e.g., .Save(), .Generate())."""
        pattern = r"\.(\w+)\s*\("
        calls = re.findall(pattern, code)
        # Filter out common noise: property accessors that look like methods
        noise = {
            "ToString", "GetType", "Equals", "GetHashCode",
            "get", "set", "Add", "Remove", "Contains",
        }
        filtered = [c for c in set(calls) if c not in noise]
        return sorted(filtered)

    def _extract_constructor_types(self, code: str) -> List[str]:
        """Extract new Type(...) patterns."""
        pattern = r"\bnew\s+(\w+)\s*[\(\{]"
        types = re.findall(pattern, code)
        # Validate against catalog if available
        if self._known_types:
            valid = [t for t in types if t in self._known_types]
        else:
            valid = types
        return sorted(set(valid))

    def _extract_property_assignments(self, code: str) -> Dict[str, str]:
        """Extract property assignments like obj.Property = value."""
        pattern = r"\.(\w+)\s*=\s*([^;=]+?)(?:;|$)"
        matches = re.findall(pattern, code)
        props: Dict[str, str] = {}
        for prop_name, value in matches:
            value = value.strip()
            # Skip event handlers and delegate assignments
            if value.startswith("new ") and "EventHandler" in value:
                continue
            # Skip method calls disguised as assignments
            if "(" in prop_name:
                continue
            props[prop_name] = value
        return props

    # ── Comparison helpers ──────────────────────────────────────────

    def _compute_enum_changes(
        self, original: SemanticSignature, fixed: SemanticSignature
    ) -> Dict[str, Tuple]:
        """Compute enum value changes between signatures."""
        changes = {}
        all_enums = set(
            list(original.enum_values.keys()) + list(fixed.enum_values.keys())
        )
        for enum_type in all_enums:
            orig_vals = set(original.enum_values.get(enum_type, []))
            fixed_vals = set(fixed.enum_values.get(enum_type, []))
            if orig_vals != fixed_vals:
                changes[enum_type] = (sorted(orig_vals), sorted(fixed_vals))
        return changes

    def _compute_method_changes(
        self, original: SemanticSignature, fixed: SemanticSignature
    ) -> Dict[str, List[str]]:
        """Compute method call changes."""
        orig_methods = set(original.method_calls)
        fixed_methods = set(fixed.method_calls)
        return {
            "added": sorted(fixed_methods - orig_methods),
            "removed": sorted(orig_methods - fixed_methods),
        }

    def _compute_type_changes(
        self, original: SemanticSignature, fixed: SemanticSignature
    ) -> List[Tuple]:
        """Compute constructor type changes."""
        orig_types = set(original.constructor_types)
        fixed_types = set(fixed.constructor_types)
        if orig_types != fixed_types:
            return [(sorted(orig_types), sorted(fixed_types))]
        return []

    def _compute_property_changes(
        self, original: SemanticSignature, fixed: SemanticSignature
    ) -> Dict[str, Any]:
        """Compute property assignment changes."""
        orig_props = set(original.property_assignments.keys())
        fixed_props = set(fixed.property_assignments.keys())

        removed = sorted(orig_props - fixed_props)
        added = sorted(fixed_props - orig_props)

        # Check for value changes on shared properties
        changed = {}
        for prop in orig_props & fixed_props:
            if original.property_assignments[prop] != fixed.property_assignments[prop]:
                changed[prop] = {
                    "original": original.property_assignments[prop],
                    "fixed": fixed.property_assignments[prop],
                }

        return {
            "added": added,
            "removed": removed,
            "changed": changed,
        }

    # ── Scoring ─────────────────────────────────────────────────────

    def _calculate_drift_score(
        self,
        enum_changes: Dict,
        method_changes: Dict,
        type_changes: List,
        property_changes: Dict,
    ) -> float:
        """Weighted scoring for semantic drift.

        Weights:
          - Enum changes: 0.8 (critical for barcode/compression types)
          - Type changes: 0.7 (constructor changes)
          - Method changes: 0.5 (API usage changes)
          - Property changes: 0.4 (configuration drift)
        """
        score = 0.0

        if enum_changes:
            score += 0.8

        if type_changes:
            score += 0.7

        added = len(method_changes.get("added", []))
        removed = len(method_changes.get("removed", []))
        if added + removed > 0:
            score += min(0.5, (added + removed) * 0.1)

        prop_removed = len(property_changes.get("removed", []))
        prop_changed = len(property_changes.get("changed", {}))
        if prop_removed + prop_changed > 0:
            score += min(0.4, (prop_removed + prop_changed) * 0.1)

        return min(1.0, score)

    # ── Utilities ───────────────────────────────────────────────────

    @staticmethod
    def _strip_comments(code: str) -> str:
        """Remove C# single-line and multi-line comments."""
        # Remove single-line comments
        code = re.sub(r"//.*$", "", code, flags=re.MULTILINE)
        # Remove multi-line comments
        code = re.sub(r"/\*.*?\*/", "", code, flags=re.DOTALL)
        return code
