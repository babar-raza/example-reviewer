"""Generic path-role classification and safety validation utilities."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class PathRole(str, Enum):
    """Semantic role of a file path used inside an example."""

    INPUT = "input"
    TEMPLATE = "template"
    FIXTURE = "fixture"
    OUTPUT = "output"
    UNKNOWN = "unknown"


class PathOperation(str, Enum):
    """Observed operation around a path literal in code."""

    READ = "read"
    WRITE = "write"
    UNKNOWN = "unknown"


SOURCE_LIKE_ROLES = frozenset({PathRole.INPUT, PathRole.TEMPLATE, PathRole.FIXTURE})

_OUTPUT_HINTS = {
    "dest",
    "destination",
    "export",
    "generated",
    "outfile",
    "output",
    "rendered",
    "result",
}
_INPUT_HINTS = {
    "data",
    "import",
    "in",
    "input",
    "load",
    "read",
    "source",
    "src",
}
_TEMPLATE_HINTS = {
    "blank",
    "empty",
    "master",
    "skeleton",
    "stub",
    "template",
}
_FIXTURE_HINTS = {
    "demo",
    "example",
    "fixture",
    "sample",
    "test",
}

_FILE_LITERAL_RE = re.compile(r'@?"([^"\r\n]+?\.[A-Za-z0-9]{1,8})"')
_WRITE_PATTERNS = (
    re.compile(r"\.Save\s*\(", re.IGNORECASE),
    re.compile(r"\bFile\.(?:WriteAllText|WriteAllBytes|WriteAllLines|Create)\s*\(", re.IGNORECASE),
    re.compile(r"\bDirectory\.CreateDirectory\s*\(", re.IGNORECASE),
    re.compile(r"\.(?:Export|Render|WriteTo)\w*\s*\(", re.IGNORECASE),
)
_READ_PATTERNS = (
    re.compile(r"\bnew\s+[A-Z][A-Za-z0-9_<>]*\s*\(", re.IGNORECASE),
    re.compile(r"\.(?:Load|Open|Import|Read|FromFile)\w*\s*\(", re.IGNORECASE),
    re.compile(r"\bFile\.(?:OpenRead|ReadAllText|ReadAllBytes|ReadAllLines)\s*\(", re.IGNORECASE),
)


@dataclass(frozen=True)
class PathLiteralOccurrence:
    """A file-like string literal found in code."""

    literal: str
    role: PathRole
    operation: PathOperation
    line_number: int
    line_text: str


@dataclass(frozen=True)
class PathRoleIssue:
    """A detected semantic path-role regression."""

    original_literal: str
    fixed_literal: str
    original_role: str
    fixed_role: str
    operation: str
    line_number: int
    message: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class PathRoleValidationResult:
    """Validation outcome for path-role preservation across code fixes."""

    valid: bool
    issues: List[PathRoleIssue] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "valid": self.valid,
            "issues": [issue.to_dict() for issue in self.issues],
        }


def classify_path_role(path: str, operation: Optional[PathOperation] = None) -> PathRole:
    """Classify a file path into a semantic role.

    Operation context wins when known because `doc.Save("foo.docx")` is an output
    even if the filename itself is generic.
    """

    op = operation or PathOperation.UNKNOWN
    if op == PathOperation.WRITE:
        return PathRole.OUTPUT

    normalized = path.replace("\\", "/")
    basename = Path(normalized).name.lower()
    stem = Path(basename).stem.lower()
    tokens = [token for token in re.split(r"[^a-z0-9]+", stem) if token]
    token_set = set(tokens)

    if token_set & _OUTPUT_HINTS:
        return PathRole.OUTPUT
    if token_set & _TEMPLATE_HINTS:
        return PathRole.TEMPLATE
    if token_set & _INPUT_HINTS:
        return PathRole.INPUT
    if token_set & _FIXTURE_HINTS:
        return PathRole.FIXTURE

    if op == PathOperation.READ:
        return PathRole.INPUT

    return PathRole.UNKNOWN


def crosses_source_output_boundary(left: PathRole, right: PathRole) -> bool:
    """Return True when a mapping crosses the source/output safety boundary."""

    return (left == PathRole.OUTPUT) != (right == PathRole.OUTPUT)


def is_safe_path_alias(canonical: str, alias: str) -> bool:
    """Return True when aliasing preserves the source/output boundary."""

    canonical_role = classify_path_role(canonical)
    alias_role = classify_path_role(alias)
    return not crosses_source_output_boundary(canonical_role, alias_role)


def sanitize_file_aliases(file_aliases: Dict[str, List[str]]) -> Tuple[Dict[str, List[str]], List[str]]:
    """Drop alias mappings that mix source-like names with output-like names."""

    sanitized: Dict[str, List[str]] = {}
    warnings: List[str] = []

    for canonical, aliases in (file_aliases or {}).items():
        safe_aliases: List[str] = []
        canonical_role = classify_path_role(canonical)
        for alias in aliases:
            alias_role = classify_path_role(alias)
            if is_safe_path_alias(canonical, alias):
                safe_aliases.append(alias)
                continue
            warnings.append(
                f"dropped unsafe alias '{alias}' ({alias_role.value}) for '{canonical}' ({canonical_role.value})"
            )
        sanitized[canonical] = safe_aliases

    return sanitized, warnings


def infer_operation_from_line(line: str) -> PathOperation:
    """Infer whether a code line is reading from or writing to a path."""

    for pattern in _WRITE_PATTERNS:
        if pattern.search(line):
            return PathOperation.WRITE
    for pattern in _READ_PATTERNS:
        if pattern.search(line):
            return PathOperation.READ
    return PathOperation.UNKNOWN


def extract_path_occurrences(code: str) -> List[PathLiteralOccurrence]:
    """Extract file-like string literals with inferred semantic roles."""

    occurrences: List[PathLiteralOccurrence] = []
    for line_number, line in enumerate(code.splitlines(), start=1):
        operation = infer_operation_from_line(line)
        for match in _FILE_LITERAL_RE.finditer(line):
            literal = match.group(1).strip()
            if "://" in literal:
                continue
            role = classify_path_role(literal, operation)
            occurrences.append(
                PathLiteralOccurrence(
                    literal=literal,
                    role=role,
                    operation=operation,
                    line_number=line_number,
                    line_text=line.strip(),
                )
            )
    return occurrences


def validate_path_role_preservation(original_code: str, fixed_code: str) -> PathRoleValidationResult:
    """Reject fixes that turn output targets into source-like/template-like paths."""

    issues: List[PathRoleIssue] = []
    original_occurrences = extract_path_occurrences(original_code)
    fixed_occurrences = extract_path_occurrences(fixed_code)

    for operation in (PathOperation.WRITE, PathOperation.READ, PathOperation.UNKNOWN):
        original_bucket = [occ for occ in original_occurrences if occ.operation == operation]
        fixed_bucket = [occ for occ in fixed_occurrences if occ.operation == operation]

        for original_occurrence, fixed_occurrence in zip(original_bucket, fixed_bucket):
            if original_occurrence.literal == fixed_occurrence.literal:
                continue

            original_name_role = classify_path_role(original_occurrence.literal)
            fixed_name_role = classify_path_role(fixed_occurrence.literal)
            original_effective_role = (
                original_name_role
                if original_name_role != PathRole.UNKNOWN
                else original_occurrence.role
            )
            fixed_effective_role = (
                fixed_name_role
                if fixed_name_role != PathRole.UNKNOWN
                else fixed_occurrence.role
            )

            if crosses_source_output_boundary(original_effective_role, fixed_effective_role):
                issues.append(
                    PathRoleIssue(
                        original_literal=original_occurrence.literal,
                        fixed_literal=fixed_occurrence.literal,
                        original_role=original_effective_role.value,
                        fixed_role=fixed_effective_role.value,
                        operation=operation.value,
                        line_number=fixed_occurrence.line_number,
                        message=(
                            f"Path role drift: '{original_occurrence.literal}' ({original_effective_role.value}) "
                            f"became '{fixed_occurrence.literal}' ({fixed_effective_role.value}) "
                            f"in a {operation.value} context"
                        ),
                    )
                )
                continue

            if operation == PathOperation.WRITE and fixed_name_role in SOURCE_LIKE_ROLES:
                issues.append(
                    PathRoleIssue(
                        original_literal=original_occurrence.literal,
                        fixed_literal=fixed_occurrence.literal,
                        original_role=original_effective_role.value,
                        fixed_role=fixed_name_role.value,
                        operation=operation.value,
                        line_number=fixed_occurrence.line_number,
                        message=(
                            f"Write target became source-like: '{fixed_occurrence.literal}' "
                            f"should remain an output path"
                        ),
                    )
                )

    return PathRoleValidationResult(valid=not issues, issues=issues)
