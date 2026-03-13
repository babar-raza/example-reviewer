"""
Article structural validator.

Generic pre-discovery pass that checks markdown article files for structural issues:
- Broken code fences (C# code outside fenced blocks)
- Duplicate code blocks across articles in the same family
- Prose filename mismatches (filenames in prose vs. adjacent code)

These are reported as warnings and do not block the pipeline.

Also provides the ArticleValidator class for use in the full pipeline.
"""

from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ..utils.markdown_parser import parse_fenced_blocks

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Public data types
# ---------------------------------------------------------------------------

@dataclass
class ArticleIssue:
    """A single structural issue found in a markdown article."""

    file_path: str
    line_number: int
    issue_type: str   # "broken_fence" | "duplicate_content" | "filename_mismatch"
    description: str
    severity: str = "warning"  # always warning for now


# ---------------------------------------------------------------------------
# Standalone validation helpers
# ---------------------------------------------------------------------------

# Patterns that suggest C# code sitting outside a fenced block
_CSHARP_LINE_PATTERNS = (
    re.compile(r"^\s*using\s+[A-Za-z]"),
    re.compile(r"^\s*(?:public|private|internal|protected|static)?\s*(?:class|struct|interface|enum|record)\s+\w+"),
    re.compile(r"^\s*namespace\s+[A-Za-z]"),
    re.compile(r"^\s{4}(?:static|public|private|internal|protected)\s"),
)

_QUOTED_FILENAME_RE = re.compile(
    r'"([\w\s.\-]+\.(?:docx|pdf|xlsx|zip|cs|txt|html|odt|rtf))"', re.IGNORECASE
)


def _check_broken_fences(file_path: str, text: str) -> List[ArticleIssue]:
    """Return issues for C# code found outside fenced blocks."""
    lines = text.splitlines()
    in_fence = False
    issues: List[ArticleIssue] = []
    run_start: Optional[int] = None  # 1-based start of current raw-code run

    def _flush_run(start: int) -> None:
        issues.append(ArticleIssue(
            file_path=file_path,
            line_number=start,
            issue_type="broken_fence",
            description=f"C# code appears outside a fenced code block (starting at line {start}).",
        ))

    for idx, line in enumerate(lines, start=1):
        if line.startswith("```"):
            in_fence = not in_fence
            if run_start is not None:
                _flush_run(run_start)
                run_start = None
            continue
        if in_fence:
            if run_start is not None:
                _flush_run(run_start)
                run_start = None
            continue
        if any(pat.search(line) for pat in _CSHARP_LINE_PATTERNS):
            if run_start is None:
                run_start = idx
        else:
            if run_start is not None:
                _flush_run(run_start)
                run_start = None

    if run_start is not None:
        _flush_run(run_start)

    return issues


def _extract_fenced_blocks(text: str) -> List[Tuple[int, str]]:
    """Return list of (start_line_1based, content) for every fenced block."""
    lines = text.splitlines()
    blocks: List[Tuple[int, str]] = []
    in_fence = False
    fence_start = 0
    fence_lines: List[str] = []

    for idx, line in enumerate(lines, start=1):
        if line.startswith("```"):
            if not in_fence:
                in_fence = True
                fence_start = idx
                fence_lines = []
            else:
                in_fence = False
                blocks.append((fence_start, "\n".join(fence_lines)))
                fence_lines = []
        elif in_fence:
            fence_lines.append(line)

    return blocks


def _check_duplicate_blocks(
    file_paths: List[str],
    contents: Dict[str, str],
) -> List[ArticleIssue]:
    """Return issues for code blocks that appear in 2+ files (same family)."""
    # hash -> list of (file_path, start_line)
    hash_map: Dict[str, List[Tuple[str, int]]] = {}

    for fp in file_paths:
        text = contents.get(fp, "")
        for start_line, block_text in _extract_fenced_blocks(text):
            normalised = "\n".join(ln.strip() for ln in block_text.splitlines() if ln.strip())
            if not normalised:
                continue
            digest = hashlib.sha256(normalised.encode("utf-8")).hexdigest()
            hash_map.setdefault(digest, []).append((fp, start_line))

    issues: List[ArticleIssue] = []
    for digest, locations in hash_map.items():
        if len(locations) < 2:
            continue
        # Report from every participating file
        for fp, start_line in locations:
            others = [other_fp for other_fp, _ in locations if other_fp != fp]
            issues.append(ArticleIssue(
                file_path=fp,
                line_number=start_line,
                issue_type="duplicate_content",
                description=f"Code block duplicated in {others[0]}",
            ))

    return issues


def _check_filename_mismatches(file_path: str, text: str) -> List[ArticleIssue]:
    """Return issues for filenames in prose not found in adjacent code."""
    lines = text.splitlines()
    issues: List[ArticleIssue] = []

    # Split into sections by headings
    sections: List[Dict[str, Any]] = []
    current_heading_line = 0
    current_lines: List[Tuple[int, str]] = []  # (1-based line num, text)

    def _flush_section() -> None:
        if current_lines:
            sections.append({
                "heading_line": current_heading_line,
                "lines": list(current_lines),
            })

    for idx, line in enumerate(lines, start=1):
        if line.startswith("#"):
            _flush_section()
            current_heading_line = idx
            current_lines = [(idx, line)]
        else:
            current_lines.append((idx, line))

    _flush_section()

    for section in sections:
        sec_lines = section["lines"]
        sec_text = "\n".join(ln for _, ln in sec_lines)

        # Collect fenced blocks in this section
        in_fence = False
        fence_texts: List[str] = []
        current_fence: List[str] = []
        for _, ln in sec_lines:
            if ln.startswith("```"):
                if not in_fence:
                    in_fence = True
                    current_fence = []
                else:
                    in_fence = False
                    fence_texts.append("\n".join(current_fence))
                    current_fence = []
            elif in_fence:
                current_fence.append(ln)

        code_combined = "\n".join(fence_texts)
        code_files = set(_QUOTED_FILENAME_RE.findall(code_combined))
        if not code_files:
            continue

        # Collect prose lines (outside fences)
        prose_text_parts: List[Tuple[int, str]] = []
        in_fence2 = False
        for line_num, ln in sec_lines:
            if ln.startswith("```"):
                in_fence2 = not in_fence2
                continue
            if not in_fence2:
                prose_text_parts.append((line_num, ln))

        for line_num, ln in prose_text_parts:
            prose_files = set(_QUOTED_FILENAME_RE.findall(ln))
            mismatches = prose_files - code_files
            if mismatches:
                issues.append(ArticleIssue(
                    file_path=file_path,
                    line_number=line_num,
                    issue_type="filename_mismatch",
                    description=(
                        f"Prose references {sorted(mismatches)} "
                        f"but adjacent code uses {sorted(code_files)}."
                    ),
                ))

    return issues


def validate_article(file_path: str) -> List[ArticleIssue]:
    """Run all structural checks on a single article file."""
    try:
        text = Path(file_path).read_text(encoding="utf-8")
    except Exception as exc:
        return [ArticleIssue(
            file_path=file_path,
            line_number=0,
            issue_type="read_error",
            description=f"Could not read file: {exc}",
            severity="error",
        )]

    issues: List[ArticleIssue] = []
    issues.extend(_check_broken_fences(file_path, text))
    issues.extend(_check_filename_mismatches(file_path, text))
    return issues


def validate_family_articles(file_paths: List[str]) -> List[ArticleIssue]:
    """Run all checks including cross-article duplicate detection."""
    contents: Dict[str, str] = {}
    issues: List[ArticleIssue] = []

    for fp in file_paths:
        try:
            contents[fp] = Path(fp).read_text(encoding="utf-8")
        except Exception as exc:
            issues.append(ArticleIssue(
                file_path=fp,
                line_number=0,
                issue_type="read_error",
                description=f"Could not read file: {exc}",
                severity="error",
            ))
            continue
        issues.extend(_check_broken_fences(fp, contents[fp]))
        issues.extend(_check_filename_mismatches(fp, contents[fp]))

    if len(file_paths) > 1:
        issues.extend(_check_duplicate_blocks(file_paths, contents))

    return issues


class ArticleValidator:
    """Validate markdown article structure and optionally audit prose against code."""

    CODEISH_OUTSIDE_FENCE = (
        re.compile(r"^\s*using\s+[A-Z]\w*(?:\.[A-Z]\w*)*;"),
        re.compile(r"^\s*(?:public|private|internal|protected)?\s*(?:class|struct|interface|enum|record)\s+\w+"),
        re.compile(r"^\s*namespace\s+[A-Z]\w*(?:\.[A-Z]\w*)*"),
    )
    QUOTED_FILENAME = re.compile(r'["\']([^"\']+\.(?:docx|doc|pdf|odt|ott|rtf|txt|pfx))["\']', re.IGNORECASE)

    def validate_files(
        self,
        file_paths: List[str],
        *,
        audit_prose: bool = False,
        llm_service=None,
    ) -> Dict[str, Any]:
        reports: List[Dict[str, Any]] = []
        contents: Dict[str, str] = {}

        for file_path in file_paths:
            try:
                content = Path(file_path).read_text(encoding="utf-8")
            except Exception as exc:
                reports.append(
                    {
                        "file_path": file_path,
                        "errors": [f"read_error: {exc}"],
                        "warnings": [],
                        "prose_audit": [],
                    }
                )
                continue

            contents[file_path] = content
            warnings = []
            warnings.extend(self._validate_fences(file_path, content))
            warnings.extend(self._validate_filename_references(file_path, content))
            prose_audit = self._audit_prose(file_path, content, llm_service) if audit_prose else []
            reports.append(
                {
                    "file_path": file_path,
                    "errors": [],
                    "warnings": warnings,
                    "prose_audit": prose_audit,
                }
            )

        duplicate_warnings = self._detect_duplicate_content(contents)
        if duplicate_warnings:
            by_file = {report["file_path"]: report for report in reports}
            for warning in duplicate_warnings:
                for file_path in warning["file_paths"]:
                    if file_path in by_file:
                        by_file[file_path]["warnings"].append(warning)

        total_warnings = sum(len(report["warnings"]) for report in reports)
        total_prose = sum(len(report["prose_audit"]) for report in reports)
        return {
            "files_checked": len(file_paths),
            "files_with_warnings": sum(1 for report in reports if report["warnings"] or report["errors"]),
            "warnings": total_warnings,
            "prose_findings": total_prose,
            "reports": reports,
        }

    def extract_adjacent_prose_sections(self, content: str) -> List[Dict[str, Any]]:
        """Return code blocks paired with their nearest preceding prose in the same section."""
        blocks = parse_fenced_blocks(content)
        lines = content.splitlines()
        sections: List[Dict[str, Any]] = []

        for block in blocks:
            heading = self._find_heading_before(lines, block["fence_start_idx"])
            prose_text, prose_span = self._find_prose_before(lines, block["fence_start_idx"])
            if not prose_text:
                continue
            sections.append(
                {
                    "block_index": block["block_index"],
                    "section_heading": heading,
                    "prose_text": prose_text,
                    "prose_span": prose_span,
                    "code": block["content"],
                    "code_span": (block["fence_start_idx"], block["fence_end_idx"]),
                }
            )

        return sections

    def _validate_fences(self, file_path: str, content: str) -> List[Dict[str, Any]]:
        lines = content.splitlines()
        in_fence = False
        warnings: List[Dict[str, Any]] = []
        for idx, line in enumerate(lines, start=1):
            if line.startswith("```"):
                in_fence = not in_fence
                continue
            if in_fence:
                continue
            if any(pattern.search(line) for pattern in self.CODEISH_OUTSIDE_FENCE):
                warnings.append(
                    {
                        "type": "fence_warning",
                        "severity": "warning",
                        "line": idx,
                        "message": "Possible C# code appears outside a fenced code block.",
                    }
                )
        if in_fence:
            warnings.append(
                {
                    "type": "fence_warning",
                    "severity": "warning",
                    "line": len(lines),
                    "message": "Unclosed fenced code block detected at end of file.",
                }
            )
        return warnings

    def _validate_filename_references(self, file_path: str, content: str) -> List[Dict[str, Any]]:
        warnings: List[Dict[str, Any]] = []
        for section in self.extract_adjacent_prose_sections(content):
            prose_files = set(self.QUOTED_FILENAME.findall(section["prose_text"]))
            code_files = set(self.QUOTED_FILENAME.findall(section["code"]))
            mismatches = sorted(prose_files - code_files)
            if mismatches and code_files:
                warnings.append(
                    {
                        "type": "filename_mismatch",
                        "severity": "warning",
                        "line": section["prose_span"][0] + 1,
                        "message": (
                            f"Prose references {mismatches} but adjacent code uses {sorted(code_files)}."
                        ),
                    }
                )
        return warnings

    def _detect_duplicate_content(self, contents: Dict[str, str]) -> List[Dict[str, Any]]:
        file_blocks: Dict[str, set[str]] = {}
        for file_path, content in contents.items():
            blocks = parse_fenced_blocks(content)
            file_blocks[file_path] = {
                hashlib.sha256(self._normalize_code(block["content"]).encode("utf-8")).hexdigest()
                for block in blocks
                if block["content"].strip()
            }

        warnings: List[Dict[str, Any]] = []
        file_paths = sorted(file_blocks.keys())
        for idx, left in enumerate(file_paths):
            for right in file_paths[idx + 1:]:
                left_blocks = file_blocks[left]
                right_blocks = file_blocks[right]
                if not left_blocks or not right_blocks:
                    continue
                overlap = left_blocks & right_blocks
                ratio = len(overlap) / max(1, min(len(left_blocks), len(right_blocks)))
                if overlap and ratio >= 0.6:
                    warnings.append(
                        {
                            "type": "duplicate_content",
                            "severity": "warning",
                            "file_paths": [left, right],
                            "message": f"Code-block overlap ratio {ratio:.2f} exceeds 0.60 between the two articles.",
                        }
                    )
        return warnings

    def _audit_prose(self, file_path: str, content: str, llm_service) -> List[Dict[str, Any]]:
        if llm_service is None:
            return []

        findings: List[Dict[str, Any]] = []
        for section in self.extract_adjacent_prose_sections(content):
            try:
                result = llm_service.review_prose_against_code(
                    prose_text=section["prose_text"],
                    code_text=section["code"],
                    section_heading=section["section_heading"] or "",
                )
            except Exception as exc:
                logger.warning("Prose audit failed for %s: %s", file_path, exc)
                continue

            if not result.get("accurate", True):
                findings.append(
                    {
                        "type": "prose_mismatch",
                        "severity": "warning",
                        "line": section["prose_span"][0] + 1,
                        "message": result.get("issues", "Prose does not accurately describe the adjacent code."),
                        "suggested_prose": result.get("corrected_prose"),
                    }
                )
        return findings

    def _find_heading_before(self, lines: List[str], before_idx: int) -> Optional[str]:
        for idx in range(before_idx - 1, -1, -1):
            stripped = lines[idx].strip()
            if stripped.startswith("#"):
                return stripped.lstrip("#").strip()
        return None

    def _find_prose_before(self, lines: List[str], before_idx: int) -> Tuple[str, Tuple[int, int]]:
        start = before_idx - 1
        while start >= 0 and not lines[start].strip():
            start -= 1
        if start < 0:
            return "", (0, 0)

        prose_lines: List[str] = []
        end = start
        while start >= 0:
            stripped = lines[start].strip()
            if not stripped:
                break
            if stripped.startswith("#") or stripped.startswith("```") or stripped.startswith("{{%"):
                break
            prose_lines.append(lines[start])
            start -= 1
        prose_lines.reverse()
        prose_text = "\n".join(line.rstrip() for line in prose_lines).strip()
        return prose_text, (start + 1, end + 1)

    @staticmethod
    def _normalize_code(code: str) -> str:
        return "\n".join(line.strip() for line in code.splitlines() if line.strip())
