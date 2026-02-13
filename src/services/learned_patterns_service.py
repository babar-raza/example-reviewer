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

    def __init__(self, family: str, db_path: Optional[Path] = None, catalog=None):
        """
        Initialize the service for a specific family.

        Args:
            family: Product family (e.g., 'zip')
            db_path: Path to api_catalog.db (defaults to data/api_catalog.db)
            catalog: Optional API catalog service for LLM context
        """
        self.family = family
        self.db_path = db_path or DEFAULT_DB_PATH
        self._catalog = catalog  # NEW: Store catalog for LLM operations
        self._connection: Optional[sqlite3.Connection] = None
        # In-run cache: patterns that succeeded during this run get priority boost
        self._run_cache: Dict[str, List[int]] = {}  # error_signature -> [pattern_ids that succeeded]
        # Preloaded patterns cache: error_signature -> List[LearnedPattern]
        self._preloaded_cache: Dict[str, List[LearnedPattern]] = {}

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

    def preload_all_patterns(self) -> None:
        """
        Preload all patterns for this family into memory cache.

        This is called once after Phase A (discovery) to avoid repeated
        database queries during compilation/runtime loops.
        """
        try:
            conn = self._get_connection()
            query = """
                SELECT * FROM learned_patterns
                WHERE family = ?
                  AND auto_approved = TRUE
                ORDER BY error_signature, priority ASC, confidence DESC
            """
            cursor = conn.execute(query, [self.family])
            rows = cursor.fetchall()

            # Group by error_signature
            for row in rows:
                pattern = LearnedPattern.from_row(row)
                sig = pattern.error_signature
                if sig not in self._preloaded_cache:
                    self._preloaded_cache[sig] = []
                self._preloaded_cache[sig].append(pattern)

            logger.info(
                f"Preloaded {len(rows)} patterns for family '{self.family}' "
                f"({len(self._preloaded_cache)} unique signatures)"
            )
        except sqlite3.Error as e:
            logger.error(f"Error preloading patterns: {e}")

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
        # Check preloaded cache first
        if error_signature in self._preloaded_cache:
            patterns = self._preloaded_cache[error_signature]
            # Apply filters (cache is already auto_approved)
            filtered = [p for p in patterns if p.confidence >= min_confidence]
            filtered = filtered[:limit]

            # Apply in-run cache boost
            cached_ids = set(self._run_cache.get(error_signature, []))
            if cached_ids:
                boosted = [p for p in filtered if p.id in cached_ids]
                rest = [p for p in filtered if p.id not in cached_ids]
                filtered = boosted + rest
                if boosted:
                    logger.debug(
                        f"In-run cache boost: {len(boosted)} patterns for '{error_signature}'"
                    )

            return filtered

        # Fall back to database query if not preloaded
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
            patterns = [LearnedPattern.from_row(row) for row in rows]

            # Boost patterns that succeeded in this run (in-run cache)
            cached_ids = set(self._run_cache.get(error_signature, []))
            if cached_ids:
                boosted = [p for p in patterns if p.id in cached_ids]
                rest = [p for p in patterns if p.id not in cached_ids]
                patterns = boosted + rest
                if boosted:
                    logger.debug(
                        f"In-run cache boost: {len(boosted)} patterns for '{error_signature}'"
                    )

            return patterns
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
                catalog=self._catalog,  # NEW: Pass catalog for LLM context
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

            # Update in-run cache on success (for boosting in same run)
            if success:
                # Find which error_signature this pattern belongs to
                try:
                    row = conn.execute(
                        "SELECT error_signature FROM learned_patterns WHERE id = ?",
                        (pattern_id,)
                    ).fetchone()
                    if row:
                        sig = row["error_signature"]
                        if sig not in self._run_cache:
                            self._run_cache[sig] = []
                        if pattern_id not in self._run_cache[sig]:
                            self._run_cache[sig].append(pattern_id)
                            logger.debug(f"In-run cache: pattern {pattern_id} cached for '{sig}'")
                except sqlite3.Error:
                    pass

            logger.debug(
                f"Recorded pattern {pattern_id} application: success={success}"
            )
        except sqlite3.Error as e:
            logger.error(f"Error recording pattern application: {e}")

    def retire_patterns(self, policy) -> Dict[str, Any]:
        """
        Retire patterns based on retirement policy criteria.

        Evaluates patterns against multiple retirement criteria:
        1. Success rate below threshold (after min_attempts)
        2. Age exceeding max_age_days

        Args:
            policy: RetirementPolicyConfig instance with retirement criteria

        Returns:
            Dict with:
            - candidates_evaluated: Number of patterns evaluated
            - retired_count: Number of patterns retired
            - retired_patterns: List of retired pattern details
        """
        # Gate: Check if retirement enabled
        if not policy.enabled:
            logger.debug("Pattern retirement disabled in config")
            return {
                'candidates_evaluated': 0,
                'retired_count': 0,
                'retired_patterns': []
            }

        conn = self._get_connection()
        now = datetime.now(timezone.utc)

        # Query patterns eligible for retirement
        # Only consider auto_approved patterns with sufficient attempts
        query = """
            SELECT
                lp.id,
                lp.error_signature,
                lp.created_at,
                lp.source,
                pp.times_applied,
                pp.times_succeeded,
                pp.success_rate,
                pp.last_used
            FROM learned_patterns lp
            JOIN pattern_performance pp ON lp.id = pp.pattern_id
            WHERE lp.family = ?
              AND lp.auto_approved = TRUE
              AND pp.times_applied >= ?
        """

        try:
            candidates = conn.execute(query, [self.family, policy.min_attempts]).fetchall()
        except sqlite3.Error as e:
            logger.error(f"Error querying retirement candidates: {e}")
            return {
                'candidates_evaluated': 0,
                'retired_count': 0,
                'retired_patterns': []
            }

        retired_patterns = []

        for row in candidates:
            pattern_id = row[0]
            error_signature = row[1]
            created_at_str = row[2]
            source = row[3]
            times_applied = row[4]
            times_succeeded = row[5]
            success_rate = row[6]

            # Calculate age
            try:
                # Parse ISO format datetime
                if created_at_str:
                    # Handle both ISO format and SQLite datetime format
                    if 'T' in created_at_str:
                        created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                    else:
                        # SQLite datetime() format: "YYYY-MM-DD HH:MM:SS"
                        created_at = datetime.strptime(created_at_str, '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc)
                    age_days = (now - created_at).days
                else:
                    # No creation date, skip age check
                    age_days = 0
            except (ValueError, AttributeError) as e:
                logger.warning(f"Failed to parse created_at for pattern {pattern_id}: {e}")
                age_days = 0

            # Evaluate retirement criteria (OR logic)
            reasons = []

            # Criterion 1: Low success rate
            if success_rate <= policy.max_success_rate:
                reasons.append(
                    f"Low success rate: {success_rate:.1%} <= {policy.max_success_rate:.1%} "
                    f"({times_succeeded}/{times_applied} successes)"
                )

            # Criterion 2: Exceeded max age
            if age_days > policy.max_age_days:
                reasons.append(
                    f"Exceeded max age: {age_days} days > {policy.max_age_days} days"
                )

            # Retire if any criterion met
            if reasons:
                reason_str = "; ".join(reasons)

                if policy.dry_run:
                    logger.info(
                        f"[DRY-RUN] Would retire pattern {pattern_id} "
                        f"({error_signature}): {reason_str}"
                    )
                else:
                    # Soft delete: set auto_approved=FALSE, mark source as retired
                    try:
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
                        logger.info(
                            f"Retired pattern {pattern_id} ({error_signature}): {reason_str}"
                        )
                    except sqlite3.Error as e:
                        logger.error(f"Error retiring pattern {pattern_id}: {e}")
                        continue

                retired_patterns.append({
                    'pattern_id': pattern_id,
                    'error_signature': error_signature,
                    'reason': reason_str,
                    'performance': {
                        'success_rate': success_rate,
                        'times_applied': times_applied,
                        'times_succeeded': times_succeeded,
                        'age_days': age_days
                    }
                })

        # Commit changes if not dry-run
        if not policy.dry_run and retired_patterns:
            try:
                conn.commit()
                logger.info(f"Committed retirement of {len(retired_patterns)} patterns")
            except sqlite3.Error as e:
                logger.error(f"Error committing retirements: {e}")
                conn.rollback()

        return {
            'candidates_evaluated': len(candidates),
            'retired_count': len(retired_patterns),
            'retired_patterns': retired_patterns
        }

    def retire_low_performers(
        self,
        max_success_rate: float = 0.3,
        min_applications: int = 10,
    ) -> int:
        """
        DEPRECATED: Use retire_patterns() with RetirementPolicyConfig instead.

        Deactivate patterns below performance threshold.

        Args:
            max_success_rate: Retire if success_rate below this (0.0-1.0)
            min_applications: Only consider patterns with at least this many uses

        Returns:
            Number of patterns retired
        """
        logger.warning(
            "retire_low_performers() is deprecated. "
            "Use retire_patterns() with RetirementPolicyConfig instead."
        )

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
        Error signature (e.g., 'CS0246', 'PASSWORD_ISSUE', 'NullReferenceException', 'MISSING_FILE:document.docx')
    """
    error_text = " ".join(errors)

    # Priority 1: CS error codes (compile-time)
    for error in errors:
        cs_match = re.search(r"(CS\d{4})", error)
        if cs_match:
            return cs_match.group(1)

    # Priority 2: Exception types (runtime)
    exc_match = re.search(r'\b(\w+Exception):', error_text)
    if exc_match:
        exception_type = exc_match.group(1)

        # Special handling for FileNotFoundException - include filename
        if exception_type == 'FileNotFoundException':
            file_match = re.search(r"'([^']+\.\w+)'", error_text)
            if file_match:
                return f"MISSING_FILE:{file_match.group(1)}"

        return exception_type

    # Priority 3: Infrastructure patterns (legacy)
    error_text_lower = error_text.lower()
    if "password" in error_text_lower:
        return "PASSWORD_ISSUE"
    if "file" in error_text_lower and ("not found" in error_text_lower or "missing" in error_text_lower):
        return "MISSING_FILE"
    if "directory" in error_text_lower and "not found" in error_text_lower:
        return "MISSING_DIRECTORY"
    if "disposed" in error_text_lower:
        return "DISPOSED_STREAM"

    return "RUNTIME_ERROR"


def extract_all_error_signatures(errors: List[str]) -> List[str]:
    """Extract all unique error signatures from a list of error messages."""
    signatures = []
    seen = set()

    # Extract CS error codes
    for error in errors:
        cs_match = re.search(r"(CS\d{4})", error)
        if cs_match and cs_match.group(1) not in seen:
            signatures.append(cs_match.group(1))
            seen.add(cs_match.group(1))

    error_text = " ".join(errors)

    # Extract runtime exceptions
    for exc_match in re.finditer(r'\b(\w+Exception):', error_text):
        exception_type = exc_match.group(1)
        if exception_type not in seen:
            # Special handling for FileNotFoundException
            if exception_type == 'FileNotFoundException':
                file_match = re.search(r"'([^']+\.\w+)'", error_text)
                if file_match:
                    sig = f"MISSING_FILE:{file_match.group(1)}"
                    if sig not in seen:
                        signatures.append(sig)
                        seen.add(sig)
                        continue
            signatures.append(exception_type)
            seen.add(exception_type)

    # Infrastructure patterns (legacy)
    error_text_lower = error_text.lower()
    if "password" in error_text_lower and "PASSWORD_ISSUE" not in seen:
        signatures.append("PASSWORD_ISSUE")
    if ("file" in error_text_lower and ("not found" in error_text_lower or "missing" in error_text_lower)
            and "MISSING_FILE" not in seen):
        signatures.append("MISSING_FILE")

    return signatures if signatures else ["RUNTIME_ERROR"]


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
