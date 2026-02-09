"""
Learned Patterns Service — Query, apply, and track learned fix patterns.

This service integrates with the auto-learn infrastructure to:
1. Query patterns from the learned_patterns table
2. Apply patterns to code (regex, using directive, code transform, LLM prompt)
3. Record pattern applications for feedback tracking
4. Retire low-performing patterns automatically

Part of the Auto-Learn Full LLM Integration (2026-02-06).
"""

import json
import logging
import re
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent.parent
DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "api_catalog.db"


@dataclass
class LearnedPattern:
    """Represents a learned fix pattern from the database."""

    id: int
    family: str
    pattern_type: str  # 'compile_error', 'runtime_error', 'infra_blocked', etc.
    error_signature: str  # CS0246, PASSWORD_ISSUE, etc.
    match_condition: Optional[str]  # Regex/condition to check before applying
    fix_template: str  # Human description (legacy)
    fix_type: str  # 'regex_replace', 'using_directive', 'code_transform', 'llm_prompt', 'template'
    fix_code: Optional[Dict[str, Any]]  # JSON with executable fix logic
    confidence: float
    auto_approved: bool
    priority: int  # Lower = executed first
    requires_llm: bool
    example_before: Optional[str]
    example_after: Optional[str]
    source: str  # 'bootstrap', 'auto_learn', 'manual'

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "LearnedPattern":
        """Create LearnedPattern from database row."""
        fix_code_raw = row["fix_code"]
        fix_code = None
        if fix_code_raw:
            try:
                fix_code = json.loads(fix_code_raw)
            except json.JSONDecodeError:
                logger.warning(f"Invalid fix_code JSON for pattern {row['id']}")

        return cls(
            id=row["id"],
            family=row["family"],
            pattern_type=row["pattern_type"],
            error_signature=row["error_signature"] or "",
            match_condition=row["match_condition"],
            fix_template=row["fix_template"],
            fix_type=row["fix_type"] or "template",
            fix_code=fix_code,
            confidence=row["confidence"],
            auto_approved=bool(row["auto_approved"]),
            priority=row["priority"] or 50,
            requires_llm=bool(row["requires_llm"]),
            example_before=row["example_before"],
            example_after=row["example_after"],
            source=row["source"] or "unknown",
        )


class LearnedPatternsService:
    """Service for querying and applying learned fix patterns."""

    # Registry of code transform functions (name -> callable)
    _transformers: Dict[str, Callable[[str], str]] = {}

    def __init__(self, family: str, db_path: Optional[Path] = None):
        """
        Initialize the service for a specific family.

        Args:
            family: Product family (e.g., 'zip')
            db_path: Path to api_catalog.db (defaults to data/api_catalog.db)
        """
        self.family = family
        self.db_path = db_path or DEFAULT_DB_PATH
        self._connection: Optional[sqlite3.Connection] = None

    def _get_connection(self) -> sqlite3.Connection:
        """Get or create database connection."""
        if self._connection is None:
            if not self.db_path.exists():
                raise FileNotFoundError(f"Database not found: {self.db_path}")
            self._connection = sqlite3.connect(str(self.db_path))
            self._connection.row_factory = sqlite3.Row
        return self._connection

    def close(self) -> None:
        """Close the database connection."""
        if self._connection:
            self._connection.close()
            self._connection = None

    def query_patterns(
        self,
        error_signature: str,
        min_confidence: float = 0.5,
        approved_only: bool = True,
        limit: int = 10,
    ) -> List[LearnedPattern]:
        """
        Query applicable patterns for an error signature.

        Args:
            error_signature: Error code/signature (e.g., 'CS0246', 'PASSWORD_ISSUE')
            min_confidence: Minimum confidence threshold (0.0-1.0)
            approved_only: Only return auto_approved patterns
            limit: Maximum patterns to return

        Returns:
            List of LearnedPattern, ordered by priority then confidence (desc)
        """
        conn = self._get_connection()

        query = """
            SELECT * FROM learned_patterns
            WHERE family = ?
              AND error_signature = ?
              AND confidence >= ?
        """
        params: List[Any] = [self.family, error_signature, min_confidence]

        if approved_only:
            query += " AND auto_approved = TRUE"

        query += " ORDER BY priority ASC, confidence DESC LIMIT ?"
        params.append(limit)

        try:
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()
            return [LearnedPattern.from_row(row) for row in rows]
        except sqlite3.Error as e:
            logger.error(f"Error querying patterns: {e}")
            return []

    def query_all_patterns(
        self,
        min_confidence: float = 0.0,
        approved_only: bool = False,
    ) -> List[LearnedPattern]:
        """Query all patterns for this family."""
        conn = self._get_connection()

        query = """
            SELECT * FROM learned_patterns
            WHERE family = ?
              AND confidence >= ?
        """
        params: List[Any] = [self.family, min_confidence]

        if approved_only:
            query += " AND auto_approved = TRUE"

        query += " ORDER BY priority ASC, confidence DESC"

        try:
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()
            return [LearnedPattern.from_row(row) for row in rows]
        except sqlite3.Error as e:
            logger.error(f"Error querying patterns: {e}")
            return []

    def apply_pattern(
        self,
        pattern: LearnedPattern,
        code: str,
        error_context: Optional[str] = None,
        llm_service: Optional[Any] = None,
    ) -> Tuple[str, bool, str]:
        """
        Apply a pattern to code.

        Args:
            pattern: The pattern to apply
            code: The code to fix
            error_context: Optional error message/context
            llm_service: LLM service instance (required for llm_prompt patterns)

        Returns:
            Tuple of (fixed_code, success, description)
        """
        if not pattern.fix_code and pattern.fix_type != "template":
            return code, False, f"Pattern {pattern.id} has no executable fix_code"

        try:
            if pattern.fix_type == "regex_replace":
                return self._apply_regex_replace(pattern, code)

            elif pattern.fix_type == "using_directive":
                return self._apply_using_directive(pattern, code)

            elif pattern.fix_type == "code_transform":
                return self._apply_code_transform(pattern, code)

            elif pattern.fix_type == "llm_prompt":
                if not llm_service:
                    return code, False, "LLM service required for llm_prompt patterns"
                return self._apply_llm_prompt(pattern, code, error_context, llm_service)

            else:
                # Template type - not executable, just descriptive
                return code, False, f"Pattern {pattern.id} is template-only (not executable)"

        except Exception as e:
            logger.error(f"Error applying pattern {pattern.id}: {e}")
            return code, False, f"Error: {str(e)}"

    def _apply_regex_replace(
        self, pattern: LearnedPattern, code: str
    ) -> Tuple[str, bool, str]:
        """Apply regex replacement pattern."""
        fix_code = pattern.fix_code
        if not fix_code:
            return code, False, "No fix_code"

        regex_pattern = fix_code.get("pattern")
        replacement = fix_code.get("replacement")

        if not regex_pattern or replacement is None:
            return code, False, "Missing pattern or replacement in fix_code"

        try:
            fixed_code, count = re.subn(regex_pattern, replacement, code)
            if count > 0:
                return fixed_code, True, f"Replaced {count} occurrence(s) via regex"
            return code, False, "Pattern did not match"
        except re.error as e:
            return code, False, f"Invalid regex: {e}"

    def _apply_using_directive(
        self, pattern: LearnedPattern, code: str
    ) -> Tuple[str, bool, str]:
        """Apply using directive insertion pattern."""
        fix_code = pattern.fix_code
        if not fix_code:
            return code, False, "No fix_code"

        directive = fix_code.get("directive")
        trigger_type = fix_code.get("trigger_type")

        if not directive:
            return code, False, "Missing directive in fix_code"

        # Check if directive already exists
        if directive in code:
            return code, False, f"Directive '{directive}' already present"

        # Check if trigger type is used in code (if specified)
        if trigger_type and trigger_type not in code:
            return code, False, f"Trigger type '{trigger_type}' not found in code"

        # Find insertion point (after last using statement or at beginning)
        lines = code.split("\n")
        insert_idx = 0
        for i, line in enumerate(lines):
            if line.strip().startswith("using ") and line.strip().endswith(";"):
                insert_idx = i + 1

        # Insert the directive
        lines.insert(insert_idx, directive)
        fixed_code = "\n".join(lines)
        return fixed_code, True, f"Added '{directive}'"

    def _apply_code_transform(
        self, pattern: LearnedPattern, code: str
    ) -> Tuple[str, bool, str]:
        """Apply registered code transform function."""
        fix_code = pattern.fix_code
        if not fix_code:
            return code, False, "No fix_code"

        transformer_name = fix_code.get("transformer")
        if not transformer_name:
            return code, False, "Missing transformer name in fix_code"

        transformer = self._transformers.get(transformer_name)
        if not transformer:
            return code, False, f"Unknown transformer: {transformer_name}"

        try:
            fixed_code = transformer(code)
            if fixed_code != code:
                return fixed_code, True, f"Applied transformer '{transformer_name}'"
            return code, False, "Transformer made no changes"
        except Exception as e:
            return code, False, f"Transformer error: {e}"

    def _apply_llm_prompt(
        self,
        pattern: LearnedPattern,
        code: str,
        error_context: Optional[str],
        llm_service: Any,
    ) -> Tuple[str, bool, str]:
        """Apply LLM-based fix using pattern's prompt template."""
        fix_code = pattern.fix_code
        if not fix_code:
            return code, False, "No fix_code"

        prompt_template = fix_code.get("prompt")
        system_prompt = fix_code.get("system_prompt", "Fix the following C# code.")

        if not prompt_template:
            return code, False, "Missing prompt in fix_code"

        # Build the prompt
        prompt = prompt_template.format(
            code=code,
            error=error_context or "",
            example_before=pattern.example_before or "",
            example_after=pattern.example_after or "",
        )

        try:
            response = llm_service.fix_code(
                code=code,
                error_logs=error_context or "",
                context_type="compile",
            )
            if response.success and response.content:
                return response.content, True, "LLM fix applied via pattern prompt"
            return code, False, f"LLM fix failed: {response.error}"
        except Exception as e:
            return code, False, f"LLM error: {e}"

    def record_application(
        self,
        pattern_id: int,
        example_id: str,
        run_id: str,
        success: bool,
    ) -> None:
        """
        Record that a pattern was applied (updates pattern_performance).

        Args:
            pattern_id: ID of the pattern applied
            example_id: ID of the example being fixed
            run_id: Current run ID
            success: Whether the fix compiled/ran successfully
        """
        conn = self._get_connection()
        now = datetime.now(timezone.utc).isoformat()

        try:
            # Update pattern_performance
            if success:
                conn.execute(
                    """
                    UPDATE pattern_performance
                    SET times_applied = times_applied + 1,
                        times_succeeded = times_succeeded + 1,
                        success_rate = CAST(times_succeeded + 1 AS REAL) / (times_applied + 1),
                        last_used = ?
                    WHERE pattern_id = ?
                    """,
                    (now, pattern_id),
                )
            else:
                conn.execute(
                    """
                    UPDATE pattern_performance
                    SET times_applied = times_applied + 1,
                        success_rate = CAST(times_succeeded AS REAL) / (times_applied + 1),
                        last_used = ?
                    WHERE pattern_id = ?
                    """,
                    (now, pattern_id),
                )

            # Also record in learning_history for audit
            conn.execute(
                """
                INSERT INTO learning_history
                (family, run_id, pattern_type, fix_applied, auto_approved, confidence, validation_status)
                VALUES (?, ?, 'pattern_application', ?, TRUE, NULL, ?)
                """,
                (
                    self.family,
                    run_id,
                    f"pattern_{pattern_id}:example_{example_id}",
                    "validated" if success else "failed",
                ),
            )

            conn.commit()
            logger.debug(
                f"Recorded pattern {pattern_id} application: success={success}"
            )
        except sqlite3.Error as e:
            logger.error(f"Error recording pattern application: {e}")

    def retire_low_performers(
        self,
        max_success_rate: float = 0.3,
        min_applications: int = 10,
    ) -> int:
        """
        Deactivate patterns below performance threshold.

        Args:
            max_success_rate: Retire if success_rate below this (0.0-1.0)
            min_applications: Only consider patterns with at least this many uses

        Returns:
            Number of patterns retired
        """
        conn = self._get_connection()

        # Find low performers
        low_performers = conn.execute(
            """
            SELECT pp.pattern_id, lp.error_signature, pp.success_rate, pp.times_applied
            FROM pattern_performance pp
            JOIN learned_patterns lp ON pp.pattern_id = lp.id
            WHERE pp.family = ?
              AND pp.times_applied >= ?
              AND pp.success_rate < ?
              AND lp.auto_approved = TRUE
            """,
            (self.family, min_applications, max_success_rate),
        ).fetchall()

        retired = 0
        for row in low_performers:
            pattern_id, signature, rate, applications = row
            logger.warning(
                f"Retiring pattern {pattern_id} ({signature}): "
                f"success_rate={rate:.1%} after {applications} applications"
            )
            conn.execute(
                """
                UPDATE learned_patterns
                SET auto_approved = FALSE,
                    source = 'retired_' || COALESCE(source, 'unknown'),
                    updated_at = datetime('now')
                WHERE id = ?
                """,
                (pattern_id,),
            )
            retired += 1

        conn.commit()
        return retired

    def get_pattern_performance(self, pattern_id: int) -> Optional[Dict[str, Any]]:
        """Get performance metrics for a pattern."""
        conn = self._get_connection()
        try:
            row = conn.execute(
                """
                SELECT * FROM pattern_performance WHERE pattern_id = ?
                """,
                (pattern_id,),
            ).fetchone()
            return dict(row) if row else None
        except sqlite3.Error as e:
            logger.error(f"Error getting pattern performance: {e}")
            return None

    @classmethod
    def register_transformer(cls, name: str, func: Callable[[str], str]) -> None:
        """
        Register a code transform function.

        Args:
            name: Name to reference in fix_code.transformer
            func: Function that takes code and returns transformed code
        """
        cls._transformers[name] = func
        logger.debug(f"Registered transformer: {name}")

    def store_pattern(
        self,
        error_signature: str,
        pattern_type: str,
        fix_type: str,
        fix_code: Dict[str, Any],
        fix_template: str,
        confidence: float = 0.5,
        auto_approved: bool = False,
        priority: int = 50,
        requires_llm: bool = False,
        example_before: Optional[str] = None,
        example_after: Optional[str] = None,
        source: str = "auto_learn",
    ) -> int:
        """
        Store a new learned pattern.

        Returns:
            The ID of the inserted pattern
        """
        conn = self._get_connection()

        try:
            cursor = conn.execute(
                """
                INSERT INTO learned_patterns
                (family, pattern_type, error_signature, fix_template, fix_type, fix_code,
                 confidence, auto_approved, priority, requires_llm, example_before, example_after, source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    self.family,
                    pattern_type,
                    error_signature,
                    fix_template,
                    fix_type,
                    json.dumps(fix_code) if fix_code else None,
                    confidence,
                    auto_approved,
                    priority,
                    requires_llm,
                    example_before,
                    example_after,
                    source,
                ),
            )
            pattern_id = cursor.lastrowid

            # Initialize performance tracking
            conn.execute(
                """
                INSERT INTO pattern_performance (pattern_id, family)
                VALUES (?, ?)
                """,
                (pattern_id, self.family),
            )

            conn.commit()
            logger.info(f"Stored new pattern {pattern_id}: {error_signature} ({fix_type})")
            return pattern_id

        except sqlite3.Error as e:
            logger.error(f"Error storing pattern: {e}")
            raise


def extract_error_signature(errors: List[str]) -> str:
    """
    Extract the primary error signature from a list of error messages.

    Args:
        errors: List of compiler/runtime error messages

    Returns:
        Error signature (e.g., 'CS0246', 'PASSWORD_ISSUE', 'MISSING_FILE')
    """
    for error in errors:
        # Try to extract CS error code
        cs_match = re.search(r"(CS\d{4})", error)
        if cs_match:
            return cs_match.group(1)

    # Check for common runtime patterns
    error_text = " ".join(errors).lower()
    if "password" in error_text:
        return "PASSWORD_ISSUE"
    if "file" in error_text and ("not found" in error_text or "missing" in error_text):
        return "MISSING_FILE"
    if "directory" in error_text and "not found" in error_text:
        return "MISSING_DIRECTORY"
    if "disposed" in error_text:
        return "DISPOSED_STREAM"

    return "UNKNOWN"


def extract_all_error_signatures(errors: List[str]) -> List[str]:
    """Extract all unique error signatures from a list of error messages."""
    signatures = []
    seen = set()
    for error in errors:
        cs_match = re.search(r"(CS\d{4})", error)
        if cs_match and cs_match.group(1) not in seen:
            signatures.append(cs_match.group(1))
            seen.add(cs_match.group(1))
    error_text = " ".join(errors).lower()
    if "password" in error_text and "PASSWORD_ISSUE" not in seen:
        signatures.append("PASSWORD_ISSUE")
    if ("file" in error_text and ("not found" in error_text or "missing" in error_text)
            and "MISSING_FILE" not in seen):
        signatures.append("MISSING_FILE")
    return signatures if signatures else ["UNKNOWN"]


def _register_default_transformers():
    """Register built-in transformers from semantic_microfixes."""
    try:
        from .semantic_microfixes import (
            fix_stream_disposal_pattern,
            fix_cs1503_rar_password_pattern,
            fix_cs1503_entries_string_index,
            fix_placeholder_archive_paths,
            fix_placeholder_directory_paths,
            fix_placeholder_passwords,
        )
        def _wrap(fn):
            def wrapper(code):
                result, _ = fn(code)
                return result
            return wrapper

        LearnedPatternsService.register_transformer("fix_stream_disposal", _wrap(fix_stream_disposal_pattern))
        LearnedPatternsService.register_transformer("fix_rar_password", _wrap(fix_cs1503_rar_password_pattern))
        LearnedPatternsService.register_transformer("fix_entries_string_index", _wrap(fix_cs1503_entries_string_index))
        LearnedPatternsService.register_transformer("fix_placeholder_archives", _wrap(fix_placeholder_archive_paths))
        LearnedPatternsService.register_transformer("fix_placeholder_dirs", _wrap(fix_placeholder_directory_paths))
        LearnedPatternsService.register_transformer("fix_placeholder_passwords", _wrap(fix_placeholder_passwords))
    except ImportError:
        pass

_register_default_transformers()
